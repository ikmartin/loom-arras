"""Landmarks as fragments: a landmark is made by TeX as the document it is, with no node identity and no marks; never compiled itself, it prints its live document's numbers.

A landmark's text lives in its step's directory, which the scan never enters, so nothing here goes through the assembly: the file is read on its own, its preamble closure is built from itself, and its labels anchor within the page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.history.ledger import Entry, History
from loom.paths import document_build
from loom.render.fragments import FragmentRenderer, Owner, _from_tex, bare_preamble, plain_text
from loom.render.markup import esc
from loom.scan.digests import loaded_packages
from loom.scan.envtree import norm_label
from loom.scan.macros import compatibility_macros, declared_alphabets, package_macros, to_mathjax
from loom.scan.model import SourceFile
from loom.scan.preamble import PreambleClosure, build_closure
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult
from loom.scan.source import read_source
from loom.tex.aux import read_cite_labels, read_numbers
from loom.tex.runner import normalise_engine

_LABEL = re.compile(r"\\label\s*\{([^}]*)\}")


@dataclass
class CanonDoc:
    path: str  # quilt-relative
    stem: str
    src: SourceFile
    closure: PreambleClosure
    title: str
    step: Entry | None = None
    labels: dict[str, str] = field(default_factory=dict)
    pairs: dict[str, str] = field(default_factory=dict)  # key -> pair hash of the version its stamp kept
    base: str = ""  # the directory its names resolve against: its document's (`History.landmark_base`)
    live: str = ""  # the live document it is a version of, whose numbers and citation labels it reads when it has none of its own


def title_of(src: SourceFile) -> str | None:
    from loom.scan.tokenize import match_group

    m = re.search(r"\\title\s*(\[[^\]]*\])?\s*\{", src.clean)
    if not m:
        return None
    end = match_group(src.clean, m.end() - 1)
    return plain_text(src.text[m.end() : end - 1]) if end > 0 else None


def load_canon(quilt: Quilt, result: ScanResult, history: History) -> list[CanonDoc]:
    """One CanonDoc per landmark, read outside the scan (`result.files` is left alone) and closed over its own preamble."""
    steps = {history.landmark_path(e).relative_to(quilt.root).as_posix(): e for e in history.landmarks()}
    out: list[CanonDoc] = []
    for rel in result.canon_files:
        src = read_source(quilt.root, rel)
        from loom.scan.directives import parse_directives

        entry = steps.get(rel)
        base = history.landmark_base(entry) if entry is not None else ""
        recorded = (entry.get("in") or (entry.get("drafted") or {}).get("path")) if entry is not None else None
        live = (history.current_document(recorded, result.masters) or "") if isinstance(recorded, str) else ""
        closure = build_closure(src, quilt.root, {}, parse_directives(src), base=base)
        stem = Path(rel).stem
        labels = {norm_label(m.group(1)): norm_label(m.group(1)) for m in _LABEL.finditer(src.clean)}
        out.append(
            CanonDoc(
                path=rel,
                stem=stem,
                src=src,
                closure=closure,
                title=title_of(src) or stem,
                step=steps.get(rel),
                labels=labels,
                pairs=landmark_pairs(history, steps.get(rel)),
                base=base,
                live=live,
            )
        )
    return out


def landmark_pairs(history: History, entry: Entry | None) -> dict[str, str]:
    """Each key a landmark reaches -> `pair_hash` of the version its stamp kept, what its environments pair by in compare."""
    if entry is None or entry.step is None:
        return {}
    from loom.history.versions import read_version
    from loom.scan.hashing import pair_hash

    out: dict[str, str] = {}
    for key in entry.get("reaches") or []:
        try:
            out[key] = pair_hash(read_version(history, key, str(entry.step))[1])
        except LookupError:
            continue
    return out


def canon_fragment_path(doc: CanonDoc) -> str:
    return f"fragments/canon/{doc.stem}.html"


def macro_set(doc: CanonDoc) -> list[dict[str, Any]]:
    """The MathJax macros of the canon's own preamble: a landmark renders as it compiled, whatever the drafting documents have since become."""
    macros = {k: v for k, v in doc.closure.macros.items() if v.kind != "let"}
    for name, macro in declared_alphabets(doc.closure.clean_text()).items():
        macros.setdefault(name, macro)
    for name, macro in package_macros(loaded_packages(doc.closure)).items():
        macros.setdefault(name, macro)
    macros.update(compatibility_macros(macros))
    return to_mathjax(macros)


