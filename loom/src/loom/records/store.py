"""The Records object: everything durable that is not source, loaded once per query, and the states, causes, facts, and derived states computed from it (book 7.6, 7.9, 7.10).

`compute` is pure over the scan result and the records; `apply` writes those results into a manifest and the diffs directory.
"""

from __future__ import annotations

import difflib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.ai.runs import thread_id
from loom.clock import today
from loom.records.annotations import ASKING, Annotation, Record, load_records
from loom.records.ledger import AcceptRow, latest_rows, read_ledger
from loom.records.selectors import resolve_selector
from loom.records.snapshots import read_snapshot
from loom.render.manifest import key_hash, own_text
from loom.scan.hashing import hash_text, normalize
from loom.scan.model import Diagnostic
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult


@dataclass
class Cause:
    kind: str
    id: str | None = None
    when: str | None = None
    before: str | None = None  # snapshot hash
    after: str | None = None  # current hash
    via: str | None = None  # direct dependency through which an indirect edit is reached

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind, "diff": None}
        if self.id:
            d["id"] = self.id
        if self.when:
            d["when"] = self.when
        if self.via:
            d["via"] = self.via
        return d


@dataclass
class KeyState:
    key: str
    state: str  # draft | accepted | incomplete
    row: AcceptRow | None = None
    fresh: bool = True
    causes: list[Cause] = field(default_factory=list)
    latest_current: Annotation | None = None
    latest_any: Annotation | None = None
    open: dict[str, int] = field(default_factory=dict)
    detached: int = 0
    previous_key_match: str | None = None

    @property
    def label(self) -> str:
        if self.state == "accepted" and not self.fresh:
            return "accepted, stale"
        return self.state


def wid_path(target: str) -> str:
    """The store directory of a work identifier, or '' when the target is not one."""
    from loom.refs.identity import parse

    wid = parse(target)
    return wid.path if wid else ""


@dataclass
class ResolvedAnnotation:
    annotation: Annotation
    record: Record
    span: tuple[int, int] | None  # in the target's own text (concatenated pieces); on a page, offsets into its text
    detached: bool
    recorded: bool = True  # the text this was written against is still recoverable: it is the current text, or frozen
    work: str = ""  # the citekey, when the target is a page of a cited work rather than a key (plan 0.13 item 2)


