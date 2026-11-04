"""Review › Needs review: every block of the person's not freshly accepted, why, and accepting it from the viewer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from loom.paths import REVIEW_DECISIONS
from loom.records.store import Records
from loom.render.manifest import own_text
from loom.scan.hashing import mathematical_hash
from loom.scan.scan import ScanResult


def _path(root: Path) -> Path:
    return root / REVIEW_DECISIONS


def _data(root: Path) -> dict[str, Any]:
    path = _path(root)
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    return data if data.get("schema") == 2 else {"schema": 2, "reviewers": {}}


def _name(root: Path, reviewer: str | None) -> str:
    from loom.scan.quilt import resolve_author

    return resolve_author(reviewer, root)[0]


def _read(root: Path, reviewer: str | None = None) -> dict[str, dict[str, str]]:
    from loom.scan.quilt import reviewer_identity

    name = reviewer if reviewer is not None else reviewer_identity(root)[0]
    return dict(_data(root).get("reviewers", {}).get(name, {})) if name else {}


def _write(root: Path, rows: dict[str, dict[str, str]], reviewer: str | None = None) -> None:
    data = _data(root)
    data["reviewers"][_name(root, reviewer)] = rows
    path = _path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def fingerprint(result: ScanResult, key: str) -> str:
    node = result.nodes[key]
    context = {
        "dependency_version": 1,
        "text": mathematical_hash(own_text(result, node)),
        "closure": {
            dep: mathematical_hash(text) if (text := result.dependencies.texts.get(dep)) is not None else None
            for dep in result.dependencies.closure(key)
            if dep != key
        },
        "preamble": Records.preamble_hash(result, result.default_master),
        "basis": node.basis,
        "incomplete": node.incomplete,
    }
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()


def refusal(result: ScanResult, key: str) -> str:
    """Why the author cannot accept `key` from the viewer, in the person's words; '' when they can.

    The one rule behind the queue's rows, `review-accept` and Incoming's accept-as-checked. A statement with no proof yet is accepted as stated (it stays unproved), and a cited result is a settled leaf, so neither is refused.
    """
    from loom.cli.review import _owned

    n = result.nodes[key]
    if n.external or n.derived_of or not _owned(result, key):
        return "It is not in your documents."
    if n.incomplete:
        said = "; ".join(t.replace("~", " ").strip().rstrip(".") for t in n.incomplete if t.strip())
        return f"It is marked incomplete: {said}." if said else "It is marked incomplete."
    if n.kind == "environment" and n.basis == "open-claim":
        return "It is a conjecture or a question, which is not accepted."
    if n.kind == "environment" and n.basis == "unclassified":
        return "Its basis is not said; a % !LOOM basis: line inside it says it."
    if any(result.dependencies.texts.get(d) is None for d in result.dependencies.closure(key)):
        return "Something it rests on cannot be identified."
    return ""


def rows_for(result: ScanResult, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Every statement and proof of the person's not freshly accepted, in dependency order: changed since accepted, taken in, or never accepted.

    A block taken in and left unchecked stays (`keep_pending`) even when an upstream acceptance makes its own fresh again. Read by the build (`manifest["unresolved"]`) and by `review-accept`, which accepts only what this lists.
    """
    from loom.cli.review import _owned

    root = result.quilt.root
    kept = {
        key for key, row in _read(root, manifest.get("reviewer", {}).get("name")).items() if row.get("explicit_pending")
    }
    from loom.review_origins import read

    shared = read(root)
    origins = {key: row["source"] for key, row in shared.items()}
    changed_by_pull = {key: row["changed"] for key, row in shared.items()}
    baselines = {key: row["baseline"] for key, row in shared.items()}
    local_before = {key: row["local_before"] for key, row in shared.items()}
    pull_keys = set(origins)
    candidates = (
        pull_keys
        | kept
        | {key for key, entry in manifest["keys"].items() if entry.get("acceptance", {}).get("fresh") is not True}
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
            for dep in sorted((set(result.dependencies.closure(key)) - {key}) & candidates):
                visit(dep)
        visiting.remove(key)
        visited.add(key)
        ordered.append(key)

    for candidate in sorted(candidates):
        visit(candidate)
    for key in ordered:
        entry = manifest["keys"].get(key)
        node = result.nodes.get(key)
        if (
            not entry
            or not node
            or node.external
            or node.kind not in ("environment", "proof")
            or not _owned(result, key)
        ):
            continue
        acceptance = entry.get("acceptance")
        if acceptance and acceptance.get("fresh") is True and key not in kept:
            continue
        if key in pull_keys:
            cause = "adopted" if origins[key].startswith("adopt:") else "incoming-pull"
        else:
            cause = "earlier-change" if acceptance else "never-accepted"
        copy = shared.get(key, {}).get("copy")
        # a copy's rows are named from the copy itself; a pull's by the workspace its record names
        label = (
            f"Taken in from the copy “{Path(copy).stem}”"
            if cause == "adopted" and copy
            else shared.get(key, {}).get("label", "")
        )
        baseline = baselines.get(key)
        local_changed = (local_before.get(key, False) or fingerprint(result, key) != baseline) if baseline else None
        if key not in pull_keys:
            local_changed = True
        out.append(
            {
                "key": key,
                "cause": cause,
                "pull": origins.get(key, "").removeprefix("pull:"),
                "source_label": label,
                "contribution": copy,
                "changed_text": changed_by_pull.get(key, False),
                "local_changed": local_changed,
                "refusal": refusal(result, key),
            }
        )
    return out


def accept(result: ScanResult, manifest: dict[str, Any], keys: list[str], reviewer: str) -> dict[str, Any]:
    """Accept what of `keys` loom can, at once; each other key is refused with its reason.

    A key the queue does not list raises KeyError (the page is stale). A block resting on one whose acceptance is stale is refused unless that one is accepted with it. Each document is compiled once; a failure raises ValueError and accepts nothing.
    """
    from loom.cli.review import _acceptance_master, _master_compiles, write_acceptance

    listed = {row["key"] for row in rows_for(result, manifest)}
    unknown = [key for key in keys if key not in listed]
    if unknown:
        raise KeyError(", ".join(unknown))
    keys = list(dict.fromkeys(keys))
    refused = {key: why for key in keys if (why := refusal(result, key))}
    states = Records(result.quilt.root, result.quilt.history_dir, reviewer=reviewer).key_states(result)
    moved = True
    while moved:  # a block refused for what it rests on may be what another rests on
        moved = False
        for key in keys:
            if key in refused:
                continue
            for dep in result.dependencies.review_targets(key):
                state = states.get(dep)
                if state and state.row and not state.fresh and (dep not in keys or dep in refused):
                    refused[key] = f"Accept {_block_name(manifest, dep)} first, or with it."
                    moved = True
                    break
    accepted = [key for key in keys if key not in refused]
    if accepted:
        contexts = {key: _acceptance_master(result, key) for key in accepted}
        for master in dict.fromkeys(contexts.values()):
            ok, why = _master_compiles(result, master)
            if not ok:
                raise ValueError(f"{master} does not compile: {why}")
        write_acceptance(result, accepted, reviewer, contexts)
        clear_accepted(result.quilt.root, accepted, reviewer)
    return {"accepted": accepted, "refused": [{"key": key, "why": refused[key]} for key in keys if key in refused]}


def _block_name(manifest: dict[str, Any], key: str) -> str:
    """A block as the person reads it: its title, else its taxon and number in the default document, else its key; a proof as the proof of its statement."""
    owner = manifest["keys"].get(key, {}).get("node", key)
    node = manifest["nodes"].get(key) or manifest["nodes"].get(owner)
    if not node:
        return key
    default = next((m["path"] for m in manifest.get("masters", []) if m.get("default")), "")
    numbers: dict[str, dict[str, Any]] = node.get("numbers") or {}
    at: dict[str, Any] = numbers.get(default) or next(iter(numbers.values()), {})
    number = str(at.get("number") or "")
    name = (node.get("name") or node.get("title") or "").strip() or (
        f"{node.get('taxon') or ''} {number}".strip() if number else owner
    )
    return f"the proof of {name}" if key != owner and key not in manifest["nodes"] else name


def clear_accepted(root: Path, keys: list[str], reviewer: str | None = None) -> None:
    rows = _read(root, reviewer)
    for key in keys:
        rows.pop(key, None)
    _write(root, rows, reviewer)


def keep_pending(result: ScanResult, keys: list[str], reviewer: str) -> None:
    """Keep unaccepted Incoming items visible even when upstream acceptance restores an older context."""
    rows = _read(result.quilt.root, reviewer)
    for key in keys:
        rows[key] = {"explicit_pending": "true"}
    _write(result.quilt.root, rows, reviewer)
