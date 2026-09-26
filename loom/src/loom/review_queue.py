"""Private, resumable decisions for the Arras unresolved review queue."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from loom.records.store import Records
from loom.render.manifest import own_text
from loom.scan.hashing import mathematical_hash
from loom.scan.scan import ScanResult, scan
from loom.sync import SyncError, SyncState, git


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
        "text": mathematical_hash(own_text(result, node)),
        "closure": {
            dep: mathematical_hash(own_text(result, result.nodes[dep])) for dep in Records.closure_hashes(result, key)
        },
        "preamble": Records.preamble_hash(result, result.default_master),
        "basis": node.basis,
        "incomplete": node.incomplete,
    }
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()


def _latest_pull_baselines(result: ScanResult, sync: SyncState) -> dict[str, str]:
    """Recover a baseline for pre-upgrade records from the last local source commit."""
    if not sync.local_commit or not sync.last_pull or sync.last_pull.get("commit") != sync.integrated:
        return {}
    root = result.quilt.root
    try:
        names = set(git(root, "ls-tree", "-r", "--name-only", "-z", sync.local_commit).decode().split("\0"))
        sources = {name for name in names | set(result.files) if name.endswith((".tex", ".sty", ".cls"))}
        overlay = {
            name: git(root, "show", f"{sync.local_commit}:{name}").decode("utf-8", errors="replace")
            if name in names
            else ""
            for name in sources
        }
        previous = scan(result.quilt, overlay=overlay)
    except SyncError:
        return {}
    return {
        key: fingerprint(previous, key)
        for key, origin in sync.review_origins.items()
        if origin == sync.integrated and key in previous.nodes
    }


def rows_for(result: ScanResult, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    root = result.quilt.root
    decisions = _read(root)
    try:
        sync = SyncState.read(root)
        pull = sync.last_pull
        origins = sync.review_origins
        changed_by_pull = sync.review_changed
        baselines = sync.review_baselines
        local_before = sync.review_local_changed
        legacy_baselines: dict[str, str] | None = None
    except SyncError:
        pull = {}
        origins = {}
        changed_by_pull = {}
        baselines = {}
        local_before = {}
        legacy_baselines = None
    if not origins and pull:
        origins = {key: pull.get("commit", "") for key in pull.get("keys", [])}
        changed_by_pull = {key: key in pull.get("changed", []) for key in origins}
    pull_keys = set(origins)
    candidates = (
        pull_keys
        | set(decisions)
        | {key for key, entry in manifest["keys"].items() if entry.get("acceptance", {}).get("fresh") is False}
    )
    pending_ok = {
        key
        for key, choice in decisions.items()
        if choice["status"] == "ok" and key in result.nodes and choice["fingerprint"] == fingerprint(result, key)
    }
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
        # Once upstream acceptance restores this block's recorded dependency
        # context, an old attention choice is no longer an unresolved review.
        # Keep an explicit OK visible until Finish review clears it.
        if fresh and (not choice or choice["status"] != "ok"):
            continue
        status = "needs-review"
        if choice:
            status = choice["status"] if choice["fingerprint"] == current else "needs-review"
        causes = entry.get("acceptance", {}).get("causes", [])
        # A current pending OK provisionally covers indirect causes through
        # that block. Keep a dependent with any direct or independent cause,
        # and keep its own explicit OK visible until Finish review.
        if (
            status != "ok"
            and causes
            and all(cause.get("kind") == "dependency-changed" and cause.get("via") in pending_ok for cause in causes)
        ):
            continue
        cause = "incoming-pull" if key in pull_keys else "earlier-change"
        baseline = baselines.get(key)
        if baseline is None and key in pull_keys:
            if legacy_baselines is None:
                legacy_baselines = _latest_pull_baselines(result, sync)
            baseline = legacy_baselines.get(key)
        local_changed = (local_before.get(key, False) or current != baseline) if baseline else None
        if key not in pull_keys:
            local_changed = True
        out.append(
            {
                "key": key,
                "status": status,
                "cause": cause,
                "pull": origins.get(key, ""),
                "changed_text": changed_by_pull.get(key, False),
                "local_changed": local_changed,
                "invalidated": bool(choice and choice["fingerprint"] != current),
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
