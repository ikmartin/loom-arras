"""Explicit source-only Git sync; local Arras may incorporate a reviewed pull."""

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
    update_documents,
)


@click.group()
def sync() -> None:
    """Prepare and review a source-only document workspace; the quilt uses ordinary Git."""


T = TypeVar("T")


def _run(action: Callable[[], T]) -> T:
    try:
        return action()
    except SyncError as exc:
        raise click.ClickException(str(exc)) from exc


@sync.command("init")
@click.option("--remote", default="origin", show_default=True)
@click.option("--branch", default="main", show_default=True)
@click.option(
    "--publish-main", default="", help="Document workspace main TeX path when it differs from the quilt master."
)
@quilt_option
def init_sync(remote: str, branch: str, publish_main: str, quilt_path: str | None) -> None:
    """Configure the document workspace for this quilt's selected documents."""
    quilt = open_quilt(quilt_path)
    state = _run(lambda: configure(quilt, remote, branch, publish_main))
    assert isinstance(state, SyncState)
    click.echo(
        f"Document workspace: {remote}/{branch} at {state.integrated[:12]}; {state.master} -> {state.published_main}"
    )


@sync.command("fetch")
@quilt_option
def fetch_sync(quilt_path: str | None) -> None:
    """Fetch document workspace changes for Incoming review without changing author files."""
    from loom.render.build import build

    quilt = open_quilt(quilt_path)

    def action() -> SyncState:
        return fetch(quilt, SyncState.read(quilt.root))

    state = _run(action)
    assert isinstance(state, SyncState)
    build(quilt)
    if state.incoming == state.prepared:
        click.echo(f"Document workspace publication {state.incoming[:12]} recognized; no incoming changes")
    elif state.incoming == state.integrated:
        click.echo(f"Document workspace {state.incoming[:12]}; no incoming changes")
    else:
        click.echo(f"Document workspace incoming {state.incoming[:12]} observed {state.observed}; review updated")


@sync.command("status")
@quilt_option
def status_sync(quilt_path: str | None) -> None:
    """Show document workspace revisions, selection, and the prepared local ref."""
    quilt = open_quilt(quilt_path)
    report = _run(lambda: summary(quilt, SyncState.read(quilt.root)))
    assert isinstance(report, dict)
    click.echo(f"Document workspace: {report['remote']}/{report['branch']}")
    if report["prepared"]:
        click.echo(f"Prepared {str(report['prepared'])[:12]} at {report['publication_ref']}")
        click.echo(f"From quilt commit {report['prepared_from']}")
    for document in report["documents"]:
        click.echo(f"  {document}")
    click.echo(f"integrated {str(report['integrated'])[:12]}")
    click.echo(f"incoming   {str(report['incoming'])[:12]}")
    for file in report["files"]:
        click.echo(f"  {file['status']} {file['path']}")


@sync.command("documents")
@click.argument("action", required=False, type=click.Choice(["add", "remove"]))
@click.argument("document", required=False)
@quilt_option
def documents_sync(action: str | None, document: str | None, quilt_path: str | None) -> None:
    """Change the persistent document workspace selection without staging, committing, or publishing."""
    quilt = open_quilt(quilt_path)
    state = _run(lambda: SyncState.read(quilt.root))
    assert isinstance(state, SyncState)
    if action is None:
        if document is not None:
            raise click.ClickException("give add or remove before DOCUMENT")
    elif document is None:
        raise click.ClickException(f"loom sync documents {action} needs DOCUMENT")
    else:
        state = _run(lambda: update_documents(quilt, state, action, document))
        verb = "added" if action == "add" else "removed"
        click.echo(f"{verb} {document}; document workspace selection updated (not staged, committed, or published)")
    for selected in state.documents or [state.master]:
        mapped = state.published_main if selected == state.master else selected
        suffix = " (document workspace main)" if selected == state.master else ""
        click.echo(f"  {selected} -> {mapped}{suffix}")


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
@quilt_option
def publish_sync(quilt_path: str | None) -> None:
    """Build and compile the committed document workspace projection locally."""
    quilt = open_quilt(quilt_path)
    state = _run(lambda: SyncState.read(quilt.root))
    commit, paths = _run(lambda: publish(quilt, state))
    click.echo(f"Prepared document workspace revision {commit[:12]}")
    click.echo(f"Local ref: {state.publication_ref}")
    click.echo(f"From quilt commit: {state.prepared_from}")
    click.echo("Documents:")
    for document in state.documents:
        click.echo(f"  {document}")
    click.echo(f"Files: {len(paths)}")
    click.echo("Remote unchanged")
