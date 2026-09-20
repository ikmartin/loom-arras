"""Flattening (book 17.13, 6.6): every `\\input`, `\\include`, and `\\nest` of a `.tex` file expanded in place, `\\nest` with its level shift, raw text so comments and directives survive.

This is what `loom linearize` writes, what `loom canonize` and `loom import` make a canon document from, and what `tex/assemble.py` wraps. A file in `skip` is left as an inclusion, with a comment above it from `marker` when one is given; a non-`.tex` inclusion (a figure's `.pspdftex`) is opaque and stays as written.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from loom.scan.expand import _read_include_arg, resolve_inclusion
from loom.scan.source import blank_comments
from loom.scan.tokenize import tokenize
from loom.tex.assemble import shift_sectioning

LOOM_STY_BEGIN = "% !LOOM begin loom-macros"
LOOM_STY_END = "% !LOOM end loom-macros"
_USEPACKAGE_LOOM = re.compile(r"^[ \t]*\\usepackage\s*(\[[^\]]*\])?\s*\{loom\}[ \t]*\n?", re.M)
_BLOCK = re.compile(re.escape(LOOM_STY_BEGIN) + r"\n.*?" + re.escape(LOOM_STY_END) + r"\n?", re.S)


@dataclass
class Flattened:
    text: str
    inlined: list[str] = field(default_factory=list)  # files spliced in, in order of first inclusion
    kept: list[str] = field(default_factory=list)  # files in `skip`, left as inclusions


def flatten(
    root: Path, rel: str, skip: set[str] | None = None, marker: Callable[[str], str] | None = None
) -> Flattened:
    """The flattened text of `rel` under `root`. Missing and system files leave the inclusion command as written."""
    skip = skip or set()
    out = Flattened(text="")

    def rec(rel: str, shift: int, stack: tuple[str, ...]) -> str:
        raw = (root / rel).read_text(encoding="utf-8", errors="replace")
        clean = blank_comments(raw)
        pieces: list[str] = []
        pos = 0
        for t in tokenize(clean):
            if t.kind != "cmd" or t.value not in ("input", "include", "nest"):
                continue
            name, arg_end = _read_include_arg(clean, t.end)
            if name is None:
                continue
            child, _problem = resolve_inclusion(root, name)
            if child is None or not child.endswith(".tex") or child in stack or child == rel:
                continue
            if child in skip:
                if child not in out.kept:
                    out.kept.append(child)
                if marker is not None:
                    line_start = raw.rfind("\n", 0, t.start) + 1
                    pieces.append(raw[pos:line_start])
                    pieces.append(marker(child).rstrip("\n") + "\n")
                    pos = line_start
                continue
            pieces.append(raw[pos : t.start])
            child_shift = shift + 1 if t.value == "nest" else shift
            if child not in out.inlined:
                out.inlined.append(child)
            body = rec(child, child_shift, (*stack, rel))
            if t.value == "nest":
                body = shift_sectioning(body, 1)
            if t.value == "include":
                body = "\\clearpage\n" + body + "\n\\clearpage\n"
            pieces.append(body if body.endswith("\n") else body + "\n")
            pos = arg_end
        pieces.append(raw[pos:])
        return "".join(pieces)

    out.text = rec(rel, 0, ())
    return out


def loom_macro_block() -> str:
    """The macros of loom.sty as a marked block, so a canon document compiles alone forever and `loom draft` can put the package line back (book 17.13)."""
    from importlib import resources

    sty = resources.files("loom").joinpath("assets", "loom.sty").read_text(encoding="utf-8")
    body = [ln for ln in sty.splitlines() if not ln.startswith(("\\NeedsTeXFormat", "\\ProvidesPackage"))]
    text = "\n".join(body).strip("\n")
    return f"{LOOM_STY_BEGIN}\n{text}\n{LOOM_STY_END}\n"


def to_canon(text: str) -> str:
    """A drafting document's flat text as a canon document: `\\usepackage{loom}` replaced by the marked macro block; unchanged when the package is not loaded."""
    m = _USEPACKAGE_LOOM.search(blank_comments(text))
    if not m:
        return text
    return text[: m.start()] + loom_macro_block() + text[m.end() :]


def from_canon(text: str) -> tuple[str, bool]:
    """The reverse: the marked block replaced by `\\usepackage{loom}`; (text, whether a block was found)."""
    m = _BLOCK.search(text)
    if not m:
        return text, False
    return text[: m.start()] + "\\usepackage{loom}\n" + text[m.end() :], True
