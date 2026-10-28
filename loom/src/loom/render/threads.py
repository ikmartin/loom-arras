"""Threads for the manifest (specs/manifest.md §10): every session, read-only.

One thread per session; its attachments are the files the session wrote into its own directory.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loom.records.annotations import Record

#: What loom keeps in a session's directory for itself, as opposed to what the session wrote there.
SESSION_FILES = ("run.log", "inbox.jsonl", "attached.json")
_MADE = re.compile(r"^(.*?)\s+→\s+(a-\d{4}-\d{2}-\d{2}-\d+)$")
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
            who = {"kind": "agent" if a.author_kind == "agent" else "person", "id": a.author_id}
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
            if not m:
                continue
            entry = {"time": m.group(1), "command": m.group(2)}
            # `loom annotate` names the annotation it made or changed after an arrow (plan 0.14)
            made = _MADE.match(entry["command"])
            if made:
                entry["command"], entry["annotation"] = made.group(1), made.group(2)
            log.append(entry)
    return {
        "id": session.id,
        "kind": "session",
        "title": session.title,
        "created": created,
        "path": rel,
        "participants": participants,
        "targets": targets,
        "attachments": attachments,
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
        record = by_rel.get(s.id)
        where = files_dir(root, s)
        out[s.id] = session_thread(root, s, record, where)
    return out
