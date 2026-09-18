"""The Records object: everything durable that is not source, loaded once per query, and the states, causes, facts, and derived states computed from it (book 7.6, 7.9, 7.10).

`compute` is pure over the scan result and the records; `apply` writes those results into a manifest and the diffs directory.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.ai.runs import thread_id
from loom.records.annotations import Annotation, Record, load_records
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

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind, "diff": None}
        if self.id:
            d["id"] = self.id
        if self.when:
            d["when"] = self.when
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


@dataclass
class ResolvedAnnotation:
    annotation: Annotation
    record: Record
    span: tuple[int, int] | None  # in the target's own text (concatenated pieces)
    detached: bool
    recorded: bool = True  # the text this was written against is still recoverable: it is the current text, or frozen


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

    # ---- states -----------------------------------------------------------------

    def key_states(self, result: ScanResult) -> dict[str, KeyState]:
        states: dict[str, KeyState] = {}
        current_hashes = {k: key_hash(result, k) for k, n in result.nodes.items() if n.kind in ("environment", "proof")}
        pre = self.preamble_hash(result, result.default_master)
        for key, n in result.nodes.items():
            if n.kind not in ("environment", "proof"):
                continue
            row = self.latest.get(key)
            ks = KeyState(key=key, state="draft", row=row)
            if n.incomplete:
                ks.state = "incomplete"
            if row is not None:
                ks.state = "incomplete" if n.incomplete else "accepted"
                current = current_hashes[key]
                closure_now = self.closure_hashes(result, key)
                if row.text != current:
                    ks.causes.append(Cause("own-text-changed", before=row.text, after=current, when=_when(result, n)))
                for dep, h in row.closure.items():
                    if dep not in result.nodes:
                        ks.causes.append(Cause("dependency-removed", id=dep, before=h))
                    elif closure_now.get(dep) != h:
                        ks.causes.append(
                            Cause(
                                "dependency-changed",
                                id=dep,
                                before=h,
                                after=closure_now.get(dep),
                                when=_when(result, result.nodes[dep]),
                            )
                        )
                for dep in closure_now:
                    if dep not in row.closure:
                        ks.causes.append(Cause("dependency-added", id=dep))
                if row.preamble and pre and row.preamble != pre:
                    ks.causes.append(Cause("preamble-changed", before=row.preamble, after=pre))
                ks.fresh = not ks.causes
            states[key] = ks
        self._review_facts(result, states, current_hashes)
        self._previous_key_matches(result, states, current_hashes)
        return states

    def _review_facts(self, result: ScanResult, states: dict[str, KeyState], current: dict[str, str]) -> None:
        for res in self.resolved(result):
            a = res.annotation
            ks = states.get(a.target_key)
            if ks is None or res.record.discarded:
                continue
            if a.in_reply_to is None and a.status == "open" and a.kind != "ok":
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
            owes_proof = n.style == "plain" and not n.external
            proved[key] = ok and (good_proof or not owes_proof)
        settled: dict[str, bool] = {}
        visiting: set[str] = set()

        def is_settled(key: str) -> bool:
            if key in settled:
                return settled[key]
            n = result.nodes.get(key)
            if n is None:
                return False
            if n.external:
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
        for rec in self.records:
            for a in rec.annotations:
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
                "target": {"key": a.target_key, "hash": a.target_hash},
                "kind": a.kind,
                "body_html": render_markdown(a.body),
                "status": a.status,
                "in_reply_to": a.in_reply_to,
                "anchored": a.selector is not None and not res.detached and res.recorded,
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
    # A display equation alone in its paragraph is a block, and Commonmark wrapped the placeholder that stood for it in
    # a <p>; leaving it there nests a div inside a p, which no dialect check should have to tolerate.
    return re.sub(r'<p>\s*(<div class="math display">.*?</div>)\s*</p>', r"\1", html_text, flags=re.S)


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
