"""A document with loom taken out: flat, and every line as the author wrote it except loom's own marks (book 17.13).

`deloom` works on a flattened text and removes exactly what loom adds: `\\usepackage{loom}` (or `loom` from a package list) and the macro block `--plain` puts in its place, `% !LOOM` lines, `\\uses{…}`, and the labels that are loom ids, moving each reference to an id onto the author's own label beside it. Two things cannot be removed without changing what the document says, and block unless kept: a referenced result whose only label is its id, and `\\incomplete{…}`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loom.reshape.linearize import _BLOCK
from loom.scan.labels import HYPERREF, LABEL_DEF, LABEL_REFS
from loom.scan.source import _protected_ranges, blank_comments

#: What `--keep-incomplete` puts where loom.sty was: the one macro kept text still needs, defined as loom.sty defines it.
INCOMPLETE_DEF = "\\providecommand{\\incomplete}[1]{}\n"

_GONE = "\x00"  # marks a removal, so a line left holding nothing else is dropped with it
_USEPACKAGE = re.compile(r"\\usepackage\s*(\[[^\]]*\])?\s*\{([^}]*)\}")
_LOOM_LINE = re.compile(r"^[ \t]*%[ \t]*!LOOM\b[^\n]*(\n|$)", re.M)
_USES = re.compile(r"\\uses\s*\{[^}]*\}")
_INCOMPLETE = re.compile(r"\\incomplete\s*\{")
_BEGIN_DOCUMENT = re.compile(r"\\begin\s*\{document\}")


@dataclass
class Delooming:
    text: str
    removed: list[str] = field(default_factory=list)  # id labels taken out
    moved: int = 0  # references moved from an id to the author's label beside it
    uses: int = 0
    directives: int = 0
    blocked_ids: dict[str, int] = field(
        default_factory=dict
    )  # referenced id with no label of the author's -> its reference count
    blocked_incomplete: list[int] = field(
        default_factory=list
    )  # 1-based lines of `\incomplete{` in the flattened source, when not kept
    kept_ids: dict[str, int] = field(default_factory=dict)  # id -> its line in the output, when kept
    kept_incomplete: list[int] = field(default_factory=list)  # lines in the output, when kept

    @property
    def blocked(self) -> bool:
        return bool(self.blocked_ids or self.blocked_incomplete)


def _line(text: str, at: int) -> int:
    return text.count("\n", 0, at) + 1


def _brace_end(clean: str, open_at: int) -> int:
    """The offset just past the brace that closes the one at `open_at`; the text's end when it never closes."""
    depth = 0
    i = open_at
    while i < len(clean):
        ch = clean[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(clean)


def deloom(text: str, ids: set[str], *, keep_ids: bool = False, keep_incomplete: bool = False) -> Delooming:
    """Take loom out of a flattened document.

    Parameters
    ----------
    text : str
        The document, flattened (`linearize.flatten`), so no node file or `\\nest` remains.
    ids : set of str
        The labels that are loom ids: the quilt's node ids, derived ones included.
    keep_ids : bool, default False
        Keep the id label of a referenced result that has no label of the author's, and its references.
    keep_incomplete : bool, default False
        Keep every `\\incomplete{…}`, with `INCOMPLETE_DEF` so the output still compiles.

    Returns
    -------
    Delooming
        The text, what was taken out, and what blocks it; `text` is only meaningful when nothing blocks.
    """
    out = Delooming(text="")
    protected = _protected_ranges(text)
    clean = blank_comments(text)

    def free(at: int) -> bool:
        return not any(a <= at < b for a, b in protected)

    edits: list[tuple[int, int, str]] = []
    package_at: int | None = None

    # the macro block `--plain` wrote, then every `% !LOOM` line; the block's own markers are such lines
    block = _BLOCK.search(text)
    if block:
        edits.append((block.start(), block.end(), _GONE))
        package_at = block.start()
    for m in _LOOM_LINE.finditer(text):
        if block and block.start() <= m.start() < block.end():
            continue
        if free(m.start()):
            edits.append((m.start(), m.end(), ""))
            out.directives += 1

    for m in _USEPACKAGE.finditer(clean):
        names = [n.strip() for n in m.group(2).split(",")]
        if "loom" not in names or not free(m.start()):
            continue
        rest = [n for n in names if n and n != "loom"]
        if rest:
            a, b = m.span(2)
            edits.append((a, b, ",".join(rest)))
        else:
            edits.append((m.start(), m.end(), _GONE))
        package_at = m.start() if package_at is None else package_at

    for m in _USES.finditer(clean):
        if free(m.start()):
            edits.append((m.start(), m.end(), _GONE))
            out.uses += 1

    incomplete = [_line(text, m.start()) for m in _INCOMPLETE.finditer(clean) if free(m.start())]
    if incomplete and not keep_incomplete:
        out.blocked_incomplete = incomplete

    # labels, grouped into runs: the labels one object carries stand together, with only space between them
    labels = [m for m in LABEL_DEF.finditer(clean) if free(m.start())]
    runs: list[list[re.Match[str]]] = []
    for m in labels:
        if runs and not clean[runs[-1][-1].end() : m.start()].strip():
            runs[-1].append(m)
        else:
            runs.append([m])
    references = [
        m
        for pattern in (LABEL_REFS, HYPERREF)
        for m in pattern.finditer(clean)
        if free(m.start()) and not m.group(1).lstrip("\\").startswith("uses")
    ]
    referenced: dict[str, int] = {}
    for m in references:
        for name in m.group(2).split(","):
            referenced[name.strip()] = referenced.get(name.strip(), 0) + 1
    moves: dict[str, str] = {}
    for run in runs:
        own = [m.group(2) for m in run if m.group(2) not in ids]
        for m in run:
            name = m.group(2)
            if name not in ids:
                continue
            if own:
                moves[name] = own[0]
            elif name in referenced:
                if not keep_ids:
                    out.blocked_ids[name] = referenced[name]
                out.kept_ids[name] = 0
                continue
            edits.append((m.start(), m.end(), _GONE))
            out.removed.append(name)
    # a reference moves by rewriting its own names, never by a pass over the text, which would reach comments and verbatim
    for m in references:
        names = re.split(r"(\s*,\s*)", text[m.start(2) : m.end(2)])
        if any(moves.get(n.strip()) for n in names[::2]):
            moved = [n if i % 2 else n.replace(n.strip(), moves.get(n.strip(), n.strip())) for i, n in enumerate(names)]
            edits.append((m.start(2), m.end(2), "".join(moved)))
            out.moved += sum(1 for n in names[::2] if n.strip() in moves)
    if incomplete and keep_incomplete:
        at = package_at
        if at is None:
            begin = _BEGIN_DOCUMENT.search(clean)
            at = begin.start() if begin else 0
        edits.append((at, at, INCOMPLETE_DEF))
    if out.blocked:
        return out

    body = text
    for a, b, new in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
        body = body[:a] + new + body[b:]
    lines = body.split("\n")
    body = "\n".join(ln for ln in lines if not (_GONE in ln and not ln.replace(_GONE, "").strip())).replace(_GONE, "")
    out.text = body
    for name in out.kept_ids:
        found = re.search(r"\\label\s*\{\s*" + re.escape(name) + r"\s*\}", out.text)
        out.kept_ids[name] = _line(out.text, found.start()) if found else 0
    kept_clean = blank_comments(out.text)
    out.kept_incomplete = [_line(out.text, m.start()) for m in _INCOMPLETE.finditer(kept_clean)]
    return out
