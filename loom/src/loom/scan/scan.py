"""The scan orchestrator: files, masters, closures, expansions, taxa, bibliography, assembly: the first step of every build.

`scan(quilt)` is the single entry point every command uses; nothing in it writes to disk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from loom.history.ledger import History, load_history
from loom.paths import NOTES_DIR, RETIRED, document_dir
from loom.scan.bib import BIBLIOGRAPHY, BibEntry, parse_bib
from loom.scan.edges import EdgeResult, find_edges
from loom.scan.expand import Expansion, expand_master
from loom.scan.graph import Graph
from loom.scan.model import Diagnostic, Fix, Location, SourceFile, Taxon
from loom.scan.nodes import Assembly, assemble
from loom.scan.preamble import PreambleClosure, build_closure, taxa_conflicts, taxa_union
from loom.scan.quilt import Quilt
from loom.scan.relations import RelationRec, find_relations
from loom.scan.source import SKIP_DIRS, SKIP_PREFIXES, discover_files, read_source

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
    # bases a caller states for documents this scan's own history cannot place: a section draft read against its saved context
    base_overrides: dict[str, str] = field(default_factory=dict, repr=False)

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
        """Where the document a record names by `path` is now: a master of this scan, or None when it is gone.

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

    @cached_property
    def agent_documents(self) -> frozenset[str]:
        """The live documents an agent and the person both edit: every copy and every document written from scratch the history records, where its moves have taken them, and any document in the agent's drafting directory, which a file put there by hand keeps an agent's (`loom:agent-document-unrecorded`)."""
        history = self.history if self.history is not None else load_history(self.quilt.history_dir)
        live = set(self.masters)
        here = {m for m in self.masters if Path(m).parent.as_posix() == self.quilt.config.drafting_ai}
        return frozenset({*history.copies(live), *history.written(live), *here})

    @cached_property
    def _bases(self) -> dict[str, str]:
        history = self.history if self.history is not None else load_history(self.quilt.history_dir)
        live = set(self.masters)
        bases = {m: document_dir(m) for m in self.masters}
        for copy, source in history.copies(live).items():
            bases[copy] = document_dir(source)
        if self.default_master is not None:
            for written in history.written(live):
                bases[written] = document_dir(self.default_master)
        bases.update({p: b for p, b in self.base_overrides.items() if p in bases})
        return bases

    def base_of(self, path: str) -> str:
        """The quilt-relative directory a document compiles from, and its names resolve against (P12).

        Parameters
        ----------
        path : str
            A quilt-relative document path.

        Returns
        -------
        str
            A person's document's own directory; an agent copy's source's, where the history's moves have taken it; a document written from scratch, the default document's, whose preamble it was given; '' at the root. A path that is not a live document gives its own directory.
        """
        return self._bases.get(path, document_dir(path))

    def document_role(self, path: str) -> str | None:
        """Whose a live document is.

        Parameters
        ----------
        path : str
            A quilt-relative document path.

        Returns
        -------
        str or None
            `"agent"` for one the person and an agent both edit (`agent_documents`), `"person"` for every other live document, None for a path that is not one.
        """
        if path not in self.masters:
            return None
        return "agent" if path in self.agent_documents else "person"


def skipped_dirs(quilt: Quilt) -> tuple[str, ...]:
    """Directories the scan never enters: `retired/`, `notes/`, the author's reference material, the history directory wherever `[quilt] history` puts it, whose frozen texts and landmarks are old versions of the quilt's own, and the sync directory when it sits inside the quilt, whose files are copies of the quilt's sources."""
    from loom.sync import skipped_directory

    synced = skipped_directory(quilt.root)
    return (RETIRED, NOTES_DIR, Path(quilt.config.history).as_posix(), *((synced,) if synced else ()))


