"""Suggested edits (plan 0.30, decision 10): old words replaced with new on a key, kept or discarded by the person, in their own log.

An edit names its key, the words it replaces as a selector (`anchor`; None means the key's body), the new text (`with`; empty deletes the quoted words), where the new text goes (`placement`: `replace` takes exactly the quoted words' place, `after` and `before` go right beside them), an optional `comment`, and the annotation it `answers`. It records the key's hash when it was written (`against`).

`.loom/edits/log.jsonl` holds its events, appended under the log's lock: `created`; `kept`, with the key's hash once the edit is in; `discarded`, with an optional `why`; and `reopened`, the viewer's undo of either. Replay gives each edit's status; whether its key already reads as it taken is computed, never stored. Keeping an edit that answers an open annotation resolves that annotation, with the edit as its reason. `apply` writes an edit into its file on the author's act, keeping a version of each document it changes first; nothing else writes the author's source.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.history.acts import Kept
from loom.locks import locked
from loom.paths import EDIT_LOG
from loom.records.ids import EDIT, draw
from loom.records.selectors import Selector, find_quote
from loom.records.store import Records
from loom.scan.nodes import NodeRec
from loom.scan.scan import ScanResult

PLACEMENTS = ("replace", "after", "before")
STATUSES = ("open", "kept", "discarded")
EVENTS = ("created", "kept", "discarded", "reopened")
#: An edit's id: what a link, a command and the viewer name it by.
ID = re.compile(rf"^{EDIT}$")


@dataclass
class Edit:
    """One suggested edit as its events replay."""

    id: str
    author_kind: str  # agent | person
    author_id: str
    created: str
    target_key: str
    target_hash: str  # the key's hash when it was written
    selector: Selector | None  # the words it replaces or stands beside; None: the key's body
    with_text: str  # the new text; empty deletes the quoted words
    placement: str
    comment: str = ""
    answers: str | None = None  # the annotation it answers
    status: str = "open"
    why: str | None = None  # why it was discarded
    kept: dict[str, Any] | None = None  # `{hash}`: its key's text once it was kept
    acts: list[dict[str, Any]] = field(default_factory=list)  # every kept, discarded and reopened event, in order

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "author": {"kind": self.author_kind, "id": self.author_id},
            "created": self.created,
            "target": {"key": self.target_key, "hash": self.target_hash},
            "quote": self.selector.exact if self.selector else None,
            "with": self.with_text,
            "placement": self.placement,
            "comment": self.comment or None,
            "answers": self.answers,
            "status": self.status,
            "why": self.why,
        }


def log_path(root: Path) -> Path:
    return root / EDIT_LOG


def append(root: Path, event: dict[str, Any]) -> None:
    """Append one event under the log's lock."""
    p = log_path(root)
    with locked(p):
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def append_new(root: Path, event: dict[str, Any], date: str) -> str:
    """Append a new edit's `created` event under an id drawn for `date`; the read and the write share the log's lock, so no two writers draw one id."""
    p = log_path(root)
    with locked(p):
        ids = {e.id for e in replay(root)[0]}
        edit_id = draw(f"e-{date}-", ids)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**event, "id": edit_id}, ensure_ascii=False, sort_keys=True) + "\n")
    return edit_id


