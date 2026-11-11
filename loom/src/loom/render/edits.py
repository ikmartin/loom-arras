"""The manifest's `suggested_edits`: each edit with its new text rendered as the document renders it, and, while it is open, its key as it would read with the edit taken."""

from __future__ import annotations

import dataclasses
import re
from typing import Any

from loom.records.edits import Edit, Unplaced, is_taken, patch, place, replay
from loom.render.convert import Converter
from loom.render.fragments import FragmentRenderer
from loom.scan.scan import ScanResult
from loom.scan.source import blank_comments


def _with_html(result: ScanResult, renderer: FragmentRenderer, edit: Edit) -> str | None:
    """The new text rendered in the context of the result it is on, else the default document; None when the converter refuses it, and the viewer renders the TeX as prose.

    New text may be a whole theorem and its proof, which only the converter reads: the viewer's own prose renderer handles a sentence, and hands `\\begin{theorem}` to MathJax, which draws it as an error.
    """
    new = edit.with_text
    node = result.nodes.get(edit.target_key) or result.nodes.get(result.default_master or "")
    if not new or node is None:
        return None
    context = dataclasses.replace(
        renderer._context(node, "master"),
        file=f"edit/{edit.id}",
        text=new,
        clean=blank_comments(new),
        child_at={},
        include_html=lambda _arg: "",
        highlight_spans=[],
        diagnostics=[],
    )
    try:
        markup = Converter(context).render_range(0, len(new))
    except Exception:  # noqa: BLE001 -- new text is an agent's, and text it cannot read falls back to prose rather than failing the build
        return None
    # drawn inside the document it is about, whose anchors carry the same labels
    return re.sub(r'(?<=\s)id="[^"]*"', "", markup)


def _change(
    result: ScanResult, renderer: FragmentRenderer, edit: Edit, files: dict[str, str | bytes]
) -> dict[str, Any] | None:
    """An open edit's `change`: `{state: ready, fragment, diff, moved}` with its key rendered taken and the patch, under `fragments/edits/`; `{state: taken}` when the key reads as it taken already; `{state: unplaced, why}` when its text has no place. None for a settled edit."""
    from loom.render.review_compare import _changed, _render

    if edit.status != "open":
        return None
    if is_taken(result, edit):
        return {"state": "taken"}
    try:
        placed = place(result, edit)
    except Unplaced as exc:
        return {"state": "unplaced", "why": str(exc)}
    master = next(iter(sorted(result.nodes[placed.key].reached_by)), None) or result.default_master
    closure = result.closures.get(master) if master else None
    _, spans = _changed(placed.own, placed.taken)
    fragment = f"fragments/edits/{edit.id}.html"
    diff = f"fragments/edits/{edit.id}.diff"
    files[fragment] = _render(renderer, result, placed.key, placed.taken, closure.raw_text() if closure else "", spans)
    files[diff] = patch(result, placed)
    return {"state": "ready", "fragment": fragment, "diff": diff, "moved": placed.moved}


def attach_edits(
    result: ScanResult, renderer: FragmentRenderer, manifest: dict[str, Any], files: dict[str, str | bytes]
) -> None:
    """Publish every suggested edit as `manifest["suggested_edits"]`, oldest first, with `with_html`, `comment_html` and `change`; rendered at build, so a static host shows them too."""
    from loom.records.store import render_markdown

    out: dict[str, Any] = {}
    edits, _ = replay(result.quilt.root)
    for edit in sorted(edits, key=lambda e: e.created):
        row = edit.to_dict()
        row["author"] = {**row["author"], "label": edit.author_id}
        row["with_html"] = _with_html(result, renderer, edit)
        row["comment_html"] = render_markdown(edit.comment) if edit.comment else None
        row["change"] = _change(result, renderer, edit, files)
        out[edit.id] = row
    manifest["suggested_edits"] = out
