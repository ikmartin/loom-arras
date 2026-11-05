"""Notes (plan 0.22.8): what a person or an agent wants kept beside something the viewer shows, and a quote is one.

A note is a record of its own beside the annotation log, `.loom/annotations/notes.jsonl`, sharing its machinery: append-only events, an author, a session. `noted` writes one with its target and, for a quote, the words quoted; `kept` stops it fading. It has no kind, severity or resolution, since quoting into a discussion asks for none (P14), and it never changes a key's state.

A note fades when it is not kept, is older than `FADE_DAYS`, and nothing durable links to it -- an annotation, a message, a page or a kept note holding `quilt:n-…`. Fading is computed (P3): a faded note is hidden by default, shown with one toggle, and never deleted.
"""

from __future__ import annotations

import html as _html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loom.clock import stamp
from loom.locks import locked
from loom.paths import NOTE_LOG

#: A note's id, which reaches a URL fragment and a `quilt:` link.
ID = re.compile(r"^n-\d{4}-\d{2}-\d{2}-\d+$")
#: How long an unkept, unlinked note stays in view.
FADE_DAYS = 14
LINK = re.compile(r"quilt:(n-\d{4}-\d{2}-\d{2}-\d+)")
#: A transcript message as a target: its session and its number in that transcript.
MESSAGE = re.compile(r"^(s-\d{4}-\d{2}-\d{2}-\d{4})#(\d+)$")


@dataclass
class Note:
    """One note as its events replay: who wrote it, where, on what, the words it quotes, what it says, and whether it is kept."""

    id: str
    when: str
    author: str
    author_kind: str  # person | agent
    session: str
    target: dict[str, Any]
    body: str = ""
    quote: str | None = None
    page: int | None = None
    rects: list[list[float]] | None = None
    kept: str | None = None  # when it was kept
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "when": self.when,
            "author": {"kind": self.author_kind, "id": self.author},
            "session": self.session,
            "target": self.target,
            "body": self.body,
        }
        for k in ("quote", "page", "rects", "kept"):
            if getattr(self, k) is not None:
                out[k] = getattr(self, k)
        return out


