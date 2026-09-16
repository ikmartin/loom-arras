"""`loom ai start [SLUG]` (book 11.4): a run directory, its `run.toml`, and the optional agent launch."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from loom.clock import now, stamp


def run_dir_name(slug: str) -> str:
    return f"{now().strftime('%Y-%m-%dT%H-%M')}-{slug}"


def start_run(root: Path, slug: str | None, agent: str | None = None) -> Path:
    """Create `ai/runs/<timestamp>-<slug>/run.toml` (with the agent's name when one is configured) and return the directory."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", (slug or "run").strip()).strip("-") or "run"
    runs = root / "ai" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    d = runs / run_dir_name(slug)
    n = 2
    while d.exists():
        d = runs / f"{run_dir_name(slug)}-{n}"
        n += 1
    d.mkdir()
    lines = [f"created = {stamp()}", f'slug = "{slug}"', "discarded = false"]
    if agent:
        lines.append(f'agent = "{Path(shlex.split(agent)[0]).name}"')
    (d / "run.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return d


def launch_prompt(run_rel: str) -> str:
    return (
        f"This directory is a quilt managed by loom. Run `loom ai orient --run {run_rel}` and follow it; "
        f"your run directory is {run_rel} and it is the only place you write files."
    )


def launch_agent(root: Path, agent: str, run_dir: Path) -> int:
    """Run the configured agent command in the quilt root with the orientation pointer as its prompt; LOOM_RUN is set for it."""
    argv = shlex.split(agent)
    if not argv:
        raise FileNotFoundError("[ai] agent is empty")
    exe = shutil.which(argv[0])
    if exe is None:
        raise FileNotFoundError(argv[0])
    rel = run_dir.relative_to(root).as_posix()
    env = dict(os.environ)
    env["LOOM_RUN"] = rel
    proc = subprocess.run([exe, *argv[1:], launch_prompt(rel)], cwd=root, env=env, check=False)
    return proc.returncode


def read_run_toml(run_dir: Path) -> dict[str, str]:
    """The flat key = value pairs of a run's run.toml (created, slug, discarded, agent, session)."""
    p = run_dir / "run.toml"
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out