def replay(root: Path) -> tuple[list[Edit], list[str]]:
    """Every edit as it now stands, in the order written, and one problem per line that cannot be read; a bad line is skipped."""
    p = log_path(root)
    rel = EDIT_LOG
    out: dict[str, Edit] = {}
    problems: list[str] = []
    if not p.is_file():
        return [], problems
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"{rel}:{n}: {exc}")
            continue
        if not isinstance(e, dict) or e.get("event") not in EVENTS:
            problems.append(f"{rel}:{n}: not an edit's event")
            continue
        eid = str(e.get("id") or "")
        if not ID.match(eid):
            problems.append(f"{rel}:{n}: {eid!r} is not an edit's id")
            continue
        if e["event"] == "created":
            anchor = e.get("anchor")
            placement = str(e.get("placement") or "replace")
            if not e.get("target") or placement not in PLACEMENTS or not isinstance(e.get("with"), str):
                problems.append(f"{rel}:{n}: {eid} names no key, no placement or no text")
                continue
            out[eid] = Edit(
                id=eid,
                author_kind="agent" if e.get("kind") == "agent" else "person",
                author_id=str(e.get("author", "")),
                created=str(e.get("when", "")),
                target_key=str(e["target"]),
                target_hash=str(e.get("against") or ""),
                selector=Selector.from_dict(anchor) if isinstance(anchor, dict) else None,
                with_text=e["with"],
                placement=placement,
                comment=str(e.get("comment") or ""),
                answers=str(e["answers"]) if e.get("answers") else None,
            )
            continue
        edit = out.get(eid)
        if edit is None:
            problems.append(f"{rel}:{n}: {e['event']} names unknown edit {eid}")
            continue
        edit.acts.append(e)
        if e["event"] == "kept":
            edit.status, edit.why = "kept", None
            edit.kept = {"hash": e["hash"]} if e.get("hash") else None
        elif e["event"] == "discarded":
            edit.status, edit.why = "discarded", str(e.get("why") or "") or None
        else:
            edit.status, edit.why, edit.kept = "open", None, None
    return list(out.values()), problems


def find(root: Path, edit_id: str) -> Edit | None:
    return next((e for e in replay(root)[0] if e.id == edit_id), None)


# ---- where an edit's text goes ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Placed:
    """An edit's text placed in its key's text as it stands now."""

    key: str
    """The node the text goes in: the edit's target, or the result holding an equation it is on."""
    file: str
    """The file holding the node, relative to the quilt root."""
    own: str
    """The node's own text now, children cut out."""
    span: tuple[int, int]
    """Where the text goes in `own`: the quote it replaces, or the point beside it it is inserted at."""
    at: tuple[int, int]
    """The same place in `file`."""
    text: str
    """What goes there: the new text, with the space or line break that joins it to the text around it."""
    moved: bool
    """The node's text has changed since the edit was written, though its quote still stands."""

    @property
    def taken(self) -> str:
        """The node's own text with the edit in place."""
        a, b = self.span
        return self.own[:a] + self.text + self.own[b:]


class Unplaced(ValueError):
    """Why an edit cannot be placed: said to the author as written."""


def node_of(result: ScanResult, key: str) -> NodeRec | None:
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


def _joined(own: str, point: int, text: str, before: bool) -> str:
    """The text with a space to join it to the word it lands against, when neither side carries whitespace."""
    left = own[point - 1 : point] if point > 0 else " "
    right = own[point : point + 1] if point < len(own) else " "
    if before:
        return text + ("" if text[-1:].isspace() or right.isspace() or not right else " ")
    return ("" if text[:1].isspace() or left.isspace() or not left else " ") + text


def place(result: ScanResult, edit: Edit) -> Placed:
    """Where `edit`'s text goes in its key's text now.

    Parameters
    ----------
    result : ScanResult
        A scan of the quilt now.
    edit : Edit
        The suggested edit.

    Returns
    -------
    Placed

    Raises
    ------
    Unplaced
        When its key is gone, or its quote no longer stands in the text exactly once.
    """
    from loom.render.manifest import key_hash

    node = node_of(result, edit.target_key)
    if node is None or node.file not in result.files:
        raise Unplaced(f"{edit.target_key}, which {edit.id} is on, is no longer in the quilt")
    own, pieces = Records.own_pieces(result, node)
    new = edit.with_text
    if edit.selector is None:
        a, b = body_span(own)
        if edit.placement == "after":
            span, text = (b, b), ("\n" if a < b else "") + new
        elif edit.placement == "before":
            span, text = (a, a), new + ("\n" if a < b else "")
        else:
            span, text = (a, b), new
    else:
        found = find_quote(own, edit.selector.exact)
        if not found:
            raise Unplaced(f"the text {edit.id} quotes no longer stands in {node.key}")
        if len(found) > 1:
            raise Unplaced(
                f"the text {edit.id} quotes now stands {len(found)} times in {node.key}, so where it goes is not known"
            )
        a, b = found[0]
        if edit.placement == "after":
            span, text = (b, b), _joined(own, b, new, before=False) if new else ""
        elif edit.placement == "before":
            span, text = (a, a), _joined(own, a, new, before=True) if new else ""
        else:
            span, text = (a, b), new
    at = Records.to_file_span(pieces, span) if span[0] < span[1] else _point(pieces, span[0])
    if at is None:
        raise Unplaced(f"the place {edit.id} names in {node.key} is not in one piece of its file")
    return Placed(node.key, node.file, own, span, at, text, edit.target_hash != key_hash(result, node.key))


