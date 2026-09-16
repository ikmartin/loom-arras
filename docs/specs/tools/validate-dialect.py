#!/usr/bin/env python3
"""Validate fragment HTML files against docs/specs/dialect.md.

Usage: validate-dialect.py FILE_OR_DIR... ; exit 1 if any fragment is invalid, printing one line per problem. Completed at M2; the M0 version checks only the envelope (no page shell, no scripts or styles) and that every block-level element from source carries data-src.
"""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

FORBIDDEN = {"html", "head", "body", "script", "style", "link", "iframe", "form", "input", "button", "object", "embed"}
BLOCKS_NEEDING_SRC = {"p", "div", "section", "details", "figure", "table", "pre", "ul", "ol", "dl", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}


class Checker(HTMLParser):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.problems: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag in FORBIDDEN:
            self.problems.append(f"{self.name}: forbidden element <{tag}>")
        if any(k.startswith("on") for k in a):
            self.problems.append(f"{self.name}: inline event handler on <{tag}>")
        if tag in BLOCKS_NEEDING_SRC and "data-src" not in a and tag != "div":
            self.problems.append(f"{self.name}: <{tag}> without data-src")


def check(path: Path) -> list[str]:
    c = Checker(str(path))
    c.feed(path.read_text(encoding="utf-8"))
    return c.problems


def main(argv: list[str]) -> int:
    files: list[Path] = []
    for arg in argv:
        p = Path(arg)
        files.extend(sorted(p.rglob("*.html")) if p.is_dir() else [p])
    problems = [line for f in files for line in check(f)]
    for line in problems:
        print(line)
    print(f"{len(files)} fragment(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
