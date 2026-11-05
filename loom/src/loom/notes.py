"""Notes (plan 0.22.8): what a person or an agent wants kept beside something the viewer shows, and a quote is one.

A note is a record of its own beside the annotation log, `.loom/annotations/notes.jsonl`, sharing its machinery: append-only events, an author, a session. `noted` writes one with its target and, for a quote, the words quoted; `kept` stops it fading. It has no kind, severity or resolution, since quoting into a discussion asks for none (P14), and it never changes a key's state.

A note fades when it is not kept, is older than `FADE_DAYS`, and nothing durable links to it -- an annotation, a message, a page or a kept note holding `quilt:n-…`. Fading is computed (P3): a faded note is hidden by default, shown with one toggle, and never deleted.

A note on a page of a PDF may be a **mark**, which says how it is drawn there: a highlight, an underline, a strike-through, a pin, ink, words on the page, a box, an oval or an arrow. A mark needs no session, never fades, and can be changed, erased and restored by events of its own. It records the hash of the PDF it was drawn on (`artifact`), so a changed file is noticed (A3): a mark with words is found again on its page and one that cannot be is detached. `rects` are `[x0, y0, x1, y1]` in points from the page's top left, or in an image's pixels.
"""

from __future__ import annotations

import hashlib
import html as _html
import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loom.clock import stamp
from loom.locks import locked
from loom.paths import NOTE_LOG
from loom.records.ids import NOTE, SESSION, draw

#: A note's id, which reaches a URL fragment and a `quilt:` link.
ID = re.compile(rf"^{NOTE}$")
#: How long an unkept, unlinked note stays in view.
FADE_DAYS = 14
LINK = re.compile(rf"quilt:({NOTE})")
#: A transcript message as a target: its session and its number in that transcript.
MESSAGE = re.compile(rf"^({SESSION})#(\d+)$")
#: How a note is drawn on a PDF page.
MARKS = ("highlight", "underline", "strike", "pin", "ink", "text", "box", "oval", "arrow")
#: The marks on a page's words, which a quote can place.
ON_WORDS = ("highlight", "underline", "strike")
#: The marks held by strokes rather than a rectangle.
STROKED = ("ink", "arrow")
#: The marks that say nothing without words of their own.
SAYING = ("pin", "text")
#: The most points one mark's strokes may hold; the manifest carries them.
MAX_POINTS = 20000


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
    mark: str | None = None  # how it is drawn on a PDF page, one of MARKS
    strokes: list[list[float]] | None = None  # x, y, x, y… per stroke, in points from the page's top left
    artifact: str | None = None  # the hash of the PDF it was written on
    origin: dict[str, Any] | None = (
        None  # where a mark taken in came from: its author, subtype, colour, and the PDF's own reference and hash
    )
    erased: str | None = None  # when it was erased
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
        for k in ("quote", "page", "rects", "kept", "mark", "strokes", "artifact", "origin", "erased"):
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
                mark=str(e["mark"]) if e.get("mark") else None,
                strokes=e.get("strokes") if isinstance(e.get("strokes"), list) else None,
                artifact=str(e["artifact"]) if e.get("artifact") else None,
                origin=e.get("origin") if isinstance(e.get("origin"), dict) else None,
            )
        elif e["id"] not in out:
            continue
        elif e.get("event") == "kept":
            out[e["id"]].kept = str(e.get("when", ""))
        elif e.get("event") == "changed":
            n = out[e["id"]]
            if isinstance(e.get("body"), str):
                n.body = e["body"]
            if isinstance(e.get("rects"), list):
                n.rects = e["rects"]
            if isinstance(e.get("strokes"), list):
                n.strokes = e["strokes"]
        elif e.get("event") == "erased":
            out[e["id"]].erased = str(e.get("when", ""))
        elif e.get("event") == "restored":
            out[e["id"]].erased = None
    return out


def _next_id(root: Path, day: str) -> str:
    return draw(f"n-{day}-", load(root))


#: A PDF's hash by its path, size and modification time: a mark is written and published far more often than a file changes, and a book takes a moment to hash.
_HASHES: dict[tuple[str, int, int], str] = {}


