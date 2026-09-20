"""Snapshots `<history>/texts/<hex>.tex`: the normalised text of a key, a statement, or a preamble at acceptance time, content-addressed so identical text is stored once and nothing is ever overwritten (book 7.2.2, 17.2).

The store is the history's `texts/` directory, shared with versions and anchors; `.loom/snapshots/` is where quilts before 0.9 kept it, read as a fallback until `loom upgrade` moves it.
"""

from __future__ import annotations

from pathlib import Path

from loom.scan.hashing import normalize, sha256

DEFAULT_HISTORY = Path(".loom") / "history"


def snapshots_dir(root: Path, history_dir: Path | None = None) -> Path:
    return (history_dir if history_dir is not None else root / DEFAULT_HISTORY) / "texts"


def legacy_snapshots_dir(root: Path) -> Path:
    return root / ".loom" / "snapshots"


def write_snapshot(root: Path, text: str, history_dir: Path | None = None) -> tuple[str, bool]:
    """Store the normalised text; return (hash, written)."""
    norm = normalize(text)
    digest = sha256(norm)
    d = snapshots_dir(root, history_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{digest.split(':', 1)[1]}.tex"
    if p.exists() or (legacy_snapshots_dir(root) / p.name).exists():
        return digest, False
    p.write_text(norm, encoding="utf-8")
    return digest, True


def read_snapshot(root: Path, digest: str, history_dir: Path | None = None) -> str | None:
    hexpart = digest.split(":", 1)[-1]
    for d in (snapshots_dir(root, history_dir), legacy_snapshots_dir(root)):
        p = d / f"{hexpart}.tex"
        if p.is_file():
            return p.read_text(encoding="utf-8")
    return None