class Records:
    def __init__(self, root: Path, history_dir: Path | None = None) -> None:
        self.root = root
        self.history_dir = history_dir
        self.rows = read_ledger(root)
        self.latest = latest_rows(self.rows)
        self.records, self.problems = load_records(root)
        self._resolved_cache: tuple[ScanResult, list[ResolvedAnnotation]] | None = None
        self._snapshot_seen: dict[str, bool] = {}

    # ---- text helpers --------------------------------------------------------

    @staticmethod
    def own_pieces(result: ScanResult, node: NodeRec) -> tuple[str, list[tuple[int, int, int]]]:
        """Own text without child markers plus a map [(concat_start, file_offset, length)] for selector spans."""
        src = result.files[node.file]
        pieces: list[tuple[int, int, int]] = []
        parts: list[str] = []
        pos = 0
        for a, b in node.own:
            parts.append(src.text[a:b])
            pieces.append((pos, a, b - a))
            pos += b - a
        return "".join(parts), pieces

    @staticmethod
    def to_file_span(pieces: list[tuple[int, int, int]], span: tuple[int, int]) -> tuple[int, int] | None:
        a, b = span
        for cstart, fstart, length in pieces:
            if cstart <= a < cstart + length:
                end = fstart + (b - cstart)
                if b <= cstart + length:
                    return fstart + (a - cstart), end
                return fstart + (a - cstart), fstart + length
        return None

    # ---- hashes ---------------------------------------------------------------

    @staticmethod
    def preamble_hash(result: ScanResult, master: str | None) -> str:
        closure = result.closures.get(master) if master else None
        return hash_text(closure.raw_text()) if closure else ""

    @staticmethod
    def closure_hashes(result: ScanResult, key: str) -> dict[str, str]:
        assert result.graph is not None
        n = result.nodes[key]
        stmt = n.of if n.kind == "proof" and n.of else key
        out: dict[str, str] = {}
        for k in result.graph.closure(key):
            if k == stmt and n.kind != "proof":
                continue
            if k in result.nodes and result.nodes[k].kind in ("environment", "section"):
                out[k] = key_hash(result, k)
        return out

    @staticmethod
    def direct_keys(result: ScanResult, key: str) -> list[str]:
        assert result.graph is not None
        n = result.nodes[key]
        direct = result.graph.direct(key)
        if n.kind == "proof" and n.of and n.of not in direct:
            direct.append(n.of)
        return direct

    # ---- states -----------------------------------------------------------------

    def key_states(self, result: ScanResult) -> dict[str, KeyState]:
        states: dict[str, KeyState] = {}
        kinds = ("environment", "proof", "section")
        current_hashes = {k: key_hash(result, k) for k, n in result.nodes.items() if n.kind in kinds}
        for key, n in result.nodes.items():
            if n.kind not in kinds:
                continue
            row = self.latest.get(key)
            ks = KeyState(key=key, state="draft", row=row)
            if n.kind == "section":
                # A section is a container, not a claim: no state, and `loom accept` refuses one. It is carried here
                # only so that its review facts are computed, because `loom comment` accepts a section as a target
                # and a finding filed on one was stored and then shown nowhere (DR-172).
                ks.state = ""
                states[key] = ks
                continue
            if n.incomplete:
                ks.state = "incomplete"
            if n.file.endswith(".proposed.tex"):
                # A proposal: read from a page and rendered by an agent, and not yet vouched for by anyone. It lives
                # in a file no bundle inputs, so it cannot be cited or compiled; `loom refs verify` moves it into the
                # digest and records the row that makes it verified (plan 0.12 §5.1, digest contract §9.9).
                ks.state = "proposed"
                states[key] = ks
                continue
            if row is not None:
                ks.state = "incomplete" if n.incomplete else "accepted"
                current = current_hashes[key]
                closure_now = self.closure_hashes(result, key)
                if row.text != current:
                    # What moved under an external node is loom's copy of somebody else's theorem, not the author's
                    # own text, and the cause is the useful half of the seal: the transcription you checked has moved.
                    moved = "transcription-changed" if n.external else "own-text-changed"
                    ks.causes.append(Cause(moved, before=row.text, after=current, when=_when(result, n)))
                if row.basis and n.kind == "environment" and row.basis != n.basis:
                    ks.causes.append(Cause("basis-changed", before=row.basis, after=n.basis, when=_when(result, n)))
                direct_now = {d: closure_now[d] for d in self.direct_keys(result, key) if d in closure_now}
                accepted_direct = (
                    row.direct if row.direct_recorded else {d: row.closure[d] for d in direct_now if d in row.closure}
                )
                for dep, h in accepted_direct.items():
                    if dep not in result.nodes:
                        ks.causes.append(Cause("dependency-removed", id=dep, before=h))
                    elif direct_now.get(dep) != h:
                        ks.causes.append(
                            Cause(
                                "dependency-changed",
                                id=dep,
                                before=h,
                                after=direct_now.get(dep),
                                when=_when(result, result.nodes[dep]),
                            )
                        )
                for dep in direct_now:
                    if dep not in accepted_direct and (row.direct_recorded or dep not in row.closure):
                        ks.causes.append(Cause("dependency-added", id=dep))
                if not row.direct_recorded:
                    # An old row does not say which closure member was direct. A removed member
                    # cannot be reached from today's graph, so retain that conservative warning.
                    for dep, h in row.closure.items():
                        if dep not in closure_now and dep not in accepted_direct:
                            ks.causes.append(Cause("dependency-removed", id=dep, before=h))
                pre = self.preamble_hash(result, row.master or result.default_master)
                if row.preamble and row.preamble != pre:
                    ks.causes.append(Cause("preamble-changed", before=row.preamble, after=pre))
            states[key] = ks
        # A stable direct dependency is an acceptance boundary. Its own unresolved edit
        # propagates; reaccepting it without changing its text resolves the indirect cause.
        visited: set[str] = set()

        def propagate(key: str, visiting: set[str]) -> None:
            if key in visited or key in visiting or key not in states:
                return
            visiting.add(key)
            ks = states[key]
            if ks.row and result.graph:
                for dep in self.direct_keys(result, key):
                    if dep not in result.nodes or dep not in ks.row.closure:
                        continue
                    if current_hashes.get(dep) != ks.row.closure[dep]:
                        continue  # the direct dependency already has its own cause
                    upstream = states.get(dep)
                    if upstream and upstream.row:
                        propagate(dep, visiting)
                        origins = [c.id for c in upstream.causes if c.kind == "dependency-changed" and c.id]
                    else:
                        origins = [
                            ancestor
                            for ancestor in result.graph.closure(dep)
                            if ancestor != dep
                            and ancestor in ks.row.closure
                            and current_hashes.get(ancestor) != ks.row.closure[ancestor]
                        ]
                    for origin in origins:
                        if origin == key or origin not in result.nodes or any(c.id == origin for c in ks.causes):
                            continue
                        ks.causes.append(
                            Cause(
                                "dependency-changed",
                                id=origin,
                                via=dep,
                                before=ks.row.closure.get(origin),
                                after=current_hashes.get(origin),
                                when=_when(result, result.nodes[origin]),
                            )
                        )
                ks.fresh = not ks.causes
            visiting.remove(key)
            visited.add(key)

        for key in states:
            propagate(key, set())
        self._observe_causes(states)
        self._review_facts(result, states, current_hashes)
        self._previous_key_matches(result, states, current_hashes)
        return states

    def _observe_causes(self, states: dict[str, KeyState]) -> None:
        """Remember the first scan that saw each unresolved cause, once per acceptance epoch."""
        path = self.root / ".loom" / "review-observations.json"
        try:
            old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except (OSError, ValueError):
            old = {}
        if not isinstance(old, dict):
            old = {}
        active: dict[str, str] = {}
        for key, state in states.items():
            if not state.row:
                continue
            for cause in state.causes:
                identity = json.dumps(
                    [key, state.row.date, state.row.text, cause.kind, cause.id, cause.via],
                    separators=(",", ":"),
                )
                first = old.get(identity)
                active[identity] = first if isinstance(first, str) else today()
                cause.when = active[identity]
        if active != old:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(active, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(temporary, path)

    def _review_facts(self, result: ScanResult, states: dict[str, KeyState], current: dict[str, str]) -> None:
        for res in self.resolved(result):
            a = res.annotation
            ks = states.get(a.target_key)
            if ks is None or res.record.discarded:
                continue
            # what awaits an answer, which is what a count is for: a note or a confirmation records rather than asks
            if a.in_reply_to is None and a.status == "open" and a.kind in ASKING:
                ks.open[a.kind] = ks.open.get(a.kind, 0) + 1
            if res.detached:
                ks.detached += 1
            if a.target_hash == current.get(a.target_key):
                if ks.latest_current is None or a.created > ks.latest_current.created:
                    ks.latest_current = a
            if ks.latest_any is None or a.created > ks.latest_any.created:
                ks.latest_any = a

    def _previous_key_matches(self, result: ScanResult, states: dict[str, KeyState], current: dict[str, str]) -> None:
        by_hash: dict[str, list[str]] = {}
        for k, h in current.items():
            by_hash.setdefault(h, []).append(k)
        for key, row in self.latest.items():
            ks = states.get(key)
            if ks is not None and ks.fresh:
                continue
            for cand in by_hash.get(row.text, []):
                cn = result.nodes.get(cand)
                if (
                    cn is not None
                    and cn.kind == "proof"
                    and cand != key
                    and cand in states
                    and states[cand].row is None
                ):
                    states[cand].previous_key_match = key

    def derived(self, result: ScanResult, states: dict[str, KeyState]) -> dict[str, dict[str, bool]]:
        assert result.graph is not None
        proved: dict[str, bool] = {}
        for key, n in result.nodes.items():
            if n.kind != "environment":
                continue
            s = states.get(key)
            ok = bool(s and s.state == "accepted" and s.fresh and not n.incomplete)
            good_proof = any(
                states.get(p) and states[p].state == "accepted" and states[p].fresh and not result.nodes[p].incomplete
                for p in n.proofs
            )
            proved[key] = ok and (
                (n.basis == "local-proof" and (good_proof or n.inline_proof)) or n.basis in ("expository", "assumption")
            )
        settled: dict[str, bool] = {}
        visiting: set[str] = set()

        def is_settled(key: str) -> bool:
            if key in settled:
                return settled[key]
            n = result.nodes.get(key)
            if n is None:
                return False
            # A section can be referenced as context, but has no statement or proof
            # to accept. Keep it in dependency tracking without making it a proof obligation.
            if n.kind == "section":
                settled[key] = True
                return True
            if n.basis == "cited-result":
                settled[key] = True
                return True
            if key in visiting:
                return False
            visiting.add(key)
            ok = proved.get(key, False)
            if ok:
                assert result.graph is not None
                deps = set(result.graph.closure(key)) - {key}
                for p in n.proofs:
                    st = states.get(p)
                    if st and st.state == "accepted" and st.fresh:
                        deps |= set(result.graph.closure(p)) - {key}
                ok = all(is_settled(d) for d in deps)
            visiting.discard(key)
            settled[key] = ok
            return ok

        out: dict[str, dict[str, bool]] = {}
        for key, n in result.nodes.items():
            if n.kind == "environment":
                out[key] = {"proved": proved.get(key, False), "settled": is_settled(key)}
        return out

    # ---- annotations -----------------------------------------------------------

    def resolved(self, result: ScanResult) -> list[ResolvedAnnotation]:
        if self._resolved_cache is not None and self._resolved_cache[0] is result:
            return self._resolved_cache[1]
        out: list[ResolvedAnnotation] = []
        texts: dict[str, str] = {}
        works: dict[str, str] = {}
        for rec in self.records:
            for a in rec.annotations:
                if a.anchor is not None:
                    out.append(self._on_page(result, a, rec, works))
                    continue
                n = result.nodes.get(a.target_key)
                if n is None:
                    region = result.assembly.regions.get(a.target_key)
                    n = result.nodes.get(region.container) if region else None
                if n is None:
                    out.append(ResolvedAnnotation(a, rec, None, True, self._recorded(a, None)))
                    continue
                if n.key not in texts:
                    texts[n.key], _ = self.own_pieces(result, n)
                kept = self._recorded(a, texts[n.key])
                if a.selector is None:
                    out.append(ResolvedAnnotation(a, rec, None, False, kept))
                    continue
                span = resolve_selector(texts[n.key], a.selector)
                out.append(ResolvedAnnotation(a, rec, span, span is None, kept))
        self._resolved_cache = (result, out)
        return out

    def _on_page(self, result: ScanResult, a: Annotation, rec: Record, works: dict[str, str]) -> ResolvedAnnotation:
        """A note on a page of a cited work, resolved against the store rather than against a key's text.

        `recorded` is whether the artifact the anchor names is the one in the store -- copy-once makes that the normal case for ever. `detached` is a text anchor whose quotation no longer locates in the page's committed text; a box is never detached, because the rectangles are the record. The target is the work's identifier, and the citekey is looked up through the bibliography so that a renamed citekey changes nothing.
        """
        from loom.refs.identity import identify, parse
        from loom.refs.pages import read_map, read_page, storage_root
        from loom.refs.search import locate_offsets

        assert a.anchor is not None
        if a.target_key not in works:
            wid = parse(a.target_key)
            found = ""
            for ck, entry in result.bib.items():
                if wid and any((w.scheme, w.value) == (wid.scheme, wid.value) for w in identify(entry)):
                    found = ck
                    break
            works[a.target_key] = found
        ck = works[a.target_key]
        if not ck or not wid_path(a.target_key):
            return ResolvedAnnotation(a, rec, None, True, False, ck)
        home = storage_root(self.root) / wid_path(a.target_key)
        m = read_map(home)
        recorded = m is not None and bool(m.sha256) and m.sha256 == a.anchor.sha256
        if a.anchor.basis != "text":
            return ResolvedAnnotation(a, rec, None, False, recorded, ck)
        page = read_page(home, a.anchor.page)
        span = locate_offsets(page, a.selector.exact) if page and a.selector and a.selector.exact else None
        return ResolvedAnnotation(a, rec, span, span is None, recorded, ck)

    def _recorded(self, a: Annotation, current: str | None) -> bool:
        """Whether the text `a` was written against can still be shown: it is the current text, or a frozen snapshot.

        Two edits between two scans lose the text in between (`lastseen.py`), and the quote may still match the new text, so `detached` does not answer this. An annotation with no `against` made no claim about a version and counts as recorded.
        """
        want = a.target_hash
        if not want:
            return True
        if current is not None and hash_text(current) == want:
            return True
        if want not in self._snapshot_seen:
            self._snapshot_seen[want] = read_snapshot(self.root, want, self.history_dir) is not None
        return self._snapshot_seen[want]

    # ---- diagnostics ------------------------------------------------------------

    def diagnostics(self, result: ScanResult, states: dict[str, KeyState]) -> list[Diagnostic]:
        diags: list[Diagnostic] = []
        for p in self.problems:
            diags.append(Diagnostic("warning", "loom:foreign-annotations", f"not a valid review record: {p}", []))
        detached: dict[str, int] = {}
        for res in self.resolved(result):
            if res.detached and not res.record.discarded:
                detached[res.annotation.target_key] = detached.get(res.annotation.target_key, 0) + 1
        for key, n in sorted(detached.items()):
            diags.append(
                Diagnostic(
                    "info",
                    "loom:detached-annotation",
                    f"{n} annotation(s) on {key} no longer match its text",
                    [],
                    [key],
                )
            )
        for key in sorted(self.latest):
            if key not in result.nodes:
                diags.append(
                    Diagnostic(
                        "info",
                        "loom:retired-ledger-key",
                        f"the ledger has rows for {key}, which no longer exists",
                        [],
                        [key],
                    )
                )
        for key, ks in states.items():
            if ks.previous_key_match:
                diags.append(
                    Diagnostic(
                        "info",
                        "loom:previous-key-match",
                        f"acceptance recorded under {ks.previous_key_match} matches the text of {key}; re-accept to confirm",
                        [],
                        [key],
                    )
                )
        return diags

    # ---- diffs -------------------------------------------------------------------

    def diff_for(self, result: ScanResult, cause: Cause, key: str) -> str | None:
        if cause.kind == "basis-changed":
            return None  # a source directive changed; no accepted text snapshot represents the old classification
        if not cause.before:
            return None
        before = read_snapshot(self.root, cause.before, self.history_dir)
        if before is None:
            return None
        target = cause.id or key
        n = result.nodes.get(target)
        if cause.kind == "preamble-changed":
            closure = result.closures.get(result.default_master) if result.default_master else None
            after = normalize(closure.raw_text()) if closure else ""
        elif n is None:
            after = ""
        else:
            after = normalize(own_text(result, n))
        return "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"accepted/{target}",
                tofile=f"current/{target}",
            )
        )

    # ---- manifest ---------------------------------------------------------------

    def apply(self, result: ScanResult, manifest: dict[str, Any], build_dir: Path | None = None) -> None:
        states = self.key_states(result)
        derived = self.derived(result, states)
        diffs_dir = build_dir / "diffs" if build_dir else None
        for key, entry in manifest["keys"].items():
            ks = states.get(key)
            if ks is None:
                continue
            entry["state"] = ks.state
            if ks.row is not None:
                acc: dict[str, Any] = {"author": ks.row.author, "date": ks.row.date, "fresh": ks.fresh}
                if not ks.fresh:
                    causes = []
                    for c in ks.causes:
                        d = c.to_dict()
                        if c.kind == "dependency-changed" and c.id and not c.via and result.graph:
                            from loom.render.convert import slug

                            edge = next(
                                (
                                    e
                                    for e in result.graph.out.get(key, [])
                                    if e.offset >= 0 and e.via != "uses" and result.graph.statement_key(e.to) == c.id
                                ),
                                None,
                            )
                            if edge:
                                label_target = result.assembly.labels.get(edge.label, edge.to)
                                d["citation"] = f"cite-{slug(edge.file)}-{edge.offset}-{slug(label_target)}"
                        text = self.diff_for(result, c, key)
                        if text and diffs_dir is not None:
                            name = f"{_slug(key)}-{c.kind}{'-' + _slug(c.id) if c.id else ''}.diff"
                            diffs_dir.mkdir(parents=True, exist_ok=True)
                            (diffs_dir / name).write_text(text, encoding="utf-8")
                            d["diff"] = f"diffs/{name}"
                        causes.append(d)
                    acc["causes"] = causes
                entry["acceptance"] = acc
            entry["reviews"] = {
                "latest_current": _fact(ks.latest_current),
                "latest_any": _fact(ks.latest_any),
                "open": dict(ks.open),
                "detached": ks.detached,
            }
            entry["previous_key_match"] = ks.previous_key_match
        for key, entry in manifest["nodes"].items():
            ks = states.get(key)
            if ks is not None:
                entry["state"] = ks.state
            if key in derived:
                entry["derived"] = derived[key]
        anns: dict[str, Any] = {}
        for res in self.resolved(result):
            a = res.annotation
            anns[a.id] = {
                "id": a.id,
                "author": {"kind": a.author_kind, "id": a.author_id, "label": _author_label(a)},
                "created": a.created,
                # a note on a page of a cited work names the work by identifier; the citekey and the page travel
                # beside it so a viewer needs no lookup to say where it is (plan 0.13 item 2)
                "target": {
                    "key": a.target_key,
                    "hash": a.target_hash,
                    "work": res.work or None,
                    "page": a.anchor.page if a.anchor else None,
                },
                "basis": a.anchor.basis if a.anchor else None,
                "kind": a.kind,
                "body_html": render_markdown(a.body),
                "status": a.status,
                "in_reply_to": a.in_reply_to,
                "anchored": (a.selector is not None or a.anchor is not None) and not res.detached and res.recorded,
                "detached": res.detached,
                "recorded": res.recorded,
                "quote": a.selector.exact if a.selector else None,
                "severity": a.severity,
                "payload": a.payload,
                "placement": a.placement,
                "discard_reason": a.discard_reason,
                # the run or comment session this belongs to; with one log it is the grouping key a viewer needs,
                # which a file path no longer is, and it is the thread's own id so the two can be joined
                "run": thread_id(res.record.rel),
                "record": res.record.rel,
                "discarded": res.record.discarded,
            }
        manifest["annotations"] = anns
        manifest["diagnostics"].extend(d.to_dict() for d in self.diagnostics(result, states))


