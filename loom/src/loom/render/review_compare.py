"""Render accepted and current key text for the review panel's contextual comparisons."""

from __future__ import annotations

import dataclasses
import difflib
import hashlib
import re
from typing import Any

from loom.records.snapshots import read_snapshot
from loom.records.store import Records
from loom.render.convert import Converter
from loom.render.fragments import FragmentRenderer
from loom.scan.hashing import normalize
from loom.scan.macros import parse_macros, to_mathjax
from loom.scan.scan import ScanResult
from loom.scan.source import blank_comments


def _tokens(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(), m.start(), m.end()) for m in re.finditer(r"\s+|[^\s]+", text)]


def _changed(before: str, after: str) -> tuple[list[list[int]], list[list[int]]]:
    left, right = _tokens(before), _tokens(after)
    match = difflib.SequenceMatcher(None, [x[0] for x in left], [x[0] for x in right], autojunk=False)
    out: list[list[list[int]]] = [[], []]
    for kind, a, b, c, d in match.get_opcodes():
        if kind == "equal":
            continue
        for index, tokens, start, end, text in ((0, left, a, b, before), (1, right, c, d, after)):
            lo = tokens[start][1] if start < len(tokens) else len(text)
            hi = tokens[end - 1][2] if end > start else lo
            out[index].append([lo, hi])
    return out[0], out[1]


def _render(
    renderer: FragmentRenderer, result: ScanResult, key: str, text: str, preamble: str, spans: list[list[int]]
) -> str:
    node = result.nodes[result.dependencies.owners.get(key, key)]
    context = dataclasses.replace(
        renderer._context(node, "master"),
        file="review/" + hashlib.sha256(key.encode()).hexdigest()[:20] + ".tex",
        text=text,
        clean=blank_comments(text),
        macros=parse_macros(blank_comments(preamble)),
        child_at={},
        include_html=lambda _arg: "",
        fallback=renderer._fallback_for_preamble(preamble, key),
        highlight_spans=[(a, b) for a, b in spans],
    )
    markup = Converter(context).render_range(0, len(text))
    # This is displayed beside a live document whose anchors use the same labels.
    return "\n".join(line.rstrip() for line in re.sub(r'(?<=\s)id="[^"]*"', "", markup).split("\n"))


def attach_comparisons(
    result: ScanResult,
    records: Records,
    renderer: FragmentRenderer,
    manifest: dict[str, Any],
    files: dict[str, str | bytes],
) -> None:
    """Attach lazy fragment paths and source ranges to text-edit causes only."""
    states = records.key_states(result)
    master = result.default_master
    closure = result.closures.get(master) if master else None
    current_preamble = closure.raw_text() if closure else ""
    for key, state in states.items():
        document = Records.row_document(result, state.row) if state.row else master
        closure = result.closures.get(document) if document else None
        current_preamble = closure.raw_text() if closure else ""
        current_macros = "review-current:" + hashlib.sha256(current_preamble.encode()).hexdigest()[:20]
        manifest["macros"]["sets"][current_macros] = to_mathjax(parse_macros(blank_comments(current_preamble)))
        if (
            key in manifest["keys"]
            and result.nodes[key].kind in ("environment", "proof")
            and (not state.row or not state.fresh)
        ):
            text = result.dependencies.texts.get(key) or ""
            digest = hashlib.sha256((key + text + current_preamble).encode()).hexdigest()[:20]
            path = f"fragments/review/{digest}-block.html"
            files[path] = _render(renderer, result, key, text, current_preamble, [])
            manifest["keys"][key]["review_fragment"] = path
            manifest["keys"][key]["review_macros"] = current_macros
        if not state.row or key not in manifest["keys"]:
            continue
        published = manifest["keys"][key].get("acceptance", {}).get("causes", [])
        for cause, entry in zip(state.causes, published, strict=True):
            if cause.id and (text := result.dependencies.texts.get(cause.id)) is not None:
                digest = hashlib.sha256((cause.id + text + current_preamble).encode()).hexdigest()[:20]
                path = f"fragments/review/{digest}-dependency.html"
                files[path] = _render(renderer, result, cause.id, text, current_preamble, [])
                entry["current_fragment"] = path
                entry["current_macros"] = current_macros
            if cause.kind not in ("own-text-changed", "dependency-changed") or not cause.before or cause.via:
                continue
            target = cause.id or key
            if target not in result.dependencies.texts:
                continue
            before = records.snapshot(cause.before)
            if before is None:
                continue
            after = normalize(result.dependencies.texts[target] or "")
            # The before snapshot belongs to this key's acceptance epoch, even if
            # the dependency was accepted again with a different preamble later.
            pre_hash = state.row.preamble
            old_preamble = read_snapshot(result.quilt.root, pre_hash, result.quilt.history_dir) or ""
            left, right = _changed(before, after)
            digest = hashlib.sha256((target + cause.before + after + pre_hash).encode()).hexdigest()[:20]
            old_path = f"fragments/review/{digest}-accepted.html"
            new_path = f"fragments/review/{digest}-current.html"
            files[old_path] = _render(renderer, result, target, before, old_preamble, left)
            files[new_path] = _render(renderer, result, target, after, current_preamble, right)
            macro_name = f"review:{digest}"
            manifest["macros"]["sets"][macro_name] = to_mathjax(parse_macros(blank_comments(old_preamble)))
            entry["comparison"] = {
                "accepted": old_path,
                "current": new_path,
                "current_macros": current_macros,
                "accepted_macros": macro_name,
                "accepted_spans": left,
                "current_spans": right,
            }
