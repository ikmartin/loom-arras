"""`.loom/sessions/`: where work belongs, as distinct from who did it (plan 0.13 §5, book 11).

A **session** is a stretch of work on the quilt -- a sitting, a review, a thread with an agent -- and it is what an annotation belongs to. An **author** is who wrote the thing. Loom conflated the two: an agent's annotation recorded the run directory as its author, so the log could say *who* only by naming a place, and a person and an agent working the same afternoon had no way to say they were doing one job.

Two facts are kept, and they are different kinds of fact. The **id** is `s-YYYY-MM-DD-NNNN`, is minted once and never changes, and is what a record, a URL and a directory name use. The **title** is what a person calls it, changes whenever they like, and is never an address.

The index is append-only, like every other record loom keeps: `created`, `renamed`, `resumed`, `closed`, `deleted`, replayed into the state that stands. A **round** is the span between an opening and the next close or resume, which is what "changed since last time" means. Deleting writes a tombstone and removes nothing; `loom session delete --purge` is the separate, louder act that really erases.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.clock import stamp

DIR = ".loom/sessions"
INDEX = f"{DIR}/index.jsonl"
#: The one session new work lands in, named here so the CLI and the viewer cannot disagree about which it is.
ACTIVE = f"{DIR}/active"

EVENTS = ("created", "renamed", "purposed", "resumed", "closed", "deleted")
ID = re.compile(r"^s-\d{4}-\d{2}-\d{2}-\d{4}$")


@dataclass
class Round:
    """One stretch of work: opened when the session was created or resumed, closed by the next close or resume."""

    opened: str
    closed: str = ""


@dataclass
class Session:
    """A session as the index leaves it."""

    id: str
    title: str
    created: str
    #: `open`, `closed`, or `deleted` -- a tombstone, which hides the session and keeps what was written in it.
    state: str = "open"
    rounds: list[Round] = field(default_factory=list)
    #: What the sitting is for, in the author's words -- a line under the title, not a second name (plan 0.13.1).
    purpose: str = ""
    #: For a session made by the migration: the run directory or comment grouping its annotations still carry.
    source: str = ""

    @property
    def last_opened(self) -> str:
        return self.rounds[-1].opened if self.rounds else self.created

    def directory(self, root: Path) -> Path:
        """Where the session's own files live; made when it first has something to put there, never before."""
        return root / DIR / self.id


def index_path(root: Path) -> Path:
    return root / INDEX


def load_events(root: Path) -> list[dict[str, Any]]:
    """Every session event ever appended, in order; an absent index reads as none and a malformed line is skipped."""
    p = index_path(root)
    if not p.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("event") in EVENTS and event.get("id"):
            out.append(event)
    return out


def append_event(root: Path, event: dict[str, Any]) -> None:
    """Append one event; opened for append so two writers interleave lines rather than losing one."""
    p = index_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def sessions(root: Path, *, deleted: bool = False) -> dict[str, Session]:
    """Every session the index leaves standing, in the order they were created.

    Parameters
    ----------
    root : Path
        The quilt.
    deleted : bool, default False
        Include tombstoned sessions, which are otherwise absent.

    Returns
    -------
    dict of str to Session
        Keyed by id.
    """
    out: dict[str, Session] = {}
    for e in load_events(root):
        sid, when = str(e["id"]), str(e.get("when", ""))
        kind = str(e["event"])
        if kind == "created":
            out[sid] = Session(
                id=sid,
                title=str(e.get("title", "")),
                created=when,
                rounds=[Round(opened=when)],
                purpose=str(e.get("purpose", "")),
                source=str(e.get("source", "")),
            )
            continue
        s = out.get(sid)
        if s is None:
            continue
        if kind == "renamed":
            s.title = str(e.get("title", s.title))
        elif kind == "purposed":
            s.purpose = str(e.get("purpose", ""))
        elif kind == "closed":
            s.state = "closed"
            if s.rounds and not s.rounds[-1].closed:
                s.rounds[-1].closed = when
        elif kind == "resumed":
            s.state = "open"
            if s.rounds and not s.rounds[-1].closed:
                s.rounds[-1].closed = when
            s.rounds.append(Round(opened=when))
        elif kind == "deleted":
            s.state = "deleted"
            if s.rounds and not s.rounds[-1].closed:
                s.rounds[-1].closed = when
    return {k: v for k, v in out.items() if deleted or v.state != "deleted"}


def next_id(root: Path, date: str) -> str:
    """The next `s-<date>-<nnnn>`, counted over every session the index has ever named, tombstones included."""
    n = 0
    prefix = f"s-{date}-"
    for e in load_events(root):
        sid = str(e["id"])
        if sid.startswith(prefix):
            try:
                n = max(n, int(sid[len(prefix) :]))
            except ValueError:
                continue
    return f"{prefix}{n + 1:04d}"


def create(root: Path, title: str, who: str, *, purpose: str = "", source: str = "") -> Session:
    """Mint a session and return it; the directory is not made until something is written into it.

    Parameters
    ----------
    root : Path
        The quilt.
    title : str
        What to call it; may be changed later and is never an address.
    who : str
        The author creating it.
    purpose : str, default ''
        What the sitting is for; shown under the title and changed later with `purposed`.
    source : str, default ''
        For the migration: the run directory or comment grouping whose annotations belong to this session.

    Returns
    -------
    Session
    """
    when = stamp()
    sid = next_id(root, when[:10])
    append_event(
        root,
        {"event": "created", "id": sid, "title": title, "who": who, "when": when}
        | ({"purpose": purpose} if purpose else {})
        | ({"source": source} if source else {}),
    )
    return sessions(root)[sid]


