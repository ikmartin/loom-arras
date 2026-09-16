"""Review records: `annotations.json` files under `comments/<author>/` and `ai/runs/<run>/`, written only by `loom comment` (book 7.4).

The scanner finds them by those two paths; a file there that fails validation is `loom:foreign-annotations`. The only field ever rewritten in place is `status`, when a comment is resolved.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.records.selectors import Selector

KINDS = ("objection", "suggestion", "question", "ok")


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
        )


@dataclass
class Record:
    path: Path  # absolute
    rel: str  # quilt-relative
    discarded: bool = False
    annotations: list[Annotation] = field(default_factory=list)
    schema: int = 1

    @property
    def is_run(self) -> bool:
        return self.rel.startswith("ai/runs/")

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "schema": self.schema,
            "discarded": self.discarded,
            "annotations": [a.to_dict() for a in self.annotations],
        }
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.path)


def record_paths(root: Path) -> list[Path]:
    out = sorted(root.glob("comments/*/*.json")) + sorted(root.glob("ai/runs/*/annotations.json"))
    return [p for p in out if not p.name.endswith(".tmp")]


def load_record(root: Path, path: Path) -> Record | str:
    """A Record, or an error string when the file is not a valid record."""
    rel = path.relative_to(root).as_posix()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return f"{rel}: {exc}"
    if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("annotations"), list):
        return f"{rel}: not a schema-1 annotations file"
    rec = Record(path=path, rel=rel, discarded=bool(data.get("discarded", False)))
    try:
        rec.annotations = [Annotation.from_dict(a) for a in data["annotations"]]
    except (KeyError, TypeError, AttributeError) as exc:
        return f"{rel}: malformed annotation ({exc})"
    return rec


def load_records(root: Path) -> tuple[list[Record], list[str]]:
    records: list[Record] = []
    problems: list[str] = []
    for p in record_paths(root):
        r = load_record(root, p)
        if isinstance(r, str):
            problems.append(r)
        else:
            records.append(r)
    return records, problems


def author_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "anonymous"


def person_record_path(root: Path, author: str, date: str) -> Path:
    return root / "comments" / author_slug(author) / f"{date}.json"


def run_record_path(run_dir: Path) -> Path:
    return run_dir / "annotations.json"


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