def _fact(a: Annotation | None) -> dict[str, Any] | None:
    if a is None:
        return None
    return {"author": {"kind": a.author_kind, "id": a.author_id}, "date": a.created}


def _author_label(a: Annotation) -> str:
    return f"{a.author_id} (run)" if a.author_kind == "run" else a.author_id


def _when(result: ScanResult, n: NodeRec) -> str | None:
    """The date a node's file last changed, from its modification time.

    Under LOOM_FIXED_TIME it is the fixed date instead: a modification time depends on when and how a quilt was copied, so a fixture built from it would differ by the day it was regenerated.
    """
    import os

    if os.environ.get("LOOM_FIXED_TIME"):
        from loom.clock import today

        return today()
    try:
        import datetime

        mtime = (result.quilt.root / n.file).stat().st_mtime
        return datetime.datetime.fromtimestamp(mtime, datetime.UTC).strftime("%Y-%m-%d")
    except OSError:
        return None


def _slug(s: str | None) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9._-]+", "_", s or "")


_MATH = re.compile(r"\$\$(.+?)\$\$|(?<!\\)\$((?:[^$\\]|\\.)+?)\$", re.S)
_HOLE = "loommathx{}x"


def _protect_math(text: str) -> tuple[str, list[tuple[bool, str]]]:
    """Lift `$...$` and `$$...$$` out of Markdown before it is rendered, leaving a bare word in their place.

    Commonmark has no math, so `$O(n^2)$` renders as literal dollars and `$a_i b_i$` loses both subscripts to emphasis. Lifting first is what stops the second: a placeholder is an ordinary word, and whatever the TeX contains is never seen by the parser.
    """
    spans: list[tuple[bool, str]] = []

    def take(m: re.Match[str]) -> str:
        display = m.group(1) is not None
        spans.append((display, (m.group(1) if display else m.group(2)).strip()))
        return _HOLE.format(len(spans) - 1)

    return _MATH.sub(take, text), spans


