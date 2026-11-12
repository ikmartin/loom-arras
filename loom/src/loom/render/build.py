"""`loom build`: scan, read records, read numbering, render, write the manifest, publish.

Rendering is cached by an input hash per fragment (the text of the files it draws on plus the numbering), so a build after a one-line edit re-renders one node and its masters. The hash carries loom's version, and in a checkout — whose version does not move between edits — a fingerprint of loom's own code, so changing the converter does not leave yesterday's HTML on disk. `--force` renders everything regardless.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

from loom.history.ledger import load_history
from loom.paths import BUILD, document_build, document_name
from loom.records.lastseen import freeze_moved
from loom.records.store import Records
from loom.refs.pages import storage_root, store_home
from loom.render.canon import CanonRenderer, canon_fragment_path, load_canon
from loom.render.fragments import FragmentRenderer, RenderPlan
from loom.render.keys import aux_bytes, code_hash
from loom.render.manifest import build_manifest
from loom.render.marks import MarkEntry, place_marks
from loom.render.publish import publish, write_atomic
from loom.render.versions import Gone, attach_versions, gone_annotations, gone_marks
from loom.scan.model import Diagnostic
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult, scan
from loom.tex.aux import read_cite_labels, read_numbers
from loom.version import __version__


@dataclass
class BuildReport:
    result: ScanResult
    manifest: dict[str, Any]
    rendered: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


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

    Two maps: `quads` for the work's results, keyed by result id, and `marks` for the annotations on its pages, keyed by annotation id. A text anchor's rectangles are derived here from the word boxes and never recorded; a box anchor's are the record itself, read back from the log. A work whose PDF is not on this machine gets no sidecar, and the viewer has nothing to draw, which is the honest state.

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

    # open means of a type that stays open until resolved, and not resolved yet
    staying = {t["id"] for t in manifest.get("annotation_types", []) if t.get("open")}
    for citekey, ref in manifest.get("references", {}).items():
        on_work = [a for a in published.values() if a["target"].get("work") == citekey]
        ref["reading"] = {
            "total": len(on_work),
            "open": sum(
                1 for a in on_work if a["status"] == "open" and a["in_reply_to"] is None and a.get("type") in staying
            ),
        }
        artifacts = ref.get("artifacts") or {}
        home = store_home(root, str(artifacts.get("dir", "")))
        if not artifacts.get("pdf") or not (home / "paper.pdf").is_file():
            continue
        results = {rid: r for rid, r in load_results(root, citekey).items() if r.anchor.kind == "pdf" and r.anchor.page}
        if not results and not on_work:
            continue
        m = read_map(home)
        rel = f"spans/{home.relative_to(storage_root(root)).as_posix()}.json"
        # what the geometry is made from: the results' anchors and words, the annotations on the pages and their drawn boxes, the copy filed, and the matching code
        key = hashlib.sha256(
            json.dumps(
                [
                    _spans_code(),
                    m.sha256 if m else "",
                    sorted(
                        [rid, r.anchor.page, r.anchor.basis, r.anchor.start, r.anchor.end, r.source_text]
                        for rid, r in results.items()
                    ),
                    sorted(
                        [
                            a["id"],
                            a["target"].get("page") or 0,
                            a.get("basis") or "",
                            a.get("quote") or "",
                            drawn.get(a["id"]) or a.get("rects") or [],
                        ]
                        for a in on_work
                    ),
                ]
            ).encode()
        ).hexdigest()[:32]
        kept = root / BUILD / "cache" / "spans" / f"{key}.json"
        if kept.is_file():
            body = kept.read_text(encoding="utf-8")
            if body:
                files[rel] = body
                ref["spans"] = {"path": rel, "sha256": hashlib.sha256(body.encode()).hexdigest()}
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
        for a in on_work:
            page = int(a["target"].get("page") or 0)
            if not page:
                continue
            if a.get("basis") is None and a.get("rects"):
                # drawn on the page with its own place, which the record holds
                marks[a["id"]] = a["rects"]
                table.boxes_of(page)  # for the page table
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
            write_atomic(kept, "")  # nothing found is remembered too, so the pages are not searched again
            continue
        body = json.dumps(
            {"artifact": m.sha256 if m else "", "pages": pages, "quads": quads, "marks": marks},
            indent=1,
            sort_keys=True,
        )
        write_atomic(kept, body)
        files[rel] = body
        ref["spans"] = {"path": rel, "sha256": hashlib.sha256(body.encode()).hexdigest()}


@cache
def _spans_code() -> str:
    """The word matching and page reading `_attach_spans` uses, fingerprinted so a cached sidecar is made again when either changes."""
    from loom.refs import pages, search

    return hashlib.sha256(Path(search.__file__).read_bytes() + Path(pages.__file__).read_bytes()).hexdigest()[:16]


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
        return f"fragments/masters/{document_name(key)}.html"
    if n.kind == "file" and key in result.assembly.digest_files:
        return f"fragments/digests/{result.assembly.digest_files[key]}.html"
    if n.id:
        return f"fragments/nodes/{n.id}.html"
    from urllib.parse import quote

    return f"fragments/keys/{quote(key, safe='')}.html"


def _input_hash(
    result: ScanResult, key: str, aux: bytes, texts: dict[str, str] | None = None, pages: dict[str, Any] | None = None
) -> str:
    """The cache key of a node, master or digest fragment: loom's version and code, the text of every file it draws on, `aux` from `keys.aux_bytes`, and the digest of each page as TeX made it that the fragment may be cut from.

    `texts` holds each file's text hash, filled as files are met, so a file every digest node draws on is hashed once per scan rather than once per node; `pages` maps each document to its current page, or None.
    """
    texts = {} if texts is None else texts
    n = result.nodes[key]
    h = hashlib.sha256()
    h.update(__version__.encode())
    h.update(code_hash().encode())
    files = {n.file}
    if n.kind in ("master", "file"):
        for exp in result.expansions.values():
            if exp.master == key:
                files |= set(exp.reached)
    for ck in n.claimants:
        files.add(result.nodes[ck].file)
    for f in sorted(files):
        if f not in texts:
            texts[f] = hashlib.sha256(result.files[f].text.encode("utf-8", errors="replace")).hexdigest()
        h.update(f.encode())
        h.update(texts[f].encode())
    h.update(aux)
    for m in [key] if n.kind == "master" else n.reached_by:
        page = (pages or {}).get(m)
        h.update(f"{m}:{page.digest if page is not None else '-'}".encode())
    return h.hexdigest()


def _canon_hash(doc, root: Path) -> str:  # type: ignore[no-untyped-def]
    """The cache key of a landmark's fragment: loom's version and code, the landmark's text, its closure's, and the `.aux` and `.bbl` it reads, its own or its live document's."""
    h = hashlib.sha256()
    h.update(__version__.encode())
    h.update(code_hash().encode())
    h.update(doc.path.encode())
    h.update(doc.src.text.encode("utf-8", errors="replace"))
    h.update(doc.closure.raw_text().encode("utf-8", errors="replace"))
    for path in filter(None, (doc.path, doc.live)):
        out = root / document_build(path)
        for p in sorted([*out.glob("*.aux"), *out.glob("*.bbl")]):
            h.update(p.read_bytes())
    return h.hexdigest()


