"""`.loom/annotations/log.jsonl`: every review event, appended, and rewritten only to delete an annotation.

One line per event, current state by replay. It replaced a tree of `annotations.json` files, one per run and one per author per day, each rewritten whole whenever anything in it changed — which is why an annotation could only ever be *replied* to. An agent re-checking a finding that still stands now `edited`s it: the history stays in the log, one current body is shown, and a finding stops accumulating restatements of itself.

Two people appending in parallel keep both lines when they merge, which is why this is JSONL and not a database: git calls it a conflict, keeping both sides resolves it, and each record's id is its own (`records/ids.py`). A malformed line is reported as `loom:foreign-annotations` and skipped; it never stops the rest from loading.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from loom.anchors import Anchor, is_page_anchor
from loom.locks import locked
from loom.paths import ANNOTATION_LOG, BUILD
from loom.records.annotations import Annotation, Record, next_id
from loom.records.ids import ANNOTATION
from loom.records.selectors import Selector

LOG = ANNOTATION_LOG
EVENTS = ("created", "replied", "edited", "resolved")


def log_path(root: Path) -> Path:
    return root / LOG


def append(root: Path, event: dict[str, Any]) -> None:
    """Append one event, under the log's lock, so it never lands while a deletion rewrites the log."""
    p = log_path(root)
    with locked(p):
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def delete(root: Path, ann_ids: list[str]) -> list[dict[str, Any]]:
    """Delete annotations from the log: each one's every event, and its replies', all the way down.

    The log is rewritten in place under its lock, so its lock keeps holding and no append lands between the read and the write; a copy of the log as it was goes to the build directory first, in case the write is cut short.

    Parameters
    ----------
    root : Path
        The quilt.
    ann_ids : list of str
        The annotations to delete; their replies go with them.

    Returns
    -------
    list of dict
        The events removed, in the log's order: what `restore` puts back.
    """
    p = log_path(root)
    with locked(p):
        lines = p.read_text(encoding="utf-8").splitlines() if p.is_file() else []
        parsed: list[tuple[str, dict[str, Any] | None]] = []
        for line in lines:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                e = None
            parsed.append((line, e if isinstance(e, dict) else None))
        gone = set(ann_ids)
        grew = True
        while grew:  # replies to replies: every annotation whose parent is going goes too
            grew = False
            for _line, e in parsed:
                if (
                    e
                    and e.get("event") == "replied"
                    and str(e.get("reply_to")) in gone
                    and str(e.get("id")) not in gone
                ):
                    gone.add(str(e["id"]))
                    grew = True
        kept = [line for line, e in parsed if not (e and str(e.get("id")) in gone)]
        removed = [e for _line, e in parsed if e and str(e.get("id")) in gone]
        if removed:
            backup = root / BUILD / "annotations-before-delete.jsonl"
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with p.open("r+", encoding="utf-8") as fh:
                fh.seek(0)
                fh.write("".join(f"{line}\n" for line in kept))
                fh.truncate()
    return removed


def restore(root: Path, events: list[dict[str, Any]]) -> list[str]:
    """Put back what `delete` removed, appended under the log's lock; refused when an annotation it creates is in the log already. Returns the ids it restored."""
    made = [str(e.get("id")) for e in events if e.get("event") in ("created", "replied")]
    p = log_path(root)
    with locked(p):
        present = {a.id for r in replay(root)[0] for a in r.annotations}
        if any(i in present for i in made):
            raise ValueError("those annotations are in the log already")
        with p.open("a", encoding="utf-8") as fh:
            for e in events:
                fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    return made


def append_new(root: Path, event: dict[str, Any], date: str) -> str:
    """Append a new annotation's event under a fresh id for `date`.

    The read and the write share the log's lock, so two writers in any two processes never draw one id.

    Parameters
    ----------
    root : Path
        The quilt.
    event : dict
        The `created` or `replied` event, without its `id`.
    date : str
        The day the id names, `YYYY-MM-DD`.

    Returns
    -------
    str
        The id it drew.

    See Also
    --------
    append : for an event about an annotation that already has an id.
    """
    with locked(log_path(root)):
        ann_id = next_id(replay(root)[0], date)
        append(root, {**event, "id": ann_id})
    return ann_id


