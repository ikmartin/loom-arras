"""Threads for the manifest (specs/manifest.md §10, book 11.4.7): every session, read-only.

One thread per session, which since plan 0.13 §5 is what a run and a day's comments both are. A session the migration made from a run reads its attachments from the run directory those bytes are still in.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loom.ai.layout import MODES
from loom.records.annotations import Record

#: What loom keeps in a session's directory for itself, as opposed to what the session wrote there.
SESSION_FILES = ("run.toml", "run.log", "annotations.json", "inbox.jsonl", "attached.json")
KINDS = {"draft-": "draft", "proposal-": "proposal", "ingest-": "digest", "plan-": "plan"}


def _attachment_kind(name: str) -> str:
    for prefix, kind in KINDS.items():
        if name.startswith(prefix):
            return kind
    if name.endswith(".notes.md"):
        return "notes"
    if name.endswith(".check.py"):
        return "script"
    return "file"


_NOTES = re.compile(r"^(?P<mode>[a-z]+)-(?P<target>.+?)(?:\.(?P<pass>\d+))?\.notes\.md$")


def _pipeline(run_dir: Path, rel: str) -> list[dict[str, Any]]:
    """The modes this run applied, derived from the notes files it wrote (specs/manifest.md §10, plan 0.11 Part A).

    Nothing declares this: a mode writes `<mode>-<target>.notes.md` without exception, so the directory already says which modes ran and against what, and it says so retroactively for runs written before the field existed. The order is the files' own, with a numbered second pass sorted after its first rather than before it -- name order rather than clock order, because a manifest that two builds of one quilt disagree about is worse than one whose sequence is alphabetical. A corpus whose publisher has no modes emits nothing here.
    """
    out: list[dict[str, Any]] = []
    for p in sorted(run_dir.iterdir(), key=lambda q: (q.name.split(".")[0], int(_pass_of(q.name)))):
        m = _NOTES.match(p.name) if p.is_file() else None
        if not m or m.group("mode") not in MODES:
            continue
        entry: dict[str, Any] = {"mode": m.group("mode"), "target": m.group("target"), "report": f"{rel}/{p.name}"}
        if m.group("pass"):
            entry["pass"] = int(m.group("pass"))
        out.append(entry)
    return out


def _pass_of(name: str) -> str:
    m = _NOTES.match(name)
    return (m.group("pass") or "1") if m else "1"


def session_thread(root: Path, session: Any, record: Record | None, run_dir: Path) -> dict[str, Any]:
    """One session as a thread: what it wrote, who took part, what it touched, and its command log. Its conversation is not here: the build pages the transcript separately (`mailbox.pages`)."""
    rel = run_dir.relative_to(root).as_posix() if run_dir.is_relative_to(root) else run_dir.as_posix()
    created = session.created
    participants: list[dict[str, str]] = []
    targets: list[str] = []
    attachments: list[dict[str, Any]] = []
    discarded = session.state != "open"
    if record is not None:
        discarded = discarded or record.discarded
        attachments.append({"name": "annotations", "kind": "annotations", "count": len(record.annotations)})
        for a in record.annotations:
            if a.target_key not in targets:
                targets.append(a.target_key)
            # every party who wrote in the session, which is the point of separating the author from the place
            who = {"kind": "agent" if a.author_kind in ("agent", "run") else "person", "id": a.author_id}
            if who not in participants:
                participants.append(who)
    for p in sorted(run_dir.iterdir()) if run_dir.is_dir() else []:
        if not p.is_file() or p.name in SESSION_FILES:
            continue
        attachments.append({"name": p.name, "kind": _attachment_kind(p.name), "path": f"{rel}/{p.name}"})
    log: list[dict[str, str]] = []
    log_path = run_dir / "run.log"
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^(\S+)\s+(.*)$", line)
            if m:
                log.append({"time": m.group(1), "command": m.group(2)})
    return {
        "id": session.id,
        "kind": "session",
        "title": session.title,
        "created": created,
        "path": rel,
        "participants": participants,
        "targets": targets,
        "attachments": attachments,
        "pipeline": _pipeline(run_dir, rel) if run_dir.is_dir() else [],
        "log": log,
        "discarded": discarded,
    }


def build_threads(root: Path, records: list[Record] | None = None) -> dict[str, Any]:
    """Every session as a thread, keyed by its id."""
    from loom.records.annotations import load_records
    from loom.sessions import files_dir, sessions

    if records is None:
        records, _ = load_records(root)
    by_rel = {r.rel: r for r in records}
    out: dict[str, Any] = {}
    for s in sessions(root).values():
        # a migrated session's annotations still carry the grouping they were written with
        record = by_rel.get(s.id) or (by_rel.get(s.source) if s.source else None)
        where = files_dir(root, s)
        out[s.id] = session_thread(root, s, record, where)
    return out
