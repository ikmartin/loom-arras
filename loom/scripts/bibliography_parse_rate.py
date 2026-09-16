#!/usr/bin/env python3
"""Measure how much of a fetched paper's bibliography loom could actually read.

The recursive reference crawl (WQ-02) rests entirely on other papers' bibliographies: to follow a citation you must parse the `.bbl` or `.bib` that came with the source, and recover an identifier from each entry. Nobody has measured how often that works on real mathematics papers, and if the answer is low the crawl's design changes shape. This reports the number and changes nothing.

It reads only what is already unpacked under `refs/`, touches no network, and writes nothing.

Usage: uv run python scripts/bibliography_parse_rate.py [QUILT ...]
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from loom.refs.identity import declared  # noqa: E402
from loom.scan.bib import parse_bib  # noqa: E402

# arXiv does not run BibTeX, so a submitter must supply the formatted bibliography -- but measuring real papers shows
# they usually do it by pasting `\begin{thebibliography}` into a .tex file rather than shipping a .bbl. So the unit is
# `\bibitem` wherever it occurs, not a file extension, which is the thing a crawler must actually cope with.
_BIBITEM = re.compile(r"\\bibitem(?:\[[^\]]*\])?\s*\{([^}]*)\}")
# `\arXiv{2407.08747}` is as common as a bare "arXiv:2407.08747", so the separator includes a brace
_ARXIV = re.compile(r"arxiv[.:/\s{]*((?:[a-z-]+/)?\d{4}\.?\d{4,5}(?:v\d+)?)", re.I)
_DOI = re.compile(r"\b10\.\d{4,9}/[^\s,}$\\]+")


def _bbl_entries(text: str) -> list[str]:
    """Each `\\bibitem`'s text, which is a formatted reference rather than fields."""
    spans = [m.start() for m in _BIBITEM.finditer(text)]
    if not spans:
        return []
    bounds = [*spans, len(text)]
    return [text[a:b] for a, b in zip(bounds[:-1], bounds[1:], strict=True)]


def _identified(entry_text: str) -> str | None:
    if m := _ARXIV.search(entry_text):
        return f"arXiv:{m.group(1)}"
    if m := _DOI.search(entry_text):
        return f"doi:{m.group(0).rstrip('.')}"
    return None


def survey(root: Path) -> Counter[str]:
    c: Counter[str] = Counter()
    refs = root / "refs"
    if not refs.is_dir():
        return c
    for work in sorted(p for p in refs.rglob("src") if p.is_dir()):
        c["works"] += 1
        bibs = list(work.rglob("*.bib"))
        if bibs:
            c["with .bib"] += 1
            for b in bibs:
                entries = parse_bib(b.read_text(encoding="utf-8", errors="replace"))
                c["entries"] += len(entries)
                c["identified"] += sum(1 for e in entries.values() if declared(e))
            continue
        items: list[str] = []
        for b in sorted(work.rglob("*.bbl")) + sorted(work.rglob("*.tex")):
            items += _bbl_entries(b.read_text(encoding="utf-8", errors="replace"))
        if items:
            c["with bibitems"] += 1
            c["entries"] += len(items)
            c["identified"] += sum(1 for i in items if _identified(i))
        else:
            c["with neither"] += 1
    return c


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or [Path.cwd()]
    total: Counter[str] = Counter()
    for root in roots:
        c = survey(root)
        total.update(c)
        if c["works"]:
            print(
                f"{root}: {c['works']} fetched work(s); {c['with .bib']} with .bib, {c['with bibitems']} with \\bibitem lists, {c['with neither']} neither"
            )
    if not total["works"]:
        print("no fetched sources under refs/; run loom digest fetch first", file=sys.stderr)
        return 2
    parseable = total["with .bib"] + total["with bibitems"]
    print()
    print(f"parseable bibliographies: {parseable} of {total['works']} ({100 * parseable / total['works']:.0f}%)")
    if total["entries"]:
        print(
            f"entries with a usable identifier: {total['identified']} of {total['entries']} ({100 * total['identified'] / total['entries']:.0f}%)"
        )
    print()
    print("WQ-02's trigger is the first number above 70% on the depth-1 sources of demos/relloc and demos/acgs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
