"""`loom build` (book 9.1): scan, read records, read numbering, render, write the manifest, publish.

Rendering is cached by an input hash per fragment (the text of the files it draws on plus the numbering), so a build after a one-line edit re-renders one node and its masters. The hash carries loom's version, and in a checkout — whose version does not move between edits — a fingerprint of loom's own code, so changing the converter does not leave yesterday's HTML on disk. `--force` renders everything regardless.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

from loom.history.ledger import load_history
from loom.records.lastseen import freeze_moved
from loom.records.store import Records
from loom.render.canon import CanonRenderer, canon_fragment_path, load_canon
from loom.render.fragments import FragmentRenderer, RenderPlan
from loom.render.manifest import build_manifest
from loom.render.marks import MarkEntry, place_marks
from loom.render.publish import publish
from loom.scan.model import Diagnostic
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult, scan
from loom.tex.aux import AuxNumber, read_cite_labels, read_numbers
from loom.version import __version__


@dataclass
class BuildReport:
    result: ScanResult
    manifest: dict[str, Any]
    rendered: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(d.severity == "error" for d in self.diagnostics)


def _attach_reports(root: Path, manifest: dict[str, Any], fragments: dict[str, str], files: dict[str, Any]) -> None:
    """Render every run's notes files as report fragments and index their blocks on the thread's pipeline.

    A report is a fragment like any other -- lazily fetched, dialect-conformant, checked by `validate-dialect.py` -- so what the manifest carries is the index a viewer navigates by and not the prose itself. A corpus whose publisher has no modes has no pipelines and nothing happens here.
    """
    from loom.render.reports import parse_report

    for tid, thread in manifest.get("threads", {}).items():
        for entry in thread.get("pipeline", []):
            src = root / entry["report"]
            if not src.is_file():
                continue
            parsed = parse_report(src.read_text(encoding="utf-8", errors="replace"), run=str(tid), src=entry["report"])
            # A leading dot would make the file invisible to every static host: a session's report lives under
            # `.loom/sessions/<id>/`, and percent-encoding the path keeps that dot at the front of the name. Vite,
            # nginx and GitHub Pages all refuse a dotfile, so the fragment 404s wherever the corpus is published.
            name = quote(entry["report"], safe="").lstrip(".")
            rel = f"fragments/reports/{name}.html"
            fragments[f"report:{entry['report']}"] = rel
            files[rel] = parsed.html
            entry["fragment"] = rel
            entry["blocks"] = [b.to_dict() for b in parsed.blocks]


class _PageTable:
    """The word boxes of one work's pages, read once each, and the page table the sidecar publishes for them."""

    def __init__(self, home: Path) -> None:
        self.home = home
        self.boxes: dict[int, str] = {}
        self.pages: dict[str, dict[str, float]] = {}

    def boxes_of(self, page: int) -> str:
        from loom.refs.pages import page_box, page_rotation, token_boxes

        if page not in self.boxes:
            try:
                self.boxes[page] = token_boxes(self.home / "paper.pdf", page, self.home)
            except Exception:  # noqa: BLE001 -- geometry is a convenience; a page without it still reads
                self.boxes[page] = ""
        if self.boxes[page] and str(page) not in self.pages:
            box = page_box(self.boxes[page])
            if box:
                self.pages[str(page)] = {
                    "width": box[0],
                    "height": box[1],
                    "rotate": page_rotation(self.home / "paper.pdf", page, self.home),
                }
        return self.boxes[page]


