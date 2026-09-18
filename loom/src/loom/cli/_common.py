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


def find_run(root: Path, run: str | None) -> Path:
    """Locate a run by name, by a prefix of its name, or by its path; with nothing, the most recent undiscarded one.

    A run directory is `2026-09-17T01-43-review-main`, so addressing one by path means remembering the minute it started. The name is what the author remembers, so that is what this accepts. An ambiguous prefix names its matches and refuses rather than guessing, as `refs resolve` does with candidates.
    """
    from loom.ai.orient import open_runs

    if run:
        p = resolve_run(root, run)
        if p is not None and p.is_dir():
            return p
        if p is not None and ("/" in run or Path(run).is_absolute()):
            raise EnvError(f'no run at {run}; loom ai start "a name" makes one')
    runs = open_runs(root, include_discarded=True)
    if not run:
        live = [r for r in runs if not r[3]]
        if not live:
            raise EnvError('no runs yet; loom ai start "a name" makes one')
        return root / live[-1][0]
    want = run.strip().lower()

    def slug(rel: str) -> str:
        """The directory's name without its leading timestamp, which is what a person types when they type a path."""
        name = rel.rsplit("/", 1)[-1]
        return name.split("-", 3)[-1] if name[:4].isdigit() else name

    exact = [r for r in runs if r[1].lower() == want or slug(r[0]) == want]
    hits = exact or [r for r in runs if want in r[1].lower() or want in slug(r[0])]
    if not hits:
        raise EnvError(f"no run matches {run!r}; loom ai runs lists them")
    if len(hits) > 1:
        named = "\n".join(f"  {r[2][:10]}: {r[1]}" for r in hits)
        raise EnvError(f"{run!r} matches {len(hits)} runs:\n{named}\ngive more of the name")
    return root / hits[0][0]
