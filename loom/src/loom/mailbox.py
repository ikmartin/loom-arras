"""`.loom/sessions/<id>/`: the mailbox a session carries, and who is listening to it (plan 0.13 §8).

**Loom is a mailbox and not an orchestrator.** A message is appended and a parked reader wakes; nothing is launched, no model is called, and no task is assigned. Two attached agents both see everything and neither is handed anything to do, which is the honest behaviour for a tool that is not orchestrating.

**Read, never consumed.** The inbox is append-only and each reader keeps a cursor of its own, so a message survives being read, a second reader sees it too, and an agent that crashed resumes where it was rather than losing the turn.

**A message always lands, even with nobody listening.** It waits in the inbox, and the surface that posted it says whether anyone was there. Refusing would lose what somebody typed, for a reason the browser cannot fix.

Events are sequence-numbered so a reader that missed some knows it missed them: a gap is the signal to resync the coarse way, rather than to stitch a stream back together from the middle.
"""

from __future__ import annotations

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


def read_events(root: Path, sid: str, since: int = 0) -> list[Event]:
    """Every event after `since`, in order; a malformed line is skipped rather than stopping the rest."""
    p = inbox_path(root, sid)
    if not p.is_file():
        return []
    out: list[Event] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(e, dict) or int(e.get("seq", 0)) <= since:
            continue
        out.append(
            Event(
                seq=int(e.get("seq", 0)),
                kind=str(e.get("kind", "message")),
                who=str(e.get("who", "")),
                when=str(e.get("when", "")),
                body=str(e.get("body", "")),
                changed=[c for c in e.get("changed", []) if isinstance(c, dict)],
            )
        )
    return out


def last_seq(root: Path, sid: str) -> int:
    events = read_events(root, sid)
    return events[-1].seq if events else 0


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
        Annotations changed alongside it, carried inline so a reader needs no second call.

    Returns
    -------
    Event
    """
    d = session_dir(root, sid)
    d.mkdir(parents=True, exist_ok=True)
    e = Event(seq=last_seq(root, sid) + 1, kind=kind, who=who, when=stamp(), body=body, changed=changed or [])
    with inbox_path(root, sid).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(e.to_json(), ensure_ascii=False, sort_keys=True) + "\n")
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
    """Record that somebody is listening, with a fresh heartbeat. Called on attaching and on every wake."""
    d = session_dir(root, sid)
    d.mkdir(parents=True, exist_ok=True)
    rows = {r["who"]: r for r in attached(root, sid, stale=True)}
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
            lines.append(
                f"  {c.get('id', '')}  {c.get('kind', '')} · {c.get('target', '')} · {c.get('act', '')} by {who}"
            )
            if c.get("body"):
                lines.append(f'      "{c["body"]}"')
    return "\n".join(lines)
