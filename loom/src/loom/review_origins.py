"""Shared provenance for incorporated contributions, with legacy pull compatibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read(root: Path) -> dict[str, dict[str, Any]]:
    """Read shared origins, falling back to older document-workspace records.

    Parameters
    ----------
    root : Path
        Quilt root containing the local records.

    Returns
    -------
    dict
        Per-node provenance; shared entries take precedence over legacy pulls.
    """
    legacy = root / ".loom/source-sync.json"
    data = json.loads(legacy.read_text()) if legacy.is_file() else {}
    origins = data.get("review_origins") or {
        key: data.get("last_pull", {}).get("commit", "") for key in data.get("last_pull", {}).get("keys", [])
    }
    out = {
        key: {
            "source": "pull:" + commit,
            "changed": data.get("review_changed", {}).get(key, key in data.get("last_pull", {}).get("changed", [])),
            "baseline": data.get("review_baselines", {}).get(key),
            "local_before": data.get("review_local_changed", {}).get(key, False),
            "label": f"Incoming from {data.get('remote', 'document workspace')}",
        }
        for key, commit in origins.items()
    }
    path = root / ".loom/review-origins.json"
    if path.is_file():
        out.update(json.loads(path.read_text()))
    return out


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