def compose(result: ScanResult, edits: list[Edit]) -> list[tuple[Edit, Placed | Unplaced]]:
    """Several edits placed together, in the order they were written: each placed in its key's text now (`place`), and one whose place meets an earlier one's in the same file Unplaced, since the earlier stands there first.

    Parameters
    ----------
    result : ScanResult
        A scan of the quilt now.
    edits : list of Edit
        The suggested edits.

    Returns
    -------
    list of (Edit, Placed or Unplaced)
        In the order written. Two places meet when they overlap, or one is a point inside or at the edge of the other.
    """
    out: list[tuple[Edit, Placed | Unplaced]] = []
    held: dict[str, list[tuple[int, int, str]]] = {}
    for edit in sorted(edits, key=lambda e: e.created):
        try:
            placed = place(result, edit)
        except Unplaced as exc:
            out.append((edit, exc))
            continue
        a, b = placed.at
        clash = next(
            (
                other
                for x, y, other in held.get(placed.file, [])
                if (a < y and x < b) or (a == b and x <= a <= y) or (x == y and a <= x <= b)
            ),
            None,
        )
        if clash is not None:
            out.append(
                (edit, Unplaced(f"{clash}, suggested before it, is on the same words; keep or discard that first"))
            )
            continue
        held.setdefault(placed.file, []).append((a, b, edit.id))
        out.append((edit, placed))
    return out


def _point(pieces: list[tuple[int, int, int]], at: int) -> tuple[int, int] | None:
    """A point of the own text in the file: inside a piece, or at the end of the one it closes."""
    for cstart, fstart, length in pieces:
        if cstart <= at <= cstart + length:
            return fstart + (at - cstart), fstart + (at - cstart)
    return None


def taken_file(result: ScanResult, placed: Placed) -> str:
    """The text of the node's file with the edit in place."""
    text = result.files[placed.file].text
    a, b = placed.at
    return text[:a] + placed.text + text[b:]


def patch(result: ScanResult, placed: Placed) -> str:
    """The edit in place, as a unified diff of the node's file against the quilt root."""
    from loom.reshape.ids import unified_diff

    return unified_diff(result.files[placed.file].text, taken_file(result, placed), placed.file)


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_taken(result: ScanResult, edit: Edit) -> bool:
    """Whether the key's text now reads as the edit taken.

    A replacement is taken when its text stands in the key and its quote no longer does but inside it; an insertion when its text stands; a deletion when its quote is gone. Whitespace is compared normalised, as a quote is.
    """
    node = node_of(result, edit.target_key)
    if node is None or node.file not in result.files:
        return False
    own = _flat(Records.own_pieces(result, node)[0])
    new = _flat(edit.with_text)
    quote = _flat(edit.selector.exact) if edit.selector else ""
    if not new:
        return bool(quote) and quote not in own
    if new not in own:
        return False
    if edit.placement != "replace" or not quote:
        return True
    return quote not in own.replace(new, "\0")


# ---- what the person does with one ----------------------------------------------------------------------------------


