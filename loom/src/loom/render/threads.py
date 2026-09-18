"""Threads for the manifest (specs/manifest.md §10, book 11.4.7): every run under `ai/runs/` and every comment session under `comments/`, read-only."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loom.ai.runs import read_run_toml
from loom.records.annotations import Record

_HEADING = re.compile(r"^##\s+(.*)$", re.M)
_DATE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}):(\d{2}))?")
KINDS = {"bundle-": "bundle", "draft-": "draft", "proposal-": "proposal", "ingest-": "digest", "plan-": "plan"}


def _attachment_kind(name: str) -> str:
    for prefix, kind in KINDS.items():
        if name.startswith(prefix):
            return kind
    if name.endswith(".notes.md"):
        return "notes"
    if name.endswith(".check.py"):
        return "script"
    return "file"


def _messages(thread: str, agent: str, fallback_time: str) -> list[dict[str, Any]]:
    """`thread.md` as messages: one per `##` heading (a dated entry), the text before the first heading as an opening message."""
    from loom.records.store import render_markdown

    out: list[dict[str, Any]] = []
    parts = _HEADING.split(thread)
    intro = parts[0]
    intro = re.sub(r"^#\s+.*$", "", intro, count=1, flags=re.M).strip()
    if intro:
        out.append(
            {"author": {"kind": "agent", "id": agent}, "time": fallback_time, "body_html": render_markdown(intro)}
        )
    for i in range(1, len(parts), 2):
        heading, body = parts[i].strip(), parts[i + 1].strip() if i + 1 < len(parts) else ""
        m = _DATE.search(heading)
        time = fallback_time
        if m:
            time = m.group(1) + (f"T{m.group(2)}:{m.group(3)}:00Z" if m.group(2) else "T00:00:00Z")
        out.append(
            {
                "author": {"kind": "agent", "id": agent},
                "time": time,
                "body_html": render_markdown(f"**{heading}**\n\n{body}" if body else f"**{heading}**"),
            }
        )
    return out


def run_thread(root: Path, run_dir: Path, record: Record | None = None) -> dict[str, Any]:
    meta = read_run_toml(run_dir)
    rel = run_dir.relative_to(root).as_posix()
    agent = meta.get("name") or meta.get("slug") or run_dir.name
    created = meta.get("created", "")
    participants: list[dict[str, str]] = [{"kind": "agent", "id": agent}]
    targets: list[str] = []
    attachments: list[dict[str, Any]] = []
    discarded = meta.get("discarded") == "true"
    if record is not None:
        discarded = discarded or record.discarded
        attachments.append({"name": "annotations", "kind": "annotations", "count": len(record.annotations)})
        for a in record.annotations:
            if a.target_key not in targets:
                targets.append(a.target_key)
            who = {"kind": a.author_kind if a.author_kind != "run" else "agent", "id": a.author_id}
            if a.author_kind == "person" and who not in participants:
                participants.append(who)
    for p in sorted(run_dir.iterdir()):
        if not p.is_file() or p.name in ("run.toml", "run.log", "thread.md", "annotations.json"):
            continue
        attachments.append({"name": p.name, "kind": _attachment_kind(p.name), "path": f"{rel}/{p.name}"})
    thread_text = (run_dir / "thread.md").read_text(encoding="utf-8") if (run_dir / "thread.md").is_file() else ""
    title_m = re.match(r"^#\s+(?:Thread:\s*)?(.+)$", thread_text.strip(), re.M) if thread_text else None
    title = title_m.group(1).strip() if title_m else agent
    log: list[dict[str, str]] = []
    log_path = run_dir / "run.log"
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^(\S+)\s+(.*)$", line)
            if m:
                log.append({"time": m.group(1), "command": m.group(2)})
    return {
        "id": run_dir.name,
        "kind": "run",
        "title": title,
        "created": created,
        "path": rel,
        "participants": participants,
        "targets": targets,
        "messages": _messages(thread_text, agent, created) if thread_text else [],
        "attachments": attachments,
        "log": log,
        "discarded": discarded,
    }


def session_thread(root: Path, record: Record) -> dict[str, Any] | None:
    """A person's annotations as a thread: each one a message, since a comment session has no journal of its own."""
    from loom.records.store import render_markdown

    if not record.annotations:
        return None
    author = record.annotations[0].author_id
    created = min(a.created for a in record.annotations)
    messages = [
        {
            "author": a.author_id,
            "time": a.created,
            "body_html": render_markdown(f"**{a.kind}** on `{a.target_key}`: {a.body}"),
        }
        for a in record.annotations
    ]
    return {
        "id": record.rel,
        "kind": "comments",
        "title": author,
        "created": created,
        "path": record.rel,
        "participants": [{"kind": "person", "id": author}],
        "targets": list(dict.fromkeys(a.target_key for a in record.annotations)),
        "messages": messages,
        "attachments": [],
        "log": [],
        "discarded": record.discarded,
    }


def build_threads(root: Path, records: list[Record] | None = None) -> dict[str, Any]:
    """Every run and every comment session as a thread, keyed by id."""
    from loom.records.annotations import load_records

    if records is None:
        records, _ = load_records(root)
    by_rel = {r.rel: r for r in records}
    out: dict[str, Any] = {}
    runs = root / "ai" / "runs"
    if runs.is_dir():
        for d in sorted(p for p in runs.iterdir() if p.is_dir()):
            t = run_thread(root, d, by_rel.get(d.relative_to(root).as_posix()))
            out[t["id"]] = t
    for rel, rec in by_rel.items():
        if rel.startswith("comments/"):
            st = session_thread(root, rec)
            if st is not None:
                out[st["id"]] = st
    return out
