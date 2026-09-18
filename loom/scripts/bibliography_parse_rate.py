#!/usr/bin/env python3
"""Measure how much of a fetched paper's bibliography loom could actually read.

The reference crawl (book 8.13) reads a fetched preprint's references from its own bibliography: the `.bib` that came with the source, or its `\\bibitem`s wherever they sit, with an arXiv number or DOI read from each entry's text by `loom.refs.crawl.bibitem`. This reports how often that works on the sources under a quilt's `refs/`, and changes nothing.

It reads only what is already unpacked under `refs/`, touches no network, and writes nothing.

Usage: uv run python scripts/bibliography_parse_rate.py [QUILT ...]
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from loom.refs.crawl import bibitem  # noqa: E402
from loom.refs.identity import declared  # noqa: E402
from loom.scan.bib import parse_bib  # noqa: E402


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
        items = []
        for b in sorted(work.rglob("*.bbl")) + sorted(work.rglob("*.tex")):
            items += bibitem.entries(b.read_text(encoding="utf-8", errors="replace"))
        if items:
            c["with bibitems"] += 1
            c["entries"] += len(items)
            c["identified"] += sum(1 for i in items if i.arxiv or i.doi)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
