"""`loom build` (book 9.1): scan, read records, read numbering, render, write the manifest, publish.

Rendering is cached by an input hash per fragment (the text of the files it draws on plus the numbering), so a build after a one-line edit re-renders one node and its masters.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.render.fragments import FragmentRenderer, RenderPlan
from loom.render.manifest import build_manifest
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


def build(quilt: Quilt, keys: list[str] | None = None, records: Any | None = None) -> BuildReport:
    root = quilt.root
    build_dir = root / "build"
    cache_dir = build_dir / "cache"
    result = scan(quilt)
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
        digest = _input_hash(result, key, numbers)
        existing = build_dir / rel
        if (wanted is not None and key not in wanted) or (index.get(rel) == digest and existing.exists()):
            report.skipped.append(key)
            continue
        if kind == "node":
            html_out = renderer.node_fragment(key)
        elif kind == "master":
            html_out = renderer.master_fragment(key)
        else:
            html_out = renderer.digest_fragment(key)
        files[rel] = html_out
        index[rel] = digest
        report.rendered.append(key)
    report.diagnostics = list(result.lint) + plan.diagnostics
    manifest = build_manifest(result, numbers, fragments, report.diagnostics, records)
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
