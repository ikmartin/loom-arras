"""What an annotation is, and the record one belongs to.

Annotations are stored as events in `.loom/annotations/log.jsonl` (`records/log.py`) and replayed into these shapes; a Record is one run's or one author's annotations as they now stand, not a file. Only `loom annotate` writes them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.anchors import Anchor
from loom.records.ids import draw
from loom.records.selectors import Selector

PLACEMENTS = ("replace", "after", "before")


@dataclass
class Annotation:
    id: str
    author_kind: str  # agent | person: who wrote it, which is not where it belongs (plan 0.13 §5)
    author_id: str
    created: str
    target_key: str  # a key in the quilt, or -- for a note on a page of a cited work -- the work's identifier
    target_hash: str
    selector: Selector | None  # the text triple: what was quoted, and the words either side
    type: str | None  # the id of its type in the quilt's types, or None: a type is only a label
    body: str
    status: str = "open"
    #: The look fields set on this annotation itself, drawn over its type's; empty: it looks as its type does.
    own_look: dict[str, Any] = field(default_factory=dict)
    #: Its whole look when it was written or last restyled: how it is drawn once its type is gone.
    drawn: dict[str, Any] = field(default_factory=dict)
    anchor: Anchor | None = None  # the page anchor of a note on a cited work's page; None on a key (plan 0.13 item 2)
    in_reply_to: str | None = None
    payload: str | None = (
        None  # suggested text; loom shows it in place and prints it as a patch, and the author applies it
    )
    placement: str | None = (
        None  # replace (exactly the quote) | after | before (beside it); with no quote, of the key's body (records/suggestions.py)
    )
    discard_reason: str | None = (
        None  # why it was withdrawn, from the discarding event's body; never typed, always replayed
    )
    #: The document this is read in, for a claim about a node that holds only there (plan 0.15, decision 9); None means the node wherever it appears.
    in_doc: str | None = None
    #: Why it was resolved, from the resolving event's body; replayed, like `discard_reason`.
    resolved_why: str | None = None
    #: A suggestion resolved as applied: `{hash}`, its key's text once the suggestion was taken.
    applied: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "author": {"kind": self.author_kind, "id": self.author_id},
            "created": self.created,
            "target": {"key": self.target_key, "hash": self.target_hash},
            "in": self.in_doc,
            "selector": self.selector.to_dict() if self.selector else None,
            "anchor": self.anchor.to_dict() if self.anchor else None,
            "type": self.type,
            "own_look": self.own_look,
            "drawn": self.drawn,
            "body": self.body,
            "status": self.status,
            "in_reply_to": self.in_reply_to,
            "payload": self.payload,
            "placement": self.placement,
            "discard_reason": self.discard_reason,
            "resolved_why": self.resolved_why,
            "applied": self.applied,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Annotation:
        sel = d.get("selector")
        anc = d.get("anchor")
        return cls(
            id=str(d["id"]),
            author_kind=str(d.get("author", {}).get("kind", "person")),
            author_id=str(d.get("author", {}).get("id", "")),
            created=str(d.get("created", "")),
            target_key=str(d.get("target", {}).get("key", "")),
            target_hash=str(d.get("target", {}).get("hash", "")),
            in_doc=d.get("in") or None,
            selector=Selector.from_dict(sel) if isinstance(sel, dict) else None,
            anchor=Anchor.from_dict(anc) if isinstance(anc, dict) else None,
            type=d.get("type") or None,
            own_look=dict(d.get("own_look") or {}),
            drawn=dict(d.get("drawn") or {}),
            body=str(d.get("body", "")),
            status=str(d.get("status", "open")),
            in_reply_to=d.get("in_reply_to"),
            payload=d.get("payload"),
            placement=d.get("placement"),
            discard_reason=d.get("discard_reason"),
            resolved_why=d.get("resolved_why"),
            applied=d.get("applied") if isinstance(d.get("applied"), dict) else None,
        )


@dataclass
class Record:
    """One session's annotations, replayed from the log; `rel` is the session id."""

    path: Path  # the log the record was replayed from
    rel: str  # the grouping key: the session id
    discarded: bool = False
    #: Why the whole session's annotations were withdrawn, from the discarding event's body; replayed, never typed.
    discard_reason: str | None = None
    annotations: list[Annotation] = field(default_factory=list)


def load_records(root: Path) -> tuple[list[Record], list[str]]:
    """Every record in the quilt, replayed from `.loom/annotations/log.jsonl`, plus one problem per unreadable line."""
    from loom.records.log import replay

    return replay(root)


def next_id(records: list[Record], date: str) -> str:
    """A fresh `a-<date>-<token>`, none of the ids in `records`. What is written draws it under the log's lock (`log.append_new`); with no lock it is only an example."""
    return draw(f"a-{date}-", {a.id for record in records for a in record.annotations})


def find_annotation(records: list[Record], ann_id: str) -> tuple[Record, Annotation] | None:
    for r in records:
        for a in r.annotations:
            if a.id == ann_id:
                return r, a
    return None