def artifact_of(pdf: Path) -> str:
    """The hash of `pdf`, read once for each version of the file."""
    at = pdf.stat()
    key = (str(pdf), at.st_size, at.st_mtime_ns)
    if key not in _HASHES:
        _HASHES[key] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    return _HASHES[key]


def pdf_of(result: Any, target: dict[str, Any]) -> Path | None:
    """The PDF a note's target is on, a shown file or a cited work's copy on this machine; None for anything else."""
    root = result.quilt.root
    if isinstance(target.get("file"), str):
        return root / target["file"] if target["file"].lower().endswith(".pdf") else None
    entry = result.bib.get(target["citekey"]) if isinstance(target.get("citekey"), str) else None
    if entry is None:
        return None
    from loom.refs.fetch import work_dir

    paper: Path = work_dir(root, entry) / "paper.pdf"
    return paper if paper.is_file() else None


def lines_of(pdf: Path, page: int, words: str) -> list[list[float]] | None:
    """Where `words` stand on a page, one rectangle per line; None where they are not there or the page cannot be read."""
    from loom.refs.pages import MapRefused, token_boxes
    from loom.refs.search import locate_span

    try:
        hit = locate_span(token_boxes(pdf, page, None), words, page)
    except MapRefused:
        return None
    return [[float(v) for v in q] for q in hit.lines] if hit else None


def _numbers(raw: Any, what: str) -> list[float]:
    """A list of finite numbers from a write, each to a hundredth of a point; NoteRefused for anything else."""
    if not isinstance(raw, list) or not all(isinstance(v, int | float) and not isinstance(v, bool) for v in raw):
        raise NoteRefused("bad-field", f"{what} is a list of numbers")
    if not all(v == v and abs(v) < 1e7 for v in raw):
        raise NoteRefused("bad-field", f"{what} is a list of numbers")
    return [round(float(v), 2) for v in raw]


def clean_rects(raw: Any) -> list[list[float]] | None:
    """Rectangles from a write, each `[x0, y0, x1, y1]` with its corners in order; None for none."""
    if not raw:
        return None
    if not isinstance(raw, list):
        raise NoteRefused("bad-field", "rects is a list of [x0, y0, x1, y1]")
    out = []
    for r in raw:
        v = _numbers(r, "a rectangle")
        if len(v) != 4:
            raise NoteRefused("bad-field", "a rectangle is [x0, y0, x1, y1]")
        out.append([min(v[0], v[2]), min(v[1], v[3]), max(v[0], v[2]), max(v[1], v[3])])
    return out


def clean_strokes(raw: Any) -> list[list[float]] | None:
    """Strokes from a write, each `x, y, x, y…` of at least two points and no more than `MAX_POINTS` in all; None for none."""
    if not raw:
        return None
    if not isinstance(raw, list):
        raise NoteRefused("bad-field", "strokes is a list of x, y, x, y…")
    out = [_numbers(s, "a stroke") for s in raw]
    if any(len(s) < 4 or len(s) % 2 for s in out):
        raise NoteRefused("bad-field", "a stroke holds an x and a y for at least two points")
    if sum(len(s) for s in out) / 2 > MAX_POINTS:
        raise NoteRefused("too-large", f"a mark holds at most {MAX_POINTS} points")
    return out


def _bounds(strokes: list[list[float]]) -> list[list[float]]:
    """The one rectangle round every stroke, which is where a stroked mark is found and landed at."""
    xs = [v for s in strokes for v in s[0::2]]
    ys = [v for s in strokes for v in s[1::2]]
    return [[min(xs), min(ys), max(xs), max(ys)]]


