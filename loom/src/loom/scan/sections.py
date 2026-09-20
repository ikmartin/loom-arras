"""Sectioning units on the expanded master (book 5.2, 5.4.2, 5.9.2).

Levels come from the command plus the \\nest shift of the segment it sits in; a unit runs to the next command of equal or higher level or to \\end{document}. Hierarchy is computed on the expanded text; the ownership span is per file: from the heading to the next heading of equal or higher level whose heading is in the same file, or the end of that file. A heading's label is the first \\label on its line or on the next non-blank line, unless that line opens an environment or another heading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loom.scan.expand import Expansion
from loom.scan.model import SourceFile
from loom.scan.tokenize import read_args

LEVELS = {
    "part": -1,
    "chapter": 0,
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
    "paragraph": 4,
    "subparagraph": 5,
}
LEVEL_NAMES = {v: k for k, v in LEVELS.items()}
_SECT = re.compile(r"\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)(\*?)\s*(?=[\[{])")
_LABEL = re.compile(r"\\label\s*\{([^}]*)\}")
_OPENER = re.compile(r"^\s*\\(begin\s*\{|part|chapter|section|subsection|subsubsection|paragraph|subparagraph)")


@dataclass
class SectionUnit:
    name: str
    starred: bool
    level: int
    exp_start: int
    exp_end: int
    title: str
    file: str
    offset: int  # heading offset in file
    heading_end: int  # offset in file just past the title's closing brace
    file_end: int = 0  # per-file ownership end
    shift: int = 0
    labels: list[str] = field(default_factory=list)
    parent: SectionUnit | None = field(default=None, repr=False)
    children: list[SectionUnit] = field(default_factory=list)
    ordinal: int = 0  # among units with the same command name in the same file


def body_range(exp: Expansion) -> tuple[int, int]:
    text = exp.text
    m = re.search(r"\\begin\s*\{document\}", text)
    start = m.end() if m else 0
    e = re.search(r"\\end\s*\{document\}", text)
    end = e.start() if e else len(text)
    return start, end


def find_sections(exp: Expansion, files: dict[str, SourceFile]) -> list[SectionUnit]:
    text = exp.text
    start, end = body_range(exp)
    units: list[SectionUnit] = []
    for m in _SECT.finditer(text, start, end):
        name, starred = m.group(1), bool(m.group(2))
        (short, title), spans, after = read_args(text, m.end(), "om")
        if title is None:
            continue
        file, offset, shift = exp.locate(m.start())
        _, heading_end, _ = exp.locate(after) if after < len(text) else (file, files[file].clean.__len__(), shift)
        heading_end = offset + (after - m.start())
        units.append(
            SectionUnit(
                name=name,
                starred=starred,
                level=LEVELS[name] + shift,
                exp_start=m.start(),
                exp_end=end,
                title=re.sub(r"\s+", " ", title.strip()),
                file=file,
                offset=offset,
                heading_end=heading_end,
                shift=shift,
            )
        )
    for i, u in enumerate(units):
        for later in units[i + 1 :]:
            if later.level <= u.level:
                u.exp_end = later.exp_start
                break
    stack: list[SectionUnit] = []
    for u in units:
        while stack and stack[-1].level >= u.level:
            stack.pop()
        if stack:
            u.parent = stack[-1]
            stack[-1].children.append(u)
        stack.append(u)
    counts: dict[tuple[str, str], int] = {}
    for u in units:
        k = (u.file, u.name)
        counts[k] = counts.get(k, 0) + 1
        u.ordinal = counts[k]
        src = files[u.file]
        u.file_end = _file_end(u, units, src, exp)
        u.labels = heading_labels(src.clean, u.heading_end)
    return units


def _file_end(u: SectionUnit, units: list[SectionUnit], src: SourceFile, exp: Expansion) -> int:
    for later in units:
        if later.exp_start <= u.exp_start:
            continue
        if later.file == u.file and later.level <= u.level and later.offset > u.offset:
            return later.offset
    if u.file == exp.master:
        e = re.search(r"\\end\s*\{document\}", src.clean)
        if e and e.start() > u.offset:
            return e.start()
    return len(src.clean)


def heading_labels(clean: str, heading_end: int) -> list[str]:
    """Labels on the heading's line, else on the next non-blank line unless it opens an environment or heading."""
    line_end = clean.find("\n", heading_end)
    line_end = len(clean) if line_end < 0 else line_end
    same_line = _LABEL.findall(clean, heading_end, line_end)
    if same_line:
        return [re.sub(r"\s+", " ", x).strip() for x in same_line]
    pos = line_end + 1
    while pos < len(clean):
        nl = clean.find("\n", pos)
        nl = len(clean) if nl < 0 else nl
        line = clean[pos:nl]
        if line.strip():
            if _OPENER.match(line):
                return []
            return [re.sub(r"\s+", " ", x).strip() for x in _LABEL.findall(line)]
        pos = nl + 1
    return []
