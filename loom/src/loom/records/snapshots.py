"""Snapshots `<history>/texts/<hex>.tex`: the normalised text of a key, a statement, or a preamble at acceptance time, content-addressed so identical text is stored once and nothing is ever overwritten (book 7.2.2, 17.2).

The store is the history's `texts/` directory, shared with versions and anchors.
"""

from __future__ import annotations

from pathlib import Path

from loom.scan.hashing import normalize, sha256

DEFAULT_HISTORY = Path(".loom") / "history"


def snapshots_dir(root: Path, history_dir: Path | None = None) -> Path:
    return (history_dir if history_dir is not None else root / DEFAULT_HISTORY) / "texts"


def write_snapshot(root: Path, text: str, history_dir: Path | None = None) -> tuple[str, bool]:
    """Store the normalised text; return (hash, written)."""
    norm = normalize(text)
    digest = sha256(norm)
    d = snapshots_dir(root, history_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{digest.split(':', 1)[1]}.tex"
    if p.exists():
        return digest, False
    p.write_text(norm, encoding="utf-8")
    return digest, True


def read_snapshot(root: Path, digest: str, history_dir: Path | None = None) -> str | None:
    p = snapshots_dir(root, history_dir) / f"{digest.split(':', 1)[-1]}.tex"
    return p.read_text(encoding="utf-8") if p.is_file() else None
