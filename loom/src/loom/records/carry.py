"""Annotations carried onto the new words when the person keeps a change (decision 12 of plan 0.30).

An annotation whose words a kept change touches gets an `edited` event: its `anchor` on the words that replaced them, and `earlier: {quote, change}`, the words it was on and the change that replaced them. Its `against` stays, so it still names the version it was written on, which the manifest publishes as its `version`. An annotation whose words were all removed becomes a point where they were (`exact` empty, `prefix` and `suffix` the text either side), drawn as an empty mark. Discarding a change carries nothing: the words an annotation is on are the person's again.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loom.records.selectors import CONTEXT, Selector, resolve_selector

if TYPE_CHECKING:
    from loom.pending import Pending
    from loom.scan.scan import ScanResult


def _moved(at: int, regions: list[tuple[int, int, int, int]], *, end: bool) -> int:
    """A place in the text before as a place in the text after: outside a changed stretch it moves with the text, inside one it goes to that stretch's words, its start or its end."""
    shift = 0
    for o0, o1, n0, n1 in regions:
        if (at <= o0) if end else (at < o0):
            break
        if (at <= o1) if end else (at < o1):
            return n1 if end else n0
        shift = n1 - o1
    return at + shift


def carry(
    result: ScanResult,
    key: str,
    before: str,
    after: str,
    changes: list[Pending],
    writer: tuple[str, str],
    resolved: list[Any] | None = None,
) -> list[str]:
    """Carry the annotations on `key` whose words changed between `before` and `after`, its own text as the person kept it before and after keeping `changes`; returns the ids carried.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned after the keep.
    key : str
        The node.
    before, after : str
        Its own text as kept, before and after.
    changes : list of Pending
        The changes kept on it, the first of which an annotation names in `earlier` when its words match none of them.
    writer : (str, str)
        Who kept them.
    resolved : list of ResolvedAnnotation, optional
        The quilt's annotations resolved against `result`, when the caller has them.

    Returns
    -------
    list of str
        The annotations carried.
    """
    from loom.clock import stamp
    from loom.pending import cut
    from loom.records.log import append
    from loom.records.store import Records

    if before == after or not changes:
        return []
    regions = cut(before, after)
    akind, aid = writer
    out: list[str] = []
    if resolved is None:
        resolved = Records(result.quilt.root, result.quilt.history_dir).resolved(result)
    for res in resolved:
        a = res.annotation
        if a.selector is None or a.in_reply_to or a.page is not None or a.anchor is not None or res.target != key:
            continue
        span = resolve_selector(before, a.selector)
        if span is None:
            continue
        lo, hi = span
        touched = [r for r in regions if (r[0] < hi and lo < r[1]) or (lo == hi and r[0] <= lo <= r[1])]
        if not touched:
            continue
        x, y = _moved(lo, regions, end=False), _moved(hi, regions, end=True)
        while x < y and after[x].isspace():
            x += 1
        while y > x and after[y - 1].isspace():
            y -= 1
        if x < y:
            anchor = Selector(after[x:y], after[max(0, x - CONTEXT) : x], after[y : y + CONTEXT])
        else:
            anchor = Selector("", after[max(0, x - CONTEXT) : x], after[x : x + CONTEXT])
        o0, o1 = touched[0][0], touched[0][1]
        named = next((c.id for c in changes if c.old and c.old in before[o0:o1]), changes[0].id)
        event: dict[str, Any] = {
            "event": "edited",
            "id": a.id,
            "when": stamp(),
            "author": aid,
            "kind": akind,
            "anchor": anchor.to_dict(),
            "earlier": {"quote": a.selector.exact, "change": named},
        }
        append(result.quilt.root, event)
        out.append(a.id)
    return out


def carry_all(result: ScanResult, before: dict[str, str], changes: list[Pending], writer: tuple[str, str]) -> list[str]:
    """`carry` on every key a kept change touched: `before` its own text as kept before the keep, by key, read again as kept now."""
    from loom.pending import kept_own
    from loom.records.edits import node_of
    from loom.records.store import Records

    out: list[str] = []
    resolved = Records(result.quilt.root, result.quilt.history_dir).resolved(result)
    for key, text in before.items():
        node = node_of(result, key)
        if node is None:
            continue
        kept = kept_own(result, node)
        now = kept.text if kept else Records.own_pieces(result, node)[0]
        mine = [c for c in changes if c.key == key or key in c.blocks]
        out += carry(result, key, text, now, mine, writer, resolved)
    return out
