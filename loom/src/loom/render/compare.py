"""Compare's texts (book 15.2.6): the differing pairs of two items, rendered with their changed words when a viewer asks, never at build.

A pair is two nodes with one plain key (`zk-0001` and `zk-0001-ai`, or a key in a landmark and today). Rendering is cached by content under `build/compare/`, so a pair renders once however many comparisons ask for it.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.history.ledger import History, load_history
from loom.history.versions import read_version
from loom.render.canon import CanonDoc, _preamble_for, load_canon
from loom.render.fragments import FragmentRenderer, RenderPlan
from loom.render.manifest import own_text
from loom.render.publish import write_atomic
from loom.render.review_compare import _render, _tokens
from loom.scan.hashing import normalize, pair_hash
from loom.scan.labels import plain_key
from loom.scan.scan import ScanResult
from loom.tex.aux import read_cite_labels, read_numbers

CACHE = "compare"
# a derived label made plain inside a token, so `\ref{zk-0001-ai}` and `\ref{zk-0001}` are the same word
_DERIVED_IN_TOKEN = re.compile(r"-ai(?=[},\]/\s]|$)")


class CompareError(Exception):
    """An item that is neither a live document nor a landmark."""


@dataclass
class Side:
    """One item of a comparison: its nodes by plain key, and what a rendering of it needs."""

    item: str
    kind: str  # "document", "landmark" or "node"
    texts: dict[str, tuple[str, str]] = field(default_factory=dict)  # plain key -> (its key there, raw own text)
    preamble: str = ""
    macros: str | None = None  # the manifest's macro set, None for the default
    step: int | None = None  # a landmark's step
    copy_of: str | None = None  # an agent document's source


def _side(result: ScanResult, history: History, canon: dict[str, CanonDoc], item: str) -> Side:
    if item in result.masters:
        side = Side(item, "document")
        closure = result.closures.get(item)
        side.preamble = closure.raw_text() if closure else ""
        side.copy_of = history.copy_of(item, result.masters)
        for key, n in result.nodes.items():
            head = result.nodes.get(key.split("/", 1)[0])
            if item in n.reached_by and head is not None and head.id and n.kind in ("environment", "proof"):
                side.texts[plain_key(key)] = (key, own_text(result, n))
        return side
    node = result.nodes.get(item)
    if node is not None and node.kind in ("environment", "proof"):
        side = Side(item, "node")
        master = next(iter(sorted(node.reached_by)), None)
        closure = result.closures.get(master) if master else None
        side.preamble = closure.raw_text() if closure else ""
        side.texts[plain_key(item)] = (item, own_text(result, node))
        return side
    by_path = {history.landmark_path(e).relative_to(result.quilt.root).as_posix(): e for e in history.landmarks()}
    entry = by_path.get(item) or history.landmark(item)
    if entry is None or entry.step is None:
        raise CompareError(f"{item} is neither a live document, a landmark nor a node")
    rel = history.landmark_path(entry).relative_to(result.quilt.root).as_posix()
    doc = canon.get(rel)
    side = Side(item, "landmark", step=entry.step)
    if doc is not None:
        side.preamble = _preamble_for(doc.closure)
        side.macros = f"canon:{doc.stem}"
    for key in entry.get("reaches") or []:
        try:
            side.texts[key] = (key, read_version(history, key, str(entry.step))[1])
        except LookupError:
            continue
    return side


def _changed(before: str, after: str) -> tuple[list[list[int]], list[list[int]]]:
    """Review's word diff, a derived label counted as its plain one."""
    left, right = _tokens(before), _tokens(after)
    words = [[_DERIVED_IN_TOKEN.sub("", x[0]) for x in side] for side in (left, right)]
    match = difflib.SequenceMatcher(None, words[0], words[1], autojunk=False)
    out: list[list[list[int]]] = [[], []]
    for kind, a, b, c, d in match.get_opcodes():
        if kind == "equal":
            continue
        for index, tokens, start, end, text in ((0, left, a, b, before), (1, right, c, d, after)):
            lo = tokens[start][1] if start < len(tokens) else len(text)
            hi = tokens[end - 1][2] if end > start else lo
            out[index].append([lo, hi])
    return out[0], out[1]


