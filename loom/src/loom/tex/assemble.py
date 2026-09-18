"""Flatten a master into one file: every \\input, \\include, and \\nest expanded in place, with \\nest's level shift applied to the text it brings in (book 6.6, 17.13).

The recursion lives in `reshape/linearize.py`; this module keeps the sectioning shift, which `atomize` and `inline` share.
"""

from __future__ import annotations

import re
from pathlib import Path

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
            pieces.append(text[pos : m.start()])
            pieces.append("\\" + _LEVELS[min(idx + 1, len(_LEVELS) - 1)])
            pos = m.end()
        pieces.append(text[pos:])
        text = "".join(pieces)
    return text


def assemble(root: Path, master_rel: str) -> str:
    """The flattened text of a master. Missing or system files leave the inclusion command as written."""
    from loom.reshape.linearize import flatten

    return flatten(root, master_rel).text
