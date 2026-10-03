"""The document workspace: pair, fetch, review, incorporate and publish."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import click

from loom.cli._common import ContentError, EnvError
from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.report import Group, Item, Report, counted
from loom.scan.quilt import Quilt
from loom.scan.scan import scan
from loom.sync import (
    WORKSPACE,
    Publication,
    SourceError,
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


#: What marks a refusal as the quilt's own content, which the author fixes in the source (exit 1); every other refusal is the workspace, the pairing or the arguments (exit 2).
def _run(action: Callable[[], T]) -> T:
    """`action()`, its SyncError raised as ContentError when the author fixes it in the source and EnvError otherwise (book 12.1)."""
    try:
        return action()
    except SourceError as exc:
        raise ContentError(str(exc)) from exc
    except SyncError as exc:
        raise EnvError(str(exc)) from exc


def _landmarks(quilt: Quilt, names: list[str]) -> list[str]:
    """Each landmark as text shows it, `DOC@STEP`: its name carries a revision's hash, which stays in the JSON (book 17.9)."""
    from loom.history.ledger import load_history

    history = load_history(quilt.history_dir)
    out = []
    for name in names:
        e = history.landmark(name)
        out.append(f"{Path(str(e.get('in') or '')).stem}@{e.step}" if e is not None and e.step is not None else name)
    return out


def _short(revision: str) -> str:
    """A revision as text shows it: 7 characters, the full one staying in the JSON."""
    return revision[:7]


@sync.command("init")
@click.argument("url")
@click.option(
    "--publish-main", default="", help="The main document's path in the workspace, when it differs from the quilt's."
)
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def init_sync(url: str, publish_main: str, as_json: bool, quilt_path: str | None) -> None:
    """Pair the quilt with a document workspace, such as an Overleaf project's Git URL.

    Loom clones the workspace into .loom/workspace/ and runs Git only there; the quilt need not be a repository, and its own is never touched.
    """
    quilt = open_quilt(quilt_path)
    state = _run(lambda: configure(quilt, url, publish_main))
    assert isinstance(state, SyncState)
    from loom.gitignore import missing

    unignored = (quilt.root / ".git").exists() and f"{WORKSPACE}/" in missing(quilt.root)
    Report(
        f"paired with {source_label(url)} ({state.branch}) at {_short(state.integrated)}; {state.master} publishes as {state.published_main}",
        ok=not unignored,
        groups=[
            Group(
                "warnings",
                [
                    Item(
                        f"`.gitignore` does not ignore {WORKSPACE}/, loom's clone of the workspace",
                        fixes=["loom upgrade"],
                    )
                ],
                problem=True,
            )
        ]
        if unignored
        else [],
        data={
            "url": url,
            "branch": state.branch,
            "integrated": state.integrated,
            "master": state.master,
            "published_main": state.published_main,
            "gitignore_missing": unignored,
        },
    ).emit(as_json)


@sync.command("fetch")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def fetch_sync(as_json: bool, quilt_path: str | None) -> None:
    """Fetch document workspace changes for Incoming review without changing author files."""
    from loom.render.build import build

    quilt = open_quilt(quilt_path)

    def action() -> SyncState:
        return fetch(quilt, SyncState.read(quilt.root))

    state = _run(action)
    assert isinstance(state, SyncState)
    build(quilt)
    label = source_label(state.url)
    data = {
        "incoming": state.incoming,
        "integrated": state.integrated,
        "prepared": state.prepared,
        "observed": state.observed,
    }
    if state.incoming == state.prepared:
        Report(
            f"nothing incoming: {label} holds the publication prepared here, {_short(state.incoming)}", data=data
        ).emit(as_json)
    elif state.incoming == state.integrated:
        Report(f"nothing incoming: {label} is at {_short(state.incoming)}, already incorporated", data=data).emit(
            as_json
        )
    else:
        Report(
            f"fetched {_short(state.incoming)} from {label}, observed {state.observed}; it waits for review in Incoming",
            ok=False,
            groups=[
                Group(
                    "to review",
                    [Item(f"the pull {_short(state.incoming)}", fixes=["loom sync patch", "loom sync incorporate"])],
                )
            ],
            data=data,
        ).emit(as_json)


