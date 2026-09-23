"""`.loom/sessions/<id>/`: the mailbox a session carries, and who is listening to it (plan 0.13 §8).

**Loom is a mailbox and not an orchestrator.** A message is appended and a parked reader wakes; nothing is launched, no model is called, and no task is assigned. Two attached agents both see everything and neither is handed anything to do, which is the honest behaviour for a tool that is not orchestrating.

**Read, never consumed.** The inbox is append-only and each reader keeps a cursor of its own, so a message survives being read, a second reader sees it too, and an agent that crashed resumes where it was rather than losing the turn.

**A message always lands, even with nobody listening.** It waits in the inbox, and the surface that posted it says whether anyone was there. Refusing would lose what somebody typed, for a reason the browser cannot fix.

Events are sequence-numbered so a reader that missed some knows it missed them: a gap is the signal to resync the coarse way, rather than to stitch a stream back together from the middle.
"""

from __future__ import annotations

import bisect
import fcntl
import json
import os
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import Any

from loom.clock import stamp
from loom.sessions import DIR

INBOX = "inbox.jsonl"
CURSORS = "cursors"
ATTACHED = "attached.json"
#: How long a heartbeat stands before the reader that wrote it is called detached.
STALE = 90.0
#: How often a parked reader's heartbeat is rewritten; well inside STALE, and slow enough that the watcher is not rebuilding the manifest for every beat.
BEAT = 30.0
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


def public(e: Event) -> dict[str, Any]:
    """An event as a viewer reads it: the stored fields, and the body rendered as annotation bodies are."""
    from loom.records.store import render_markdown

    out = e.to_json()
    if e.body:
        out["body_html"] = render_markdown(e.body)
    return out


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


