"""Explicit mathematical decisions bound to an inspected incorporation preview."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from loom.cli.review import _acceptance_master, _owned
from loom.records.store import Records
from loom.render.manifest import own_text
from loom.render.publish import write_atomic
from loom.review_queue import fingerprint
from loom.scan.scan import ScanResult, scan
from loom.sync import SyncError


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _source(result: ScanResult) -> str:
    return _digest(
        {
            "files": {p: f.text for p, f in result.files.items()},
            "config": (result.quilt.root / "config.toml").read_text(),
        }
    )


def _refusal(result: ScanResult, key: str) -> str:
    n = result.nodes[key]
    if n.external or n.derived_of or not _owned(result, key):
        return "This is not a live author-owned block."
    if n.incomplete or (n.kind == "environment" and n.basis in ("open-claim", "unclassified")):
        return "Resolve this block's incomplete or unclassified status before acceptance."
    if any(result.dependencies.texts.get(d) is None for d in result.dependencies.closure(key)):
        return "A complete mathematical dependency could not be identified."
    return ""


def preview(before: ScanResult, overlay: dict[str, str], binding: dict[str, str], reviewer: str) -> dict[str, Any]:
    """Publish an immutable prospective mathematical review, without accepting or applying source."""
    from loom.render.fragments import FragmentRenderer, RenderPlan
    from loom.render.review_compare import _changed, _render
    from loom.scan.macros import parse_macros, to_mathjax
    from loom.scan.source import blank_comments
    from loom.tex.aux import read_cite_labels, read_numbers

    root = before.quilt.root
    after = scan(before.quilt, overlay=overlay)
    keys = [
        k
        for k, n in after.nodes.items()
        if n.kind in ("environment", "proof")
        and not n.external
        and _owned(after, k)
        and (k not in before.nodes or fingerprint(before, k) != fingerprint(after, k))
    ]
    keys.sort(key=lambda k: (after.nodes[k].file, after.nodes[k].start, k))
    saved = {
        "binding": binding,
        "reviewer": reviewer,
        "source": _source(before),
        "overlay": overlay,
        "fingerprints": {k: fingerprint(after, k) for k in keys},
    }
    token = _digest(saved)
    write_atomic(root / "build/incorporation-review" / (token + ".json"), json.dumps(saved))
    renderers = [
        FragmentRenderer(
            RenderPlan(
                result=r,
                numbers={m: read_numbers(root, m) for m in r.masters},
                cite_labels={m: read_cite_labels(root, m) for m in r.masters},
                svg_cache=root / "build/cache/svg",
                svg_out=root / "build/svg",
            )
        )
        for r in (before, after)
    ]
    items: list[dict[str, Any]] = []
    changed = {
        k for k in keys if k not in before.nodes or own_text(before, before.nodes[k]) != own_text(after, after.nodes[k])
    }
    for key in keys:
        node = after.nodes[key]
        old = own_text(before, before.nodes[key]) if key in before.nodes else ""
        new = own_text(after, node)
        spans = _changed(old, new)
        sides: list[dict[str, Any] | None] = []
        for i, (result, text) in enumerate(((before, old), (after, new))):
            if key not in result.nodes:
                sides.append(None)
                continue
            master = _acceptance_master(result, key)
            pre = result.closures[master].raw_text() if master in result.closures else ""
            path = f"incorporation-review/{token}-{len(items)}-{i}.html"
            write_atomic(root / "build" / path, _render(renderers[i], result, key, text, pre, spans[i]))
            sides.append({"path": path, "macros": to_mathjax(parse_macros(blank_comments(pre)))})
        dependencies = sorted(
            d
            for d in after.dependencies.closure(key)
            if before.dependencies.texts.get(d) != after.dependencies.texts.get(d)
        )
        proof_changed = node.kind == "proof" and node.of in changed and key not in changed
        items.append(
            {
                "key": key,
                "name": node.title or f"{node.taxon or node.kind} · {key}",
                "reason": (
                    "Existing proof · statement changed in the AI revision"
                    if binding.get("kind") == "adopt"
                    else "Existing proof · statement changed in this pull"
                )
                if proof_changed
                else "Mathematical text changed"
                if key in changed
                else "Unchanged text · cited support changed"
                if dependencies
                else "Unchanged text · document context changed",
                "dependencies": sorted({after.dependencies.owners.get(d, d) for d in dependencies}),
                "local": sides[0],
                "proposed": sides[1],
                "unavailable": _refusal(after, key),
            }
        )
    return {"token": token, "reviewer": reviewer, "items": items}


def validate(
    before: ScanResult, token: str, binding: dict[str, str], reviewer: str, accept: list[str]
) -> dict[str, Any]:
    """Refuse stale previews and invalid acceptance selections before incorporation."""
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise SyncError("Inspect the mathematical preview before submitting decisions")
    path = before.quilt.root / "build/incorporation-review" / (token + ".json")
    if not path.is_file():
        raise SyncError("Mathematical preview unavailable; inspect it again")
    saved: dict[str, Any] = json.loads(path.read_text())
    if (
        _digest(saved) != token
        or saved["binding"] != binding
        or saved["reviewer"] != reviewer
        or saved["source"] != _source(before)
    ):
        raise SyncError("Source, revision or reviewer changed; inspect a fresh preview and choose acceptance again")
    if len(set(accept)) != len(accept) or set(accept) - saved["fingerprints"].keys():
        raise SyncError("Acceptance must name distinct mathematical blocks in the inspected preview")
    after = scan(before.quilt, overlay=saved["overlay"])
    for key in accept:
        if why := _refusal(after, key):
            raise SyncError(f"{key}: {why}")
    _dependencies(after, accept, reviewer)
    return saved


def _dependencies(result: ScanResult, keys: list[str], reviewer: str) -> None:
    states = Records(result.quilt.root, result.quilt.history_dir, reviewer=reviewer).key_states(result)
    for key in keys:
        for dep in result.dependencies.review_targets(key):
            state = states.get(dep)
            if state and state.row and not state.fresh and dep not in keys:
                raise SyncError(
                    f"Accept {dep} too, or keep {key} for review; its mathematical support is still pending"
                )


def finish(result: ScanResult, saved: dict[str, Any], accept: list[str], reviewer: str) -> dict[str, Any]:
    """Record only explicit choices; an acceptance failure leaves incorporated mathematics pending."""
    from loom.cli.review import _master_compiles, write_acceptance
    from loom.review_queue import clear_accepted, keep_pending

    keys = [k for k in saved["fingerprints"] if k in result.nodes]
    keep_pending(result, keys, reviewer)
    if not accept:
        return {"accepted": [], "pending": keys}
    try:
        for key in accept:
            if key not in result.nodes or fingerprint(result, key) != saved["fingerprints"][key]:
                raise SyncError("The incorporated mathematics differs from the inspected preview; review it again")
            if why := _refusal(result, key):
                raise SyncError(f"{key}: {why}")
        _dependencies(result, accept, reviewer)
        contexts = {k: _acceptance_master(result, k) for k in accept}
        for master in dict.fromkeys(contexts.values()):
            ok, why = _master_compiles(result, master)
            if not ok:
                raise SyncError(f"{master} does not compile: {why}")
        if _source(scan(result.quilt)) != _source(result):
            raise SyncError("Source changed during compilation; inspect the mathematics again")
        write_acceptance(result, accept, reviewer, contexts)
        clear_accepted(result.quilt.root, accept, reviewer)
    except Exception as exc:
        # Source incorporation already succeeded. Never report it as failed or invite a second application.
        return {
            "accepted": [],
            "pending": keys,
            "acceptance_error": f"Changes incorporated, but acceptance could not be recorded: {exc}. The blocks remain in Needs review.",
        }
    return {"accepted": accept, "pending": [k for k in keys if k not in accept]}
