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
            rel = f"fragments/reports/{quote(entry['report'], safe='')}.html"
            fragments[f"report:{entry['report']}"] = rel
            files[rel] = parsed.html
            entry["fragment"] = rel
            entry["blocks"] = [b.to_dict() for b in parsed.blocks]


def _attach_page_images(root: Path, manifest: dict[str, Any], build_dir: Path) -> None:
    """Render the anchor page of every pending proposal and name it on the result's manifest row (plan 0.12 §5.3).

    Pending proposals only: they are the one place a person is asked to judge a rendering, and the text layer beside them has lost the notation the judgement is about. A handful of pages, cached by artifact hash and page under `build/pages/`; a work whose PDF is not on this machine gets no image and the viewer says so.
    """
    from loom.refs.images import anchor_focus, anchor_images
    from loom.refs.proposals import PROPOSED, load_results

    for citekey, ref in manifest.get("references", {}).items():
        rows = ref.get("results") or {}
        pending = [rid for rid, row in rows.items() if row.get("state") == PROPOSED]
        if not pending:
            continue
        recorded = load_results(root, citekey)
        for rid in pending:
            if rid in recorded:
                images = anchor_images(root, build_dir, recorded[rid])
                if images:
                    rows[rid]["page_images"] = images
                    focus = anchor_focus(root, recorded[rid])
                    if focus is not None:
                        rows[rid]["page_focus"] = focus


def _attach_spans(root: Path, manifest: dict[str, Any], files: dict[str, Any]) -> None:
    """One sidecar per work holding the geometry of its anchors, and a pointer to it on the reference (plan 0.13 item 2).

    Beside the manifest for the reason `_write_source` gives: the manifest is loaded whole on every poll, and geometry is wanted for the one paper being read. The pointer carries the sidecar's own hash, which is what lets a viewer notice a stale copy while `loom serve` rebuilds under it.

    Quads are derived, never recorded: an anchor says where it is in the page's text, and the rectangles to draw it with are computed here from the word boxes. A work whose PDF is not on this machine gets no sidecar, and the viewer has nothing to draw, which is the honest state.
    """
    from loom.refs.pages import page_box, read_map, token_boxes
    from loom.refs.proposals import load_results
    from loom.refs.search import locate_span

    for citekey, ref in manifest.get("references", {}).items():
        artifacts = ref.get("artifacts") or {}
        home = root / str(artifacts.get("dir", ""))
        if not artifacts.get("pdf") or not (home / "paper.pdf").is_file():
            continue
        recorded = {
            rid: r for rid, r in load_results(root, citekey).items() if r.anchor.kind == "pdf" and r.anchor.page
        }
        if not recorded:
            continue
        pages: dict[str, dict[str, float]] = {}
        quads: dict[str, list[list[float]]] = {}
        boxes: dict[int, str] = {}
        for rid, r in recorded.items():
            page = r.anchor.page
            if page not in boxes:
                try:
                    boxes[page] = token_boxes(home / "paper.pdf", page, home)
                except Exception:  # noqa: BLE001 -- geometry is a convenience; a page without it still reads
                    boxes[page] = ""
            if not boxes[page]:
                continue
            span = locate_span(boxes[page], r.source_text, page)
            if span is None:
                continue
            quads[rid] = [list(q) for q in span.lines]
            if str(page) not in pages:
                box = page_box(boxes[page])
                if box:
                    pages[str(page)] = {"width": box[0], "height": box[1], "rotate": 0.0}
        if not quads:
            continue
        m = read_map(home)
        body = json.dumps({"artifact": m.sha256 if m else "", "pages": pages, "quads": quads}, indent=1, sort_keys=True)
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
    """Mark entries grouped by the node whose fragment shows them (a proof's marks belong to its statement's node)."""
    out: dict[str, list[MarkEntry]] = {}
    for res in records.resolved(result):
        if res.span is None or res.record.discarded:
            continue
        a = res.annotation
        n = result.nodes.get(a.target_key)
        if n is None:
            region = result.assembly.regions.get(a.target_key)
            n = result.nodes.get(region.container) if region else None
        if n is None:
            continue
        _, pieces = Records.own_pieces(result, n)
        span = Records.to_file_span(pieces, res.span)
        if span is None:
            continue
        owner = n.of if n.kind == "proof" and n.of else n.key
        out.setdefault(owner, []).append(
            MarkEntry(a.id, a.selector.exact if a.selector else "", n.file, span[0], span[1])
        )
    return out


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
    _attach_page_images(result.quilt.root, manifest, build_dir)
    _attach_spans(result.quilt.root, manifest, files)
    _attach_reports(result.quilt.root, manifest, fragments, files)
    _write_source(result, fragments, files)
    report.diagnostics = [d for d in report.diagnostics] + [
        Diagnostic(d["severity"], d["code"], d["message"]) for d in manifest["diagnostics"][len(report.diagnostics) :]
    ]
    report.manifest = manifest
    prune = ("fragments/", "source/", "spans/") if wanted is None else ()
    if wanted is None:
        for rel in list(index):
            if rel not in fragments.values():
                index.pop(rel)
    # a fragment the cache skipped is already on disk as it should be: kept from the prune, not read back and rewritten
    publish(build_dir, files, manifest, prune, keep={rel for rel in fragments.values() if rel not in files})
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=0, sort_keys=True), encoding="utf-8")
    return report
