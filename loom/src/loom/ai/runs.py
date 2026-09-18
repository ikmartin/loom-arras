"""`loom ai start "NAME"` (book 11.4): a run directory and its `run.toml`.

A run is a chat thread: a directory that is never concluded, named by the author and addressed by that name. `run.toml` records only what nothing can derive — when it was made, what the author called it, and whether it has been discarded. What the run was about is derived from the annotations it made, and which modes it used from the notes files it wrote (DR-150). Loom does not launch the agent: `loom ai init` writes the line in `CLAUDE.md` that tells one what to run, and the author types `claude`.
"""

from __future__ import annotations

import re
from pathlib import Path

from loom.clock import now, stamp

SLUG_MAX = 48


def run_slug(name: str) -> str:
    """A filesystem-safe, truncated form of a run's name, for the directory it lives in."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", (name or "run").strip()).strip("-").lower() or "run"
    return slug[:SLUG_MAX].rstrip("-") or "run"


def run_dir_name(name: str) -> str:
    return f"{now().strftime('%Y-%m-%dT%H-%M')}-{run_slug(name)}"


def start_run(root: Path, name: str | None) -> Path:
    """Create `ai/runs/<timestamp>-<slug>/run.toml` and return the directory; the timestamp leads so the names sort chronologically."""
    name = (name or "run").strip() or "run"
    runs = root / "ai" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    d = runs / run_dir_name(name)
    n = 2
    while d.exists():
        d = runs / f"{run_dir_name(name)}-{n}"
        n += 1
    d.mkdir()
    write_run_toml(d, {"created": stamp(), "name": name, "discarded": "false"})
    return d


def read_run_toml(run_dir: Path) -> dict[str, str]:
    """The flat key = value pairs of a run's run.toml (created, name, discarded).

    A hand-rolled reader rather than tomllib: the file is flat by construction, and a reader that cannot fail keeps a hand-edited run readable.
    """
    p = run_dir / "run.toml"
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def write_run_toml(run_dir: Path, values: dict[str, str]) -> None:
    """Write a run's metadata, quoting every value but the booleans so a name may hold spaces."""
    lines = [f"{k} = {v}" if k == "discarded" else f'{k} = "{v}"' for k, v in values.items()]
    (run_dir / "run.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_name(run_dir: Path) -> str:
    """A run's name: what the author called it, or the directory name for a run that predates names."""
    meta = read_run_toml(run_dir)
    return meta.get("name") or meta.get("slug") or run_dir.name


def rename_run(run_dir: Path, name: str) -> None:
    """Change a run's name in place; the directory keeps the name it was created under, since it is an address."""
    meta = read_run_toml(run_dir)
    meta["name"] = name.strip()
    write_run_toml(run_dir, meta)
