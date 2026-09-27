"""Text normalisation and hashing (book 5.13).

Own text is hashed after: comment lines that are not directives removed, trailing whitespace stripped, tabs to spaces, blank runs collapsed, newlines normalised. A child cut out of a parent's region leaves a `% !LOOM child: KEY` line so structural changes change the hash.
"""

from __future__ import annotations

import hashlib
import re

_DIRECTIVE = re.compile(r"^\s*%\s*!LOOM\b")


def normalize(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    blank = False
    for raw in lines:
        line = raw.replace("\t", "    ").rstrip()
        stripped = line.lstrip()
        if stripped.startswith("%") and not _DIRECTIVE.match(line):
            continue
        if not line:
            if out and not blank:
                out.append("")
            blank = True
            continue
        blank = False
        out.append(line)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n" if out else ""


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_text(text: str) -> str:
    return sha256(normalize(text))


def child_marker(key: str) -> str:
    return f"% !LOOM child: {key}\n"


def mathematical_hash(text: str) -> str:
    """Hash a node's mathematics without its display-name directives; source snapshots retain them."""
    from loom.scan.source import _protected_ranges

    protected = _protected_ranges(text)
    pattern = re.compile(r"^[ \t]*%[ \t]*!LOOM[ \t]+name[ \t]*:[^\r\n]*(?:\r?\n|$)", re.M)
    return hash_text(pattern.sub(lambda m: m.group() if any(a <= m.start() < b for a, b in protected) else "", text))