class NoteRefused(Exception):
    """A note that cannot be written or kept, and why; `code` is the write API's."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _path(root: Path) -> Path:
    return root / NOTE_LOG


def _append(root: Path, event: dict[str, Any]) -> None:
    p = _path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def load(root: Path) -> dict[str, Note]:
    """Every note by id, its events replayed in order; a malformed line is skipped."""
    out: dict[str, Note] = {}
    try:
        lines = _path(root).read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(e, dict) or not ID.match(str(e.get("id", ""))):
            continue
        if e.get("event") == "noted" and isinstance(e.get("target"), dict):
            out[e["id"]] = Note(
                id=e["id"],
                when=str(e.get("when", "")),
                author=str(e.get("author", "")),
                author_kind="agent" if e.get("kind") == "agent" else "person",
                session=str(e.get("session", "")),
                target=dict(e["target"]),
                body=str(e.get("body") or ""),
                quote=str(e["quote"]) if e.get("quote") else None,
                page=int(e["page"]) if isinstance(e.get("page"), int) else None,
                rects=e.get("rects") if isinstance(e.get("rects"), list) else None,
            )
        elif e.get("event") == "kept" and e["id"] in out:
            out[e["id"]].kept = str(e.get("when", ""))
    return out


def _next_id(root: Path, day: str) -> str:
    taken = [int(i.rsplit("-", 1)[1]) for i in load(root) if i.startswith(f"n-{day}-")]
    return f"n-{day}-{max(taken, default=0) + 1:04d}"


def target_of(
    result: Any,
    on: str,
    *,
    page: int | None = None,
    rects: list[list[float]] | None = None,
    quote: str | None = None,
) -> dict[str, Any]:
    """What `on` names, as a note's target: a session, a message (`SESSION#SEQ`), a shown file by its path, a cited work or one of its pages, or a key, a region or a document; NoteRefused when it names nothing the viewer shows.

    A work with no page is the whole work, which has no words to quote.
    """
    from loom.cli._common import EnvError
    from loom.cli._quilt import resolve_key
    from loom.cli.review import _work_target
    from loom.files import Shown
    from loom.links import SESSION
    from loom.mailbox import read_events
    from loom.sessions import sessions

    root = result.quilt.root
    on = on.strip()
    if SESSION.match(on):
        if on not in sessions(root):
            raise NoteRefused("no-such-session", f"no session {on}", 404)
        return {"session": on}
    m = MESSAGE.match(on)
    if m:
        sid, seq = m.group(1), int(m.group(2))
        if not any(e.seq == seq and e.kind == "message" for e in read_events(root, sid)):
            raise NoteRefused("no-such-message", f"no message {seq} in {sid}", 404)
        return {"message": {"session": sid, "seq": seq}}
    if Path(on).suffix and not on.endswith(".tex") and (root / on).is_file():
        if not Shown.of(result.quilt).is_shown(on):
            raise NoteRefused("no-such-file", f"{on} is hidden from the viewer", 404)
        return {"file": on}
    work = _work_target(result, on)
    if work is not None:
        if page is None and (quote or rects):
            raise NoteRefused("missing-field", f"a quote on a cited work names its page: {on} --page N")
        if page is not None and page < 1:
            raise NoteRefused("bad-field", "a page is counted from 1")
        citekey, wid = work
        return {"work": f"{wid.scheme}:{wid.value}", "citekey": citekey}
    try:
        return {"key": resolve_key(result, on)}
    except EnvError:
        raise NoteRefused("no-such-thing", f"{on} names nothing the viewer shows", 404) from None


def write(
    result: Any,
    on: str,
    *,
    author: str,
    author_kind: str,
    session: str,
    body: str = "",
    quote: str | None = None,
    page: int | None = None,
    rects: list[list[float]] | None = None,
) -> Note:
    """Write one note on `on`, quoting `quote` there when given; a quote with neither words nor a region is the target alone."""
    target = target_of(result, on, page=page, rects=rects, quote=quote)
    if not (body.strip() or (quote or "").strip() or rects or target.get("session")):
        raise NoteRefused("empty", "a note quotes something or says something")
    root = result.quilt.root
    when = stamp()
    # the read and the write share the log's lock, so two writers in any two processes never draw one id
    with locked(_path(root)):
        note = Note(
            id=_next_id(root, when[:10]),
            when=when,
            author=author,
            author_kind=author_kind,
            session=session,
            target=target,
            body=body.strip(),
            quote=(quote or "").strip() or None,
            page=page,
            rects=rects,
        )
        event = {"event": "noted", "kind": "agent" if author_kind == "agent" else "person", **note.to_dict()}
        event["author"] = author
        _append(root, event)
    return note


def keep(root: Path, note_id: str, who: str) -> Note:
    """Keep `note_id`, so it never fades; keeping a kept note changes nothing."""
    notes = load(root)
    note = notes.get(note_id)
    if note is None:
        raise NoteRefused("no-such-note", f"no note {note_id}", 404)
    if note.kept is None:
        when = stamp()
        _append(root, {"event": "kept", "id": note_id, "when": when, "author": who})
        note.kept = when
    return note


def linked(result: Any, notes: dict[str, Note]) -> set[str]:
    """The notes something durable links to: an annotation's body, a message, a page, or a kept note."""
    from loom.mailbox import read_events
    from loom.pages import read, state_page
    from loom.records.annotations import load_records
    from loom.sessions import sessions

    root = result.quilt.root
    texts: list[str] = []
    records, _ = load_records(root)
    texts += [a.body for r in records for a in r.annotations]
    for s in sessions(root).values():
        texts += [e.body for e in read_events(root, s.id) if e.kind == "message"]
    texts.append(read(root, state_page(result.quilt.config)) or "")
    texts += [n.body for n in notes.values() if n.kept]
    return {m for t in texts for m in LINK.findall(t or "")}


def _days(when: str, now: str) -> float:
    try:
        a = datetime.fromisoformat(when.replace("Z", "+00:00"))
        b = datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return (b - a) / timedelta(days=1)


def _plain(text: str) -> str:
    return " ".join(text.split())


def detached(result: Any, note: Note) -> bool:
    """Whether a note's quote is gone from what it is on: a file's text (an HTML page's as read), a message's, or a key's own; a region or no quote never detaches."""
    from loom.mailbox import read_events
    from loom.render.manifest import own_text

    if not note.quote:
        return False
    root, t = result.quilt.root, note.target
    if "file" in t:
        try:
            text = (root / t["file"]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return True
        if t["file"].lower().endswith((".html", ".htm")):
            text = _html.unescape(re.sub(r"<[^>]+>", " ", text))
    elif "message" in t:
        found = [e.body for e in read_events(root, t["message"]["session"]) if e.seq == t["message"]["seq"]]
        text = found[0] if found else ""
    elif "key" in t:
        key = t["key"].split("#", 1)[0]
        node = result.nodes.get(key)
        if node is None:
            return True
        text = own_text(result, node)
    else:
        return False
    return _plain(note.quote) not in _plain(text)


def published(result: Any) -> dict[str, dict[str, Any]]:
    """Every note as the manifest carries it, with `faded` and `detached` computed now."""
    notes = load(result.quilt.root)
    links = linked(result, notes)
    now = stamp()
    out: dict[str, dict[str, Any]] = {}
    for nid, n in notes.items():
        row = n.to_dict()
        row["faded"] = n.kept is None and nid not in links and _days(n.when, now) > FADE_DAYS
        row["detached"] = detached(result, n)
        out[nid] = row
    return out
