"""Shared provenance for incorporated contributions: a pull from the document workspace or an adopted AI draft."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read(root: Path) -> dict[str, dict[str, Any]]:
    """Read the shared provenance store, empty when nothing has been incorporated.

    Parameters
    ----------
    root : Path
        Quilt root containing the local records.

    Returns
    -------
    dict
        Per-node provenance: where each key's incorporated text came from.
    """
    path = root / ".loom/review-origins.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def write(root: Path, origins: dict[str, dict[str, Any]]) -> None:
    """Atomically persist a complete shared provenance store.

    Parameters
    ----------
    root : Path
        Quilt root containing the local records.
    origins : dict
        Complete per-node provenance, including unrelated contributions retained by the caller.
    """
    path = root / ".loom/review-origins.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(origins, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)