@sync.command("status")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def status_sync(as_json: bool, quilt_path: str | None) -> None:
    """Show document workspace revisions, selection, and the prepared local ref."""
    quilt = open_quilt(quilt_path)
    report = _run(lambda: summary(quilt, SyncState.read(quilt.root)))
    assert isinstance(report, dict)
    label = source_label(str(report["url"]))
    files = sorted(report["files"], key=lambda f: f["path"])
    incoming, integrated = str(report["incoming"]), str(report["integrated"])
    if incoming != integrated:
        verdict = f"{label} ({report['branch']}): {counted(len(files), 'file')} incoming at {_short(incoming)}, waiting for review"
    else:
        verdict = f"{label} ({report['branch']}): nothing incoming; the quilt has incorporated {_short(integrated)}"
    lines = [
        "",
        f"workspace:   {report['url']}",
        f"integrated:  {_short(integrated)}",
        f"incoming:    {_short(incoming)}",
    ]
    if report["prepared"]:
        lines.append(
            f"prepared:    {_short(str(report['prepared']))}, stamped as {', '.join(_landmarks(quilt, list(report['prepared_landmarks'])))}"
        )
    Report(
        verdict,
        ok=incoming == integrated,
        lines=lines,
        groups=[
            Group("documents that publish", [Item("", key=d) for d in report["documents"]], limit=None),
            *(
                [
                    Group(
                        "incoming files",
                        [Item(f["status"], key=f["path"]) for f in files],
                        limit=None,
                        next="loom sync patch",
                    )
                ]
                if files
                else []
            ),
        ],
        data=report,
    ).emit(as_json)


@sync.command("documents")
@click.argument("action", required=False, type=click.Choice(["add", "remove"]))
@click.argument("document", required=False)
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def documents_sync(action: str | None, document: str | None, as_json: bool, quilt_path: str | None) -> None:
    """Change which documents publish to the workspace, without publishing."""
    quilt = open_quilt(quilt_path)
    state = _run(lambda: SyncState.read(quilt.root))
    assert isinstance(state, SyncState)
    verdict = ""
    if action is None:
        if document is not None:
            raise EnvError("give add or remove before DOCUMENT")
    elif document is None:
        raise EnvError(f"loom sync documents {action} needs DOCUMENT")
    else:
        state = _run(lambda: update_documents(quilt, state, action, document))
        verb = "added" if action == "add" else "removed"
        verdict = f"{verb} {document}; the selection is saved, not published"
    # each document where it is now: the record keeps the paths it was written with (book 4.6)
    main, selected_now = current_selection(state, scan(quilt))
    rows = [{"document": d, "as": state.published_main if d == main else d, "main": d == main} for d in selected_now]
    items = [
        Item(
            f"as {state.published_main if d == main else d}" + (" (document workspace main)" if d == main else ""),
            key=d,
        )
        for d in selected_now
    ]
    Report(
        verdict or f"{counted(len(rows), 'document')} publish to {source_label(state.url)}",
        groups=[Group("documents that publish", items, limit=None, next="loom sync publish" if verdict else None)],
        data={"documents": rows, "action": action, "document": document},
    ).emit(as_json)


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
            raise EnvError(f"{to} exists; refusing to overwrite it")
        to.write_bytes(patch)
        click.echo(f"wrote {to}")


@sync.command("incorporate")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def incorporate_sync(as_json: bool, quilt_path: str | None) -> None:
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
    Report(
        f"incorporated {_short(pulled)} from {source_label(state.url)} into {counted(len(result['paths']), 'file')}; its mathematics remains to be reviewed",
        ok=False,
        groups=[
            Group("files changed", [Item("", key=p) for p in sorted(result["paths"])], limit=None),
            Group(
                "as it was, stamped as landmarks",
                [Item("", key=m) for m in _landmarks(quilt, result["landmarks"])],
                limit=None,
            ),
        ],
        data={"pulled": pulled, **result},
    ).emit(as_json)


@sync.command("publish")
@click.option("--push", is_flag=True, help="Push the prepared revision to the document workspace.")
@click.option("--json", "as_json", is_flag=True)
@quilt_option
def publish_sync(push: bool, as_json: bool, quilt_path: str | None) -> None:
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
    data = {
        "commit": publication.commit,
        "paths": publication.paths,
        "landmarks": publication.landmarks,
        "unchanged": publication.unchanged,
        "reused": publication.reused,
        "pushed": False,
    }
    if publication.unchanged:
        Report(
            f"nothing to publish: {label} already holds these {counted(len(publication.paths), 'file')}", data=data
        ).emit(as_json)
        return
    files = f"{counted(len(publication.paths), 'file')} for {', '.join(state.documents)}"
    stamped = Group(
        "stamped earlier as landmarks" if publication.reused else "stamped as landmarks",
        [Item("", key=m) for m in _landmarks(quilt, publication.landmarks)],
        limit=None,
    )
    if push:
        _run(lambda: push_publication(quilt, state, publication.commit))
        data["pushed"] = True
        Report(f"published {_short(publication.commit)} to {label}: {files}", groups=[stamped], data=data).emit(as_json)
        return
    Report(
        f"prepared {_short(publication.commit)}: {files}; {label} is unchanged until loom sync publish --push sends it",
        ok=False,
        groups=[stamped],
        data=data,
    ).emit(as_json)