def _marks_hash(marks: dict[str, list[MarkEntry]], key: str, result: ScanResult) -> str:
    n = result.nodes[key]
    keys = [key] if n.kind != "master" else [k for k, node in result.nodes.items() if key in node.reached_by]
    h = hashlib.sha256()
    for k in sorted(keys):
        for m in marks.get(k, []):
            h.update(
                f"{m.ann_id}|{m.start}|{m.end}|{m.in_doc or ''}|{m.gone}|{m.lead}|{m.quote if m.gone else ''}".encode()
            )
    return h.hexdigest()[:16]


def _marks_by_node(result: ScanResult, records: Records, gone: list[Gone] | None = None) -> dict[str, list[MarkEntry]]:
    """Mark entries grouped by the node whose fragment shows them: a proof's marks under its statement, and on the proof's own page.

    A comment on an equation with no quote (a box drawn round it) marks the display itself, found by the offset of its label. An annotation whose words are gone marks where they were with an empty mark (`versions.gone_marks`), from `gone` when the caller has it.
    """
    out: dict[str, list[MarkEntry]] = gone_marks(gone_annotations(result, records) if gone is None else gone)
    for res in records.resolved(result):
        # a note whose version is gone is not pinned to the text that replaced it; it is counted beside its key instead
        if not res.recorded:
            continue
        a = res.annotation
        region = result.assembly.regions.get(res.target)
        if res.span is None and a.selector is None and region is not None and a.in_reply_to is None:
            host = result.nodes.get(region.container)
            if host is not None:
                entry = MarkEntry(a.id, "", region.file, region.offset, region.offset, res.in_doc)
                owner = host.of if host.kind == "proof" and host.of else host.key
                out.setdefault(owner, []).append(entry)
                if owner != host.key:
                    out.setdefault(host.key, []).append(entry)
            continue
        if res.span is None:
            continue
        n = result.nodes.get(res.target)
        if n is None:
            n = result.nodes.get(region.container) if region else None
        if n is None:
            continue
        _, pieces = Records.own_pieces(result, n)
        span = Records.to_file_span(pieces, res.span)
        if span is None:
            continue
        # `in` as the history's moves leave it, so a note read in a document is drawn in whatever that document became
        entry = MarkEntry(a.id, a.selector.exact if a.selector else "", n.file, span[0], span[1], res.in_doc)
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
    from loom.mailbox import inbox_path, pages
    from loom.sessions import sessions

    for sid in sessions(root):
        inbox = inbox_path(root, sid)
        try:
            stamp: tuple[int, int] | None = (inbox.stat().st_mtime_ns, inbox.stat().st_size)
        except OSError:
            stamp = None
        known = _TRANSCRIPTS.get(inbox)
        if stamp is not None and known is not None and known[0] == stamp:
            files.update(known[1])
            continue
        made = {
            f"transcripts/{sid}/{n}.json": json.dumps(page, ensure_ascii=False, indent=1, sort_keys=True)
            for n, page in pages(root, sid).items()
        }
        if stamp is not None:
            _TRANSCRIPTS[inbox] = (stamp, made)
        files.update(made)


