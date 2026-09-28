"""The scan orchestrator: files, masters, closures, expansions, taxa, bibliography, assembly (book 9.1 step 1).

`scan(quilt)` is the single entry point every command uses; nothing in it writes to disk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from loom.history.ledger import History, load_history
from loom.scan.bib import BIBLIOGRAPHY, BibEntry, parse_bib
from loom.scan.edges import EdgeResult, find_edges
from loom.scan.expand import Expansion, expand_master
from loom.scan.graph import Graph
from loom.scan.model import Diagnostic, Fix, Location, SourceFile, Taxon
from loom.scan.nodes import Assembly, assemble
from loom.scan.preamble import PreambleClosure, build_closure, taxa_conflicts, taxa_union
from loom.scan.quilt import Quilt
from loom.scan.relations import RelationRec, find_relations
from loom.scan.source import discover_files, read_source

_DOCCLASS = re.compile(r"\\documentclass\b")


@dataclass
class ScanResult:
    quilt: Quilt
    files: dict[str, SourceFile] = field(default_factory=dict)
    masters: list[str] = field(default_factory=list)
    default_master: str | None = None
    canon_files: list[str] = field(
        default_factory=list
    )  # the landmarks' texts, kept in their steps' directories and never scanned; the renderer draws them on its own
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
    history: History | None = None  # the ledger as this scan read it
    _trails: dict[str, list[str]] = field(default_factory=dict, repr=False)

    @cached_property
    def dependencies(self):  # type: ignore[no-untyped-def]
        from loom.records.dependencies import Dependencies

        return Dependencies(self)

    @property
    def nodes(self):  # type: ignore[no-untyped-def]
        return self.assembly.nodes

    def document_trail(self, path: str) -> list[str]:
        """Every path the document a record names by `path` has had, against this scan's masters; memoised per scan, since every record naming a document asks.

        Parameters
        ----------
        path : str
            A document path as a record wrote it.

        Returns
        -------
        list of str
            `path` first and where it is now, or was last known, last.

        See Also
        --------
        current_document : the last path, or None when it is gone.
        loom.history.ledger.History.document_trail : the walk itself.
        """
        if path not in self._trails:
            history = self.history if self.history is not None else load_history(self.quilt.history_dir)
            self._trails[path] = history.document_trail(path, set(self.masters))
        return self._trails[path]

    def current_document(self, path: str) -> str | None:
        """Where the document a record names by `path` is now: a master of this scan, or None when it is gone (book 7.3).

        Parameters
        ----------
        path : str
            A document path as a record wrote it: an acceptance row's `master`, an annotation's `in`, the sync record's documents.

        Returns
        -------
        str or None
            `path` when it is live, else the live document the history's moves lead to, else None.

        See Also
        --------
        loom.history.ledger.History.current_document : the lookup itself.
        """
        end = self.document_trail(path)[-1]
        return end if end in self.masters else None

    def document_role(self, path: str) -> str | None:
        """Which drafting directory a live document is in (book 4.1).

        Parameters
        ----------
        path : str
            A quilt-relative document path.

        Returns
        -------
        str or None
            `"drafting"` for a document only the person edits, `"drafting-ai"` for one the person and an agent both edit, None for a path that is not a live document.
        """
        if path not in self.masters:
            return None
        parent = Path(path).parent.as_posix()
        return "drafting-ai" if parent == self.quilt.config.drafting_ai else "drafting"


def _stems_taken(masters: list[str]) -> list[Diagnostic]:
    """`loom:document-stem-taken` for each stem two live documents share: arras routes a document and loom writes its PDF by stem."""
    by_stem: dict[str, list[str]] = {}
    for m in masters:
        by_stem.setdefault(Path(m).stem, []).append(m)
    return [
        Diagnostic(
            "error",
            "loom:document-stem-taken",
            f"{' and '.join(paths)} are both named {stem}; arras and the build tell documents apart by name, so rename one",
            [Location(p, 1) for p in paths],
        )
        for stem, paths in sorted(by_stem.items())
        if len(paths) > 1
    ]


def skipped_dirs(quilt: Quilt) -> tuple[str, ...]:
    """Directories the scan never enters: `retired/`, `notes/`, the author's reference material (book 4.1), and the history directory wherever `[quilt] history` puts it, whose frozen texts and landmarks are old versions of the quilt's own."""
    return ("retired", "notes", Path(quilt.config.history).as_posix())


def landmark_documents(quilt: Quilt) -> list[str]:
    """The quilt-relative path of every landmark's text, oldest first: the file each landmark step keeps in its directory (book 17.9)."""
    from loom.history.ledger import load_history

    history = load_history(quilt.history_dir)
    out: list[str] = []
    for e in history.landmarks():
        path = history.landmark_path(e)
        if path.is_file():
            out.append(path.relative_to(quilt.root).as_posix())
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
    result.canon_files = landmark_documents(quilt)
    for rel in paths:
        result.files[rel] = read_source(root, rel, overlay.get(rel))
    history = result.history = load_history(quilt.history_dir)
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
    drafting, drafting_ai = quilt.config.drafting, quilt.config.drafting_ai
    for rel, src in result.files.items():
        if src.ignored or not _DOCCLASS.search(src.clean):
            continue
        if Path(rel).parent.as_posix() in (drafting, drafting_ai):
            result.masters.append(rel)
        else:
            result.diagnostics.append(
                Diagnostic(
                    "info",
                    "loom:documentclass-outside-drafts",
                    f"{rel} has \\documentclass but is outside the drafting directories {drafting}/ and {drafting_ai}/; it is scanned as an ordinary file",
                    [Location(rel, 1)],
                )
            )
    result.diagnostics.extend(_stems_taken(result.masters))
    main = quilt.config.main
    own = [m for m in result.masters if result.document_role(m) == "drafting"]
    if main in own:
        result.default_master = main
    elif own:
        result.default_master = own[0]
        result.diagnostics.append(
            Diagnostic(
                "warning",
                "loom:main-not-found",
                f"[quilt] main = {main} is not a master; using {own[0]}",
                [],
            )
        )
    # the quilt's own bibliography, gathered from the landmarks by `loom refs scan`; an author's `.bib` reaches it only through a landmark that names it (book 8.2)
    if (root / BIBLIOGRAPHY).is_file():
        result.bib.update(parse_bib(read_source(root, BIBLIOGRAPHY).text))
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
        result.files,
        result.closures,
        result.expansions,
        result.taxa,
        set(result.bib),
        result.default_master,
        result.quilt.config.basis,
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
