"""% !LOOM and % !TEX directives (book 5.11): declarations the scanner reads, never actions.

File-level directives sit in the first twenty lines before any node; node-level ones inside a node's own text. `% !TEX root = ...` and `% !TEX program = ...` are read in their own form.
"""

from __future__ import annotations

import re

from loom.scan.model import Directive, SourceFile

# `source` is the pre-0.5 spelling of `extracted-from` and stays known, so a quilt that has not been upgraded lints clean (DR-109)
KNOWN_KEYS = {
    "author",
    "created",
    "tags",
    "see",
    "environment",
    "digest",
    "prefix",
    "extracted-from",
    "published-as",
    "source",
    "method",
    "proofs",
    "requires",
    "numbering",
    "shared",
}
LIST_KEYS = {"author", "tags", "see", "requires"}
BARE_KEYS = {"ignore"}
REGION_KEYS = {
    "macros",
    "loom-macros",
}  # loom-macros: the block a canon document carries in place of \usepackage{loom} (17.13)
HEAD_LINES = 20

_LINE = re.compile(r"^[ \t]*%[ \t]*!(LOOM|TEX)[ \t]+(.*?)[ \t]*$", re.M)


def parse_directives(src: SourceFile) -> list[Directive]:
    out: list[Directive] = []
    for m in _LINE.finditer(src.text):
        family, rest = m.group(1), m.group(2)
        line = src.line_of(m.start())
        if family == "TEX":
            tm = re.match(r"(root|program)\s*=\s*(.+)$", rest)
            if tm:
                out.append(Directive(tm.group(1), tm.group(2).strip(), src.path, m.start(), line, "tex"))
            continue
        if rest in BARE_KEYS:
            out.append(Directive(rest, "", src.path, m.start(), line, "bare"))
            continue
        rm = re.match(r"(begin|end)\s+([a-z][a-z-]*)$", rest)
        if rm:
            out.append(Directive(rm.group(2), "", src.path, m.start(), line, rm.group(1)))
            continue
        km = re.match(r"([a-z][a-z-]*)\s*:\s*(.*)$", rest)
        if km:
            out.append(Directive(km.group(1), km.group(2).strip(), src.path, m.start(), line, "kv"))
            continue
        out.append(Directive(rest.split()[0] if rest.split() else rest, rest, src.path, m.start(), line, "unknown"))
    return out


def list_value(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def file_level(directives: list[Directive], first_node_offset: int | None) -> list[Directive]:
    """Directives in the first twenty lines and before any node."""
    return [
        d for d in directives if d.line <= HEAD_LINES and (first_node_offset is None or d.offset < first_node_offset)
    ]


def within(directives: list[Directive], ranges: list[tuple[int, int]]) -> list[Directive]:
    return [d for d in directives if any(a <= d.offset < b for a, b in ranges)]
