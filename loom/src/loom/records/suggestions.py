"""Where a suggestion's payload goes, and the text it leaves (plan 0.20.7): the one reading of `placement` the patch, the compile, the viewer's preview and resolving as applied all share.

`replace` covers exactly the quoted words; `after` and `before` go right after and right before them. A suggestion with no quote is about the whole key, and its anchor is the key's body: its own text inside `\\begin{…}`, its label and any leading `\\uses{…}`, and before `\\end{…}`. An empty payload with `replace` deletes the quote. `apply` writes it into the file on the author's act, keeping a version of each document it changes first; nothing else writes the author's source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from loom.history.acts import Kept
from loom.records.annotations import PLACEMENTS, Annotation
from loom.records.selectors import find_quote
from loom.records.store import Records
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult


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
    if ann.payload is None or ann.placement not in PLACEMENTS:
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


class ApplyRefused(Exception):
    """A suggestion that cannot be written in, and why in the person's words; `code` is the write API's."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def apply(result: ScanResult, ann: Annotation, actor: str | None) -> tuple[list[str], Kept]:
    """Write suggestion `ann` into its key's file: a version of each of the person's documents made of the file kept first (P7), then the file, then an `apply` act in the ledger.

    The author's act: the caller refuses an agent, and resolves the suggestion as applied against a scan of the file as written. Raises ApplyRefused for an annotation that is no open suggestion carrying text, one whose key already reads as it taken, one its quote no longer places, and one on a key none of the person's documents reads (an agent's copy, whose changes come in with the copy). Returns the person's documents the file is part of, and the versions kept.
    """
    from loom.history.acts import APPLY, documents_reaching, keep_versions, write_file
    from loom.history.ledger import append_entry

    if ann.payload is None or ann.in_reply_to:
        raise ApplyRefused("not-a-suggestion", f"{ann.id} carries no text, so there is nothing of it to put in")
    if ann.status != "open":
        raise ApplyRefused("not-open", f"It is {'withdrawn' if ann.status == 'discarded' else 'resolved'} already")
    node = _node(result, ann.target_key)
    if node is not None and not any(result.document_role(d) == "person" for d in node.reached_by):
        copy = next((d for d in node.reached_by if result.document_role(d) == "agent"), None)
        raise ApplyRefused(
            "on-a-copy",
            f"It is on the agent's copy “{copy.rsplit('/', 1)[-1]}”; it comes in with the copy"
            if copy
            else "It is on a block none of your documents reads",
        )
    if is_taken(result, ann):
        raise ApplyRefused("taken", "Its block reads as it taken already: resolve it as applied")
    try:
        placed = place(result, ann)
    except Unplaced as exc:
        raise ApplyRefused("unplaced", str(exc)) from exc
    root = result.quilt.root
    kept = keep_versions(result, [placed.file], APPLY, "Before applying a suggestion", actor)
    write_file(root / placed.file, taken_file(result, placed))
    append_entry(result.quilt.history_dir, APPLY, {"annotation": ann.id, "key": placed.key, "path": placed.file}, actor)
    return documents_reaching(result, [placed.file]), kept