def _base(
    result: ScanResult, history: History, left: Side, right: Side, lk: str, rk: str, lh: str, rh: str
) -> str | None:
    """Which side holds the base of one pair: 'left', 'right', 'both' (changed on both sides since it), or None."""
    for side, key in ((left, lk), (right, rk)):
        if side.kind == "landmark" or key == plain_key(key):
            continue
        copy = next(
            (
                c
                for c in (result.nodes[key].reached_by if key in result.nodes else ())
                if c in history.copies(result.masters)
            ),
            None,
        )
        base = history.bases(copy, result.masters).get(key) if copy else None
        if base is None:
            continue
        try:
            math = pair_hash(read_version(history, str(base["key"]), str(base["step"]))[1])
        except LookupError:
            continue
        if lh == math:
            return "left"
        if rh == math:
            return "right"
        return "both"
    if left.kind == "landmark" and right.kind == "landmark":
        return "left" if (left.step or 0) <= (right.step or 0) else "right"
    if left.kind == "landmark":
        return "left"
    if right.kind == "landmark":
        return "right"
    return None


def _cached(
    root: Path,
    renderer: FragmentRenderer,
    result: ScanResult,
    context: str,
    text: str,
    preamble: str,
    spans: list[list[int]],
) -> str:
    """The published path of one side's highlighted rendering, rendered only when no earlier request left it."""
    from loom.render.keys import code_hash
    from loom.version import __version__

    h = hashlib.sha256()
    for part in (__version__, code_hash(), context, text, preamble, repr(spans)):
        h.update(part.encode("utf-8", errors="replace"))
        h.update(b"\0")
    rel = f"{CACHE}/{h.hexdigest()[:32]}.html"
    path = root / "build" / rel
    if not path.is_file():
        write_atomic(path, _render(renderer, result, context, text, preamble, spans))
    return rel


def compare(result: ScanResult, left: str, right: str) -> dict[str, Any]:
    """The differing pairs of two items, each side rendered with its changed words.

    Parameters
    ----------
    result : ScanResult
        A scan of the quilt now.
    left, right : str
        Each a live document's path, a landmark by its path, name, step or `DOC@STEP`, or a live node's key.

    Returns
    -------
    dict
        `{"left": {item, kind, macros}, "right": {...}, "pairs": [...]}`. Each pair has `pair` (the plain key), `base` ('left', 'right', 'both' or None) and, per side, `key`, `hash` and `fragment` (a path under the build directory; absent when no live node gives the rendering its context). Pairs whose `pair_hash`es agree are left out: a display name changed alone is no difference (book 17.7).

    Raises
    ------
    CompareError
        When an item is neither a live document nor a landmark.
    """
    root = result.quilt.root
    history = load_history(result.quilt.history_dir)
    canon = {d.path: d for d in load_canon(result.quilt, result, history)}
    sides = _side(result, history, canon, left), _side(result, history, canon, right)
    plan = RenderPlan(
        result=result,
        numbers={m: read_numbers(root, m) for m in result.masters},
        cite_labels={m: read_cite_labels(root, m) for m in result.masters},
        svg_cache=root / "build" / "cache" / "svg",
        svg_out=root / "build" / "svg",
    )
    renderer = FragmentRenderer(plan)
    pairs: list[dict[str, Any]] = []
    order = [k for k in sides[0].texts if k in sides[1].texts]
    for pk in order:
        (lk, ltext), (rk, rtext) = sides[0].texts[pk], sides[1].texts[pk]
        lh, rh = pair_hash(ltext), pair_hash(rtext)
        if lh == rh:
            continue
        before, after = normalize(ltext), normalize(rtext)
        spans = _changed(before, after)
        entry: dict[str, Any] = {"pair": pk, "base": _base(result, history, *sides, lk, rk, lh, rh)}
        for name, side, key, text, h, sp in (
            ("left", sides[0], lk, before, lh, spans[0]),
            ("right", sides[1], rk, after, rh, spans[1]),
        ):
            out: dict[str, Any] = {"key": key, "hash": h}
            # a rendering takes its numbers and labels from a live node of the pair; a pair the quilt no longer has keeps its whole-node marks
            context = key if key in result.nodes else (pk if pk in result.nodes else None)
            if context is not None:
                out["fragment"] = _cached(root, renderer, result, context, text, side.preamble, sp)
            entry[name] = out
        pairs.append(entry)
    return {
        "left": {"item": sides[0].item, "kind": sides[0].kind, "macros": sides[0].macros},
        "right": {"item": sides[1].item, "kind": sides[1].kind, "macros": sides[1].macros},
        "pairs": pairs,
    }