class CanonRenderer:
    """Makes landmarks by TeX as the documents they are, under their own preambles, with none of a node's identity: a statement pairs with the live one by its label."""

    def __init__(self, renderer: FragmentRenderer) -> None:
        self.renderer = renderer
        self.result = renderer.result
        self.root = renderer.result.quilt.root

    def owner(self, doc: CanonDoc) -> Owner:
        """The landmark as the document its text is read in: its own preamble and directory, and, as it is never compiled, its live document's numbers, citation labels and aux."""
        root = self.root
        begin = re.search(r"\\begin\s*\{document\}", doc.src.clean)
        own = root / document_build(doc.path) / f"{Path(doc.path).stem}.aux"
        live = root / document_build(doc.live) / f"{Path(doc.live).stem}.aux" if doc.live else None
        return Owner(
            doc.path,
            doc.base,
            doc.closure,
            read_numbers(root, doc.path) or (read_numbers(root, doc.live) if doc.live else {}),
            read_cite_labels(root, doc.path) or (read_cite_labels(root, doc.live) if doc.live else {}),
            dict(doc.closure.macros),
            doc.src.text[: begin.start()] if begin else bare_preamble(doc.closure.taxa),
            own if own.is_file() else (live if live is not None and live.is_file() else None),
            normalise_engine(doc.closure.engine or self.result.quilt.config.engine),
        )

    def fragment(self, doc: CanonDoc) -> str:
        """The landmark's fragment: its body cut at each statement and proof standing at its top level, made by TeX in one batch, and shaped as a page is."""
        begin = re.search(r"\\begin\s*\{document\}", doc.src.clean)
        end_m = re.search(r"\\end\s*\{document\}", doc.src.clean)
        start = begin.end() if begin else 0
        end = end_m.start() if end_m else len(doc.src.clean)
        names = {*doc.closure.taxa, "proof"}
        regions = [(doc.path, a, b) for a, b in top_envs(doc.src.clean, start, end, names)]
        made = self.renderer.snippet_page(
            self.owner(doc), regions, [], files={doc.path: doc.src}, pairs=doc.pairs, labels=doc.labels
        )
        head = f'<h1 data-src="{doc.path}:0:0">{esc(doc.title)}</h1>'
        return _stamp(_from_tex(head + made.master_html()), doc)


_OPEN = re.compile(r"\\(begin|end)\s*\{([^}]*)\}")


def top_envs(clean: str, start: int, end: int, names: set[str]) -> list[tuple[int, int]]:
    """`clean[start:end]` cut into spans: each environment named in `names` that stands outside every other environment, and the prose between, blank prose left out."""
    out: list[tuple[int, int]] = []
    pos = start
    depth = 0
    opened: int | None = None
    for m in _OPEN.finditer(clean, start, end):
        name = m.group(2).strip()
        if name == "document":
            continue
        if m.group(1) == "begin":
            if depth == 0 and name in names:
                if clean[pos : m.start()].strip():
                    out.append((pos, m.start()))
                opened = m.start()
            depth += 1
        else:
            depth = max(depth - 1, 0)
            if depth == 0 and opened is not None:
                out.append((opened, m.end()))
                pos, opened = m.end(), None
    if opened is not None:
        pos = opened
    if clean[pos:end].strip():
        out.append((pos, end))
    return out


def _stamp(fragment: str, doc: CanonDoc) -> str:
    m = re.match(r"\s*<(\w+)", fragment)
    if not m:
        return fragment
    i = m.end()
    return fragment[:i] + f' data-fragment="canon" data-macros="canon:{esc(doc.stem)}"' + fragment[i:]


def _preamble_for(closure: PreambleClosure) -> str:
    """The canon's own preamble text: it is flat and self-contained, so its first fragment is the whole of it."""
    first = closure.fragments[0] if closure.fragments else None
    return first.src.text[first.start : first.end] if first else ""


def canon_entry(doc: CanonDoc, fragment: str, hashed: str) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "path": doc.path,
        "stem": doc.stem,
        "title": doc.title,
        "fragment": fragment,
        "hash": hashed,
    }
    if doc.step is not None and doc.step.step is not None:
        entry["step"] = f"{doc.step.step:04d}"
        entry["name"] = doc.step.name
        if doc.step.message:
            entry["message"] = doc.step.message
        entry["when"] = doc.step.when
        # a landmark loom kept itself, before an adoption or a sync wrote over the draft, rather than one the author stamped
        if doc.step.data.get("kept_for"):
            entry["kept_for"] = doc.step.data["kept_for"]
    return entry
