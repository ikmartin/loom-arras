"""The scan orchestrator: files, masters, closures, expansions, taxa, bibliography, assembly (book 9.1 step 1).

`scan(quilt)` is the single entry point every command uses; nothing in it writes to disk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from loom.scan.bib import BibEntry, parse_bib
from loom.scan.edges import EdgeResult, find_edges
from loom.scan.expand import Expansion, expand_master
from loom.scan.graph import Graph
from loom.scan.model import Diagnostic, Location, SourceFile, Taxon
from loom.scan.nodes import Assembly, assemble
from loom.scan.preamble import PreambleClosure, build_closure, taxa_conflicts, taxa_union
from loom.scan.quilt import Quilt
from loom.scan.relations import RelationRec, find_relations
from loom.scan.source import SKIP_DIRS, discover_files, read_source

_DOCCLASS = re.compile(r"\\documentclass\b")


@dataclass
class ScanResult:
    quilt: Quilt
    files: dict[str, SourceFile] = field(default_factory=dict)
    masters: list[str] = field(default_factory=list)
    default_master: str | None = None
    closures: dict[str, PreambleClosure] = field(default_factory=dict)
    expansions: dict[str, Expansion] = field(default_factory=dict)
    taxa: dict[str, Taxon] = field(default_factory=dict)
    bib: dict[str, BibEntry] = field(default_factory=dict)
    assembly: Assembly = field(default_factory=Assembly)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    edges: EdgeResult = field(default_factory=EdgeResult)
    relations: list[RelationRec] = field(default_factory=list)
    graph: Graph | None = None
    lint: list[Diagnostic] = field(default_factory=list)

    @property
    def nodes(self):  # type: ignore[no-untyped-def]
        return self.assembly.nodes


def find_bib_files(root: Path) -> list[str]:
    out: list[str] = []
    for path in root.rglob("*.bib"):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        out.append(rel.as_posix())
    return sorted(out)


def scan(quilt: Quilt) -> ScanResult:
    root = quilt.root
    result = ScanResult(quilt=quilt)
    for rel in discover_files(root):
        result.files[rel] = read_source(root, rel)
    for rel, src in result.files.items():
        if src.encoding != "utf-8":
            result.diagnostics.append(
                Diagnostic(
                    "warning",
                    "loom:non-utf8-source",
                    f"{rel} is not UTF-8; decoded as {src.encoding}",
                    [Location(rel, 1)],
                )
            )
    drafts = quilt.config.drafts.strip("/")
    for rel, src in result.files.items():
        if src.ignored or not _DOCCLASS.search(src.clean):
            continue
        if Path(rel).parent.as_posix() == drafts:
            result.masters.append(rel)
        else:
            result.diagnostics.append(
                Diagnostic(
                    "info",
                    "loom:documentclass-outside-drafts",
                    f"{rel} has \\documentclass but is outside {drafts}/; it is scanned as an ordinary file",
                    [Location(rel, 1)],
                )
            )
    main = quilt.config.main
    if main in result.masters:
        result.default_master = main
    elif result.masters:
        result.default_master = result.masters[0]
        result.diagnostics.append(
            Diagnostic(
                "warning",
                "loom:main-not-found",
                f"[quilt] main = {main} is not a master; using {result.masters[0]}",
                [],
            )
        )
    for rel in find_bib_files(root):
        result.bib.update(parse_bib(read_source(root, rel).text))
    from loom.scan.directives import parse_directives

    for m in result.masters:
        src = result.files[m]
        closure = build_closure(src, root, result.files, parse_directives(src))
        result.closures[m] = closure
        result.diagnostics.extend(closure.diagnostics)
        exp = expand_master(src, root, result.files)
        result.expansions[m] = exp
        result.diagnostics.extend(exp.diagnostics)
    ordered = [c for k, c in result.closures.items() if k == result.default_master] + [
        c for k, c in result.closures.items() if k != result.default_master
    ]
    result.taxa = taxa_union(ordered)
    for env, decls in taxa_conflicts(ordered):
        desc = "; ".join(f"{m}: {d}" for m, d in decls)
        result.diagnostics.append(
            Diagnostic("warning", "loom:taxon-conflict", f"environment {env} declared differently: {desc}", [])
        )
    result.assembly = assemble(
        result.files, result.closures, result.expansions, result.taxa, set(result.bib), result.default_master
    )
    result.diagnostics.extend(result.assembly.diagnostics)
    for path, fe in result.assembly.envs.items():
        src = result.files[path]
        for kind, off, env in fe.problems:
            msg = (
                f"\\begin{{{env}}} is never closed in this file"
                if kind == "unclosed"
                else f"\\end{{{env}}} has no matching \\begin in this file"
            )
            result.diagnostics.append(
                Diagnostic("error", "loom:environment-spans-files", msg, [Location(path, src.line_of(off))])
            )
    result.edges = find_edges(result.assembly, result.files)
    # relations are resolved beside the edges and stored beside them; nothing that walks the graph can reach one
    seen = find_relations(result.assembly, result.files)
    result.relations = seen.relations
    result.diagnostics.extend(seen.diagnostics)
    result.graph = Graph(result.assembly, result.edges.edges)
    from loom.scan.lint import lint as _lint

    result.lint = _lint(result, result.edges, result.graph)
    return result
