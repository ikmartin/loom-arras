#!/usr/bin/env python3
"""Validate fragment HTML files against docs/specs/dialect.md (interface version 1).

Usage: validate-dialect.py FILE_OR_DIR... ; prints one line per problem and a summary; exit 1 if any fragment is invalid. Checks the envelope (no page shell, scripts, styles, iframes, forms, inline handlers), the element and class vocabulary, that block elements from source carry data-src, that inclusions carry data-key, and that no absolute URL appears outside a.url and img[src].
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

FORBIDDEN = {"html", "head", "body", "script", "style", "link", "iframe", "form", "input", "button", "object", "embed", "meta", "title", "base", "template"}
ALLOWED = {
    "section", "h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "details", "summary", "span", "a", "em", "strong", "code", "u",
    "blockquote", "pre", "ul", "ol", "dl", "li", "dt", "dd", "hr", "mark", "figure", "figcaption", "img", "svg", "table",
    "thead", "tbody", "tr", "th", "td", "br",
}
ALLOWED_CLASSES = {
    "div": {"env", "include", "included", "math", "display", "annotation-block"},
    "details": {"env", "env-proof", "annotation-block"},
    "summary": {"env-label"},
    "p": {"env-label", "annotation-block"},
    "span": {"number", "taxon", "title", "math", "inline", "cite", "footnote", "incomplete", "smallcaps", "tex-color"},
    "a": {"ref", "ref-eq", "ref-dangling", "url"},
    "mark": {"annotation"},
    "figure": {"diagram", "fallback", "failed"},
    "section": {"annotation-block"},
}
BLOCKS_NEEDING_SRC = {"section", "h1", "h2", "h3", "h4", "h5", "h6", "p", "details", "figure", "table", "pre", "ul", "ol", "dl", "blockquote"}


class Checker(HTMLParser):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.problems: list[str] = []
        self.svg_depth = 0
        self.figure_depth = 0
        self.seen_any = False

    def _add(self, msg: str) -> None:
        self.problems.append(f"{self.name}:{self.getpos()[0]}: {msg}")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        self.seen_any = True
        if tag == "svg":
            self.svg_depth += 1
        if tag == "figure":
            self.figure_depth += 1
        if self.svg_depth and tag != "svg":
            return
        if tag in FORBIDDEN:
            self._add(f"forbidden element <{tag}>")
            return
        if tag not in ALLOWED:
            self._add(f"element <{tag}> is not in the dialect")
            return
        if any(k.lower().startswith("on") for k in a):
            self._add(f"inline event handler on <{tag}>")
        classes = set(a.get("class", "").split())
        if classes:
            allowed = ALLOWED_CLASSES.get(tag, set())
            bad = {c for c in classes if c not in allowed and not c.startswith("env-")}
            if bad:
                self._add(f"<{tag}> has classes outside the dialect: {', '.join(sorted(bad))}")
        if tag == "div":
            if "include" in classes and "data-key" not in a:
                self._add("div.include without data-key")
            if ("env" in classes or "math" in classes or "included" in classes) and "data-src" not in a and "include" not in classes:
                self._add(f"div.{'.'.join(sorted(classes))} without data-src")
        elif tag in BLOCKS_NEEDING_SRC and "data-src" not in a and "env-label" not in classes and not (tag == "pre" and self.figure_depth):
            self._add(f"<{tag}> without data-src")
        if "data-src" in a and not re.match(r"^[^:]+:\d+:\d+$", a["data-src"]):
            self._add(f"malformed data-src {a['data-src']!r}")
        for k, v in a.items():
            if k.startswith("xmlns"):
                continue
            if re.match(r"^(https?:)?//", v) and not ((tag == "a" and k == "href" and "url" in classes) or (tag == "img" and k == "src")):
                self._add(f"absolute URL in {k} of <{tag}>")
        if tag == "img" and re.match(r"^(https?:)?//", a.get("src", "")):
            self._add("img with an external src")

    def handle_endtag(self, tag: str) -> None:
        if tag == "svg" and self.svg_depth:
            self.svg_depth -= 1
        if tag == "figure" and self.figure_depth:
            self.figure_depth -= 1


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
