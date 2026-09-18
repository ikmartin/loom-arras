"""The scan orchestrator: files, masters, closures, expansions, taxa, bibliography, assembly (book 9.1 step 1).

`scan(quilt)` is the single entry point every command uses; nothing in it writes to disk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from loom.history.ledger import load_history
from loom.scan.bib import BibEntry, parse_bib
from loom.scan.edges import EdgeResult, find_edges
from loom.scan.expand import Expansion, expand_master
from loom.scan.graph import Graph
from loom.scan.model import Diagnostic, Fix, Location, SourceFile, Taxon
from loom.scan.nodes import Assembly, assemble
from loom.scan.preamble import PreambleClosure, build_closure, taxa_conflicts, taxa_union
from loom.scan.quilt import Quilt
from loom.scan.relations import RelationRec, find_relations
from loom.scan.source import IGNORE_RE, SKIP_DIRS, SKIP_PREFIXES, discover_files, read_source

_DOCCLASS = re.compile(r"\\documentclass\b")


@dataclass
class ScanResult:
    quilt: Quilt
    files: dict[str, SourceFile] = field(default_factory=dict)
    masters: list[str] = field(default_factory=list)
    default_master: str | None = None
    canon_files: list[str] = field(
        default_factory=list
    )  # the canon documents, never scanned; the renderer draws them on its own
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


def find_bib_files(root: Path, skip_top: tuple[str, ...] = ()) -> list[str]:
    """The quilt's bibliography files.

    A `.bib` inside a fetched or crawled work's source under `refs/`, or inside a run under `ai/`, is someone else's bibliography, not the quilt's; reading it would merge a whole library's references into the author's. The canon directory and `retired/` (`skip_top`) hold nothing that is source.
    """
    out: list[str] = []
    for path in root.rglob("*.bib"):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if rel.as_posix().startswith(SKIP_PREFIXES):
            continue
        if len(rel.parts) > 1 and rel.parts[0] in skip_top:
            continue
        out.append(rel.as_posix())
    return sorted(out)


def skipped_dirs(quilt: Quilt) -> tuple[str, ...]:
    """Top-level directories the scan never enters: the canon directory and `retired/` (book 4.1.2)."""
    return (quilt.config.canon, "retired")


def canon_documents(quilt: Quilt) -> list[str]:
    """The `.tex` files directly under the canon directory, sorted; `% !LOOM ignore` in the first twenty lines is honoured."""
    d = quilt.canon_dir
    if not d.is_dir():
        return []
    out: list[str] = []
    for p in sorted(d.glob("*.tex")):
        head = "\n".join(p.read_text(encoding="utf-8", errors="replace").split("\n", 20)[:20])
        if IGNORE_RE.search(head):
            continue
        out.append(p.relative_to(quilt.root).as_posix())
    return out


def scan(quilt: Quilt, overlay: dict[str, str] | None = None) -> ScanResult:
    """Scan a quilt. `overlay` maps quilt-relative paths to the text of unsaved editor buffers, which stand in for what is on disk; a path the quilt does not contain is added, so a new file is scanned before it is first saved."""
    root = quilt.root
    result = ScanResult(quilt=quilt)
    overlay = overlay or {}
    skip = skipped_dirs(quilt)
    paths = list(discover_files(root, skip))
    for extra in sorted(overlay):
        if extra not in paths and not extra.startswith(tuple(f"{d}/" for d in skip)):
            paths.append(extra)
    result.canon_files = canon_documents(quilt)
    for rel in paths:
        result.files[rel] = read_source(root, rel, overlay.get(rel))
    history = load_history(quilt.history_dir)
    for rel, entry in sorted(history.superseded_paths().items()):
        src = result.files.get(rel)
        if src is None:
            continue
        # a conversion recorded that its output replaced this document, so it defines nothing until `loom live` says otherwise (book 17.12)
        src.ignored = True
        src.superseded = entry.action
        result.diagnostics.append(
            Diagnostic(
                "info",
                "loom:superseded-file",
                f"{rel} was superseded by {', '.join(str(t) for t in _targets(entry))} ({entry.action}, {entry.when[:10]}); it defines nothing",
                [Location(rel, 1)],
                subject="record",
                fixes=[Fix("make it live again", f"loom live {rel}")],
            )
        )
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
    drafting = quilt.config.drafting
    for rel, src in result.files.items():
        if src.ignored or not _DOCCLASS.search(src.clean):
            continue
        if Path(rel).parent.as_posix() == drafting:
            result.masters.append(rel)
        else:
            result.diagnostics.append(
                Diagnostic(
                    "info",
                    "loom:documentclass-outside-drafts",
                    f"{rel} has \\documentclass but is outside the drafting directory {drafting}/; it is scanned as an ordinary file",
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
    for rel in find_bib_files(root, skip):
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


def _targets(entry) -> list[str]:  # type: ignore[no-untyped-def]
    to = entry.get("to")
    if isinstance(to, list):
        return [str(t) for t in to]
    if isinstance(to, dict):
        return [str(to.get("path", ""))]
    return [str(to)] if to else []
