"""Rendered source comparisons for document prose, without acceptance identities."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from loom.render.manifest import own_text
from loom.render.review_compare import _changed, _render
from loom.scan.hashing import normalize
from loom.scan.scan import ScanResult


def prose_sections(result: ScanResult) -> dict[str, tuple[str, str]]:
    return {
        key: (node.title or key, document_body(re.sub(r"^% !LOOM child:.*$", "", own_text(result, node), flags=re.M)))
        for key, node in result.nodes.items()
        if node.kind in ("section", "master", "file")
        and not node.derived_of
        and node.file.endswith(".tex")
        and not node.file.startswith(result.quilt.config.drafting_ai + "/")
    }


def pair(
    renderer: Any,
    result: ScanResult,
    key: str,
    before: str,
    after: str,
    old_preamble: str,
    new_preamble: str,
    files: dict[str, str | bytes],
) -> dict[str, Any]:
    """Render one revision-bound pair; retain source when rendering is unavailable."""
    left, right = _changed(before, after)
    digest = hashlib.sha256((before + after + old_preamble + new_preamble).encode()).hexdigest()[:24]
    paths: list[str | None] = []
    for side, text, pre, spans in (("local", before, old_preamble, left), ("incoming", after, new_preamble, right)):
        path = f"fragments/incoming/prose-{digest}-{side}.html"
        if not text or key not in result.nodes:
            paths.append(None)
        else:
            files[path] = _render(renderer, result, key, text, pre, spans)
            paths.append(path)
    return {"local": paths[0], "incoming": paths[1], "current": before, "proposed": after}


def attach_prose(
    result: ScanResult,
    base: ScanResult,
    incoming: ScanResult,
    renderer: Any,
    files: dict[str, str | bytes],
    current_pre: str,
    incoming_pre: str,
    macros: str,
) -> list[dict[str, Any]]:
    old, new, local = prose_sections(base), prose_sections(incoming), prose_sections(result)
    out = []
    for key in sorted(old.keys() | new.keys()):
        before = normalize(old.get(key, ("", ""))[1])
        after = normalize(new.get(key, ("", ""))[1])
        if before == after:
            continue
        current = normalize(local.get(key, ("", ""))[1])
        out.append(
            {
                "key": "prose:" + key,
                "name": new.get(key, old.get(key, (key, "")))[0],
                "category": "prose",
                "kind": "added" if not before else "removed" if not after else "edited",
                "local_changed": current != before,
                "conflict": current != before and current != after,
                "already_local": current == after,
                "incoming_macros": macros,
                "affected": [],
                **pair(renderer, result, key, current, after, current_pre, incoming_pre, files),
            }
        )
    return out


def document_body(text: str) -> str:
    """The readable document skeleton; preamble and ordering remain in the exact source diff."""
    if r"\begin{document}" in text:
        text = text.split(r"\begin{document}", 1)[1]
    return text.split(r"\end{document}", 1)[0]
