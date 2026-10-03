"""The document workspace: pair, fetch, review, incorporate and publish."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import click

from loom.cli._quilt import open_quilt, quilt_option
from loom.scan.scan import scan
from loom.sync import (
    WORKSPACE,
    Publication,
    SyncError,
    SyncState,
    configure,
    current_selection,
    fetch,
    incoming_patch,
    incorporate,
    publish,
    push_publication,
    source_label,
    summary,
    update_documents,
)


@click.group()
def sync() -> None:
    """Exchange the paper's sources with a document workspace, such as an Overleaf project."""


T = TypeVar("T")


def _run(action: Callable[[], T]) -> T:
    try:
        return action()
    except SyncError as exc:
        raise click.ClickException(str(exc)) from exc


@sync.command("init")
@click.argument("url")
@click.option(
    "--publish-main", default="", help="The main document's path in the workspace, when it differs from the quilt's."
)
@quilt_option
def init_sync(url: str, publish_main: str, quilt_path: str | None) -> None:
    """Pair the quilt with a document workspace, such as an Overleaf project's Git URL.

    Loom clones the workspace into .loom/workspace/ and runs Git only there; the quilt need not be a repository, and its own is never touched.
    """
    quilt = open_quilt(quilt_path)
    state = _run(lambda: configure(quilt, url, publish_main))
    assert isinstance(state, SyncState)
    click.echo(
        f"Paired with {source_label(url)} ({state.branch}) at {state.integrated[:12]}; {state.master} publishes as {state.published_main}"
    )
    from loom.gitignore import missing

    if (quilt.root / ".git").exists() and f"{WORKSPACE}/" in missing(quilt.root):
        click.echo(f"`.gitignore` does not ignore {WORKSPACE}/, loom's clone of the workspace; `loom upgrade` adds it.")


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
    click.echo(f"Document workspace: {report['url']} ({report['branch']})")
    if report["prepared"]:
        click.echo(f"Prepared {str(report['prepared'])[:12]}, stamped as {', '.join(report['prepared_landmarks'])}")
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
    """Change which documents publish to the workspace, without publishing."""
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
        click.echo(f"{verb} {document}; document workspace selection updated (not published)")
    # each document where it is now: the record keeps the paths it was written with (book 4.6)
    main, selected_now = current_selection(state, scan(quilt))
    for selected in selected_now:
        mapped = state.published_main if selected == main else selected
        suffix = " (document workspace main)" if selected == main else ""
        click.echo(f"  {selected} -> {mapped}{suffix}")


@sync.command("patch")
@click.option("--to", type=click.Path(path_type=Path), help="Write the incoming Git patch to a new file.")
@quilt_option
def patch_sync(to: Path | None, quilt_path: str | None) -> None:
    """Print the fetched pull as a patch against the quilt's paths, for reading."""
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


@sync.command("incorporate")
@quilt_option
def incorporate_sync(quilt_path: str | None) -> None:
    """Apply the fetched pull to the quilt's files, stamping first each document it reaches; Incoming does the same."""
    from loom.cli._common import refuse_under_agent

    refuse_under_agent(
        "loom sync incorporate",
        "Incorporating a collaborator's changes is the author's; `loom sync patch` prints them for reading.",
    )
    quilt = open_quilt(quilt_path)
    state = _run(lambda: SyncState.read(quilt.root))
    assert isinstance(state, SyncState)
    pulled = state.incoming
    result = _run(lambda: incorporate(quilt, state))
    assert isinstance(result, dict)
    click.echo(
        f"Incorporated {pulled[:12]} from {source_label(state.url)}: {len(result['paths'])} file(s); mathematics remains to be reviewed"
    )
    for path in result["paths"]:
        click.echo(f"  {path}")
    for landmark in result["landmarks"]:
        click.echo(f"As it was: landmark {landmark}")


@sync.command("publish")
@click.option("--push", is_flag=True, help="Push the prepared revision to the document workspace.")
@quilt_option
def publish_sync(push: bool, quilt_path: str | None) -> None:
    """Prepare the selected documents' sources as a workspace revision, check each compiles, and stamp each as published."""
    if push:
        from loom.cli._common import refuse_under_agent

        refuse_under_agent(
            "loom sync publish --push",
            "Publishing to the document workspace is the author's; without --push this prepares and checks the revision.",
        )
    quilt = open_quilt(quilt_path)
    state = _run(lambda: SyncState.read(quilt.root))
    assert isinstance(state, SyncState)
    label = source_label(state.url)
    publication = _run(lambda: publish(quilt, state))
    assert isinstance(publication, Publication)
    if publication.unchanged:
        click.echo(f"Nothing to publish: {label} already holds these {len(publication.paths)} files")
        return
    verb = "Publishing" if push else "Prepared"
    click.echo(f"{verb} {publication.commit[:12]}: {len(publication.paths)} files for {', '.join(state.documents)}")
    for landmark in publication.landmarks:
        click.echo(f"  {'stamped earlier' if publication.reused else 'stamped'} as landmark {landmark}")
    if push:
        _run(lambda: push_publication(quilt, state, publication.commit))
        click.echo(f"Published to {label}")
    else:
        click.echo(f"{label} unchanged; `loom sync publish --push` sends it")