def _placed(
    result: Any,
    target: dict[str, Any],
    mark: str | None,
    page: int | None,
    quote: str | None,
    rects: list[list[float]] | None,
    strokes: list[list[float]] | None,
    body: str,
) -> tuple[list[list[float]] | None, str | None]:
    """A note's place on a PDF page as it is recorded, and the hash of that PDF.

    `write` and `take_in` both ask this. A mark on words given only as a quote is placed by the page's word boxes, refused when they are not there; a plain quote is placed the same way where it can be, and otherwise stays a quote with no place.
    """
    pdf = pdf_of(result, target)
    if mark is None:
        if pdf is None or page is None:
            return rects, None
        if quote and not rects:
            rects = lines_of(pdf, page, quote)
        return rects, artifact_of(pdf)
    if mark not in MARKS:
        raise NoteRefused("bad-field", f"a mark is one of: {', '.join(MARKS)}")
    if pdf is None:
        raise NoteRefused("not-a-pdf", "a mark is drawn on a page of a PDF held on this machine")
    if page is None or page < 1:
        raise NoteRefused("missing-field", "a mark names its page, counted from 1")
    if mark in SAYING and not body:
        raise NoteRefused("empty", f"a {mark} says something")
    if mark in STROKED:
        if not strokes:
            raise NoteRefused("missing-field", f"{mark} needs its strokes")
        return _bounds(strokes), artifact_of(pdf)
    if mark in ON_WORDS:
        if not rects and not quote:
            raise NoteRefused("missing-field", f"a {mark} names the words or the rectangles it is on")
        if not rects:
            rects = lines_of(pdf, page, quote or "")
            if not rects:
                raise NoteRefused("not-on-page", f"those words are not on page {page}")
    elif not rects or len(rects) != 1:
        raise NoteRefused("missing-field", f"a {mark} names its one rectangle")
    return rects, artifact_of(pdf)


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
    mark: str | None = None,
    strokes: list[list[float]] | None = None,
) -> Note:
    """Write one note on `on`, quoting `quote` there when given; a quote with neither words nor a region is the target alone.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned.
    on : str
        What it is on: see `target_of`.
    author : str
        Who writes it.
    author_kind : str
        `person` or `agent`.
    session : str
        The session it is filed in; empty for a mark outside any.
    body : str, default ''
        What it says.
    quote : str, optional
        The words it quotes.
    page : int, optional
        The page, on a cited work or a PDF.
    rects : list of [x0, y0, x1, y1], optional
        Where it is, in points from the page's top left or an image's pixels.
    mark : str, optional
        How it is drawn on a PDF page, one of `MARKS`.
    strokes : list of list of float, optional
        A stroked mark's points, x, y, x, y… per stroke.

    Returns
    -------
    Note
        The note as written.

    See Also
    --------
    take_in : many marks at once, from a PDF's own annotations.
    """
    target = target_of(result, on, page=page, rects=rects, quote=quote)
    rects = clean_rects(rects)
    strokes = clean_strokes(strokes)
    if not (body.strip() or (quote or "").strip() or rects or strokes or target.get("session")):
        raise NoteRefused("empty", "a note quotes something or says something")
    root = result.quilt.root
    rects, artifact = _placed(result, target, mark, page, (quote or "").strip() or None, rects, strokes, body.strip())
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
            mark=mark,
            strokes=strokes,
            artifact=artifact,
        )
        event = {"event": "noted", "kind": "agent" if author_kind == "agent" else "person", **note.to_dict()}
        event["author"] = author
        _append(root, event)
    return note


def _mine(notes: dict[str, Note], note_id: str, who: str, who_kind: str) -> Note:
    """The note `note_id`, for someone allowed to change it: a person may change any, an agent only its own (K5)."""
    note = notes.get(note_id)
    if note is None:
        raise NoteRefused("no-such-note", f"no note {note_id}", 404)
    if who_kind == "agent" and note.author != who:
        raise NoteRefused("not-yours", f"{note_id} is {note.author}'s; an agent changes only its own", 403)
    return note


