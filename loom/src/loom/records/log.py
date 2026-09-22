"""`annotations/log.jsonl`: every review event, appended, never rewritten (book 7.4).

One line per event, current state by replay. It replaced a tree of `annotations.json` files, one per run and one per author per day, each rewritten whole whenever anything in it changed — which is why an annotation could only ever be *replied* to. An agent re-checking a finding that still stands now `edited`s it: the history stays in the log, one current body is shown, and a finding stops accumulating restatements of itself.

Two people appending in parallel merge as two lines, which is why this is JSONL and not a database. A malformed line is reported as `loom:foreign-annotations` and skipped; it never stops the rest from loading.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from loom.anchors import Anchor, is_page_anchor
from loom.records.annotations import KINDS, Annotation, Record
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
    """Which record an event belongs to: its session, or -- for an event written before sessions -- its run, or the author and the day.

    This is the manifest's grouping key. Since plan 0.13 §5 it is the session, which is where work belongs and is now said outright rather than inferred from who wrote it. The two older forms are still read, because the log is append-only and what was written before sessions was written before sessions; `loom session migrate` gives each of them a session, and `sessions_by_source` is what maps one to the other.
    """
    session = event.get("session")
    if session:
        return str(session)
    run = event.get("run")
    if run:
        return str(run)
    from loom.records.annotations import author_slug

    day = str(event.get("when", ""))[:10]
    return f"comments/{author_slug(str(event.get('author', '')))}/{day}"


#: What `loom comment` writes as an id. An id reaches a DOM id and a URL fragment in the viewer, and would reach a
#: filename the first time anything stored one per annotation, so it is the one identifier worth checking on the way in.
ID = re.compile(r"^a-\d{4}-\d{2}-\d{2}-\d+$")


def _annotation(event: dict[str, Any]) -> Annotation:
    """One `created` or `replied` event as an annotation.

    `anchor` is one of two shapes under one name: the text triple every annotation has carried since book 7.5, or -- on a note against a page of a cited work -- a page anchor carrying `kind` beside that triple (plan 0.13 item 2). The triple is read in both cases; the page anchor only when `kind` says so, since `Selector.from_dict` would otherwise swallow the page fields without a word.
    """
    anchor = event.get("anchor")
    return Annotation(
        id=str(event["id"]),
        # `run` on an event written before sessions said the same thing this says outright (plan 0.13 §5)
        author_kind="agent" if (str(event.get("kind", "")) == "agent" or event.get("run")) else "person",
        author_id=str(event.get("author", "")),
        created=str(event.get("when", "")),
        target_key=str(event.get("target", "")),
        target_hash=str(event.get("against", "")),
        selector=Selector.from_dict(anchor) if isinstance(anchor, dict) else None,
        anchor=Anchor.from_dict(anchor) if is_page_anchor(anchor) else None,
        kind=str(event.get("annotation_kind") or "objection"),
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
            # Reported, not corrected. A kind loom does not know is still shown -- `kind` is an open string and a
            # viewer renders one it has never heard of -- but a log line missing the column, or spelling it the way
            # an older draft of the plan spelled it, produced a finding that silently claimed to be an objection.
            if event.get("annotation_kind") not in KINDS:
                problems.append(f"{LOG}:{n}: {event.get('annotation_kind')!r} is not one of {', '.join(KINDS)}")
            if not ID.match(ann.id):
                problems.append(f"{LOG}:{n}: {ann.id!r} is not an annotation id")
            if kind == "replied" and str(event.get("reply_to") or "") not in index:
                # Otherwise it is in the record and on no page: not a finding, because it answers one, and under no
                # finding, because the one it answers is not there.
                problems.append(f"{LOG}:{n}: replies to unknown annotation {event.get('reply_to')!r}")
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
            # A status change is reversed by appending its undo, never by removing the event that made it. Discarding
            # has always replayed this way; resolving did not, so a resolution was the one state nothing could take
            # back -- and `--resolve` is the verb a run can apply to its own finding (DR-174).
            ann.status = "open" if event.get("undo") else "resolved"
        elif kind == "discarded":
            undo = bool(event.get("undo"))
            ann.status = "open" if undo else "discarded"
            ann.discard_reason = None if undo else (str(event.get("body") or "") or None)
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
