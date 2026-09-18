"""Shared CLI plumbing: exit codes, JSON output, and the two error classes every command raises.

Exit codes follow the book's 12.1: 0 success, 1 a content problem the author can fix in the source, 2 a usage or environment problem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

EXIT_OK = 0
EXIT_CONTENT = 1
EXIT_USAGE = 2


class ContentError(click.ClickException):
    """A problem in the quilt's content (lint errors, failed identity test, refused write). Exit 1."""

    exit_code = EXIT_CONTENT

    def format_message(self) -> str:
        return self.message


class EnvError(click.ClickException):
    """A usage or environment problem (bad arguments, missing tool, no author name). Exit 2."""

    exit_code = EXIT_USAGE

    def format_message(self) -> str:
        return self.message


def emit_json(obj: Any) -> None:
    """Print one JSON document to stdout and nothing else there; diagnostics go to stderr."""
    click.echo(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def note(message: str) -> None:
    """Progress or diagnostic text, always on stderr so --json stdout stays clean."""
    click.echo(message, err=True)


def resolve_run(root: Path, run_dir: str | None) -> Path | None:
    """A `--run` directory as a path: absolute as given, otherwise relative to the quilt root (never to the shell's cwd), so `--run ai/runs/x` means the quilt's run from any directory.

    See Also
    --------
    find_run : the same, but accepting a run's name or a prefix of it.
    """
    if not run_dir:
        return None
    p = Path(run_dir).expanduser()
    return p if p.is_absolute() else root / p


def under_runs(root: Path, p: Path) -> bool:
    """Whether a resolved `--run` path is inside `ai/runs/`, which is the only place an agent may write."""
    try:
        return p.resolve().is_relative_to((root / "ai" / "runs").resolve())
    except (OSError, ValueError):
        return False


def find_run(root: Path, run: str | None) -> Path:
    """Locate a run by name, by a prefix of its name, or by its path; with nothing, the most recent undiscarded one.

    A run directory is `2026-09-17T01-43-review-main`, so addressing one by path means remembering the minute it started. The name is what the author remembers, so that is what this accepts. An ambiguous prefix names its matches and refuses rather than guessing, as `refs resolve` does with candidates.

    **Names are matched before paths, and a path must be under `ai/runs/`.** Both orderings used to be the other way round, and the consequence was severe: an unmatched `--run` was created as a directory at the quilt root, and that directory then satisfied the path test on every later command, so the run the author had named was never reached and every annotation was filed under a run that did not exist.
    """
    from loom.ai.orient import open_runs

    runs = open_runs(root, include_discarded=True)
    if not run:
        live = [r for r in runs if not r[3]]
        if not live:
            raise EnvError('no runs yet; loom ai start "a name" makes one')
        return root / live[-1][0]
    if not runs:
        raise EnvError('no runs yet; loom ai start "a name" makes one')

    want = run.strip().strip("/").lower()

    def spellings(rel: str, name: str) -> tuple[str, ...]:
        """Every way of writing this run: its name, its directory, the directory without its leading timestamp, and the path."""
        dirname = rel.rsplit("/", 1)[-1]
        slug = dirname.split("-", 4)[-1] if dirname[:4].isdigit() else dirname
        return (name.lower(), dirname.lower(), slug.lower(), rel.lower())

    exact = [r for r in runs if want in spellings(r[0], r[1])]
    hits = exact or [r for r in runs if any(want in s for s in spellings(r[0], r[1]))]
    if len(hits) > 1:
        named = "\n".join(f"  {r[2][:10]}: {r[1]}" for r in hits)
        raise EnvError(f"{run!r} matches {len(hits)} runs:\n{named}\ngive more of the name")
    if hits:
        return root / hits[0][0]

    # Only then a path, and only one that exists inside ai/runs/. Nothing here creates a directory.
    p = resolve_run(root, run)
    if p is not None and p.is_dir() and under_runs(root, p):
        return p
    if p is not None and p.is_dir():
        raise EnvError(f"{run} is not under ai/runs/; an agent writes only in its own run directory")
    raise EnvError(f"no run matches {run!r}; loom ai runs lists them")
