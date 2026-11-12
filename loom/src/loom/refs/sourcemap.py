"""Where words on a cited work's page stand in its LaTeX source, for a work whose store holds `src/`.

Computed when the manifest is published and never recorded (P3): the page is the record, and the source a reading of it. The source is read as `digest.extract.extract_digest` reads it, its expansion's files each indexed once per build as `tex.align.Source`, and a mark's words are placed with `Source.place`, nearest the share of the file its page is of the paper.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loom.scan.scan import ScanResult
from loom.tex.align import Source, rendered_words, run_positions

#: One index per work, kept for the scan it was made for: a build publishes every annotation on a work from one.
_INDEX: dict[tuple[str, str], tuple[ScanResult, list[_File] | None]] = {}


@dataclass
class _File:
    """One file of a work's source: its path under the quilt, its text, and its words."""

    rel: str
    text: str
    source: Source


def _index(result: ScanResult, citekey: str) -> list[_File] | None:
    """The files of the work's source as `extract_digest` reads them, each indexed; None for a work with no source on this machine or one that does not read."""
    root: Path = result.quilt.root
    key = (str(root), citekey)
    kept = _INDEX.get(key)
    if kept is not None and kept[0] is result:
        return kept[1]
    out: list[_File] | None = None
    entry = result.bib.get(citekey)
    if entry is not None:
        try:
            out = _read(root, entry)
        except Exception:  # a source loom cannot read is no source; the page stands alone
            out = None
    _INDEX[key] = (result, out)
    return out


def _read(root: Path, entry: Any) -> list[_File] | None:
    from loom.digest.extract import TEXT_EXTS
    from loom.refs.build import main_tex
    from loom.reshape.importer import closure_of
    from loom.scan.directives import parse_directives
    from loom.scan.expand import expand_master
    from loom.scan.preamble import build_closure
    from loom.scan.source import read_source
    from loom.tex.tex4ht import definitions

    src = main_tex(root, entry)
    if src is None:
        return None
    paper_dir = src.resolve().parent
    found, _outside = closure_of(paper_dir, src.resolve())
    files = {rel: read_source(paper_dir, rel) for rel, path in found.items() if path.suffix.lower() in TEXT_EXTS}
    if src.name not in files:
        files[src.name] = read_source(paper_dir, src.name)
    master = files[src.name]
    closure = build_closure(master, paper_dir, files, parse_directives(master), foreign=True)
    macros, environments = definitions(closure)
    exp = expand_master(master, paper_dir, files)
    out = []
    for rel in [src.name, *(r for r in exp.reached if r != src.name)]:
        if rel in files and rel.endswith(".tex"):
            rel_root = (paper_dir / rel).resolve().relative_to(root.resolve()).as_posix()
            out.append(_File(rel_root, files[rel].text, Source(files[rel].clean, macros, environments)))
    return out


def source_of(
    result: ScanResult, citekey: str, exact: str, prefix: str, suffix: str, page: int
) -> dict[str, Any] | None:
    """Where a mark's words on a page of `citekey` stand in the work's source.

    Parameters
    ----------
    result : ScanResult
        The scan the manifest is published from.
    citekey : str
        The work.
    exact, prefix, suffix : str
        The mark's words and the words either side of them, as it recorded them.
    page : int
        The page it stands on now, from 1; its share of the paper is where in each file the words are looked for first.

    Returns
    -------
    dict or None
        `{path, bytes, exact}`, a LaTeX anchor's shape: the file under the quilt, the range its words take in it as byte offsets, and the source there; None for a work with no source, a mark with no words, or words not found.
    """
    words = rendered_words(exact)
    if not words or page < 1:
        return None
    files = _index(result, citekey)
    if not files:
        return None
    pages = _pages(result, citekey) or page
    before, after = rendered_words(prefix), rendered_words(suffix)
    for run, lead in (([*before, *words, *after], len(before)), (words, 0)):
        for f in files:
            near = int(len(f.text) * (page - 1) / max(pages, 1))
            got = f.source.place(run, near)
            if got is None:
                continue
            # the context finds the place, and the mark's own words within it its ends
            first = bisect_left(f.source.starts, got.start)
            last = bisect_right(f.source.starts, got.end) - 1
            at = run_positions(f.source.texts, run, first, last)
            mine = [i for i in at[lead : lead + len(words)] if i is not None]
            if mine:
                return _span(f, f.source.words[min(mine)].start, f.source.words[max(mine)].end)
    return None


def _span(f: _File, a: int, b: int) -> dict[str, Any]:
    """Characters `a` to `b` of a source file as a LaTeX anchor carries them."""
    return {
        "path": f.rel,
        "bytes": [len(f.text[:a].encode("utf-8")), len(f.text[:b].encode("utf-8"))],
        "exact": f.text[a:b],
    }


def _pages(result: ScanResult, citekey: str) -> int | None:
    """How many pages the work's filed copy has, from its map."""
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map

    entry = result.bib.get(citekey)
    m = read_map(work_dir(result.quilt.root, entry)) if entry is not None else None
    return m.pages if m else None
