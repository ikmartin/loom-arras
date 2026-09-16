"""File discovery and decoding (book 5.1, 4.9).

Every .tex under the root except build/ is a source file. Decoding tries UTF-8, then Mac Roman, then Latin-1; the fallback is reported by the caller as loom:non-utf8-source. Comments are blanked to spaces so every later stage sees the same offsets as the raw text.
"""

from __future__ import annotations

import re
from pathlib import Path

from loom.scan.model import SourceFile

SKIP_DIRS = {"build", ".git", "node_modules", ".loom", ".svelte-kit", ".claude"}
SKIP_PREFIXES = (
    "ai/",
    "refs/src/",
    "refs/pdf/",
)  # run outputs and fetched sources are not the quilt's text (book 11.2, 8.9)
IGNORE_RE = re.compile(r"^\s*%\s*!LOOM\s+ignore\s*$", re.M)
_VERB_RE = re.compile(r"\\verb\*?(\S)(.*?)\1")
_VERBATIM_RE = re.compile(r"\\begin\{(verbatim\*?|lstlisting|comment|filecontents\*?)\}.*?\\end\{\1\}", re.S)


def discover_files(root: Path) -> list[str]:
    """Quilt-relative posix paths of every .tex file under root, sorted, skipping build/ and tool directories."""
    found: list[str] = []
    for path in root.rglob("*.tex"):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if rel.as_posix().startswith(SKIP_PREFIXES):
            continue
        found.append(rel.as_posix())
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
    """Replace every comment (from an unescaped % to end of line) with spaces, leaving verbatim regions untouched."""
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
        clean=blank_comments(text),
        encoding=enc,
        ignored=ignored,
        line_starts=line_starts(text),
    )
