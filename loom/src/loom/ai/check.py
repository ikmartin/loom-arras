"""`loom ai check RUN` (book 11.8): files outside the run, the annotation log, and `build/` modified since the run started."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from loom.ai.runs import read_run_toml

# `annotations/` holds the log every `loom comment --run` appends to, which is the agent's own sanctioned write and
# not a write outside its run; `comments/` is the name that directory had before the log replaced it.
SKIP = {".git", "build", "annotations", ".loom", "node_modules"}


def outside_writes(root: Path, run_dir: Path) -> list[str]:
    meta = read_run_toml(run_dir)
    created = meta.get("created")
    if not created:
        raise ValueError(f"{run_dir} has no run.toml with a created time")
    since = datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
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
        ):  # run.toml records whole seconds; a file written in the run's first second is not the agent's
            out.append(rel.as_posix())
    return out
