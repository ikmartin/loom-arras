"""Publish a fetched source revision without changing the quilt's actual review state."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from loom.records.store import Records
from loom.render.manifest import own_text
from loom.render.review_compare import _changed, _render
from loom.scan.hashing import normalize
from loom.scan.macros import parse_macros, to_mathjax
from loom.scan.quilt import load_quilt
from loom.scan.scan import ScanResult, scan
from loom.scan.source import blank_comments
from loom.sync import SyncError, SyncState, changed_files, git, tree_files


def _scan_tree(root: Path, commit: str, config: bytes, home: Path, state: SyncState) -> ScanResult:
    stage = home / commit[:12]
    stage.mkdir()
    (stage / "config.toml").write_bytes(config)
    for rel, data in tree_files(root, commit).items():
        if rel == state.published_main:
            rel = state.master
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return scan(load_quilt(stage))


def _citation(result: ScanResult, dependent: str, target: str) -> str | None:
    if result.graph is None:
        return None
    from loom.render.convert import slug

    edge = next(
        (
            e
            for e in result.graph.out.get(dependent, [])
            if e.offset >= 0 and e.via != "uses" and result.graph.statement_key(e.to) == target
        ),
        None,
    )
    if edge is None:
        return None
    label_target = result.assembly.labels.get(edge.label, edge.to)
    return f"cite-{slug(edge.file)}-{edge.offset}-{slug(label_target)}"


def _source_files(root: Path, state: SyncState) -> list[dict[str, str]]:
    out = changed_files(root, state.integrated, state.incoming)
    for entry in out:
        if Path(entry["path"]).suffix.lower() not in (".tex", ".bib", ".sty", ".cls", ".bst"):
            continue
        raw = git(root, "diff", "--no-ext-diff", "--unified=3", state.integrated, state.incoming, "--", entry["path"])
        entry["diff"] = raw.decode("utf-8", errors="replace")
    return out


def attach_incoming(
    result: ScanResult,
    renderer: Any,
    manifest: dict[str, Any],
    files: dict[str, str | bytes],
) -> None:
    """Attach an optional, prospective review of a pinned incoming Git commit."""
    try:
        state = SyncState.read(result.quilt.root)
    except SyncError:
        return
    if not state.incoming or state.incoming == state.integrated:
        return
    root = result.quilt.root
    config = (root / "config.toml").read_bytes()
    with tempfile.TemporaryDirectory(prefix="loom-incoming-") as temporary:
        home = Path(temporary)
        try:
            base = _scan_tree(root, state.integrated, config, home, state)
            incoming = _scan_tree(root, state.incoming, config, home, state)
        except (OSError, ValueError, SyncError) as exc:
            manifest["incoming"] = {
                "remote": state.remote,
                "branch": state.branch,
                "base": state.integrated,
                "commit": state.incoming,
                "observed": state.observed,
                "changes": [],
                "files": _source_files(root, state),
                "issues": [f"incoming source cannot be scanned: {exc}"],
            }
            return
        issues = [d.message for d in incoming.diagnostics if d.code in ("duplicate-id", "loom:unlabelled-node")]
        current_pre = result.closures.get(result.default_master) if result.default_master else None
        incoming_pre = incoming.closures.get(incoming.default_master) if incoming.default_master else None
        local_preamble = current_pre.raw_text() if current_pre else ""
        incoming_preamble = incoming_pre.raw_text() if incoming_pre else ""
        incoming_macro_name = f"incoming:{state.incoming[:12]}"
        manifest["macros"]["sets"][incoming_macro_name] = to_mathjax(parse_macros(blank_comments(incoming_preamble)))
        records = Records(root, result.quilt.history_dir)
        accepted = records.latest
        changes: list[dict[str, Any]] = []
        all_keys = set(base.nodes) | set(incoming.nodes)
        for key in sorted(all_keys):
            if key not in manifest["keys"] and key not in incoming.nodes:
                continue
            before_node = base.nodes.get(key)
            after_node = incoming.nodes.get(key)
            if before_node is None and after_node is None:
                continue
            if before_node and before_node.kind not in ("environment", "proof"):
                continue
            if after_node and after_node.kind not in ("environment", "proof"):
                continue
            before = normalize(own_text(base, before_node)) if before_node else ""
            after = normalize(own_text(incoming, after_node)) if after_node else ""
            if before == after:
                continue
            local_node = result.nodes.get(key)
            local = normalize(own_text(result, local_node)) if local_node else ""
            local_spans, incoming_spans = _changed(local, after)
            digest = hashlib.sha256((key + local + after + state.incoming).encode()).hexdigest()[:20]
            local_path = f"fragments/incoming/{digest}-local.html"
            incoming_path = f"fragments/incoming/{digest}-incoming.html"
            if local_node is not None:
                files[local_path] = _render(renderer, result, key, local, local_preamble, local_spans)
                files[incoming_path] = _render(renderer, result, key, after, incoming_preamble, incoming_spans)
            affected = []
            for dependent, entry in manifest["keys"].items():
                if dependent == key or dependent not in accepted or key not in entry.get("closure", []):
                    continue
                affected.append({"key": dependent, "citation": _citation(result, dependent, key)})
            changes.append(
                {
                    "key": key,
                    "kind": "added" if before_node is None else "removed" if after_node is None else "edited",
                    "local_changed": local != before,
                    "conflict": local != before and after != before and local != after,
                    "already_local": local == after,
                    "local": local_path if local_node else None,
                    "incoming": incoming_path if local_node and after_node else None,
                    "incoming_macros": incoming_macro_name,
                    "affected": affected,
                }
            )
        manifest["incoming"] = {
            "remote": state.remote,
            "branch": state.branch,
            "base": state.integrated,
            "commit": state.incoming,
            "observed": state.observed,
            "changes": changes,
            "files": _source_files(root, state),
            "issues": issues,
        }
        prepared = root / "build" / "incoming" / f"{state.incoming}.json"
        if prepared.is_file():
            details = json.loads(prepared.read_text(encoding="utf-8"))
            if details.get("base") == state.integrated and details.get("incoming") == state.incoming:
                manifest["incoming"]["prepared"] = {
                    "patch": str(root / "build" / "incoming" / f"{state.incoming}.patch"),
                    "root": str(root),
                    "incoming": state.incoming,
                    "paths": details["paths"],
                }
