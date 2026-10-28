"""Where a suggestion's payload goes, and the text it leaves (plan 0.20.7): the one reading of `placement` the patch, the compile, the viewer's preview and resolving as applied all share.

`replace` covers exactly the quoted words; `after` and `before` go right after and right before them. A suggestion with no quote is about the whole key, and its anchor is the key's body: its own text inside `\\begin{…}`, its label and any leading `\\uses{…}`, and before `\\end{…}`. An empty payload with `replace` deletes the quote. Loom never writes the result into the author's source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from loom.records.annotations import PLACEMENTS, Annotation
from loom.records.selectors import find_quote
from loom.records.store import Records
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult

#: An annotation kind whose payload is a change to the text; a citation's payload is the work it proposes.
SUGGESTION = "suggestion"


@dataclass(frozen=True)
class Placed:
    """A payload placed in its key's text as it stands now."""

    key: str
    """The node the payload goes in: the annotation's target, or the result holding an equation it is on."""
    file: str
    """The file holding the node, relative to the quilt root."""
    own: str
    """The node's own text now, children cut out."""
    span: tuple[int, int]
    """Where the payload goes in `own`: the quote it replaces, or the point beside it it is inserted at."""
    at: tuple[int, int]
    """The same place in `file`."""
    text: str
    """What goes there: the payload, with the space or line break that joins it to the text around it."""
    moved: bool
    """The node's text has changed since the annotation was written, though its quote still stands."""

    @property
    def taken(self) -> str:
        """The node's own text with the payload in place."""
        a, b = self.span
        return self.own[:a] + self.text + self.own[b:]


class Unplaced(ValueError):
    """Why a payload cannot be placed: said to the author as written."""


def _node(result: ScanResult, key: str) -> NodeRec | None:
    region = result.assembly.regions.get(key)
    node: NodeRec | None = result.nodes.get(region.container if region else key)
    return node


def _balanced(text: str, at: int, opening: str, closing: str) -> int:
    """The index after the group `opening`…`closing` that opens at `at`, braces inside it kept whole; `at` itself when none opens there."""
    if at >= len(text) or text[at] != opening:
        return at
    depth = braces = 0
    i = at
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if opening != "{" and ch in "{}":
            braces += 1 if ch == "{" else -1
        elif braces == 0 and ch == opening:
            depth += 1
        elif braces == 0 and ch == closing:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return at


def body_span(own: str) -> tuple[int, int]:
    """The key's body in its own text: after `\\begin{…}`, its optional title, `\\label{…}` and leading `\\uses{…}`, and before `\\end{…}`.

    A text that is no environment is all body.
    """
    m = re.match(r"\s*\\begin\{[^}]*\}", own)
    end = own.rfind("\\end{")
    if not m or end < m.end():
        return 0, len(own)
    at = _balanced(own, m.end(), "[", "]")
    while True:
        head = re.match(r"\s*\\(label|uses)\{", own[at:])
        if not head:
            break
        at = _balanced(own, at + head.end() - 1, "{", "}")
    # the body begins on the line after its head, and ends before the whitespace that precedes `\end`
    start = at + 1 if own[at : at + 1] == "\n" else at
    stop = end
    while stop > start and own[stop - 1] in " \t\n":
        stop -= 1
    return start, stop


def _joined(own: str, point: int, payload: str, before: bool) -> str:
    """The payload with a space to join it to the word it lands against, when neither side carries whitespace."""
    left = own[point - 1 : point] if point > 0 else " "
    right = own[point : point + 1] if point < len(own) else " "
    if before:
        return payload + ("" if payload[-1:].isspace() or right.isspace() or not right else " ")
    return ("" if payload[:1].isspace() or left.isspace() or not left else " ") + payload


