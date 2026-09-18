"""`annotations/log.jsonl`: every review event, appended, never rewritten (book 7.4).

One line per event, current state by replay. It replaced a tree of `annotations.json` files, one per run and one per author per day, each rewritten whole whenever anything in it changed — which is why an annotation could only ever be *replied* to. An agent re-checking a finding that still stands now `edited`s it: the history stays in the log, one current body is shown, and a finding stops accumulating restatements of itself.

Two people appending in parallel merge as two lines, which is why this is JSONL and not a database. A malformed line is reported as `loom:foreign-annotations` and skipped; it never stops the rest from loading.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loom.records.annotations import Annotation, Record
from loom.records.selectors import Selector

LOG = "annotations/log.jsonl"
EVENTS = ("created", "replied", "edited", "resolved", "discarded")


def log_path(root: Path) -> Path:
    return root / LOG


def append(root: Path, event: dict[str, Any]) -> None:
    """Append one event. The file is opened for append so two writers interleave lines rather than losing one."""
    p = log_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def source_of(event: dict[str, Any]) -> str:
    """Which record an event belongs to: its run, or the author and the day they wrote it.

    This is the manifest's grouping key, and the reason a run is a first-class column rather than something encoded into the author's name. A person's annotations group by day because "what the author said on the 16th" is a session a reader looks for, where everything one person has ever written is not.
    """
    run = event.get("run")
    if run:
        return str(run)
    from loom.records.annotations import author_slug

    day = str(event.get("when", ""))[:10]
    return f"comments/{author_slug(str(event.get('author', '')))}/{day}"


def _annotation(event: dict[str, Any]) -> Annotation:
    anchor = event.get("anchor")
    return Annotation(
        id=str(event["id"]),
        author_kind="run" if event.get("run") else "person",
        author_id=str(event.get("author", "")),
        created=str(event.get("when", "")),
        target_key=str(event.get("target", "")),
        target_hash=str(event.get("against", "")),
        selector=Selector.from_dict(anchor) if isinstance(anchor, dict) else None,
        kind=str(event.get("annotation_kind", "objection")),
        body=str(event.get("body", "")),
        status="open",
        in_reply_to=event.get("reply_to"),
        severity=event.get("severity"),
        payload=event.get("payload"),
        placement=event.get("placement"),
    )


def replay(root: Path) -> tuple[list[Record], list[str]]:
    """Every annotation as it now stands, grouped into one Record per run and per author, plus one problem per bad line."""
    p = log_path(root)
    problems: list[str] = []
    order: list[str] = []
    by_source: dict[str, list[Annotation]] = {}
    index: dict[str, tuple[str, Annotation]] = {}
    discarded_sources: set[str] = set()
    if not p.is_file():
        return [], problems
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"{LOG}:{n}: {exc}")
            continue
        if not isinstance(event, dict) or event.get("event") not in EVENTS:
            problems.append(f"{LOG}:{n}: not a review event")
            continue
        kind = event["event"]
        if kind in ("created", "replied"):
            if "id" not in event:
                problems.append(f"{LOG}:{n}: {kind} without an id")
                continue
            src = source_of(event)
            ann = _annotation(event)
            if src not in by_source:
                by_source[src] = []
                order.append(src)
            by_source[src].append(ann)
            index[ann.id] = (src, ann)
            continue
        # every later event names an annotation, or a whole source to discard
        target = event.get("id")
        if target is None:
            if kind == "discarded":
                # a whole-source discard names its record outright: a person's source key carries the day they wrote,
                # which cannot be recovered from the event's own timestamp
                src = str(event.get("source") or source_of(event))
                if event.get("undo"):
                    discarded_sources.discard(src)
                else:
                    discarded_sources.add(src)
                continue
            problems.append(f"{LOG}:{n}: {kind} without an id")
            continue
        found = index.get(str(target))
        if found is None:
            problems.append(f"{LOG}:{n}: {kind} names unknown annotation {target}")
            continue
        _src, ann = found
        if kind == "edited":
            for f in ("body", "severity", "payload", "placement"):
                if f in event:
                    setattr(ann, f, event[f])
        elif kind == "resolved":
            ann.status = "resolved"
        elif kind == "discarded":
            ann.status = "open" if event.get("undo") else "discarded"
    out: list[Record] = []
    for src in order:
        out.append(
            Record(
                path=p,
                rel=src,
                discarded=src in discarded_sources,
                annotations=by_source[src],
            )
        )
    return out, problems
