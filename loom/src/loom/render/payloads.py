"""Proposed text rendered as the document renders it: each annotation's payload, beside its TeX, as `payload_html`; and each open suggestion's key as it would read with the suggestion taken, as `change`."""

from __future__ import annotations

import dataclasses
import re
from typing import Any

from loom.records.store import Records
from loom.records.suggestions import SUGGESTION, Unplaced, is_taken, patch, place
from loom.render.convert import Converter
from loom.render.fragments import FragmentRenderer
from loom.scan.scan import ScanResult
from loom.scan.source import blank_comments


def attach_payloads(result: ScanResult, renderer: FragmentRenderer, manifest: dict[str, Any]) -> None:
    """Give every annotation that proposes text its proposal rendered, in the context of the result it is on.

    A proposal may be a whole theorem and its proof, which only the converter reads: the viewer's own prose renderer handles a sentence, and hands `\\begin{theorem}` to MathJax, which draws it as an error. An annotation on no result is read in the default document; a proposal the converter refuses keeps `payload_html` null and the viewer renders the TeX as prose.
    """
    for entry in manifest.get("annotations", {}).values():
        entry["payload_html"] = None
        payload = entry.get("payload")
        # the result it is on, else the default document, whose theorems and macros are the quilt's
        node = result.nodes.get((entry.get("target") or {}).get("key") or "") or result.nodes.get(
            result.default_master or ""
        )
        if not payload or node is None:
            continue
        context = dataclasses.replace(
            renderer._context(node, "master"),
            file=f"payload/{entry['id']}",
            text=payload,
            clean=blank_comments(payload),
            child_at={},
            include_html=lambda _arg: "",
            highlight_spans=[],
            diagnostics=[],
        )
        try:
            markup = Converter(context).render_range(0, len(payload))
        except Exception:  # noqa: BLE001 -- a proposal is an agent's text, and one it cannot read falls back to prose rather than failing the build
            continue
        # drawn inside the document it is about, whose anchors carry the same labels
        entry["payload_html"] = re.sub(r'(?<=\s)id="[^"]*"', "", markup)


def attach_changes(
    result: ScanResult,
    records: Records,
    renderer: FragmentRenderer,
    manifest: dict[str, Any],
    files: dict[str, str | bytes],
) -> None:
    """Give every open suggestion carrying text its `change`: its key as it would read with the suggestion taken, or why it cannot be shown so.

    `{"state": "ready", "fragment", "diff", "moved"}` is the key rendered with the payload in place, its changed words marked as Review marks them, and the patch `loom suggestion` prints, both under `fragments/suggestions/`; `{"state": "taken"}` says the key already reads as the suggestion taken, so resolving it as applied is offered; `{"state": "unplaced", "why"}` says why the payload has no place. Rendered at build, so a static host shows it too.
    """
    from loom.render.review_compare import _changed, _render

    entries = manifest.get("annotations", {})
    for record in records.records:
        if record.discarded:
            continue
        for ann in record.annotations:
            entry = entries.get(ann.id)
            if entry is None or ann.kind != SUGGESTION or ann.payload is None or ann.status != "open":
                continue
            if is_taken(result, ann):
                entry["change"] = {"state": "taken"}
                continue
            try:
                placed = place(result, ann)
            except Unplaced as exc:
                entry["change"] = {"state": "unplaced", "why": str(exc)}
                continue
            master = next(iter(sorted(result.nodes[placed.key].reached_by)), None) or result.default_master
            closure = result.closures.get(master) if master else None
            _, spans = _changed(placed.own, placed.taken)
            fragment = f"fragments/suggestions/{ann.id}.html"
            diff = f"fragments/suggestions/{ann.id}.diff"
            files[fragment] = _render(
                renderer, result, placed.key, placed.taken, closure.raw_text() if closure else "", spans
            )
            files[diff] = patch(result, placed)
            entry["change"] = {"state": "ready", "fragment": fragment, "diff": diff, "moved": placed.moved}
