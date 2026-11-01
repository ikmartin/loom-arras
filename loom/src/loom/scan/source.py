"""File discovery and decoding.

Every .tex under the root outside `.loom/` and tool directories is a source file, and so is every digest, which `.loom/digests/` holds. Decoding tries UTF-8, then Mac Roman, then Latin-1; the fallback is reported by the caller as loom:non-utf8-source. Comments are blanked to spaces so every later stage sees the same offsets as the raw text.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from loom.paths import COPIES, DIGESTS, LOOM, STORAGE
from loom.scan.model import SourceFile

#: Directories never read, by name at any depth: loom's own, whose digests alone are read on purpose, and tools'.
SKIP_DIRS = {".git", "node_modules", LOOM, ".svelte-kit", ".claude"}
IGNORE_RE = re.compile(r"^\s*%\s*!LOOM\s+ignore\s*$", re.M)
_VERB_RE = re.compile(r"\\verb\*?(\S)(.*?)\1")
_VERBATIM_RE = re.compile(r"\\begin\{(verbatim\*?|lstlisting|comment|filecontents\*?)\}.*?\\end\{\1\}", re.S)


def discover_files(root: Path, skip_top: tuple[str, ...] = ()) -> list[str]:
    """Quilt-relative posix paths of every .tex file under root, sorted: every one outside `SKIP_DIRS` and the directories in `skip_top` (the history directory and the sync directory, given relative to root), every digest, and every agent copy.

    Digests are read from `.loom/digests/` on purpose, outside the store: a fetched e-print under the store is a whole paper carrying its own labels (DR-108, DR-192). Agent copies are read from `.loom/copies/`, where `loom draft --ai` makes them.
    """
    found: list[str] = []
    for path in root.rglob("*.tex"):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if len(rel.parts) > 1 and rel.as_posix().startswith(tuple(f"{d.strip('/')}/" for d in skip_top)):
            continue
        found.append(rel.as_posix())
    digests = root / DIGESTS
    if digests.is_dir():
        found += [
            p.relative_to(root).as_posix() for p in digests.rglob("*.tex") if not p.is_relative_to(root / STORAGE)
        ]
    copies = root / COPIES
    if copies.is_dir():
        found += [p.relative_to(root).as_posix() for p in copies.glob("*.tex") if p.is_file()]
    return sorted(found)


def decode(data: bytes) -> tuple[str, str]:
    """Return (text, encoding). UTF-8 first; Mac Roman then Latin-1 accept every byte, so the first fallback always wins."""
    for enc in ("utf-8", "mac_roman", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace"), "latin-1"


def _protected_ranges(text: str) -> list[tuple[int, int]]:
    ranges = [(m.start(), m.end()) for m in _VERBATIM_RE.finditer(text)]
    ranges += [(m.start(), m.end()) for m in _VERB_RE.finditer(text)]
    return sorted(ranges)


def blank_comments(text: str) -> str:
    """Replace every comment (from an unescaped % to end of line) with spaces, leaving verbatim regions untouched.

    A long text's result is remembered, as `tokenize`'s is: a served quilt reads every file again on every change.
    """
    return _blank_cached(text) if len(text) >= 4096 else _blank_comments(text)


@lru_cache(maxsize=256)
def _blank_cached(text: str) -> str:
    return _blank_comments(text)


def _blank_comments(text: str) -> str:
    protected = _protected_ranges(text)
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "%":
            if any(a <= i < b for a, b in protected):
                i += 1
                continue
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out)


def line_starts(text: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


#: The marked block that carries loom's three macros in a document's own preamble, in place of `\\usepackage{loom}` (`reshape.linearize.loom_macro_block`).
MACRO_BLOCK_BEGIN = "% !LOOM begin loom-macros"
MACRO_BLOCK_END = "% !LOOM end loom-macros"
MACRO_BLOCK = re.compile(re.escape(MACRO_BLOCK_BEGIN) + r"\n.*?" + re.escape(MACRO_BLOCK_END) + r"\n?", re.S)


def blank_macro_block(text: str, clean: str) -> str:
    """`clean` with loom's macro block blanked as a comment is: its definitions of `\\nest` and `\\uses` are loom's, not the document's inclusions or dependencies."""
    for m in MACRO_BLOCK.finditer(text):
        clean = clean[: m.start()] + re.sub(r"[^\n]", " ", clean[m.start() : m.end()]) + clean[m.end() :]
    return clean


def read_source(root: Path, rel: str, overlay: str | None = None) -> SourceFile:
    """One file as the scanner sees it. `overlay` is the text of an unsaved editor buffer, used in place of what is on disk; it is decoded already, and CRLF is normalised here as for a file."""
    abspath = root / rel
    if overlay is None:
        text, enc = decode(abspath.read_bytes())
    else:
        text, enc = overlay, "utf-8"
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    head = "\n".join(text.split("\n", 20)[:20])
    ignored = bool(IGNORE_RE.search(head))
    return SourceFile(
        path=rel,
        abspath=abspath,
        text=text,
        clean=blank_macro_block(text, blank_comments(text)),
        encoding=enc,
        ignored=ignored,
        line_starts=line_starts(text),
    )