def _attach_spans(root: Path, manifest: dict[str, Any], files: dict[str, Any]) -> None:
    """One sidecar per work holding the geometry of its anchors, and a pointer to it on the reference (plan 0.13 item 2).

    Beside the manifest for the reason `_write_source` gives: the manifest is loaded whole on every poll, and geometry is wanted for the one paper being read. The pointer carries the sidecar's own hash, which is what lets a viewer notice a stale copy while `loom serve` rebuilds under it.

    Two maps: `quads` for the work's results, keyed by result id, and `marks` for the notes on its pages, keyed by annotation id. A text anchor's rectangles are derived here from the word boxes and never recorded; a box anchor's are the record itself, read back from the log. A work whose PDF is not on this machine gets no sidecar, and the viewer has nothing to draw, which is the honest state.

    Runs after `Records.apply`, so it reads the published annotations and writes each reference's `reading` count.
    """
    from loom.records.annotations import load_records
    from loom.refs.pages import read_map, read_page
    from loom.refs.proposals import load_results
    from loom.refs.search import locate_span

    published = manifest.get("annotations", {})
    # the box anchors' own rectangles, which the manifest does not carry
    drawn: dict[str, list[list[float]]] = {}
    if any(a.get("basis") == "box" for a in published.values()):
        for record in load_records(root)[0]:
            for a in record.annotations:
                if a.anchor is not None and a.anchor.basis == "box" and a.anchor.quads:
                    drawn[a.id] = a.anchor.quads

    for citekey, ref in manifest.get("references", {}).items():
        notes = [a for a in published.values() if a["target"].get("work") == citekey and not a["discarded"]]
        ref["reading"] = {
            "total": len(notes),
            "open": sum(1 for a in notes if a["status"] == "open" and a["in_reply_to"] is None),
        }
        artifacts = ref.get("artifacts") or {}
        home = root / str(artifacts.get("dir", ""))
        if not artifacts.get("pdf") or not (home / "paper.pdf").is_file():
            continue
        results = {rid: r for rid, r in load_results(root, citekey).items() if r.anchor.kind == "pdf" and r.anchor.page}
        if not results and not notes:
            continue
        table = _PageTable(home)
        quads: dict[str, list[list[float]]] = {}
        marks: dict[str, list[list[float]]] = {}
        for rid, r in results.items():
            xml = table.boxes_of(r.anchor.page)
            # An anchor that records a span says which words on the page it means, and the page's own text is what those offsets index; a result read off a page instead carries the words it quoted. A mechanically extracted result's `source_text` is its LaTeX, which is not what the page says, so matching that was what left an extracted digest with no geometry at all.
            needle = r.source_text
            if r.anchor.basis == "text" and r.anchor.end > r.anchor.start:
                page_text = read_page(home, r.anchor.page) or ""
                needle = page_text[r.anchor.start : r.anchor.end] or needle
            span = locate_span(xml, needle, r.anchor.page) if xml else None
            if span is not None:
                quads[rid] = [list(q) for q in span.lines]
        for a in notes:
            page = int(a["target"].get("page") or 0)
            if not page:
                continue
            if a.get("basis") == "box":
                if a["id"] in drawn:
                    marks[a["id"]] = drawn[a["id"]]
                    table.boxes_of(page)  # for the page table
                continue
            xml = table.boxes_of(page)
            span = locate_span(xml, a.get("quote") or "", page) if xml and a.get("quote") else None
            if span is not None:
                marks[a["id"]] = [list(q) for q in span.lines]
        pages = table.pages
        if not quads and not marks:
            continue
        m = read_map(home)
        body = json.dumps(
            {"artifact": m.sha256 if m else "", "pages": pages, "quads": quads, "marks": marks},
            indent=1,
            sort_keys=True,
        )
        rel = f"spans/{artifacts['dir'].removeprefix('digests/storage/')}.json"
        files[rel] = body
        ref["spans"] = {"path": rel, "sha256": hashlib.sha256(body.encode()).hexdigest()}


def _write_source(result: ScanResult, fragments: dict[str, str], files: dict[str, Any]) -> None:
    """One file per key holding its own LaTeX, for the viewer's verbatim toggle (specs/manifest.md §1).

    Beside the manifest rather than inside it: the manifest is loaded whole on every poll and already runs to hundreds of kilobytes, while source is wanted one key at a time and only when a reader asks to see it.
    """
    from loom.tex.bundle import region_text

    for key, n in result.nodes.items():
        if n.kind not in ("environment", "section") and not (n.kind == "proof" and n.id):
            continue
        try:
            text = region_text(result, key)
        except (KeyError, IndexError):
            continue
        rel = f"source/{quote(key, safe='')}.tex"
        fragments[f"source:{key}"] = rel
        files[rel] = text