def cursor(root: Path, sid: str, reader: str) -> int:
    """Where this reader had got to, or 0. A cursor is per reader, because the inbox is a broadcast."""
    p = session_dir(root, sid) / CURSORS / f"{_slug(reader)}.txt"
    try:
        return int(p.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def set_cursor(root: Path, sid: str, reader: str, seq: int) -> None:
    p = session_dir(root, sid) / CURSORS / f"{_slug(reader)}.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(seq) + "\n", encoding="utf-8")


def _slug(who: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in who.lower()).strip("-") or "reader"


def attach(root: Path, sid: str, who: str, kind: str = "person") -> None:
    """Record that somebody is listening, with a fresh heartbeat. Called on attaching and on every wake.

    The file is rewritten only when the row is new or its beat is `BEAT` old: `loom serve` watches it, and a rewrite per wake would rebuild the manifest four times a second while an agent is parked.
    """
    d = session_dir(root, sid)
    d.mkdir(parents=True, exist_ok=True)
    rows = {r["who"]: r for r in attached(root, sid, stale=True)}
    prev = rows.get(who)
    if prev and prev.get("kind") == kind and prev.get("pid") == os.getpid() and _age(str(prev.get("beat", ""))) < BEAT:
        return
    rows[who] = {
        "who": who,
        "kind": kind,
        "pid": os.getpid(),
        "beat": stamp(),
        "since": rows.get(who, {}).get("since", stamp()),
    }
    (d / ATTACHED).write_text(json.dumps(list(rows.values()), indent=1, sort_keys=True) + "\n", encoding="utf-8")


def detach(root: Path, sid: str, who: str) -> None:
    """Take a reader out of the list, for a command that is leaving on purpose rather than dying."""
    d = session_dir(root, sid)
    rows = [r for r in attached(root, sid, stale=True) if r.get("who") != who]
    if d.is_dir():
        (d / ATTACHED).write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def waiting_on(root: Path, sid: str, name: str = "") -> str:
    """What to tell somebody who has just posted and nobody was listening.

    Three states, not two. Nobody has ever attached here, and the message waits for whoever comes; somebody *was* attached and their heartbeat has gone quiet, which is what an agent looks like for the whole time it is doing what it was asked, since the beat is written only while parked; or the only reader attached is you.

    The distinction is the one the composer used to get wrong: it told an author whose agent was mid-task that nobody was attached and they should go and start a watcher.
    """
    from datetime import datetime

    live = [r for r in attached(root, sid) if r.get("who") != name]
    if live:
        return ""
    ever = [r for r in attached(root, sid, stale=True) if r.get("who") != name]
    if not ever:
        return f"nobody is attached — it waits in the inbox. Start one with: loom session watch {sid}"
    who = ", ".join(sorted({str(r.get("who", "someone")) for r in ever}))
    when = max((str(r.get("beat", "")) for r in ever), default="")
    mins = ""
    try:
        gap = (datetime.now(UTC) - datetime.fromisoformat(when.replace("Z", "+00:00"))).total_seconds()
        mins = f" {int(gap // 60)} min ago" if gap >= 60 else " moments ago"
    except ValueError:
        pass
    return f"{who} is not listening this second — last here{mins}, probably working. It waits in the inbox and they will see it when they next look."


def _age(when: str) -> float:
    """Seconds since an ISO stamp; infinite for one that does not parse."""
    from datetime import datetime

    try:
        return (datetime.now(UTC) - datetime.fromisoformat(when.replace("Z", "+00:00"))).total_seconds()
    except ValueError:
        return float("inf")


def attached(root: Path, sid: str, *, stale: bool = False) -> list[dict[str, Any]]:
    """Who is listening now.

    A heartbeat older than `STALE` means detached: a reader that was killed writes no farewell, and a list that believed it forever would tell the composer somebody is there when nobody is.
    """
    from datetime import datetime

    p = session_dir(root, sid) / ATTACHED
    if not p.is_file():
        return []
    try:
        rows = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(rows, list):
        return []
    if stale:
        return [r for r in rows if isinstance(r, dict)]
    now = datetime.now(UTC)
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            beat = datetime.fromisoformat(str(r.get("beat", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if (now - beat).total_seconds() <= STALE:
            out.append(r)
    return out


def render(events: list[Event]) -> str:
    """The events as a person or an agent reads them: the same text in the terminal and in `--json`'s `text`.

    One rendering, so a person tailing a session and an agent parked on it are told the same thing in the same words, and a difference between the two surfaces cannot hide a difference in what happened.
    """
    lines: list[str] = []
    for e in events:
        lines.append(f"{e.when[11:16]} {e.who}: {e.body}" if e.kind == "message" else f"{e.when[11:16]} — {e.body}")
        for c in e.changed:
            who = c.get("by", "")
            # what a reader can act on: the citekey and the page for a note on a page, the key otherwise
            where = f"{c['work']} p.{c['page']}" if c.get("work") and c.get("page") else c.get("target", "")
            lines.append(f"  {c.get('id', '')}  {c.get('kind', '')} · {where} · {c.get('act', '')} by {who}")
            if c.get("body"):
                lines.append(f'      "{c["body"]}"')
    return "\n".join(lines)


def work_of(root: Path, annotation: Any) -> str | None:
    """The citekey a page note's target names, or None when the target is a key in the corpus.

    The record stores the work's identifier, which is what two quilts agree on; every `loom refs` command wants the citekey, which is what this machine calls it. Nothing mapped one to the other, so an agent given a changed-annotation block had an address it could not use.
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


def changed_since(root: Path, session: Any) -> list[dict[str, Any]]:
    """The annotations that changed in this session since its last message, carried inline with the next one.

    A post says *what changed*, not only *what was typed*, so a parked agent needs no second call to find out what it is being asked about -- and gets it in the same words `loom session next` prints. Without this, "have another look" arrives with nothing attached and the agent must go and diff the log to learn what moved.

    It lives here rather than beside the write API because **both surfaces post**: `loom session send` and the composer must attach the same thing, and when this was the API's own helper the terminal's messages went out bare.
    """
    from loom.records.annotations import load_records

    # By id rather than by clock: `stamp()` has second resolution, so a message and an annotation written in the same
    # second cannot be ordered by their timestamps, and the first post of a session would drop what prompted it.
    sent = {str(c.get("id", "")) for e in read_events(root, session.id) for c in e.changed}
    since = session.last_opened
    records, _ = load_records(root)
    out: list[dict[str, Any]] = []
    for record in records:
        if record.rel not in (session.id, session.source):
            continue
        for a in record.annotations:
            if a.id in sent or a.created < since or a.status == "discarded":
                continue
            out.append(
                {
                    "id": a.id,
                    "kind": a.kind,
                    "target": a.target_key,
                    # A page note targets the work's identifier, which no `loom refs` command accepts. An agent
                    # handed only that has to find the citekey by trial -- which is what the reading study watched
                    # one do. The citekey and the page travel with it, as `ai findings` prints them.
                    "work": work_of(root, a),
                    "page": a.anchor.page if a.anchor else None,
                    "act": "replied" if a.in_reply_to else "created",
                    "by": a.author_id,
                    "body": a.body,
                }
            )
    return out