def change(
    root: Path,
    note_id: str,
    who: str,
    who_kind: str,
    *,
    body: str | None = None,
    rects: Any = None,
    strokes: Any = None,
) -> Note:
    """Change what a note says or, on a mark that is not on words, where it stands.

    The words a highlight is on are its place, so a mark on words does not move; a pin or words on the page cannot be emptied, since they would then say nothing. The change is an event, and the log keeps what it replaced.

    Parameters
    ----------
    root : Path
        The quilt's root.
    note_id : str
        The note.
    who : str
        Who changes it.
    who_kind : str
        `person`, who may change any note, or `agent`, who may change only its own.
    body : str, optional
        What it says now.
    rects : list of [x0, y0, x1, y1], optional
        Where a box, an oval, a pin or words on the page stands now.
    strokes : list of list of float, optional
        Where ink or an arrow runs now; its rectangle follows.

    Returns
    -------
    Note
        The note as it now stands.

    See Also
    --------
    erase : take it off the page.
    """
    note = _mine(load(root), note_id, who, who_kind)
    event: dict[str, Any] = {"event": "changed", "id": note_id, "when": stamp(), "author": who}
    if body is not None:
        if note.mark in SAYING and not body.strip():
            raise NoteRefused("empty", f"a {note.mark} says something; erase it instead")
        event["body"] = note.body = body.strip()
    if strokes:
        if note.mark not in STROKED:
            raise NoteRefused("bad-field", "only ink and an arrow hold strokes")
        event["strokes"] = note.strokes = clean_strokes(strokes)
        event["rects"] = note.rects = _bounds(note.strokes or [])
    elif rects:
        if note.mark is None or note.mark in ON_WORDS or note.mark in STROKED:
            raise NoteRefused("bad-field", "this note's place is not a rectangle of its own to move")
        event["rects"] = note.rects = clean_rects(rects)
    if set(event) == {"event", "id", "when", "author"}:
        raise NoteRefused("missing-field", "say what changes: body, rects or strokes")
    _append(root, event)
    return note


def erase(root: Path, note_id: str, who: str, who_kind: str) -> Note:
    """Take a note off the page and out of every list; the log keeps it, and erasing an erased note changes nothing.

    Parameters
    ----------
    root : Path
        The quilt's root.
    note_id : str
        The note.
    who : str
        Who erases it.
    who_kind : str
        `person`, who may erase any note, or `agent`, who may erase only its own.

    Returns
    -------
    Note
        The note, with when it was erased.

    See Also
    --------
    restore : put it back.
    """
    note = _mine(load(root), note_id, who, who_kind)
    if note.erased is None:
        note.erased = stamp()
        _append(root, {"event": "erased", "id": note_id, "when": note.erased, "author": who})
    return note


def restore(root: Path, note_id: str, who: str, who_kind: str) -> Note:
    """Put an erased note back; restoring one that stands changes nothing.

    Parameters
    ----------
    root : Path
        The quilt's root.
    note_id : str
        The note.
    who : str
        Who restores it.
    who_kind : str
        `person`, who may restore any note, or `agent`, who may restore only its own.

    Returns
    -------
    Note
        The note as it now stands.
    """
    note = _mine(load(root), note_id, who, who_kind)
    if note.erased is not None:
        _append(root, {"event": "restored", "id": note_id, "when": stamp(), "author": who})
        note.erased = None
    return note


def _bound(rects: list[list[float]]) -> list[float]:
    """The one rectangle round `rects`."""
    return [min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)]


def _same_place(a: list[list[float]], b: list[list[float]]) -> bool:
    """Whether two lists of rectangles bound one place, within the two points a rewrite of the file may move it."""
    return bool(a and b) and all(abs(x - y) <= 2 for x, y in zip(_bound(a), _bound(b), strict=True))