def _event(root: Path, kind: str, sid: str, who: str, **extra: Any) -> None:
    append_event(root, {"event": kind, "id": sid, "who": who, "when": stamp(), **extra})


def rename(root: Path, sid: str, title: str, who: str) -> None:
    """Change what a session is called. Nothing on disk moves: the directory is named by the id, which is an address."""
    _event(root, "renamed", sid, who, title=title)


def purpose(root: Path, sid: str, text: str, who: str) -> None:
    """Say what the sitting is for, or clear it with ''. An event rather than a field, so the index stays a log."""
    _event(root, "purposed", sid, who, purpose=text)


def close(root: Path, sid: str, who: str) -> None:
    """End the current round. A closed session keeps everything written in it and stops taking new work."""
    _event(root, "closed", sid, who)


def resume(root: Path, sid: str, who: str) -> None:
    """Open a new round on a session, which is what "changed since last time" is measured from."""
    _event(root, "resumed", sid, who)


def delete(root: Path, sid: str, who: str, why: str = "") -> None:
    """Tombstone a session: it leaves the viewer, and the log keeps every annotation written in it."""
    _event(root, "deleted", sid, who, **({"why": why} if why else {}))


def active(root: Path) -> str | None:
    """The session new work lands in, or None when there is none."""
    p = root / ACTIVE
    try:
        sid = p.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return sid if sid and ID.match(sid) else None


def set_active(root: Path, sid: str | None) -> None:
    """Make one session the active one, or clear it. Written as a file rather than an event: this is a pointer, not history."""
    p = root / ACTIVE
    p.parent.mkdir(parents=True, exist_ok=True)
    if sid is None:
        p.unlink(missing_ok=True)
        return
    p.write_text(sid + "\n", encoding="utf-8")


def ensure_active(root: Path, who: str, title: str = "") -> Session:
    """The active session, creating one if nothing is active.

    Annotating with no session open is the common case on a first sitting, and refusing it would make the first comment of the day a two-command ritual. A person and an agent are treated alike here (plan 0.13 §5).
    """
    sid = active(root)
    standing = sessions(root)
    if sid and sid in standing:
        return standing[sid]
    s = create(root, title or f"session of {stamp()[:10]}", who)
    set_active(root, s.id)
    return s


def resolve(root: Path, needle: str) -> Session | None:
    """A session by id, by title, or by a unique id suffix; None when nothing or more than one matches.

    See Also
    --------
    loom.cli._common.find_session : the same, refusing with the matches named rather than returning None.
    """
    standing = sessions(root, deleted=True)
    if needle in standing:
        return standing[needle]
    want = needle.strip().lower()
    for pick in (
        lambda s: s.title.lower() == want,
        lambda s: s.id.endswith(want),
        lambda s: want in s.title.lower(),
    ):
        hits = [s for s in standing.values() if pick(s)]
        if hits:
            return hits[0] if len(hits) == 1 else None
    return None


def by_source(root: Path) -> dict[str, str]:
    """Which session each pre-session grouping belongs to: `ai/runs/<dir>` or `comments/<who>/<date>` to a session id."""
    return {s.source: s.id for s in sessions(root, deleted=True).values() if s.source}


def migrate(root: Path, who: str) -> list[Session]:
    """Give every run and every day's comments a session, and return the ones this call made.

    Nothing in `annotations/log.jsonl` is rewritten -- it is append-only and this is not an exception. Each session records the grouping its annotations already carry as its `source`, and an annotation's session is read through that. A run that was discarded becomes a closed session; a run still going becomes an open one.

    Parameters
    ----------
    root : Path
        The quilt.
    who : str
        Who ran the migration; recorded as the author of the events it writes.

    Returns
    -------
    list of Session
        Sessions made by this call, in the order the groupings were found. Empty when there was nothing left to do.
    """
    from loom.ai.runs import RUNS_DIR, read_run_toml, run_name
    from loom.records.annotations import load_records

    known = by_source(root)
    made: list[Session] = []
    runs = root / RUNS_DIR
    if runs.is_dir():
        for d in sorted(p for p in runs.iterdir() if p.is_dir()):
            rel = d.relative_to(root).as_posix()
            if rel in known:
                continue
            meta = read_run_toml(d)
            s = create(root, run_name(d), who, source=rel)
            if str(meta.get("discarded", "")).lower() == "true":
                close(root, s.id, who)
            made.append(s)
            known[rel] = s.id
    records, _ = load_records(root)
    for rec in sorted(records, key=lambda r: r.rel):
        if not rec.rel.startswith("comments/") or rec.rel in known:
            continue
        # `comments/<author>/<date>`: the day's work by one person, which is the session they would have opened
        parts = rec.rel.split("/")
        title = f"{parts[1]}, {parts[2]}" if len(parts) > 2 else rec.rel
        s = create(root, title, who, source=rec.rel)
        close(root, s.id, who)
        made.append(s)
        known[rec.rel] = s.id
    return made


def files_dir(root: Path, s: Session) -> Path:
    """Where a session's own files are -- its notes, its thread, its command log.

    `.loom/sessions/<id>/`, except for a session the migration made from a run, whose files are still in the run directory the agent wrote them to. Nothing is moved: the run directory is where those bytes are, and a record that points somewhere they are not is worse than an inconsistent path.
    """
    own = s.directory(root)
    if own.is_dir():
        return own
    if s.source and s.source.startswith("ai/runs/") and (root / s.source).is_dir():
        return root / s.source
    return own
