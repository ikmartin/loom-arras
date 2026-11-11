"""Threads for the manifest (specs/manifest.md §10): every session, read-only.

One thread per session; its attachments are the files the session wrote into its own directory.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loom.records.annotations import Record
from loom.records.ids import ANNOTATION

if TYPE_CHECKING:
    from loom.scan.scan import ScanResult

#: What loom keeps in a session's directory for itself, as opposed to what the session wrote there.
SESSION_FILES = ("run.log", "inbox.jsonl")
_MADE = re.compile(rf"^(.*?)\s+→\s+({ANNOTATION})$")
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


def names(command: str, result: ScanResult | None) -> list[dict[str, str]]:
    """The keys and files a logged command names, each once: a word the quilt knows as a key, or a path to a file or document, a document under where it is now when it has moved since. A word naming nothing in the quilt is left out; nothing is read from the command's verb."""
    if result is None:
        return []
    out: list[dict[str, str]] = []
    for word in command.split()[1:]:
        w = word.strip("\"'`,;()[]")
        if not w or w.startswith("-"):
            continue
        entry: dict[str, str] | None = None
        now = result.current_document(w) if "/" in w or "." in w else None
        if now is not None:
            entry = {"path": now}
        elif w in result.nodes:
            entry = {"key": w}
        elif ("/" in w or "." in w) and (w in result.files or (result.quilt.root / w).is_file()):
            entry = {"path": w}
        if entry is not None and entry not in out:
            out.append(entry)
    return out


def session_thread(
    root: Path, session: Any, record: Record | None, run_dir: Path, result: ScanResult | None = None
) -> dict[str, Any]:
    """One session as a thread: what it wrote, who took part, what it touched, and its command log, each line with what it names (`names`) when a scan is given. Its conversation is not here: the build pages the transcript separately (`mailbox.pages`)."""
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
    log: list[dict[str, Any]] = []
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
            named = names(entry["command"], result)
            log.append({**entry, "names": named} if named else entry)
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


def build_threads(root: Path, records: list[Record] | None = None, result: ScanResult | None = None) -> dict[str, Any]:
    """Every session as a thread, keyed by its id, oldest first; with a scan, each log line says what it names."""
    from loom.records.annotations import load_records
    from loom.sessions import files_dir, sessions

    if records is None:
        records, _ = load_records(root)
    by_rel = {r.rel: r for r in records}
    out: dict[str, Any] = {}
    for s in sorted(sessions(root).values(), key=lambda s: s.created):
        record = by_rel.get(s.id)
        where = files_dir(root, s)
        out[s.id] = session_thread(root, s, record, where, result)
    return out


def last_active(root: Path, sid: str, manifest: dict[str, Any]) -> str:
    """When session `sid` was last written in: the newest of its logged commands, the annotations and notes written in it, and its transcript's last message; '' when nothing was. Read from the manifest as built, and the transcript's end."""
    from loom.mailbox import last_event

    times = [e["time"] for e in (manifest.get("threads", {}).get(sid) or {}).get("log", [])]
    times += [a.get("created") or "" for a in manifest.get("annotations", {}).values() if a.get("run") == sid]
    times += [n.get("when") or "" for n in (manifest.get("notes") or {}).values() if n.get("session") == sid]
    said = last_event(root, sid)
    if said is not None:
        times.append(said.when)
    return max((t for t in times if t), default="")
