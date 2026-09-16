"""Flatten a master into one file: every \\input, \\include, and \\nest expanded in place, with \\nest's level shift applied to the text it brings in (book 12.5 `loom assemble`, 6.5 inline).

Raw text is used, so comments and directives survive; the output compiles identically and is what arXiv or latexdiff want.
"""

from __future__ import annotations

import re
from pathlib import Path

from loom.scan.expand import _read_include_arg, resolve_inclusion
from loom.scan.source import blank_comments
from loom.scan.tokenize import tokenize

_LEVELS = ["chapter", "section", "subsection", "subsubsection", "paragraph", "subparagraph"]


def shift_sectioning(text: str, by: int) -> str:
    """Shift every sectioning command down `by` levels (\\section -> \\subsection for by=1), as \\nest does at compile time."""
    if by <= 0:
        return text
    for _ in range(by):
        pieces: list[str] = []
        pos = 0
        for m in re.finditer(r"\\(chapter|section|subsection|subsubsection|paragraph|subparagraph)(?![A-Za-z@])", text):
            name = m.group(1)
            idx = _LEVELS.index(name)
            new = _LEVELS[min(idx + 1, len(_LEVELS) - 1)]
            pieces.append(text[pos : m.start()])
            pieces.append("\\" + new)
            pos = m.end()
        pieces.append(text[pos:])
        text = "".join(pieces)
    return text


def assemble(root: Path, master_rel: str) -> str:
    """The flattened text of a master. Missing or system files leave the inclusion command as written."""

    def rec(rel: str, shift: int, stack: tuple[str, ...]) -> str:
        raw = (root / rel).read_text(encoding="utf-8", errors="replace")
        clean = blank_comments(raw)
        out: list[str] = []
        pos = 0
        for t in tokenize(clean):
            if t.kind != "cmd" or t.value not in ("input", "include", "nest"):
                continue
            name, arg_end = _read_include_arg(clean, t.end)
            if name is None:
                continue
            child, problem = resolve_inclusion(root, name)
            if child is None or not child.endswith(".tex") or child in stack or child == rel:
                continue
            out.append(raw[pos : t.start])
            child_shift = shift + 1 if t.value == "nest" else shift
            body = rec(child, child_shift, (*stack, rel))
            if t.value == "nest":
                body = shift_sectioning(body, 1)
            if t.value == "include":
                body = "\\clearpage\n" + body + "\n\\clearpage\n"
            out.append(body if body.endswith("\n") else body + "\n")
            pos = arg_end
        out.append(raw[pos:])
        return "".join(out)

    return rec(master_rel, 0, ())
