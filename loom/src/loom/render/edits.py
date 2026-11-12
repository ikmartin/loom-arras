"""The manifest's `suggested_edits`: each edit with its new text made by TeX as the document makes it, and, while it is open, its key as it would read with the edit taken."""

from __future__ import annotations

from typing import Any

from loom.records.edits import Edit, Unplaced, is_taken, patch, place, replay
from loom.render.fragments import FragmentRenderer
from loom.scan.scan import ScanResult


def _ask_with_html(result: ScanResult, renderer: FragmentRenderer, edit: Edit, row: dict[str, Any]) -> None:
    """Ask for the new text made by TeX, in the terms of the result it is on, else the default document; `row["with_html"]` is set when the build's previews are made, and stays None when TeX refuses it, so the viewer renders the TeX as prose.

    New text may be a whole theorem and its proof, which only TeX reads: the viewer's own prose renderer handles a sentence, and hands `\\begin{theorem}` to MathJax, which draws it as an error. Made with the build's other previews (`FragmentRenderer.previews`).
    """
    row["with_html"] = None
    new = edit.with_text
    node = result.nodes.get(edit.target_key) or result.nodes.get(result.default_master or "")
    if not new or node is None:
        return
    later = renderer.previews.ask(node.key, new, None, [])

    def took(html: str, row: dict[str, Any] = row) -> None:
        row["with_html"] = None if html.startswith('<pre class="source"') else html

    renderer.previews.on_made(later, took)


def _change(
    result: ScanResult, renderer: FragmentRenderer, edit: Edit, files: dict[str, str | bytes]
) -> dict[str, Any] | None:
    """An open edit's `change`: `{state: ready, fragment, diff, moved}` with its key made taken and the patch, under `fragments/edits/`; `{state: taken}` when the key reads as it taken already; `{state: unplaced, why}` when its text has no place. None for a kept or discarded edit."""
    from loom.render.review_compare import _changed, _render_into

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
    _render_into(
        files, fragment, renderer, result, placed.key, placed.taken, closure.raw_text() if closure else "", spans
    )
    files[diff] = patch(result, placed)
    return {"state": "ready", "fragment": fragment, "diff": diff, "moved": placed.moved}


def attach_edits(
    result: ScanResult, renderer: FragmentRenderer, manifest: dict[str, Any], files: dict[str, str | bytes]
) -> None:
    """Publish every suggested edit as `manifest["suggested_edits"]`, oldest first, with `with_html`, `comment_html` and `change`; made at build, so a static host shows them too."""
    from loom.records.store import render_markdown

    out: dict[str, Any] = {}
    edits, _ = replay(result.quilt.root)
    for edit in sorted(edits, key=lambda e: e.created):
        row = edit.to_dict()
        row["author"] = {**row["author"], "label": edit.author_id}
        _ask_with_html(result, renderer, edit, row)
        row["comment_html"] = render_markdown(edit.comment) if edit.comment else None
        row["change"] = _change(result, renderer, edit, files)
        out[edit.id] = row
    manifest["suggested_edits"] = out