def unread_dir(quilt: Quilt, rel: str) -> str | None:
    """The directory that keeps the scan out of a quilt-relative path.

    Parameters
    ----------
    quilt : Quilt
        The quilt `rel` is in.
    rel : str
        A quilt-relative POSIX path.

    Returns
    -------
    str or None
        The tool or loom directory `discover_files` skips, or the `skipped_dirs` entry, that `rel` sits in; None when the scan reads it.
    """
    for part in Path(rel).parts[:-1]:
        if part in SKIP_DIRS:
            return part
    for prefix in SKIP_PREFIXES:
        if rel.startswith(prefix):
            return prefix.rstrip("/")
    return next((d for d in skipped_dirs(quilt) if rel.startswith(f"{d}/")), None)


def landmark_bases(quilt: Quilt) -> dict[str, str]:
    """Each landmark's text, quilt-relative, -> the directory its names resolve against (`History.landmark_base`)."""
    history = load_history(quilt.history_dir)
    out: dict[str, str] = {}
    for e in history.landmarks():
        path = history.landmark_path(e)
        if path.is_file():
            out[path.relative_to(quilt.root).as_posix()] = history.landmark_base(e)
    return out


def landmark_documents(quilt: Quilt) -> list[str]:
    """The quilt-relative path of every landmark's text, oldest first: the file each landmark step keeps in its directory."""
    from loom.history.ledger import load_history

    history = load_history(quilt.history_dir)
    out: list[str] = []
    for e in history.landmarks():
        path = history.landmark_path(e)
        if path.is_file():
            out.append(path.relative_to(quilt.root).as_posix())
    return out


def scan(quilt: Quilt, overlay: dict[str, str] | None = None, *, bases: dict[str, str] | None = None) -> ScanResult:
    """Scan a quilt. `overlay` maps quilt-relative paths to the text of unsaved editor buffers, which stand in for what is on disk; a path the quilt does not contain is added, so a new file is scanned before it is first saved. `bases` states the directory a document compiles from where the quilt's own history cannot (`ScanResult.base_of`)."""
    root = quilt.root
    result = ScanResult(quilt=quilt, base_overrides=dict(bases or {}))
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
    from loom.draft_lifecycle import closed_drafts

    for rel in closed_drafts(history):
        if rel in result.files:
            result.files[rel].ignored = True
    for rel, entry in sorted(history.superseded_paths().items()):
        src = result.files.get(rel)
        if src is None:
            continue
        # a conversion recorded that its output replaced this document, so it defines nothing until `loom live` says otherwise
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
    # a document is any file read here with \documentclass, wherever it sits; what is not read, ignored or superseded is none
    result.masters.extend(rel for rel, src in result.files.items() if not src.ignored and _DOCCLASS.search(src.clean))
    main = quilt.config.main
    own = [m for m in result.masters if result.document_role(m) == "person"]
    if main in own:
        result.default_master = main
    elif main and own:
        result.default_master = own[0]
        result.diagnostics.append(
            Diagnostic(
                "warning",
                "loom:main-not-found",
                f"[quilt] main = {main} is not a master; using {own[0]}",
                [],
            )
        )
    elif len(own) == 1:
        result.default_master = own[0]
    elif own:
        # several documents and no word on which is the default: choosing one by its path would be arbitrary
        result.diagnostics.append(
            Diagnostic(
                "info",
                "loom:main-unset",
                f"[quilt] main is unset and the quilt holds {len(own)} documents, so none is the default one loom compiles and reads macros from; set main in config.toml to one of them",
                [],
            )
        )
    # the quilt's own bibliography, gathered from the landmarks by `loom library update`; an author's `.bib` reaches it only through a landmark that names it
    if (root / BIBLIOGRAPHY).is_file():
        result.bib.update(parse_bib(read_source(root, BIBLIOGRAPHY).text))
    from loom.scan.directives import parse_directives

    for m in result.masters:
        src = result.files[m]
        base = result.base_of(m)
        closure = build_closure(src, root, result.files, parse_directives(src), base=base)
        result.closures[m] = closure
        result.diagnostics.extend(closure.diagnostics)
        exp = expand_master(src, root, result.files, base)
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
    from loom.refs.scan import other_versions

    result.edges = find_edges(result.assembly, result.files, other_versions(result.bib))
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