#: Each session's transcript pages as last written, by its inbox's modification time and size: a session nobody wrote in since is not rendered again by a server that rebuilds on every change.
_TRANSCRIPTS: dict[Path, tuple[tuple[int, int], dict[str, str]]] = {}


#: The fragments' input hashes for the last scan built from, the numbering they were hashed with, and each file's text hash; a build from the same scan (`reuse`) reads them rather than hashing every file again.
_INPUT_HASHES: tuple[ScanResult | None, bytes, dict[str, str], dict[str, str]] = (None, b"", {}, {})


def build(
    quilt: Quilt,
    keys: list[str] | None = None,
    records: Records | None = None,
    force: bool = False,
    reuse: ScanResult | None = None,
    progress: Callable[[str, str, int, int | None], None] | None = None,
    tex: bool = True,
) -> BuildReport:
    """Scan, read the records, render what changed and publish the build directory.

    Parameters
    ----------
    quilt : Quilt
        The quilt to build.
    keys : list of str, optional
        Render only these keys, their proofs and the documents reaching them; default every fragment.
    records : Records, optional
        Records already read; default read here.
    force : bool, default False
        Render every fragment again, and retry every figure that failed before.
    reuse : ScanResult, optional
        A scan of this quilt to build from instead of scanning again. Only a caller that knows no scan input changed passes one: `loom serve`, after a change to records alone or a version kept, whose landmark is read again here.
    progress : callable, optional
        Told `(stage, item, n, total)` as the build moves: `scanning`, `rendering` once per fragment with its place in the count, `recording`, `publishing`; what a caller shows as progress (T6).
    tex : bool, default True
        Whether TeX may run for text no compile makes (snippets, pictures); without it that text comes from the cache or shows as its source.

    Returns
    -------
    BuildReport
        The scan, the manifest, and what was rendered and skipped.
    """
    root = quilt.root
    build_dir = root / BUILD
    cache_dir = build_dir / "cache"

    def told(stage: str, item: str = "", n: int = 0, total: int | None = None) -> None:
        if progress is not None:
            progress(stage, item, n, total)

    told("scanning")
    result = reuse if reuse is not None else scan(quilt)
    if reuse is not None:
        from loom.scan.scan import landmark_documents

        # a version kept since (a keep's, a recorded one) adds a landmark and nothing else the scan reads
        result.canon_files = landmark_documents(quilt)
    records = records or Records(root, quilt.history_dir)
    # the one moment loom can still see both the text an annotation was written against and the text that replaced it
    freeze_moved(result, records.records)
    gone = gone_annotations(result, records)
    marks = _marks_by_node(result, records, gone)
    numbers = {m: read_numbers(root, m) for m in result.masters}
    cite_labels = {m: read_cite_labels(root, m) for m in result.masters}
    from loom.render.fromhtml import page_for

    # each document's page as TeX made it, where one is current with its sources; the rest show as their source
    pages = {m: page_for(result, m) for m in result.masters}
    plan = RenderPlan(
        result=result,
        numbers=numbers,
        cite_labels=cite_labels,
        cache=cache_dir,
        svg_out=build_dir / "svg",
        pages=pages,
        tex=tex,
    )
    if force:
        # a text TeX refused may have been refused for the machine's sake, a package since installed; --force tries each once more
        for failed in [*(cache_dir / "snippets").glob("*.failed"), *(cache_dir / "previews").glob("*.html")]:
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
        # a mark that names a document is drawn in that document and nowhere else (plan 0.15, decision 9)
        if kind == "node":
            return place_marks(renderer.node_fragment(key), [m for m in marks.get(key, []) if m.in_doc is None])
        if kind == "master":
            return place_marks(
                renderer.master_fragment(key),
                [
                    m
                    for k, ms in marks.items()
                    for m in ms
                    if key in result.nodes[k].reached_by and m.in_doc in (None, key)
                ],
            )
        return renderer.digest_fragment(key)

    jobs: list[tuple[str, str, str, str]] = []
    aux = aux_bytes(numbers, cite_labels)
    global _INPUT_HASHES
    if _INPUT_HASHES[0] is not result or _INPUT_HASHES[1] != aux:
        _INPUT_HASHES = (result, aux, {}, {})
    hashes, texts = _INPUT_HASHES[2], _INPUT_HASHES[3]
    for key, kind in targets:
        rel = fragment_path(result, key)
        label = key if kind == "node" else f"{kind}:{key}"
        fragments[label] = rel
        if key not in hashes:
            hashes[key] = _input_hash(result, key, aux, texts, pages)
        digest = hashes[key] + _marks_hash(marks, key, result)
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
    # What no compile makes, nodes no document reaches and digests, is made by TeX first, one batch per preamble, so the pool below only cuts fragments.
    renderer.prepare([key for key, _kind, _rel, _digest in jobs])
    # Rendered on a pool, assembled in order. The expensive part is waiting on TeX, a landmark's snippets or a page's diagrams, and waiting on a subprocess releases the GIL, so threads overlap exactly that.
    # Landmarks share the pool and are submitted first: each is one long job, so started last it would run alone after every node had finished.
    from concurrent.futures import ThreadPoolExecutor
    from functools import partial

    tasks = [partial(canon_renderer.fragment, doc) for doc, _rel, _digest in canon_jobs]
    tasks += [partial(render_one, key, kind) for key, kind, _rel, _digest in jobs]

    def render_job(task: Any) -> tuple[str, list[Any]]:
        with renderer.collecting() as diags:
            return task(), diags

    names = [doc.path for doc, _rel, _digest in canon_jobs] + [key for key, _kind, _rel, _digest in jobs]
    told("rendering", "", 0, len(tasks))
    done: list[tuple[str, list[Any]]] = []
    with ThreadPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as pool:
        for n, out in enumerate(pool.map(render_job, tasks), 1):
            done.append(out)
            told("rendering", names[n - 1], n, len(tasks))
    canon_done, node_done = done[: len(canon_jobs)], done[len(canon_jobs) :]
    # every job's diagnostics, nodes then landmarks, each in job order: the order a single thread would have produced, whatever order they finished
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
    told("recording")
    records.apply(result, manifest, build_dir)
    from loom.draft_lifecycle import attach_closed

    attach_closed(result, manifest, files)
    from loom.section_drafts import attach_context

    attach_context(result, manifest, files)
    from loom.render.review_compare import attach_comparisons

    _attach_spans(result.quilt.root, manifest, files)
    attach_comparisons(result, records, renderer, manifest, files)
    from loom.render.incoming import attach_incoming

    attach_incoming(result, renderer, manifest, files)
    from loom.render.incoming import attach_adoptions

    attach_adoptions(result, renderer, manifest, files)
    from loom.render.edits import attach_edits

    attach_edits(result, renderer, manifest, files)
    attach_versions(result, records, renderer, manifest, files, gone)
    # every preview asked for above, made by TeX together, one batch per preamble
    renderer.previews.make()
    from loom.review_queue import rows_for

    manifest["unresolved"] = rows_for(result, manifest)
    _write_source(result, fragments, files)
    _write_transcripts(result.quilt.root, files)
    from loom.files import BODIES, attach_files
    from loom.looks import DIFFS
    from loom.looks import attach_changes as attach_look_changes
    from loom.scan.quilt import reviewer_identity

    attach_files(result, manifest, files)
    from loom.render.threads import last_active

    for s in manifest.get("sessions", []):
        s["last"] = last_active(result.quilt.root, s["id"], manifest)
    from loom.config_edit import published as published_config

    manifest["config"] = published_config(result)
    attach_look_changes(result, reviewer_identity(result.quilt.root)[0], manifest, files)
    # every diagnostic, lint's, the renderer's and the records', whole and with whose it is to fix
    from loom.scan.owners import stamped

    report.diagnostics = stamped(result, [Diagnostic.from_dict(d) for d in manifest["diagnostics"]])
    manifest["diagnostics"] = [d.to_dict() for d in report.diagnostics]
    report.manifest = manifest
    prune = ("fragments/", "source/", "spans/", "transcripts/", f"{BODIES}/", f"{DIFFS}/") if wanted is None else ()
    if wanted is None:
        for rel in list(index):
            if rel not in fragments.values():
                index.pop(rel)
    # a fragment the cache skipped is already on disk as it should be: kept from the prune, not read back and rewritten
    told("publishing")
    publish(build_dir, files, manifest, prune, keep={rel for rel in fragments.values() if rel not in files})
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=0, sort_keys=True), encoding="utf-8")
    return report