def fragment_path(result: ScanResult, key: str) -> str:
    n = result.nodes[key]
    if n.kind == "master":
        return f"fragments/masters/{Path(key).stem}.html"
    if n.kind == "file" and key in result.assembly.digest_files:
        return f"fragments/digests/{result.assembly.digest_files[key]}.html"
    if n.id:
        return f"fragments/nodes/{n.id}.html"
    from urllib.parse import quote

    return f"fragments/keys/{quote(key, safe='')}.html"


@cache
def _code_hash() -> str:
    """A fingerprint of loom's own rendering code, or '' for a released version, which its version string already identifies.

    In a checkout the version stays `0.1.0.dev0` across every edit, so a changed converter would otherwise hit the cache and republish the HTML it was meant to replace. Read once per process, since a served quilt rebuilds on every keystroke.
    """
    if "dev" not in __version__:
        return ""
    h = hashlib.sha256()
    for path in sorted((Path(__file__).resolve().parent.parent).rglob("*.py")):
        h.update(path.read_bytes())
    return h.hexdigest()[:16]


def _aux_bytes(numbers: dict[str, dict[str, AuxNumber]], cite_labels: dict[str, dict[str, str]]) -> bytes:
    """Every master's number table and citation labels as the byte stream `_input_hash` feeds its digest.

    Quilt-wide and the same for every fragment, so `build` serialises it once rather than once per node.
    """
    parts: list[str] = []
    for m in sorted(numbers):
        for lab, num in sorted(numbers[m].items()):
            parts.append(f"{m}|{lab}|{num.number}|{num.page}")
    for m in sorted(cite_labels):
        for ck, lab in sorted(cite_labels[m].items()):
            parts.append(f"{m}|cite|{ck}|{lab}")
    return "".join(parts).encode()


def _input_hash(result: ScanResult, key: str, aux: bytes) -> str:
    """The cache key of a node, master or digest fragment: loom's version and code, the text of every file it draws on, and `aux` from `_aux_bytes`."""
    n = result.nodes[key]
    h = hashlib.sha256()
    h.update(__version__.encode())
    h.update(_code_hash().encode())
    files = {n.file}
    if n.kind in ("master", "file"):
        for exp in result.expansions.values():
            if exp.master == key:
                files |= set(exp.reached)
    for ck in n.claimants:
        files.add(result.nodes[ck].file)
    for f in sorted(files):
        h.update(f.encode())
        h.update(result.files[f].text.encode("utf-8", errors="replace"))
    h.update(aux)
    return h.hexdigest()


def _canon_hash(doc, root: Path) -> str:  # type: ignore[no-untyped-def]
    """The cache key of a canon fragment: loom's version and code, the document's text, and its closure's."""
    h = hashlib.sha256()
    h.update(__version__.encode())
    h.update(_code_hash().encode())
    h.update(doc.path.encode())
    h.update(doc.src.text.encode("utf-8", errors="replace"))
    h.update(doc.closure.raw_text().encode("utf-8", errors="replace"))
    for p in sorted([*(root / "build").glob(f"{doc.stem}/*.aux"), *(root / "build").glob(f"{doc.stem}/*.bbl")]):
        h.update(p.read_bytes())
    return h.hexdigest()


def _marks_hash(marks: dict[str, list[MarkEntry]], key: str, result: ScanResult) -> str:
    n = result.nodes[key]
    keys = [key] if n.kind != "master" else [k for k, node in result.nodes.items() if key in node.reached_by]
    h = hashlib.sha256()
    for k in sorted(keys):
        for m in marks.get(k, []):
            h.update(f"{m.ann_id}|{m.start}|{m.end}".encode())
    return h.hexdigest()[:16]


