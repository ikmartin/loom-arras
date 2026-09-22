"""Private, resumable decisions for the Arras unresolved review queue."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from loom.records.store import Records
from loom.render.manifest import key_hash
from loom.scan.scan import ScanResult
from loom.sync import SyncError, SyncState


def _path(root: Path) -> Path:
    return root / ".loom" / "review-decisions.json"


def _read(root: Path) -> dict[str, dict[str, str]]:
    path = _path(root)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _write(root: Path, rows: dict[str, dict[str, str]]) -> None:
    path = _path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def fingerprint(result: ScanResult, key: str) -> str:
    node = result.nodes[key]
    context = {
        "text": key_hash(result, key),
        "closure": Records.closure_hashes(result, key),
        "preamble": Records.preamble_hash(result, result.default_master),
        "basis": node.basis,
        "incomplete": node.incomplete,
    }
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()


def rows_for(result: ScanResult, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    root = result.quilt.root
    decisions = _read(root)
    try:
        sync = SyncState.read(root)
        pull = sync.last_pull
        origins = sync.review_origins
        changed_by_pull = sync.review_changed
    except SyncError:
        pull = {}
        origins = {}
        changed_by_pull = {}
    if not origins and pull:
        origins = {key: pull.get("commit", "") for key in pull.get("keys", [])}
        changed_by_pull = {key: key in pull.get("changed", []) for key in origins}
    pull_keys = set(origins)
    candidates = (
        pull_keys
        | set(decisions)
        | {key for key, entry in manifest["keys"].items() if entry.get("acceptance", {}).get("fresh") is False}
    )
    out = []
    # Walk actual immediate dependencies, not the closure size: proofs may have
    # short closures but still rely on a changed statement earlier in the pull.
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str) -> None:
        if key in visited or key in visiting:
            return
        visiting.add(key)
        if key in result.nodes:
            for dep in sorted(set(Records.direct_keys(result, key)) & candidates):
                visit(dep)
        visiting.remove(key)
        visited.add(key)
        ordered.append(key)

    for candidate in sorted(candidates):
        visit(candidate)
    for key in ordered:
        entry = manifest["keys"].get(key)
        node = result.nodes.get(key)
        if not entry or not node or node.external or node.kind not in ("environment", "proof") or not node.reached_by:
            continue
        choice = decisions.get(key)
        current = fingerprint(result, key)
        fresh = entry.get("acceptance", {}).get("fresh") is True
        if fresh and key not in pull_keys and not choice:
            continue
        if fresh and choice is None:
            continue
        status = "needs-review"
        if choice:
            status = (
                choice["status"]
                if choice["status"] == "requires-attention" or choice["fingerprint"] == current
                else "needs-review"
            )
        cause = "incoming-pull" if key in pull_keys else "earlier-change"
        out.append(
            {
                "key": key,
                "status": status,
                "cause": cause,
                "pull": origins.get(key, ""),
                "changed_text": changed_by_pull.get(key, False),
                "invalidated": bool(choice and choice["status"] == "ok" and choice["fingerprint"] != current),
            }
        )
    return out


def decide(result: ScanResult, key: str, status: str) -> None:
    if status not in ("ok", "requires-attention"):
        raise ValueError("decision must be ok or requires-attention")
    if key not in result.nodes or result.nodes[key].kind not in ("environment", "proof"):
        raise ValueError(f"{key} is not a reviewable statement or proof")
    rows = _read(result.quilt.root)
    rows[key] = {"status": status, "fingerprint": fingerprint(result, key)}
    _write(result.quilt.root, rows)


def pending(result: ScanResult) -> list[str]:
    rows = _read(result.quilt.root)
    keys = sorted(key for key, row in rows.items() if row["status"] == "ok")
    for key in keys:
        if key not in result.nodes or rows[key]["fingerprint"] != fingerprint(result, key):
            raise ValueError(f"{key} changed since OK; review it again")
    return keys


def clear_accepted(root: Path, keys: list[str]) -> None:
    rows = _read(root)
    for key in keys:
        rows.pop(key, None)
    _write(root, rows)
