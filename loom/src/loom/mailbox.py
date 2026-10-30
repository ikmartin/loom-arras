"""`.loom/sessions/<id>/inbox.jsonl`: a session's transcript, what `loom session say` appends and the viewer's Transcript reads.

**Loom keeps a record, not a conversation.** A message is appended; no model is called, no task is assigned and nobody is woken. The inbox is append-only, and its events are sequence-numbered so a reader polling it (`/_api/events`) knows when it missed some.
"""

from __future__ import annotations

import bisect
import fcntl
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loom.clock import stamp
from loom.sessions import DIR

INBOX = "inbox.jsonl"
#: Events per transcript page in the build.
PAGE = 100


def session_dir(root: Path, sid: str) -> Path:
    return root / DIR / sid


def inbox_path(root: Path, sid: str) -> Path:
    return session_dir(root, sid) / INBOX


@dataclass(frozen=True)
class Event:
    """One thing that happened in a session, in the order it happened."""

    seq: int
    kind: str
    who: str
    when: str
    body: str
    #: Annotations changed alongside the message, carried inline so a reader needs no second call.
    changed: list[dict[str, Any]]

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"seq": self.seq, "kind": self.kind, "who": self.who, "when": self.when}
        if self.body:
            out["body"] = self.body
        if self.changed:
            out["changed"] = self.changed
        return out


def _event(line: str | bytes) -> Event | None:
    """One inbox line as an Event, or None for a blank or malformed one."""
    if not line.strip():
        return None
    try:
        e = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(e, dict):
        return None
    return Event(
        seq=int(e.get("seq", 0)),
        kind=str(e.get("kind", "message")),
        who=str(e.get("who", "")),
        when=str(e.get("when", "")),
        body=str(e.get("body", "")),
        changed=[c for c in e.get("changed", []) if isinstance(c, dict)],
    )


def read_events(root: Path, sid: str, since: int = 0) -> list[Event]:
    """Every event after `since`, in order; a malformed line is skipped rather than stopping the rest."""
    p = inbox_path(root, sid)
    if not p.is_file():
        return []
    out: list[Event] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        e = _event(line)
        if e is not None and e.seq > since:
            out.append(e)
    return out


def last_seq(root: Path, sid: str) -> int:
    """The last event's sequence number, read from the end of the file rather than the whole of it."""
    p = inbox_path(root, sid)
    try:
        size = p.stat().st_size
    except OSError:
        return 0
    with p.open("rb") as fh:
        pos, tail = size, b""
        while pos > 0:
            n = min(4096, pos)
            pos -= n
            fh.seek(pos)
            tail = fh.read(n) + tail
            lines = tail.split(b"\n")
            # the first piece may be the end of a line that started further back
            whole = lines if pos == 0 else lines[1:]
            for line in reversed(whole):
                e = _event(line)
                if e is not None:
                    return e.seq
    return 0


class Transcript:
    """A session's inbox, indexed by where each event starts, so a reader polling it reads only what is new.

    Held by `loom serve` for as long as it runs (`transcript()`); a file that shrank was rewritten, and the index starts again. A line still being written, with no newline yet, is left for the next refresh.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.size = 0
        self.seqs: list[int] = []
        self.offsets: list[int] = []

    def refresh(self) -> None:
        try:
            size = self.path.stat().st_size
        except OSError:
            size = 0
        if size < self.size:
            self.size, self.seqs, self.offsets = 0, [], []
        if size == self.size:
            return
        with self.path.open("rb") as fh:
            fh.seek(self.size)
            pos = self.size
            for raw in fh:
                if not raw.endswith(b"\n"):
                    break
                e = _event(raw)
                if e is not None and (not self.seqs or e.seq > self.seqs[-1]):
                    self.seqs.append(e.seq)
                    self.offsets.append(pos)
                pos += len(raw)
        self.size = pos

    @property
    def seq(self) -> int:
        self.refresh()
        return self.seqs[-1] if self.seqs else 0

    def since(self, seq: int) -> list[Event]:
        """Every event after `seq`, reading from the first of them rather than from the top of the file."""
        self.refresh()
        i = bisect.bisect_right(self.seqs, seq)
        if i == len(self.seqs):
            return []
        with self.path.open("rb") as fh:
            fh.seek(self.offsets[i])
            raw = fh.read(self.size - self.offsets[i])
        return [e for e in (_event(line) for line in raw.split(b"\n")) if e is not None and e.seq > seq]


_TRANSCRIPTS: dict[Path, Transcript] = {}


def transcript(root: Path, sid: str) -> Transcript:
    """The one index of a session's inbox this process keeps."""
    p = inbox_path(root, sid)
    if p not in _TRANSCRIPTS:
        _TRANSCRIPTS[p] = Transcript(p)
    return _TRANSCRIPTS[p]


