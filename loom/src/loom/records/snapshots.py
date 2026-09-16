"""Snapshots `.loom/snapshots/<hex>.tex`: the normalised text of a key, a statement, or a preamble at acceptance time, content-addressed so identical text is stored once and nothing is ever overwritten (book 7.2.2)."""

from __future__ import annotations

from pathlib import Path

from loom.scan.hashing import normalize, sha256


def snapshots_dir(root: Path) -> Path:
    return root / ".loom" / "snapshots"


def write_snapshot(root: Path, text: str) -> tuple[str, bool]:
    """Store the normalised text; return (hash, written)."""
    norm = normalize(text)
    digest = sha256(norm)
    d = snapshots_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{digest.split(':', 1)[1]}.tex"
    if p.exists():
        return digest, False
    p.write_text(norm, encoding="utf-8")
    return digest, True


def read_snapshot(root: Path, digest: str) -> str | None:
    hexpart = digest.split(":", 1)[-1]
    p = snapshots_dir(root) / f"{hexpart}.tex"
    return p.read_text(encoding="utf-8") if p.is_file() else None
