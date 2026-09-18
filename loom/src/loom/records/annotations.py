"""What an annotation is, and the record one belongs to (book 7.4).

Annotations are stored as events in `annotations/log.jsonl` (`records/log.py`) and replayed into these shapes; a Record is one run's or one author's annotations as they now stand, not a file. Only `loom comment` and `loom refs note` write them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.records.selectors import Selector

KINDS = ("objection", "suggestion", "question", "ok", "citation")
SEVERITIES = ("major", "moderate", "minor")
PLACEMENTS = ("replace", "after", "before")


@dataclass
class Annotation:
    id: str
    author_kind: str  # run | person
    author_id: str
    created: str
    target_key: str
    target_hash: str
    selector: Selector | None
    kind: str
    body: str
    status: str = "open"
    in_reply_to: str | None = None
    severity: str | None = None  # major | moderate | minor: how bad the fault is, not how keen the suggestion
    payload: str | None = None  # suggested text, previewed and copied by the author; nothing applies it (WQ-27)
    placement: str | None = None  # replace | after | before, relative to the anchor: a hint for where a viewer shows it
    discard_reason: str | None = (
        None  # why it was withdrawn, from the discarding event's body; never typed, always replayed
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "author": {"kind": self.author_kind, "id": self.author_id},
            "created": self.created,
            "target": {"key": self.target_key, "hash": self.target_hash},
            "selector": self.selector.to_dict() if self.selector else None,
            "kind": self.kind,
            "body": self.body,
            "status": self.status,
            "in_reply_to": self.in_reply_to,
            "severity": self.severity,
            "payload": self.payload,
            "placement": self.placement,
            "discard_reason": self.discard_reason,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Annotation:
        sel = d.get("selector")
        return cls(
            id=str(d["id"]),
            author_kind=str(d.get("author", {}).get("kind", "person")),
            author_id=str(d.get("author", {}).get("id", "")),
            created=str(d.get("created", "")),
            target_key=str(d.get("target", {}).get("key", "")),
            target_hash=str(d.get("target", {}).get("hash", "")),
            selector=Selector.from_dict(sel) if isinstance(sel, dict) else None,
            kind=str(d.get("kind", "objection")),
            body=str(d.get("body", "")),
            status=str(d.get("status", "open")),
            in_reply_to=d.get("in_reply_to"),
            severity=d.get("severity"),
            payload=d.get("payload"),
            placement=d.get("placement"),
            discard_reason=d.get("discard_reason"),
        )


@dataclass
class Record:
    """One run's or one author's annotations, replayed from the log; `rel` is the run directory or `comments/<author>`."""

    path: Path  # the log the record was replayed from
    rel: str  # the grouping key: ai/runs/<run>, or comments/<author-slug>
    discarded: bool = False
    annotations: list[Annotation] = field(default_factory=list)

    @property
    def is_run(self) -> bool:
        return self.rel.startswith("ai/runs/")


def load_records(root: Path) -> tuple[list[Record], list[str]]:
    """Every record in the quilt, replayed from `annotations/log.jsonl`, plus one problem per unreadable line."""
    from loom.records.log import replay

    return replay(root)


def author_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "anonymous"


def next_id(records: list[Record], date: str) -> str:
    """The next `a-<date>-<nnnn>` over every record in the quilt, so ids are unique quilt-wide (book 7.4.2, amended: the counter is not per file)."""
    n = 0
    prefix = f"a-{date}-"
    for record in records:
        for a in record.annotations:
            if a.id.startswith(prefix):
                try:
                    n = max(n, int(a.id[len(prefix) :]))
                except ValueError:
                    continue
    return f"{prefix}{n + 1:04d}"


def find_annotation(records: list[Record], ann_id: str) -> tuple[Record, Annotation] | None:
    for r in records:
        for a in r.annotations:
            if a.id == ann_id:
                return r, a
    return None
