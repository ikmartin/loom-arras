"""Explicit source-only Git sync; Arras reads the resulting review but writes no source."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import click

from loom.cli._quilt import open_quilt, quilt_option
from loom.sync import (
    SyncError,
    SyncState,
    configure,
    fetch,
    finish_incorporation,
    incoming_patch,
    mark_incorporated,
    prepare_incorporation,
    publish,
    summary,
)


@click.group()
def sync() -> None:
    """Fetch and publish the document source through a Git remote."""


T = TypeVar("T")


def _run(action: Callable[[], T]) -> T:
    try:
        return action()
    except SyncError as exc:
        raise click.ClickException(str(exc)) from exc


@sync.command("init")
@click.option("--remote", default="origin", show_default=True)
@click.option("--branch", default="main", show_default=True)
@click.option("--publish-main", default="", help="Overleaf's main TeX path when it differs from the quilt master.")
@quilt_option
def init_sync(remote: str, branch: str, publish_main: str, quilt_path: str | None) -> None:
    """Pair the current Overleaf revision with this quilt's drafting master."""
    quilt = open_quilt(quilt_path)
    state = _run(lambda: configure(quilt, remote, branch, publish_main))
    assert isinstance(state, SyncState)
    click.echo(f"source sync: {remote}/{branch} at {state.integrated[:12]}; {state.master} -> {state.published_main}")


@sync.command("fetch")
@quilt_option
def fetch_sync(quilt_path: str | None) -> None:
    """Fetch Overleaf without changing author files, then publish Incoming review."""
    from loom.render.build import build

    quilt = open_quilt(quilt_path)

    def action() -> SyncState:
        return fetch(quilt, SyncState.read(quilt.root))

    state = _run(action)
    assert isinstance(state, SyncState)
    build(quilt)
    click.echo(f"incoming {state.incoming[:12]} observed {state.observed}; review updated")


@sync.command("status")
@quilt_option
def status_sync(quilt_path: str | None) -> None:
    """Show the integrated and incoming source revisions."""
    quilt = open_quilt(quilt_path)
    report = _run(lambda: summary(quilt, SyncState.read(quilt.root)))
    assert isinstance(report, dict)
    click.echo(f"integrated {str(report['integrated'])[:12]}")
    click.echo(f"incoming   {str(report['incoming'])[:12]}")
    for file in report["files"]:
        click.echo(f"  {file['status']} {file['path']}")


@sync.command("patch")
@click.option("--to", type=click.Path(path_type=Path), help="Write the incoming Git patch to a new file.")
@quilt_option
def patch_sync(to: Path | None, quilt_path: str | None) -> None:
    """Print a patch for the author to inspect and apply in the editor."""
    quilt = open_quilt(quilt_path)
    patch = _run(lambda: incoming_patch(quilt, SyncState.read(quilt.root)))
    assert isinstance(patch, bytes)
    if to is None:
        sys.stdout.buffer.write(patch)
    else:
        if to.exists():
            raise click.ClickException(f"{to} exists; refusing to overwrite it")
        to.write_bytes(patch)
        click.echo(f"wrote {to}")


@sync.command("incorporated")
@click.option("--yes", is_flag=True, help="Confirm that the incoming source was applied and committed.")
@quilt_option
def incorporated_sync(yes: bool, quilt_path: str | None) -> None:
    """Record that the author has incorporated a pull; accept no mathematics."""
    if not yes:
        click.confirm("Have you applied and committed the whole incoming source update?", abort=True)
    quilt = open_quilt(quilt_path)
    state = _run(lambda: mark_incorporated(quilt, SyncState.read(quilt.root)))
    assert isinstance(state, SyncState)
    click.echo(f"source incorporated through {state.integrated[:12]}; mathematical acceptances unchanged")


@sync.command("prepare")
@quilt_option
def prepare_sync(quilt_path: str | None) -> None:
    """Prepare a pinned patch for the author to apply with Git."""
    quilt = open_quilt(quilt_path)
    prepared = _run(lambda: prepare_incorporation(quilt, SyncState.read(quilt.root)))
    click.echo(f"in {prepared['root']}: git apply '{prepared['patch']}'")


@sync.command("finish")
@quilt_option
def finish_sync(quilt_path: str | None) -> None:
    """Verify the author's Git application and commit the source and sync record."""
    quilt = open_quilt(quilt_path)
    result = _run(lambda: finish_incorporation(quilt, SyncState.read(quilt.root)))
    click.echo(f"incorporated {result['integrated'][:12]} in local source commit {result['source_commit'][:12]}")


@sync.command("publish")
@click.option("--push", is_flag=True, help="Push the checked source-only commit to Overleaf.")
@quilt_option
def publish_sync(push: bool, quilt_path: str | None) -> None:
    """Project committed LaTeX inputs onto the Overleaf branch and check compilation."""
    quilt = open_quilt(quilt_path)
    result = _run(lambda: publish(quilt, SyncState.read(quilt.root), push=push))
    assert isinstance(result, tuple)
    commit, paths = result
    click.echo(f"source-only commit {commit[:12]} ({len(paths)} files){' pushed' if push else '; pass --push to send'}")
    for path in paths:
        click.echo(f"  {path}")
