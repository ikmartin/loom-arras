"""Render accepted and current key text for the review panel's contextual comparisons."""

from __future__ import annotations

import dataclasses
import difflib
import hashlib
import json
import re
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from loom.records.snapshots import read_snapshot
from loom.records.store import Records
from loom.render.convert import Converter
from loom.render.fragments import FragmentRenderer
from loom.render.publish import write_atomic
from loom.scan.hashing import normalize
from loom.scan.macros import parse_macros, to_mathjax
from loom.scan.model import Macro
from loom.scan.nodes import NodeRec
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


@lru_cache(maxsize=64)
def _preamble_macros(preamble: str) -> dict[str, Macro]:
    """A preamble's macros, parsed once: a build renders a review fragment per key against one or two preambles."""
    return parse_macros(blank_comments(preamble))


@lru_cache(maxsize=64)
def _preamble_mathjax(preamble: str) -> list[dict[str, object]]:
    return to_mathjax(_preamble_macros(preamble))


def _fallback(
    renderer: FragmentRenderer, result: ScanResult, node: NodeRec, key: str, preamble: str
) -> Callable[[str, str, str], str]:
    """The figure fallback for a preview: the fragments' own where `preamble` is a live document's, so a figure is compiled once and shared from the SVG cache, else one closed over the recorded preamble the preview shows.

    A live document's previews pass its closure's raw text; the fragments compile against the document's own preamble only, which loads its local files itself, so the two must be matched here rather than compared as keys.
    """
    for master in result.masters:
        closure = result.closures.get(master)
        if closure is not None and closure.raw_text() == preamble:
            return renderer._fallback(master, node.file, key)
    return renderer._fallback_for_preamble(preamble, key)


def _render(
    renderer: FragmentRenderer, result: ScanResult, key: str, text: str, preamble: str, spans: list[list[int]]
) -> str:
    """One preview's markup, from `build/cache/previews/` when a build has rendered the same thing before.

    Keyed on everything the markup is made from: the text, the preamble, the highlighted spans, the node it is drawn as, and the renderer's `salt`. A served quilt rebuilds on every change and a quilt with thousands of results has a preview for each, so rendering them all again on each rebuild was most of its time.
    """
    owner = result.dependencies.owners.get(key, key)
    h = hashlib.sha256(json.dumps([renderer.salt, key, owner, text, preamble, spans]).encode()).hexdigest()[:32]
    cached = renderer.plan.svg_cache.parent / "previews" / f"{h}.html"
    if cached.is_file():
        return cached.read_text(encoding="utf-8")
    markup = _render_now(renderer, result, key, text, preamble, spans)
    write_atomic(cached, markup)
    return markup


def _render_now(
    renderer: FragmentRenderer, result: ScanResult, key: str, text: str, preamble: str, spans: list[list[int]]
) -> str:
    node = result.nodes[result.dependencies.owners.get(key, key)]
    context = dataclasses.replace(
        renderer._context(node, "master"),
        file="review/" + hashlib.sha256(key.encode()).hexdigest()[:20] + ".tex",
        text=text,
        clean=blank_comments(text),
        macros=dict(_preamble_macros(preamble)),
        child_at={},
        include_html=lambda _arg: "",
        fallback=_fallback(renderer, result, node, key, preamble),
        highlight_spans=[(a, b) for a, b in spans],
    )
    markup = Converter(context).render_range(0, len(text))
    # This is displayed beside a live document whose anchors use the same labels.
    return "\n".join(line.rstrip() for line in re.sub(r'(?<=\s)id="[^"]*"', "", markup).split("\n"))


def _machine_made(result: ScanResult) -> set[str]:
    """The cited papers' results their extraction recorded (`mechanical`), which no person reviews and so get no review preview."""
    from loom.refs.proposals import load_results

    root = result.quilt.root
    out: set[str] = set()
    for citekey in {n.digest for n in result.nodes.values() if n.external and n.digest}:
        out |= {rid for rid, r in load_results(root, citekey).items() if r.cls == "mechanical"}
    return out


def attach_comparisons(
    result: ScanResult,
    records: Records,
    renderer: FragmentRenderer,
    manifest: dict[str, Any],
    files: dict[str, str | bytes],
) -> None:
    """Attach lazy fragment paths and source ranges to text-edit causes only."""
    states = records.key_states(result)
    machine = _machine_made(result)
    master = result.default_master
    closure = result.closures.get(master) if master else None
    current_preamble = closure.raw_text() if closure else ""
    for key, state in states.items():
        document = Records.row_document(result, state.row) if state.row else master
        closure = result.closures.get(document) if document else None
        current_preamble = closure.raw_text() if closure else ""
        current_macros = "review-current:" + hashlib.sha256(current_preamble.encode()).hexdigest()[:20]
        manifest["macros"]["sets"][current_macros] = list(_preamble_mathjax(current_preamble))
        if (
            key in manifest["keys"]
            and result.nodes[key].kind in ("environment", "proof")
            and (not state.row or not state.fresh)
            and key not in machine
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
