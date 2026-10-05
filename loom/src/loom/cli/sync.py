"""The document workspace: pair, fetch, review, incorporate and publish."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import click

from loom.cli._common import ContentError, EnvError, destination
from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.help import CommandGroup
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


@click.group(cls=CommandGroup)
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
@click.option("--dry-run", is_flag=True, help="Say what would change and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def init_sync(url: str, publish_main: str, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Pair the quilt with a document workspace, such as an Overleaf project's Git URL.

    Loom clones the workspace into .loom/workspace/ and runs Git only there; the quilt need not be a repository, and its own is never touched. A URL that is a remote of the quilt's own repository is refused, and `publish --push` refuses a workspace that holds a quilt.
    """
    quilt = open_quilt(quilt_path)
    state = _run(lambda: configure(quilt, url, publish_main, write=not dry_run))
    assert isinstance(state, SyncState)
    from loom.gitignore import missing

    unignored = (quilt.root / ".git").exists() and f"{WORKSPACE}/" in missing(quilt.root)
    Report(
        f"{'would pair' if dry_run else 'paired'} with {source_label(url)} ({state.branch}) at {_short(state.integrated)}; {state.master} {'would publish' if dry_run else 'publishes'} as {state.published_main}",
        ok=not unignored,
        dry_run=dry_run,
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
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
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
                    [
                        Item(
                            f"the pull {_short(state.incoming)}",
                            fixes=["loom sync status --patch", "loom sync incorporate"],
                        )
                    ],
                )
            ],
            data=data,
        ).emit(as_json)


@sync.command("status")
@click.option("--patch", is_flag=True, help="Print the incoming revision as a patch against the quilt's paths instead.")
@click.option(
    "--to",
    type=click.Path(path_type=Path),
    default=None,
    metavar="FILE",
    help="With --patch, write the patch to FILE, a new file outside the quilt's sources.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def status_sync(patch: bool, to: Path | None, as_json: bool, quilt_path: str | None) -> None:
    """Show the document workspace's revisions, the selection and what is prepared; --patch prints the incoming diff."""
    quilt = open_quilt(quilt_path)
    if to is not None and not patch:
        raise EnvError("--to writes the incoming patch; give --patch with it")
    if patch:
        target = destination(quilt, to) if to is not None else None
        diff = _run(lambda: incoming_patch(quilt, SyncState.read(quilt.root)))
        assert isinstance(diff, bytes)
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(diff)
            Report(f"wrote the incoming patch to {to}", data={"to": str(to), "bytes": len(diff)}).emit(as_json)
        elif as_json:
            text = diff.decode("utf-8", errors="replace")
            Report("the incoming patch" if diff else "nothing incoming", data={"patch": text}).emit(True)
        elif diff:
            sys.stdout.buffer.write(diff)
        else:
            Report("nothing incoming; no patch").emit(False)
        return
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
                        next="loom sync status --patch",
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
@click.option("--dry-run", is_flag=True, help="Say what would change and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def documents_sync(
    action: str | None, document: str | None, dry_run: bool, as_json: bool, quilt_path: str | None
) -> None:
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
        state = _run(lambda: update_documents(quilt, state, action, document, write=not dry_run))
        if dry_run:
            verdict = f"would {action} {document}; nothing saved"
        else:
            verdict = f"{'added' if action == 'add' else 'removed'} {document}; the selection is saved, not published"
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
        dry_run=dry_run and bool(verdict),
        groups=[
            Group(
                "documents that would publish" if dry_run and verdict else "documents that publish",
                items,
                limit=None,
                next="loom sync publish" if verdict and not dry_run else None,
            )
        ],
        data={"documents": rows, "action": action, "document": document},
    ).emit(as_json)


@sync.command("incorporate")
@click.option("--dry-run", is_flag=True, help="Say what would change and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def incorporate_sync(dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
    """Apply the fetched pull to the quilt's files, stamping first each document it reaches; Incoming does the same."""
    from loom.cli._common import refuse_under_agent

    refuse_under_agent(
        "loom sync incorporate",
        "Incorporating a collaborator's changes is the author's; `loom sync status --patch` prints them for reading.",
    )
    quilt = open_quilt(quilt_path)
    state = _run(lambda: SyncState.read(quilt.root))
    assert isinstance(state, SyncState)
    pulled = state.incoming
    if dry_run:
        from loom.sync import _reaching, pull_files

        after = _run(lambda: pull_files(quilt, state))
        assert isinstance(after, dict)
        documents = _reaching(quilt.root, current_selection(state, scan(quilt))[1], set(after))
        Report(
            f"would incorporate {_short(pulled)} from {source_label(state.url)} into {counted(len(after), 'file')}",
            dry_run=True,
            groups=[
                Group("files that would change", [Item("", key=p) for p in sorted(after)], limit=None),
                Group("documents that would be stamped first", [Item("", key=d) for d in documents], limit=None),
            ],
            data={"pulled": pulled, "paths": sorted(after), "documents": documents},
        ).emit(as_json)
        return
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
@click.option("--dry-run", is_flag=True, help="Say what would change and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def publish_sync(push: bool, dry_run: bool, as_json: bool, quilt_path: str | None) -> None:
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
    publication = _run(lambda: publish(quilt, state, write=not dry_run))
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
            f"nothing to publish: {label} already holds these {counted(len(publication.paths), 'file')}",
            dry_run=dry_run,
            data=data,
        ).emit(as_json)
        return
    files = f"{counted(len(publication.paths), 'file')} for {', '.join(state.documents)}"
    if dry_run:
        if publication.reused:
            verdict = f"the revision prepared earlier, {_short(publication.commit)}, holds these {files}" + (
                f"; it would be pushed to {label}" if push else "; nothing new would be prepared"
            )
        else:
            verdict = f"would prepare {files}" + (f" and push it to {label}" if push else f"; {label} stays unchanged")
        documents = _landmarks(quilt, publication.landmarks) if publication.reused else publication.landmarks
        Report(
            verdict,
            dry_run=True,
            groups=[
                Group(
                    "stamped earlier as landmarks" if publication.reused else "documents that would be stamped",
                    [Item("", key=m) for m in documents],
                    limit=None,
                )
            ],
            data={
                **data,
                "commit": publication.commit or None,
                "landmarks": publication.landmarks if publication.reused else [],
                "documents": [] if publication.reused else publication.landmarks,
            },
        ).emit(as_json)
        return
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