def _restore_math(html_text: str, spans: list[tuple[bool, str]]) -> str:
    """Put each lifted span back as the dialect writes it (specs/dialect.md §2.6)."""
    import html as _html

    for i, (display, tex) in enumerate(spans):
        tex = _html.escape(tex, quote=False)
        block = (
            f'<div class="math display">\\[{tex}\\]</div>'
            if display
            else f'<span class="math inline">\\({tex}\\)</span>'
        )
        html_text = html_text.replace(_HOLE.format(i), block)
    return _lift_display_math(html_text)


def _lift_display_math(html_text: str) -> str:
    """Take every display equation out of the paragraph Commonmark wrapped it in, splitting the paragraph around it.

    The dialect writes display math as a `div` (specs/dialect.md §2.6) and Commonmark wraps a paragraph's content in a `p`, so an equation that is not separated by blank lines lands inside one -- which is invalid, and which a browser fixes by closing the paragraph early and leaving the prose after the equation outside it. Writing a sentence, a newline, `$$...$$`, a newline and another sentence is how annotations are actually written, so this is the ordinary case rather than the edge one.
    """
    div = re.compile(r'<div class="math display">.*?</div>', re.S)

    def split(m: re.Match[str]) -> str:
        inner = m.group(1)
        if not div.search(inner):
            return m.group(0)
        out: list[str] = []
        pos = 0
        for d in div.finditer(inner):
            before = inner[pos : d.start()].strip()
            if before:
                out.append(f"<p>{before}</p>")
            out.append(d.group(0))
            pos = d.end()
        rest = inner[pos:].strip()
        if rest:
            out.append(f"<p>{rest}</p>")
        return "\n".join(out)

    return re.sub(r"<p>(.*?)</p>", split, html_text, flags=re.S)