def source_of(event: dict[str, Any]) -> str:
    """Which record an event belongs to: its session, the manifest's grouping key (plan 0.13 §5); '' when it names none."""
    return str(event.get("session") or "")


#: What `loom annotate` writes as an id. An id reaches a DOM id and a URL fragment in the viewer, and would reach a
#: filename the first time anything stored one per annotation, so it is the one identifier worth checking on the way in.
ID = re.compile(rf"^{ANNOTATION}$")


def _look(given: Any) -> dict[str, Any]:
    """A look as an event carries it: a table of the four fields, any of them absent."""
    return (
        {k: given[k] for k in ("color", "style", "weight", "opacity") if k in given} if isinstance(given, dict) else {}
    )


def _annotation(event: dict[str, Any]) -> Annotation:
    """One `created` or `replied` event as an annotation.

    `anchor` is one of two shapes under one name: the text triple every annotation carries, or -- on a note against a page of a cited work -- a page anchor carrying `kind` beside that triple (plan 0.13 item 2). The triple is read in both cases; the page anchor only when `kind` says so, since `Selector.from_dict` would otherwise swallow the page fields without a word.
    """
    anchor = event.get("anchor")
    return Annotation(
        id=str(event["id"]),
        author_kind="agent" if str(event.get("kind", "")) == "agent" else "person",
        author_id=str(event.get("author", "")),
        created=str(event.get("when", "")),
        target_key=str(event.get("target", "")),
        target_hash=str(event.get("against", "")),
        in_doc=str(event["in"]) if event.get("in") else None,
        selector=Selector.from_dict(anchor) if isinstance(anchor, dict) else None,
        anchor=Anchor.from_dict(anchor) if is_page_anchor(anchor) else None,
        type=str(event["type"]) if event.get("type") else None,
        own_look=_look(event.get("look")),
        drawn=_look(event.get("drawn")),
        body=str(event.get("body", "")),
        status="open",
        in_reply_to=event.get("reply_to"),
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
            if not src:
                # every writer names the session; a line that does not was written by something else
                problems.append(f"{LOG}:{n}: {kind} {event['id']!r} names no session")
                continue
            ann = _annotation(event)
            # a type the quilt no longer lists is not a problem: the annotation keeps its look and reads as untyped
            if event.get("type") is not None and not isinstance(event.get("type"), str):
                problems.append(f"{LOG}:{n}: its type is not a type's id")
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
        # every later event names an annotation
        target = event.get("id")
        if target is None:
            problems.append(f"{LOG}:{n}: {kind} without an id")
            continue
        found = index.get(str(target))
        if found is None:
            problems.append(f"{LOG}:{n}: {kind} names unknown annotation {target}")
            continue
        _src, ann = found
        if kind == "edited":
            for f in ("body", "payload", "placement"):
                if f in event:
                    setattr(ann, f, event[f])
            # restyled or retyped: the type it now has, the look set on it, and the look it is drawn with once its type is gone
            if "type" in event:
                ann.type = str(event["type"]) if event["type"] else None
            if "look" in event:
                ann.own_look = _look(event["look"])
            if "drawn" in event:
                ann.drawn = _look(event["drawn"])
            # a restated finding is about the text it was restated against
            if event.get("against"):
                ann.target_hash = str(event["against"])
        elif kind == "resolved":
            # a resolution is reversed by appending its undo, never by removing the event that made it (DR-174)
            undo = bool(event.get("undo"))
            ann.status = "open" if undo else "resolved"
            ann.resolved_why = None if undo else (str(event.get("body") or "") or None)
            ann.applied = None if undo or not isinstance(event.get("applied"), dict) else dict(event["applied"])
    out: list[Record] = []
    for src in order:
        out.append(Record(path=p, rel=src, annotations=by_source[src]))
    return out, problems
