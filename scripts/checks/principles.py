#!/usr/bin/env python3
"""Book chapter 1 holds every design principle, and everything that cites one names one that exists (book 1.2; DR-323-ikmartin).

Usage:
    scripts/checks/principles.py [--write]

A set is a section `## 1.N X · What it governs`; a principle is a heading `### Xn. Title` inside its set's section. The chapter's sets table and its index (between `<!-- principles:sets -->` and `<!-- principles:index -->` markers) are generated from those headings, and `--write` rewrites them. The check holds:

- every principle heading sits in the section of its own letter, and a set's numbers run 1, 2, 3 ... without a gap or a repeat (a retired principle keeps its heading);
- no two sets share a letter;
- the two generated tables are what the headings say;
- every principle name cited in the book, the specifications, AGENTS.md, CLAUDE.md, or the source or tests of loom or arras exists.

Exit 0 when all hold, 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAPTER = ROOT / "docs" / "book" / "01-design-principles.md"
FIX = "python3 scripts/checks/principles.py --write"

SET = re.compile(r"^## (1\.\d+) ([A-Z]) · (.+?)\s*$", re.M)
PRINCIPLE = re.compile(r"^### ([A-Z])(\d+)\. (.+?)\s*$", re.M)
SECTION = re.compile(r"^## ", re.M)
CITED = re.compile(r"(?<![\w./#-])([A-Z])(\d{1,2})(?![\w./-])")

#: Where a principle is cited: what people and agents read, and the comments in the code that follows them.
CITING = [
    *(ROOT / "docs" / "book").glob("*.md"),
    *(ROOT / "docs" / "specs").rglob("*.md"),
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
    *(ROOT / "arras" / "src").rglob("*.ts"),
    *(ROOT / "arras" / "src").rglob("*.svelte"),
    *(ROOT / "arras" / "tests").rglob("*.ts"),
    *(ROOT / "loom" / "tests").rglob("*.py"),
    *(p for p in (ROOT / "loom" / "src" / "loom").rglob("*.py") if "assets" not in p.parts),
]


def slug(heading: str) -> str:
    """The anchor a Markdown renderer gives a heading: lowercase, punctuation dropped, spaces to hyphens."""
    text = re.sub(r"[^\w\s-]", "", heading.lower())
    return re.sub(r"\s", "-", text.strip())


def read(text: str) -> tuple[list[tuple[str, str, str]], dict[str, list[tuple[int, str]]], list[str]]:
    """The sets (section, letter, what it governs), each set's principles (number, title) in order, and what is wrong."""
    sets = [(m.group(1), m.group(2), m.group(3)) for m in SET.finditer(text)]
    problems: list[str] = []
    letters = [letter for _, letter, _ in sets]
    for letter in sorted({x for x in letters if letters.count(x) > 1}):
        problems.append(f"two sets use the letter {letter}")
    starts = {m.group(2): m.start() for m in SET.finditer(text)}
    bounds = sorted(m.start() for m in SECTION.finditer(text))
    found: dict[str, list[tuple[int, str]]] = {letter: [] for letter in letters}
    for m in PRINCIPLE.finditer(text):
        letter, number, title = m.group(1), int(m.group(2)), m.group(3)
        home = max((s for s in bounds if s < m.start()), default=-1)
        owner = next((x for x, s in starts.items() if s == home), None)
        if owner != letter:
            problems.append(f"{letter}{number} sits outside the {letter} section (`## 1.N {letter} · ...`)")
            continue
        found[letter].append((number, title))
    for letter, items in found.items():
        numbers = [n for n, _ in items]
        if numbers != list(range(1, len(numbers) + 1)):
            problems.append(f"the {letter} set is numbered {numbers}; numbers run from 1 without a gap or repeat, and are never reused")
    return sets, found, problems


def tables(sets: list[tuple[str, str, str]], found: dict[str, list[tuple[int, str]]]) -> tuple[str, str]:
    """The sets table and the index, as the headings make them."""
    rows = ["| set | governs | section | principles |", "|---|---|---|---|"]
    for section, letter, governs in sets:
        items = found.get(letter, [])
        span = f"{letter}1–{letter}{len(items)}" if len(items) > 1 else (f"{letter}1" if items else "none yet")
        rows.append(f"| {letter} | {governs} | {section} | {span} |")
    index = ["| name | principle |", "|---|---|"]
    for _, letter, _ in sets:
        for number, title in found.get(letter, []):
            index.append(f"| [{letter}{number}](#{slug(f'{letter}{number}. {title}')}) | {title} |")
    return "\n".join(rows), "\n".join(index)


def between(text: str, name: str) -> tuple[int, int] | None:
    """The span of what lies between a generated block's two markers."""
    start = text.find(f"<!-- principles:{name} -->\n")
    end = text.find(f"<!-- /principles:{name} -->")
    if start < 0 or end < 0:
        return None
    return start + len(f"<!-- principles:{name} -->\n"), end


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--write", action="store_true", help="rewrite the sets table and the index from the headings")
    args = parser.parse_args()
    text = CHAPTER.read_text(encoding="utf-8")
    sets, found, problems = read(text)
    want = dict(zip(("sets", "index"), tables(sets, found), strict=True))
    for name, block in want.items():
        span = between(text, name)
        if span is None:
            problems.append(f"the `<!-- principles:{name} -->` block is missing from {CHAPTER.relative_to(ROOT)}")
        elif text[span[0] : span[1]] != block + "\n":
            if args.write:
                text = text[: span[0]] + block + "\n" + text[span[1] :]
            else:
                problems.append(f"the {name} table is not what the headings say: {FIX}")
    if args.write:
        CHAPTER.write_text(text, encoding="utf-8")
    known = {f"{letter}{n}" for letter, items in found.items() for n, _ in items}
    letters = set(found)
    for path in CITING:
        if not path.is_file():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for name in dict.fromkeys(m.group(1) + m.group(2) for m in CITED.finditer(line)):
                if name[0] in letters and name not in known:
                    problems.append(f"{path.relative_to(ROOT)}:{line_no} cites {name}, which chapter 1 does not hold")
    for p in problems:
        print(f"principles: {p}")
    if problems:
        return 1
    count = sum(len(items) for items in found.values())
    print(f"principles: ok ({len(sets)} sets, {count} principles)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
