"""`loom ai check SESSION` (book 11.8): files outside the session, the annotation log, and `build/` modified since it opened."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loom.sessions import Session, files_dir

# `annotations/` holds the log every `loom comment` appends to, which is the agent's own sanctioned write and not a
# write outside its session. `.loom/` is skipped wholesale, which is where the session's own directory lives.
SKIP = {".git", "build", "annotations", ".loom", "node_modules"}


def outside_writes(root: Path, session: Session) -> list[str]:
    """Files changed since the session's current round opened, outside the places it is allowed to write."""
    run_dir = files_dir(root, session)
    opened = session.last_opened
    if not opened:
        raise ValueError(f"{session.id} has no opening time")
    since = datetime.fromisoformat(opened.replace("Z", "+00:00")).timestamp()
    out: list[str] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP for part in rel.parts[:-1]) or rel.parts[0] in SKIP:
            continue
        if p.is_relative_to(run_dir):
            continue
        if (
            p.stat().st_mtime > since + 1.0
        ):  # the index records whole seconds; a file written in the round's first second is not the agent's
            out.append(rel.as_posix())
    return out
