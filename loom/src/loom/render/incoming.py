"""Publish a fetched source revision without changing the quilt's actual review state."""

from __future__ import annotations

import difflib
import hashlib
import tempfile
from pathlib import Path
from typing import Any

from loom.records.store import Records
from loom.render.manifest import own_text
from loom.render.prose_changes import attach_prose, document_body, pair
from loom.render.review_compare import _changed, _render
from loom.scan.hashing import mathematical_hash, normalize
from loom.scan.macros import parse_macros, to_mathjax
from loom.scan.quilt import load_quilt
from loom.scan.scan import ScanResult, scan
from loom.scan.source import blank_comments
from loom.sync import SyncError, SyncState, changed_files, current_selection, git, source_label, tree_files, workspace


def _scan_tree(clone: Path, commit: str, config: bytes, home: Path, state: SyncState, main: str) -> ScanResult:
    """A scan of one workspace revision from loom's clone, staged under `home`, Overleaf's main written at `main`, the local path it maps to now."""
    stage = home / commit[:12]
    stage.mkdir()
    (stage / "config.toml").write_bytes(config)
    for rel, data in tree_files(clone, commit).items():
        if rel == state.published_main:
            rel = main
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


def _source_files(clone: Path, state: SyncState) -> list[dict[str, str]]:
    out = changed_files(clone, state.integrated, state.incoming)
    for entry in out:
        if Path(entry["path"]).suffix.lower() not in (".tex", ".bib", ".sty", ".cls", ".bst"):
            continue
        raw = git(clone, "diff", "--no-ext-diff", "--unified=3", state.integrated, state.incoming, "--", entry["path"])
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
            main = current_selection(state, result)[0]
            clone = workspace(root)
            base = _scan_tree(clone, state.integrated, config, home, state, main)
            incoming = _scan_tree(clone, state.incoming, config, home, state, main)
        except (OSError, ValueError, SyncError) as exc:
            try:
                listed = _source_files(workspace(root), state)
            except SyncError:
                listed = []
            manifest["incoming"] = {
                "workspace": state.url,
                "branch": state.branch,
                "base": state.integrated,
                "commit": state.incoming,
                "observed": state.observed,
                "changes": [],
                "files": listed,
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
            targets = {key} | {
                target
                for target, owner in incoming.dependencies.owners.items()
                if owner == key
                and target.startswith("equation:")
                and mathematical_hash(incoming.dependencies.texts.get(target) or "")
                != mathematical_hash(base.dependencies.texts.get(target) or "")
            }
            affected = []
            for dependent in manifest["keys"]:
                if (
                    dependent == key
                    or dependent not in accepted
                    or not targets.intersection(result.dependencies.closure(dependent))
                ):
                    continue
                affected.append({"key": dependent, "citation": _citation(result, dependent, key)})
            changes.append(
                {
                    "key": key,
                    "kind": "added" if before_node is None else "removed" if after_node is None else "edited",
                    "current": local,
                    "proposed": after,
                    "local_changed": local != before,
                    "conflict": local != before and after != before and local != after,
                    "already_local": local == after,
                    "local": local_path if local_node else None,
                    "incoming": incoming_path if local_node and after_node else None,
                    "incoming_macros": incoming_macro_name,
                    "affected": affected,
                }
            )
        changes.extend(
            attach_prose(
                result, base, incoming, renderer, files, local_preamble, incoming_preamble, incoming_macro_name
            )
        )
        from loom.review_queue import fingerprint

        affected_keys = [
            key
            for key, node in incoming.nodes.items()
            if node.kind in ("environment", "proof")
            and not node.derived_of
            and key in base.nodes
            and fingerprint(base, key) != fingerprint(incoming, key)
        ]
        manifest["incoming"] = {
            "affected": affected_keys,
            "workspace": state.url,
            "branch": state.branch,
            "base": state.integrated,
            "commit": state.incoming,
            "observed": state.observed,
            "changes": changes,
            "files": _source_files(clone, state),
            "issues": issues,
        }


def attach_adoptions(
    result: ScanResult, renderer: Any, manifest: dict[str, Any], files: dict[str, str | bytes]
) -> None:
    """Publish agent documents' changes beside the optional workspace pull in Incoming."""
    from loom.adopt import comparison, decisions
    from loom.history.ledger import load_history
    from loom.reshape.copy import derived_key

    contributions = []
    for copy in sorted(load_history(result.quilt.history_dir).copies(result.masters)):
        try:
            data = comparison(result, copy)
            choices = decisions(result, copy, manifest.get("reviewer", {}).get("name"))
            rows = []
            for row in data["changes"]:
                if not row["offered"]:
                    continue
                key = row["key"]
                original = next(
                    (old for old, new in data["baseline"].get("mapping", {}).items() if new == key.split("/", 1)[0]),
                    key.split("/", 1)[0],
                )
                derived = derived_key(original + ("/" + key.split("/", 1)[1] if "/" in key else ""))
                local_node = result.nodes.get(key)
                proposed_node = result.nodes.get(derived)
                current_pre = result.closures.get(data["source"])
                proposal_pre = result.closures.get(copy)
                macro_name = "adopt:" + data["fingerprint"][:20]
                manifest["macros"]["sets"][macro_name] = to_mathjax(
                    parse_macros(blank_comments(proposal_pre.raw_text() if proposal_pre else ""))
                )
                before, after = row["current"], row["proposed"]
                left, right = _changed(before, after)
                digest = hashlib.sha256((data["fingerprint"] + key).encode()).hexdigest()[:20]
                local_path = f"fragments/incoming/{digest}-local.html"
                proposed_path = f"fragments/incoming/{digest}-proposal.html"
                if local_node:
                    files[local_path] = _render(
                        renderer, result, key, before, current_pre.raw_text() if current_pre else "", left
                    )
                if proposed_node:
                    files[proposed_path] = _render(
                        renderer,
                        result,
                        proposed_node.key,
                        after,
                        proposal_pre.raw_text() if proposal_pre else "",
                        right,
                    )
                from loom.records.dependencies import historical_display

                changed_targets = {key} if row["math_changed"] else set()
                for target, owner in result.dependencies.owners.items():
                    if owner == key and target.startswith("equation:"):
                        label = target.removeprefix("equation:")
                        old_display = historical_display(before, label) or ""
                        new_display = historical_display(after, label) or ""
                        if mathematical_hash(old_display) != mathematical_hash(new_display):
                            changed_targets.add(target)
                affected = [
                    {"key": k, "citation": _citation(result, k, key)}
                    for k in manifest["keys"]
                    if changed_targets.intersection(result.dependencies.closure(k))
                    and k != key
                    and not result.nodes[k].derived_of
                ]
                rows.append(
                    {
                        **row,
                        "incoming_macros": macro_name,
                        "local": local_path if local_node else None,
                        "incoming": proposed_path if proposed_node else None,
                        "affected": affected,
                    }
                )
            current_pre = result.closures.get(data["source"])
            proposal_pre = result.closures.get(copy)
            context_key = next((k for k, n in result.nodes.items() if data["source"] in n.reached_by), "")
            prose = pair(
                renderer,
                result,
                context_key,
                document_body(data["current_document"]),
                document_body(data["proposed_document"]),
                current_pre.raw_text() if current_pre else "",
                proposal_pre.raw_text() if proposal_pre else "",
                files,
            )
            prose["incoming_macros"] = "adopt:" + data["fingerprint"][:20]
            manifest["macros"]["sets"][prose["incoming_macros"]] = to_mathjax(
                parse_macros(blank_comments(proposal_pre.raw_text() if proposal_pre else ""))
            )
            if rows or data["document_changed"]:
                contributions.append(
                    {
                        "kind": "adopt",
                        "copy": copy,
                        "source": data["source"],
                        "label": f"Incoming from agent document “{Path(copy).stem}”",
                        "fingerprint": data["fingerprint"],
                        "changes": rows,
                        "document_changed": data["document_changed"],
                        "document_comparison": prose,
                        "document_conflict": data["document_conflict"],
                        "document_diff": "".join(
                            difflib.unified_diff(
                                data["current_document"].splitlines(True),
                                data["proposed_document"].splitlines(True),
                                fromfile="Working document",
                                tofile="Proposed document",
                            )
                        ),
                        "choices": choices,
                        "issues": [],
                    }
                )
        except (SyncError, OSError, ValueError) as exc:
            contributions.append(
                {
                    "kind": "adopt",
                    "copy": copy,
                    "label": f"Incoming from agent document “{Path(copy).stem}”",
                    "changes": [],
                    "issues": [str(exc)],
                }
            )
    # Preserve the existing pull field for clients; contributions adds the common source inventory.
    pulled = manifest.get("incoming")
    manifest["contributions"] = (
        [
            {
                "kind": "workspace",
                "label": f"Incoming from {source_label(pulled['workspace'])}",
                **pulled,
            }
        ]
        if pulled
        else []
    ) + contributions