def _marks_by_node(result: ScanResult, records: Records) -> dict[str, list[MarkEntry]]:
    """Mark entries grouped by the node whose fragment shows them: a proof's marks under its statement, and on the proof's own page.

    A comment on an equation with no quote (a box drawn round it) marks the display itself, found by the offset of its label.
    """
    out: dict[str, list[MarkEntry]] = {}
    for res in records.resolved(result):
        if res.record.discarded:
            continue
        # a note whose version is gone is not pinned to the text that replaced it; it is counted beside its key instead
        if not res.recorded:
            continue
        a = res.annotation
        region = result.assembly.regions.get(a.target_key)
        if res.span is None and a.selector is None and region is not None and a.in_reply_to is None:
            host = result.nodes.get(region.container)
            if host is not None:
                entry = MarkEntry(a.id, "", region.file, region.offset, region.offset)
                owner = host.of if host.kind == "proof" and host.of else host.key
                out.setdefault(owner, []).append(entry)
                if owner != host.key:
                    out.setdefault(host.key, []).append(entry)
            continue
        if res.span is None:
            continue
        n = result.nodes.get(a.target_key)
        if n is None:
            n = result.nodes.get(region.container) if region else None
        if n is None:
            continue
        _, pieces = Records.own_pieces(result, n)
        span = Records.to_file_span(pieces, res.span)
        if span is None:
            continue
        entry = MarkEntry(a.id, a.selector.exact if a.selector else "", n.file, span[0], span[1])
        owner = n.of if n.kind == "proof" and n.of else n.key
        out.setdefault(owner, []).append(entry)
        # a labelled proof has a page of its own too, and its marks belong on it as well as under its statement
        if owner != n.key:
            out.setdefault(n.key, []).append(entry)
    return out


def _write_transcripts(root: Path, files: dict[str, str | bytes]) -> None:
    """Every session's transcript as pages under `transcripts/<id>/<n>.json`, so a viewer with no publisher running still reads the chat.

    Out of the manifest, which every viewer polls: a long conversation would make every poll pay for it.
    """
    from loom.mailbox import pages
    from loom.sessions import sessions

    for sid in sessions(root):
        for n, page in pages(root, sid).items():
            files[f"transcripts/{sid}/{n}.json"] = json.dumps(page, ensure_ascii=False, indent=1, sort_keys=True)


