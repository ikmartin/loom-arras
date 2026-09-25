"""The `.gitignore` lines loom relies on: `loom init` writes them, `loom upgrade` adds the missing ones to an older quilt, and `loom doctor` checks them, all from this one list.

They cover loom's own files: what it builds, the documents it stores, its caches, runtime state, and the agent command it refuses to run once committed. The init template's other lines (the seed space, a hand compile's artifacts) are defaults the author may change, so upgrade leaves them alone.
"""

from __future__ import annotations

from pathlib import Path

from loom.agent import CONFIG
from loom.records.lastseen import CACHE

MANAGED = (
    "build/",
    "digests/storage/**/paper.pdf",
    "digests/storage/**/src/",
    "digests/storage/cache/",
    CACHE,
    ".loom/serve.json",
    ".loom/sessions/*/attached.json",
    ".loom/sessions/*/cursors/",
    ".loom/sessions/*/agent.*",
    CONFIG,
)


def missing(root: Path) -> list[str]:
    """The MANAGED lines the quilt's `.gitignore` lacks, in MANAGED's order."""
    p = root / ".gitignore"
    have = set(p.read_text(encoding="utf-8").splitlines()) if p.is_file() else set()
    return [line for line in MANAGED if line not in have]


def ensure(root: Path) -> list[str]:
    """Append the missing MANAGED lines under one comment, touching nothing else; returns what it added."""
    lines = missing(root)
    if not lines:
        return []
    p = root / ".gitignore"
    existing = p.read_text(encoding="utf-8") if p.is_file() else ""
    block = "# loom's own files: what it builds and stores, its caches and runtime state, and the agent command it will not run once committed\n"
    p.write_text(existing.rstrip("\n") + ("\n" if existing else "") + block + "\n".join(lines) + "\n", encoding="utf-8")
    return lines