#: A block heading in a report: any level, the block's name in brackets, and whatever the agent wrote after it (`ai/rules.md`, Where work goes).
BLOCK_HEADING = re.compile(r"^(?P<hashes>#{1,6})[ \t]*\[(?P<name>[a-z][a-z0-9-]*)\][ \t]*(?P<rest>.*)$", re.M)


def render_body(body: str) -> str:
    """A message's Markdown as a viewer shows it: as annotation bodies are rendered, with a report's bracketed blocks each in a `<section data-block="NAME">`.

    A block's heading shows its name, or what the agent wrote after the brackets, and never the brackets themselves, which only classify it; what comes before the first block, the line naming the mode, stays outside any section. A body with no bracketed heading renders exactly as an annotation's. The viewer folds a long report after its first block, reading these sections.
    """
    from html import escape

    from loom.records.store import render_markdown

    found = list(BLOCK_HEADING.finditer(body))
    if not found:
        return render_markdown(body)
    pieces = [render_markdown(body[: found[0].start()].rstrip())] if body[: found[0].start()].strip() else []
    for i, m in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(body)
        name, level = m.group("name"), len(m.group("hashes"))
        title = (m.group("rest") or "").strip() or name
        inner = body[m.end() : end].strip()
        pieces.append(
            f'<section data-block="{name}"><h{level}>{escape(title)}</h{level}>'
            + (render_markdown(inner) if inner else "")
            + "</section>"
        )
    return "".join(pieces)


def public(e: Event) -> dict[str, Any]:
    """An event as a viewer reads it: the stored fields, and the body rendered (`render_body`)."""
    out = e.to_json()
    if e.body:
        out["body_html"] = render_body(e.body)
    return out


def page(root: Path, sid: str, n: int) -> dict[str, Any]:
    """Page `n` of a session's transcript as it stands now, read through the session's index: what `loom serve` answers for a page, since a message rebuilds nothing and the build's copy goes stale."""
    events = [e for e in transcript(root, sid).since(PAGE * (n - 1)) if e.seq <= PAGE * n]
    return {"session": sid, "page": n, "events": [public(e) for e in events]}


def pages(root: Path, sid: str) -> dict[int, dict[str, Any]]:
    """The transcript in the build's pages: page n holds seqs PAGE*(n-1)+1 to PAGE*n, so a reader that knows the last seq knows which pages exist."""
    out: dict[int, dict[str, Any]] = {}
    for e in read_events(root, sid):
        n = (e.seq - 1) // PAGE + 1
        out.setdefault(n, {"session": sid, "page": n, "events": []})["events"].append(public(e))
    return out