def build(
    quilt: Quilt, keys: list[str] | None = None, records: Records | None = None, force: bool = False
) -> BuildReport:
    root = quilt.root
    build_dir = root / "build"
    cache_dir = build_dir / "cache"
    result = scan(quilt)
    records = records or Records(root, quilt.history_dir)
    # the one moment loom can still see both the text an annotation was written against and the text that replaced it
    freeze_moved(result, records.records, quilt.history_dir)
    marks = _marks_by_node(result, records)
    numbers = {m: read_numbers(root, m) for m in result.masters}
    cite_labels = {m: read_cite_labels(root, m) for m in result.masters}
    plan = RenderPlan(
        result=result, numbers=numbers, cite_labels=cite_labels, svg_cache=cache_dir / "svg", svg_out=build_dir / "svg"
    )
    if force:
        # a remembered SVG failure may have been the machine's, a package since installed; --force tries each once more
        for failed in plan.svg_cache.glob("*.failed"):
            failed.unlink()
    renderer = FragmentRenderer(plan)
    index_path = cache_dir / "fragments.json"
    index: dict[str, str] = {}
    if index_path.exists() and not force:
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index = {}
    fragments: dict[str, str] = {}
    files: dict[str, str | bytes] = {}
    report = BuildReport(result=result, manifest={})
    wanted: set[str] | None = None
    if keys:
        wanted = set()
        for k in keys:
            n = result.nodes.get(k)
            if n is None:
                continue
            wanted.add(k)
            wanted |= set(n.proofs)
            wanted |= set(n.reached_by)
    targets: list[tuple[str, str]] = []
    for key, n in result.nodes.items():
        if n.kind in ("environment", "section") or (n.kind == "proof" and n.id):
            targets.append((key, "node"))
        elif n.kind == "master":
            targets.append((key, "master"))
        elif n.kind == "file" and key in result.assembly.digest_files:
            targets.append((key, "digest"))

    def render_one(key: str, kind: str) -> str:
        if kind == "node":
            return place_marks(renderer.node_fragment(key), marks.get(key, []))
        if kind == "master":
            return place_marks(
                renderer.master_fragment(key),
                [m for k, ms in marks.items() for m in ms if key in result.nodes[k].reached_by],
            )
        return renderer.digest_fragment(key)

    jobs: list[tuple[str, str, str, str]] = []
    aux = _aux_bytes(numbers, cite_labels)
    for key, kind in targets:
        rel = fragment_path(result, key)
        label = key if kind == "node" else f"{kind}:{key}"
        fragments[label] = rel
        digest = _input_hash(result, key, aux) + _marks_hash(marks, key, result)
        existing = build_dir / rel
        if (wanted is not None and key not in wanted) or (index.get(rel) == digest and existing.exists()):
            report.skipped.append(key)
            continue
        jobs.append((key, kind, rel, digest))
    history = load_history(quilt.history_dir)
    canon_docs = load_canon(quilt, result, history)
    canon_renderer = CanonRenderer(renderer)
    canon_entries: list[dict[str, Any]] = []
    canon_jobs: list[tuple[Any, str, str]] = []
    from loom.render.canon import canon_entry

    for doc in canon_docs:
        rel = canon_fragment_path(doc)
        digest = _canon_hash(doc, root)
        if (wanted is not None) or (index.get(rel) == digest and (build_dir / rel).exists()):
            report.skipped.append(f"canon:{doc.path}")
        else:
            canon_jobs.append((doc, rel, digest))
        fragments[f"canon:{doc.path}"] = rel
        canon_entries.append(canon_entry(doc, rel, digest))
    # Rendered on a pool, assembled in order. The expensive part is waiting on LaTeX -- a diagram the converter cannot draw is compiled to SVG, twice through latex and once through dvisvgm, up to three times with different preambles -- and with sixteen real digests carrying 74 diagrams the first build of the study quilt took 454 seconds on one thread. Waiting on a subprocess releases the GIL, so threads overlap exactly that.
    # Canon documents share the pool and are submitted first: each is one long job that compiles its own preamble's diagrams one after another, so started last it would run alone after every node had finished.
    from concurrent.futures import ThreadPoolExecutor
    from functools import partial

    tasks = [partial(canon_renderer.fragment, doc) for doc, _rel, _digest in canon_jobs]
    tasks += [partial(render_one, key, kind) for key, kind, _rel, _digest in jobs]

    def render_job(task: Any) -> tuple[str, list[Any]]:
        with renderer.collecting() as diags:
            return task(), diags

    with ThreadPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        done = list(pool.map(render_job, tasks))
    canon_done, node_done = done[: len(canon_jobs)], done[len(canon_jobs) :]
    # every job's diagnostics, nodes then canon, each in job order: the order a single thread would have produced, whatever order they finished
    for _, diags in node_done + canon_done:
        plan.diagnostics.extend(diags)
    for (key, _kind, rel, digest), (html_out, _) in zip(jobs, node_done, strict=True):
        files[rel] = html_out
        index[rel] = digest
        report.rendered.append(key)
    for (doc, rel, digest), (html_out, _) in zip(canon_jobs, canon_done, strict=True):
        files[rel] = html_out
        index[rel] = digest
        report.rendered.append(f"canon:{doc.path}")
    report.diagnostics = list(result.lint) + plan.diagnostics
    manifest = build_manifest(
        result, numbers, fragments, report.diagnostics, canon=canon_docs, canon_entries=canon_entries, history=history
    )
    records.apply(result, manifest, build_dir)
    from loom.render.review_compare import attach_comparisons

    _attach_spans(result.quilt.root, manifest, files)
    attach_comparisons(result, records, renderer, manifest, files)
    from loom.render.incoming import attach_incoming

    attach_incoming(result, renderer, manifest, files)
    from loom.review_queue import rows_for

    manifest["unresolved"] = rows_for(result, manifest)
    _attach_reports(result.quilt.root, manifest, fragments, files)
    _write_source(result, fragments, files)
    _write_transcripts(result.quilt.root, files)
    report.diagnostics = [d for d in report.diagnostics] + [
        Diagnostic(d["severity"], d["code"], d["message"]) for d in manifest["diagnostics"][len(report.diagnostics) :]
    ]
    report.manifest = manifest
    prune = ("fragments/", "source/", "spans/", "transcripts/") if wanted is None else ()
    if wanted is None:
        for rel in list(index):
            if rel not in fragments.values():
                index.pop(rel)
    # a fragment the cache skipped is already on disk as it should be: kept from the prune, not read back and rewritten
    publish(build_dir, files, manifest, prune, keep={rel for rel in fragments.values() if rel not in files})
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=0, sort_keys=True), encoding="utf-8")
    return report