def place(result: ScanResult, ann: Annotation) -> Placed:
    """Where `ann`'s payload goes in its key's text now.

    Parameters
    ----------
    result : ScanResult
        A scan of the quilt now.
    ann : Annotation
        A suggestion carrying a payload and a placement.

    Returns
    -------
    Placed

    Raises
    ------
    Unplaced
        When it is no suggestion, carries no payload or no placement, its key is gone, or its quote no longer stands in the text exactly once.
    """
    from loom.render.manifest import key_hash

    if ann.kind != SUGGESTION:
        raise Unplaced(
            f"{ann.id} is a {ann.kind}, not a suggestion; only a suggestion's payload is a change to the text"
        )
    if ann.payload is None:
        raise Unplaced(f"{ann.id} carries no payload")
    if ann.placement not in PLACEMENTS:
        raise Unplaced(f"{ann.id} says nowhere for its payload to go: it has no placement")
    node = _node(result, ann.target_key)
    if node is None or node.file not in result.files:
        raise Unplaced(f"{ann.target_key}, which {ann.id} is on, is no longer in the quilt")
    own, pieces = Records.own_pieces(result, node)
    payload = ann.payload
    if ann.selector is None:
        a, b = body_span(own)
        if ann.placement == "after":
            span, text = (b, b), ("\n" if a < b else "") + payload
        elif ann.placement == "before":
            span, text = (a, a), payload + ("\n" if a < b else "")
        else:
            span, text = (a, b), payload
    else:
        found = find_quote(own, ann.selector.exact)
        if not found:
            raise Unplaced(f"the text {ann.id} quotes no longer stands in {node.key}")
        if len(found) > 1:
            raise Unplaced(
                f"the text {ann.id} quotes now stands {len(found)} times in {node.key}, so where it goes is not known"
            )
        a, b = found[0]
        if ann.placement == "after":
            span, text = (b, b), _joined(own, b, payload, before=False) if payload else ""
        elif ann.placement == "before":
            span, text = (a, a), _joined(own, a, payload, before=True) if payload else ""
        else:
            span, text = (a, b), payload
    at = Records.to_file_span(pieces, span) if span[0] < span[1] else _point(pieces, span[0])
    if at is None:
        raise Unplaced(f"the place {ann.id} names in {node.key} is not in one piece of its file")
    return Placed(node.key, node.file, own, span, at, text, ann.target_hash != key_hash(result, node.key))


def _point(pieces: list[tuple[int, int, int]], at: int) -> tuple[int, int] | None:
    """A point of the own text in the file: inside a piece, or at the end of the one it closes."""
    for cstart, fstart, length in pieces:
        if cstart <= at <= cstart + length:
            return fstart + (at - cstart), fstart + (at - cstart)
    return None


def taken_file(result: ScanResult, placed: Placed) -> str:
    """The text of the node's file with the payload in place."""
    text = result.files[placed.file].text
    a, b = placed.at
    return text[:a] + placed.text + text[b:]


def patch(result: ScanResult, placed: Placed) -> str:
    """The payload in place, as a unified diff of the node's file against the quilt root."""
    from loom.reshape.ids import unified_diff

    return unified_diff(result.files[placed.file].text, taken_file(result, placed), placed.file)


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_taken(result: ScanResult, ann: Annotation) -> bool:
    """Whether the key's text now reads as the suggestion taken.

    A replacement is taken when its payload stands in the text and its quote no longer does but inside it; an insertion when its payload stands; a deletion when its quote is gone. Whitespace is compared normalised, as a quote is.
    """
    if ann.kind != SUGGESTION or ann.payload is None or ann.placement not in PLACEMENTS:
        return False
    node = _node(result, ann.target_key)
    if node is None or node.file not in result.files:
        return False
    own = _flat(Records.own_pieces(result, node)[0])
    payload = _flat(ann.payload)
    quote = _flat(ann.selector.exact) if ann.selector else ""
    if not payload:
        return bool(quote) and quote not in own
    if payload not in own:
        return False
    if ann.placement != "replace" or not quote:
        return True
    return quote not in own.replace(payload, "\0")
