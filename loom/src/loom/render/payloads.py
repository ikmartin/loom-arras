"""Proposed text rendered as the document renders it: each annotation's payload, beside its TeX, as `payload_html`."""

from __future__ import annotations

import dataclasses
import re
from typing import Any

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
