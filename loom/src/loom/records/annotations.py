"""What an annotation is, and the record one belongs to.

Annotations are stored as events in `.loom/annotations/log.jsonl` (`records/log.py`) and replayed into these shapes; a Record is one author's annotations as they now stand, not a file. Only `loom annotate` writes them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.anchors import Anchor
from loom.records.ids import draw
from loom.records.selectors import Selector


@dataclass
class Annotation:
    id: str
    author_kind: str  # agent | person: who wrote it, which is not where it belongs (plan 0.13 §5)
    author_id: str
    created: str
    target_key: str  # a key, a cited work's identifier (on one of its pages or the whole work), or a project PDF's path
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
    #: The document this is read in, for a claim about a node that holds only there (plan 0.15, decision 9); None means the node wherever it appears.
    in_doc: str | None = None
    #: Why it was resolved, from the resolving event's body; replayed.
    resolved_why: str | None = None
    #: On a PDF page without a page anchor (`records/marks.py`): the page, its place and strokes in points from the page's top left, the drawing tool, the PDF's hash and where an import came from.
    page: int | None = None
    rects: list[list[float]] | None = None
    strokes: list[list[float]] | None = None
    mark: str | None = None
    artifact: str | None = None
    origin: dict[str, Any] | None = None
    #: A mark drawn on a PDF page, not on words: its top left less its pin word's, by which it is found again on a changed file (`marks.context_at`).
    gap: list[float] | None = None

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
            "resolved_why": self.resolved_why,
            **{
                k: getattr(self, k)
                for k in ("page", "rects", "strokes", "mark", "artifact", "origin", "gap")
                if getattr(self, k) is not None
            },
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
            resolved_why=d.get("resolved_why"),
            page=d.get("page") if isinstance(d.get("page"), int) else None,
            rects=d.get("rects") if isinstance(d.get("rects"), list) else None,
            strokes=d.get("strokes") if isinstance(d.get("strokes"), list) else None,
            mark=d.get("mark") or None,
            artifact=d.get("artifact") or None,
            origin=d.get("origin") if isinstance(d.get("origin"), dict) else None,
            gap=d.get("gap") if isinstance(d.get("gap"), list) else None,
        )


@dataclass
class Record:
    """One author's annotations, replayed from the log; `rel` is the author's name."""

    path: Path  # the log the record was replayed from
    rel: str  # the grouping key: the author's name
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
