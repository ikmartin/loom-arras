"""`loom build` (book 9.1): scan, read records, read numbering, render, write the manifest, publish.

Rendering is cached by an input hash per fragment (the text of the files it draws on plus the numbering), so a build after a one-line edit re-renders one node and its masters.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.records.store import Records
from loom.render.fragments import FragmentRenderer, RenderPlan
from loom.render.manifest import build_manifest
from loom.render.marks import MarkEntry, place_marks
from loom.render.publish import publish
from loom.scan.model import Diagnostic
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult, scan
from loom.tex.aux import AuxNumber, read_numbers
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


def _input_hash(result: ScanResult, key: str, numbers: dict[str, dict[str, AuxNumber]]) -> str:
    n = result.nodes[key]
    h = hashlib.sha256()
    h.update(__version__.encode())
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
    for m in sorted(numbers):
        for lab, num in sorted(numbers[m].items()):
            h.update(f"{m}|{lab}|{num.number}|{num.page}".encode())
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


def build(quilt: Quilt, keys: list[str] | None = None, records: Records | None = None) -> BuildReport:
    root = quilt.root
    build_dir = root / "build"
    cache_dir = build_dir / "cache"
    result = scan(quilt)
    records = records or Records(root)
    marks = _marks_by_node(result, records)
    numbers = {m: read_numbers(root, m) for m in result.masters}
    plan = RenderPlan(result=result, numbers=numbers, svg_cache=cache_dir / "svg", svg_out=build_dir / "svg")
    renderer = FragmentRenderer(plan)
    index_path = cache_dir / "fragments.json"
    index: dict[str, str] = {}
    if index_path.exists():
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
    for key, kind in targets:
        rel = fragment_path(result, key)
        label = key if kind == "node" else f"{kind}:{key}"
        fragments[label] = rel
        digest = _input_hash(result, key, numbers) + _marks_hash(marks, key, result)
        existing = build_dir / rel
        if (wanted is not None and key not in wanted) or (index.get(rel) == digest and existing.exists()):
            report.skipped.append(key)
            continue
        if kind == "node":
            html_out = place_marks(renderer.node_fragment(key), marks.get(key, []))
        elif kind == "master":
            html_out = place_marks(
                renderer.master_fragment(key),
                [m for k, ms in marks.items() for m in ms if key in result.nodes[k].reached_by],
            )
        else:
            html_out = renderer.digest_fragment(key)
        files[rel] = html_out
        index[rel] = digest
        report.rendered.append(key)
    report.diagnostics = list(result.lint) + plan.diagnostics
    manifest = build_manifest(result, numbers, fragments, report.diagnostics)
    records.apply(result, manifest, build_dir)
    report.diagnostics = [d for d in report.diagnostics] + [
        Diagnostic(d["severity"], d["code"], d["message"]) for d in manifest["diagnostics"][len(report.diagnostics) :]
    ]
    report.manifest = manifest
    prune = ("fragments/",) if wanted is None else ()
    if wanted is None:
        for rel in list(index):
            if rel not in fragments.values():
                index.pop(rel)
        for rel in fragments.values():
            if rel not in files and (build_dir / rel).exists():
                files[rel] = (build_dir / rel).read_text(encoding="utf-8")
    publish(build_dir, files, manifest, prune)
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=0, sort_keys=True), encoding="utf-8")
    return report
