"""Flattening: every `\\input`, `\\include`, and `\\nest` of a `.tex` file expanded in place, `\\nest` with its level shift, raw text so comments and directives survive.

This is what `loom linearize` writes, what `loom stamp` keeps as a landmark's text and `loom import` keeps a paper as received in, and what `tex/assemble.py` wraps. A file in `skip` is left as an inclusion, with a comment above it from `marker` when one is given; a non-`.tex` inclusion (a figure's `.pspdftex`) is opaque and stays as written.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from loom.paths import document_dir
from loom.scan.expand import _read_include_arg, resolve_inclusion
from loom.scan.source import MACRO_BLOCK, MACRO_BLOCK_BEGIN, MACRO_BLOCK_END, blank_comments
from loom.scan.tokenize import tokenize
from loom.tex.assemble import shift_sectioning

_USEPACKAGE_LOOM = re.compile(r"^[ \t]*\\usepackage\s*(\[[^\]]*\])?\s*\{loom\}[ \t]*\n?", re.M)
_BLOCK = MACRO_BLOCK


@dataclass
class Flattened:
    text: str
    inlined: list[str] = field(default_factory=list)  # files spliced in, in order of first inclusion
    kept: list[str] = field(default_factory=list)  # files in `skip`, left as inclusions
    #: The source file and line each line of `text` came from, by its 0-based index: what a report on the flat text names to its reader.
    origins: list[tuple[str, int]] = field(default_factory=list)

    def origin(self, line: int) -> tuple[str, int] | None:
        """The file and line the flat text's `line` (1-based) came from; None past its end."""
        return self.origins[line - 1] if 0 < line <= len(self.origins) else None


def flatten(
    root: Path,
    rel: str,
    skip: set[str] | None = None,
    marker: Callable[[str], str] | None = None,
    *,
    overlay: dict[str, str] | None = None,
    base: str | None = None,
) -> Flattened:
    """The flattened text of `rel` under `root`. Missing and system files leave the inclusion command as written.

    Inclusions resolve against `base`, the directory the document compiles from: default `rel`'s own, and its source's for a text derived from another document (an agent copy, a landmark).
    """
    skip = skip or set()
    home = document_dir(rel) if base is None else base
    out = Flattened(text="")

    def rec(rel: str, shift: int, stack: tuple[str, ...]) -> tuple[str, list[tuple[str, int]]]:
        raw = (
            overlay[rel]
            if overlay is not None and rel in overlay
            else (root / rel).read_text(encoding="utf-8", errors="replace")
        )
        clean = blank_comments(raw)
        pieces: list[str] = []
        lines: list[tuple[str, int]] = []  # one per line the pieces end, the line its text ends in

        def own(a: int, b: int) -> None:
            """`raw[a:b]` copied, each line it ends credited to this file's line it ends on."""
            first = raw.count("\n", 0, a) + 1
            lines.extend((rel, first + i) for i in range(raw.count("\n", a, b)))
            pieces.append(raw[a:b])

        pos = 0
        for t in tokenize(clean):
            if t.kind != "cmd" or t.value not in ("input", "include", "nest"):
                continue
            name, arg_end = _read_include_arg(clean, t.end)
            if name is None:
                continue
            child, _problem = resolve_inclusion(root, name, base=home)
            if child is None or not child.endswith(".tex") or child in stack or child == rel:
                continue
            if child in skip:
                if child not in out.kept:
                    out.kept.append(child)
                if marker is not None:
                    line_start = raw.rfind("\n", 0, t.start) + 1
                    own(pos, line_start)
                    pieces.append(marker(child).rstrip("\n") + "\n")
                    lines.append((rel, raw.count("\n", 0, t.start) + 1))
                    pos = line_start
                continue
            own(pos, t.start)
            at = (rel, raw.count("\n", 0, t.start) + 1)
            child_shift = shift + 1 if t.value == "nest" else shift
            if child not in out.inlined:
                out.inlined.append(child)
            body, inner = rec(child, child_shift, (*stack, rel))
            if t.value == "nest":
                body = shift_sectioning(body, 1)  # line for line, so `inner` still holds
            if t.value == "include":
                body = "\\clearpage\n" + body + "\n\\clearpage\n"
                inner = [at, *inner, at, at]
            if not body.endswith("\n"):
                body += "\n"
            lines.extend(inner[: body.count("\n")] + [at] * (body.count("\n") - len(inner)))
            pieces.append(body)
            pos = arg_end
        own(pos, len(raw))
        if not raw.endswith("\n"):
            lines.append((rel, raw.count("\n") + 1))
        return "".join(pieces), lines

    out.text, out.origins = rec(rel, 0, ())
    return out


def loom_macro_block() -> str:
    """The macros of loom.sty as a marked block: what a document loom starts, imports or restores carries in its preamble, so it compiles from its own directory with no file beside it (P12)."""
    from importlib import resources

    sty = resources.files("loom").joinpath("assets", "loom.sty").read_text(encoding="utf-8")
    body = [ln for ln in sty.splitlines() if not ln.startswith(("\\NeedsTeXFormat", "\\ProvidesPackage"))]
    text = "\n".join(body).strip("\n")
    return f"{MACRO_BLOCK_BEGIN}\n{text}\n{MACRO_BLOCK_END}\n"


def to_canon(text: str) -> str:
    """A drafting document's flat text without loom, as `loom history show --plain` prints it: `\\usepackage{loom}` replaced by the marked macro block; unchanged when the package is not loaded."""
    m = _USEPACKAGE_LOOM.search(blank_comments(text))
    if not m:
        return text
    return text[: m.start()] + loom_macro_block() + text[m.end() :]


def with_macro_block(text: str) -> tuple[str, bool]:
    """`text` with loom's macro block after its `\\documentclass` line, unless it carries the block already or loads loom.sty; (text, whether the block was added)."""
    if _BLOCK.search(text) or _USEPACKAGE_LOOM.search(blank_comments(text)):
        return text, False
    m = re.search(r"\\documentclass\s*(\[[^\]]*\])?\s*\{[^}]*\}[^\n]*\n?", blank_comments(text))
    if m is None:
        return text, False
    end = m.end() if text[m.end() - 1 : m.end()] == "\n" else m.end()
    head = text[:end] if text[:end].endswith("\n") else text[:end] + "\n"
    return head + loom_macro_block() + text[end:], True


def from_canon(text: str) -> tuple[str, bool]:
    """The reverse: the marked block replaced by `\\usepackage{loom}`; (text, whether a block was found)."""
    m = _BLOCK.search(text)
    if not m:
        return text, False
    return text[: m.start()] + "\\usepackage{loom}\n" + text[m.end() :], True