def post(
    root: Path, sid: str, body: str, who: str, *, kind: str = "message", changed: list[dict[str, Any]] | None = None
) -> Event:
    """Append one message, and return it.

    Parameters
    ----------
    root : Path
        The quilt.
    sid : str
        The session.
    body : str
        What was said.
    who : str
        Who said it, by the name they declared.
    kind : str, default 'message'
        `message` from a person or an agent; other kinds are loom's own notes about the session.
    changed : list of dict, optional
        Annotations changed alongside it, carried inline so a reader needs no second call. A post with these may have no body.

    Returns
    -------
    Event

    Raises
    ------
    ValueError
        When there is neither a body nor anything changed.
    """
    if not body.strip() and not changed:
        raise ValueError("a message with no text and nothing attached says nothing")
    d = session_dir(root, sid)
    d.mkdir(parents=True, exist_ok=True)
    # Two writers -- the person through the viewer and an agent through `say` -- must not draw the same number.
    with inbox_path(root, sid).open("a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            e = Event(seq=last_seq(root, sid) + 1, kind=kind, who=who, when=stamp(), body=body, changed=changed or [])
            fh.write(json.dumps(e.to_json(), ensure_ascii=False, sort_keys=True) + "\n")
            fh.flush()
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    return e


def render(events: list[Event]) -> str:
    """The events as an agent reads them in `loom ai orient`'s chat tail, each message's annotations beneath it."""
    lines: list[str] = []
    for e in events:
        lines.append(f"{e.when[11:16]} {e.who}: {e.body}" if e.kind == "message" else f"{e.when[11:16]} — {e.body}")
        if e.changed:
            lines.append(render_changes(e.changed))
    return "\n".join(lines)


def render_changes(changed: list[dict[str, Any]]) -> str:
    """The annotations a message carries, or `loom since` reports, as an agent reads them: one line each, then the words it is on, its body and what it proposes."""
    lines: list[str] = []
    for c in changed:
        who = c.get("by", "")
        # what a reader can act on: the citekey and the page for a note on a page, the key otherwise
        where = f"{c['work']} p.{c['page']}" if c.get("work") and c.get("page") else c.get("target", "")
        mine = " · to your annotation" if c.get("yours") else ""
        now = f" · now {c['status']}" if c.get("status") else ""
        lines.append(f"  {c.get('id', '')}  {c.get('kind', '')} · {where} · {c.get('act', '')} by {who}{mine}{now}")
        if c.get("quote"):
            lines.append(f'      on "{c["quote"]}"')
        if c.get("body"):
            lines.append(f'      "{c["body"]}"')
        if c.get("payload"):
            lines.append(f"      proposes ({c.get('placement') or 'replace'}): {c['payload']}")
    return "\n".join(lines)


def work_of(root: Path, annotation: Any) -> str | None:
    """The citekey a page note's target names, or None when the target is a key in the corpus.

    The record stores the work's identifier, which is what two quilts agree on; every `loom library` command wants the citekey, which is what this machine calls it. Nothing mapped one to the other, so an agent given a changed-annotation block had an address it could not use.
    """
    if annotation.anchor is None:
        return None
    from loom.refs.identity import identify, parse
    from loom.scan.bib import BIBLIOGRAPHY, parse_bib

    wid = parse(annotation.target_key)
    if wid is None:
        return None
    try:
        bib = parse_bib((root / BIBLIOGRAPHY).read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    for ck, entry in bib.items():
        if any((w.scheme, w.value) == (wid.scheme, wid.value) for w in identify(entry)):
            return ck
    return None


def annotation_row(root: Path, a: Any) -> dict[str, Any]:
    """One annotation or reply as a message carries it and `loom since` reports it: whole, with the words it is on and what it proposes.

    A page note's target is the work's identifier, which no `loom library` command takes, so the citekey and the page travel with it, as `ai annotations` prints them.
    """
    row: dict[str, Any] = {
        "id": a.id,
        "kind": a.kind,
        "target": a.target_key,
        "work": work_of(root, a),
        "page": a.anchor.page if a.anchor else None,
        "act": "replied" if a.in_reply_to else "created",
        "by": a.author_id,
        "body": a.body,
    }
    if a.selector is not None and a.selector.exact:
        row["quote"] = a.selector.exact
    for field in ("severity", "payload", "placement"):
        if getattr(a, field):
            row[field] = getattr(a, field)
    return row


def pending(root: Path, session: Any, who: str) -> list[dict[str, Any]]:
    """The packet: what `who` wrote in this session since a message last carried any, carried by their next `loom session say` (plan 0.14).

    Only the sender's own annotations and replies go, a person's: an agent's are its own, and sending them back would be telling it what it said. Each is carried whole (`annotation_row`), because the inbox is the record of what was sent.
    """
    from loom.records.annotations import load_records

    # By id rather than by clock: `stamp()` has second resolution, so a message and an annotation written in the same
    # second cannot be ordered by their timestamps, and the first post of a session would drop what prompted it.
    sent = {str(c.get("id", "")) for e in read_events(root, session.id) for c in e.changed}
    since = session.last_opened
    records, _ = load_records(root)
    out: list[dict[str, Any]] = []
    for record in records:
        if record.rel != session.id:
            continue
        for a in record.annotations:
            if a.id in sent or a.created < since or a.status == "discarded" or a.author_kind != "person":
                continue
            if a.author_id == who:
                out.append(annotation_row(root, a))
    return out