def render_markdown(text: str, src: str | None = None, offset: int = 0) -> str:
    """Markdown rendered into the dialect's inline subset, math included.

    Every body loom publishes as HTML comes through here -- annotations, thread messages, an agent's report -- and all of them are written by people and agents who use `$...$` without thinking about it.

    Parameters
    ----------
    text : str
        The Markdown as it was written.
    src : str, optional
        The file this text came from, quilt-relative. Given it, every block element carries `data-src="FILE:START:END"` in character offsets, as the dialect requires of anything that originates in source (specs/dialect.md §1.4).
    offset : int, default 0
        Where `text` begins in that file, when it is a slice of one.

    Returns
    -------
    str
        Dialect HTML.
    """
    protected, spans = _protect_math(text)
    try:
        from markdown_it import MarkdownIt

        md = MarkdownIt("commonmark", {"html": False})
        if src is None:
            out = str(md.render(protected)).strip()
        else:
            out = str(md.renderer.render(_sourced(md.parse(protected), protected, src, offset), md.options, {})).strip()
    except Exception:  # noqa: BLE001
        import html

        out = "<p>" + html.escape(protected) + "</p>"
    return _restore_math(out, spans)


def _sourced(tokens: list[Any], text: str, src: str, offset: int) -> list[Any]:
    """Stamp `data-src` on every opening block token, from the line map markdown-it already keeps.

    A report is written in a file like anything else loom publishes, so its blocks can say where they came from rather than being exempted from the rule that they must.
    """
    starts = [0]
    for line in text.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    for tok in tokens:
        if tok.map is None or tok.nesting == -1 or tok.hidden:
            continue
        lo, hi = tok.map
        a = offset + starts[min(lo, len(starts) - 1)]
        b = offset + starts[min(hi, len(starts) - 1)]
        tok.attrSet("data-src", f"{src}:{a}:{b}")
    return tokens