class EditRefused(Exception):
    """An edit that cannot be written, kept or discarded, and why in the person's words; `code` is the write API's."""

    def __init__(self, code: str, message: str, status: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def apply(result: ScanResult, edit: Edit, actor: str | None) -> tuple[list[str], Kept]:
    """Write `edit` into its key's file: a version of each of the person's documents made of the file kept first (P7), then the file, then an `apply` act in the ledger.

    The author's act: the caller refuses an agent, and records the edit kept against a scan of the file as written (`keep`). Raises EditRefused for an edit that is not open, one whose key already reads as it taken, one its quote no longer places, and one on a key none of the person's documents reads (an agent's copy, whose changes come in with the copy). Returns the person's documents the file is part of, and the versions kept.
    """
    from loom.history.acts import APPLY, documents_reaching, keep_versions, write_file
    from loom.history.ledger import append_entry

    if edit.status != "open":
        raise EditRefused("not-open", f"It is {edit.status} already")
    node = node_of(result, edit.target_key)
    if node is not None and not any(result.document_role(d) == "person" for d in node.reached_by):
        copy = next((d for d in node.reached_by if result.document_role(d) == "agent"), None)
        raise EditRefused(
            "on-a-copy",
            f"It is on the agent's copy “{copy.rsplit('/', 1)[-1]}”; it comes in with the copy"
            if copy
            else "It is on a block none of your documents reads",
        )
    if is_taken(result, edit):
        raise EditRefused("taken", "Its block reads as it taken already: keep it without applying it")
    try:
        placed = place(result, edit)
    except Unplaced as exc:
        raise EditRefused("unplaced", str(exc)) from exc
    root = result.quilt.root
    kept = keep_versions(result, [placed.file], APPLY, "Before applying a suggested edit", actor)
    write_file(root / placed.file, taken_file(result, placed))
    append_entry(result.quilt.history_dir, APPLY, {"edit": edit.id, "key": placed.key, "path": placed.file}, actor)
    return documents_reaching(result, [placed.file]), kept


def keep(result: ScanResult, edit: Edit, writer: tuple[str, str]) -> str:
    """Record `edit` kept, with its key's hash as the text now reads (taken already, or just written by `apply`), and resolve the open annotation it answers, with the edit as the reason. Returns what to say."""
    from loom.clock import stamp
    from loom.records.annotations import find_annotation, load_records
    from loom.records.log import append as append_annotation
    from loom.records.types import load_types
    from loom.render.manifest import key_hash

    if edit.status != "open":
        raise EditRefused("not-open", f"{edit.id} is {edit.status} already")
    if not is_taken(result, edit):
        raise EditRefused(
            "not-taken",
            f"{edit.target_key} does not yet read as {edit.id} taken; `loom changes {edit.id}` prints the patch that takes it",
        )
    akind, aid = writer
    node = node_of(result, edit.target_key)
    when = stamp()
    append(
        result.quilt.root,
        {
            "event": "kept",
            "id": edit.id,
            "when": when,
            "author": aid,
            "kind": akind,
            "hash": key_hash(result, node.key) if node else "",
        },
    )
    said = f"kept {edit.id}"
    found = find_annotation(load_records(result.quilt.root)[0], edit.answers) if edit.answers else None
    if found is not None:
        ann = found[1]
        t = load_types(result.quilt.root).get(ann.type)
        if ann.status == "open" and t is not None and t.open:
            append_annotation(
                result.quilt.root,
                {
                    "event": "resolved",
                    "id": ann.id,
                    "when": when,
                    "author": aid,
                    "kind": akind,
                    "body": f"kept suggested edit {edit.id}",
                },
            )
            said += f"; resolved {ann.id}, which it answers"
    return said


def discard(root: Path, edit: Edit, writer: tuple[str, str], why: str | None = None, *, undo: bool = False) -> str:
    """Discard `edit`, with why; with `undo`, open a kept or discarded edit again. A person may discard any edit, an agent only its own. Returns what to say."""
    from loom.clock import stamp

    akind, aid = writer
    if akind == "agent" and not (edit.author_kind == "agent" and edit.author_id == aid):
        raise EditRefused(
            "not-yours", f"{edit.id} is {edit.author_id}'s, and an agent discards only its own edits", 403
        )
    if undo:
        if edit.status == "open":
            raise EditRefused("not-settled", f"{edit.id} is open; there is nothing to undo")
        append(root, {"event": "reopened", "id": edit.id, "when": stamp(), "author": aid, "kind": akind})
        return f"reopened {edit.id}"
    if edit.status != "open":
        raise EditRefused("not-open", f"{edit.id} is {edit.status} already")
    event: dict[str, Any] = {"event": "discarded", "id": edit.id, "when": stamp(), "author": aid, "kind": akind}
    if why:
        event["why"] = why
    append(root, event)
    return f"discarded {edit.id}"