def take_in(
    result: Any,
    on: str,
    items: Iterable[dict[str, Any]],
    *,
    author: str,
    author_kind: str,
    session: str = "",
) -> dict[str, int]:
    """Write a PDF's own annotations as marks on `on`, skipping what is already here.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned.
    on : str
        The PDF they are taken onto: a shown file's path or a citekey.
    items : iterable of dict
        Each `{page, mark, rects?, strokes?, body?, origin?}`, in points from the page's top left.
    author : str
        Who takes them in; what wrote each one stays in its `origin`.
    author_kind : str
        `person` or `agent`.
    session : str, default ''
        The session they are filed in; none for a person at the viewer.

    Returns
    -------
    dict
        `{taken, already, skipped}`: how many were written, how many stand here already by page, place and words, and how many could not be placed. An erased mark counts as already here, so taking a PDF in again does not bring it back.

    See Also
    --------
    write : one mark, or any other note.
    """
    from loom.refs.pages import MapRefused, token_boxes
    from loom.refs.search import words_under

    root = result.quilt.root
    probe = target_of(result, on, page=1)
    pdf = pdf_of(result, probe)
    if pdf is None:
        raise NoteRefused("not-a-pdf", f"{on} is not a PDF held on this machine")
    # one count over the whole run, so the log stays locked from the read to the last write and no writer beside it draws an id from this run
    with locked(_path(root)):
        notes = load(root)
        held = [n for n in notes.values() if n.target == probe and n.page and n.rects]
        when = stamp()
        day = when[:10]
        count = max((int(i.rsplit("-", 1)[1]) for i in notes if i.startswith(f"n-{day}-")), default=0)
        boxes: dict[int, str] = {}
        out = {"taken": 0, "already": 0, "skipped": 0}
        for item in items:
            try:
                page = item.get("page")
                mark = item.get("mark")
                body = str(item.get("body") or "").strip()
                rects = clean_rects(item.get("rects"))
                strokes = clean_strokes(item.get("strokes"))
                if not isinstance(page, int) or not isinstance(mark, str):
                    raise NoteRefused("bad-field", "an item names its page and mark")
                rects, artifact = _placed(result, probe, mark, page, None, rects, strokes, body)
            except NoteRefused:
                out["skipped"] += 1
                continue
            here = rects or []
            if any(n.page == page and (n.body or "") == body and _same_place(n.rects or [], here) for n in held):
                out["already"] += 1
                continue
            quote = None
            if mark in ON_WORDS:
                if page not in boxes:
                    try:
                        boxes[page] = token_boxes(pdf, page, None)
                    except MapRefused:
                        boxes[page] = ""
                quote = words_under(boxes[page], here) or None
            origin = dict(item["origin"]) if isinstance(item.get("origin"), dict) else None
            if origin and origin.get("ref"):
                origin["sha"] = artifact
            count += 1
            note = Note(
                id=f"n-{day}-{count:04d}",
                when=when,
                author=author,
                author_kind=author_kind,
                session=session,
                target=probe,
                body=body,
                quote=quote,
                page=page,
                rects=here,
                mark=mark,
                strokes=strokes,
                artifact=artifact,
                origin=origin,
            )
            event = {"event": "noted", "kind": "agent" if author_kind == "agent" else "person", **note.to_dict()}
            event["author"] = author
            _append(root, event)
            held.append(note)
            out["taken"] += 1
    return out


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


def _on_the_pdf_now(result: Any, note: Note, pdf: Path) -> tuple[bool, list[list[float]] | None]:
    """Whether a note on a PDF is detached, and where its words stand when the file has changed under them.

    Unchanged bytes keep the place as written, so nothing reads the file. A changed file puts words back through the page's word boxes, and anything else is detached (A3). A note that names no hash was written with nothing to compare, and nothing is claimed of it.
    """
    if not pdf.is_file():
        return bool(note.artifact), None
    if note.artifact is None or note.artifact == artifact_of(pdf):
        return False, None
    lines = lines_of(pdf, note.page, note.quote) if note.quote and note.page else None
    return lines is None, lines


def detached(result: Any, note: Note) -> bool:
    """Whether a note is gone from what it is on: a PDF's bytes changed under it and its words are not found again, or its quote left a file's text (an HTML page's as read), a message's, or a key's own; a region elsewhere or no quote never detaches."""
    from loom.mailbox import read_events
    from loom.render.manifest import own_text

    pdf = pdf_of(result, note.target)
    if pdf is not None:
        return _on_the_pdf_now(result, note, pdf)[0]
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
    """Every note as the manifest carries it, oldest first, with `faded` and `detached` computed now."""
    notes = load(result.quilt.root)
    links = linked(result, notes)
    now = stamp()
    out: dict[str, dict[str, Any]] = {}
    for nid, n in sorted(notes.items(), key=lambda item: item[1].when):
        pdf = pdf_of(result, n.target)
        ref, sha = (n.origin or {}).get("ref"), (n.origin or {}).get("sha")
        hides = ref if ref and pdf is not None and pdf.is_file() and sha == artifact_of(pdf) else None
        # an erased note is gone from every list; one standing for an annotation in its file stays, so the viewer goes on hiding that annotation
        if n.erased and not hides:
            continue
        row = n.to_dict()
        row["faded"] = n.mark is None and n.kept is None and nid not in links and _days(n.when, now) > FADE_DAYS
        if hides:
            row["hides"] = hides
        if pdf is not None:
            row["detached"], moved = _on_the_pdf_now(result, n, pdf)
            if moved:
                row["rects"] = moved
        else:
            row["detached"] = detached(result, n)
        out[nid] = row
    return out
