"""`loom adopt`: inspect an agent document's changes and incorporate them into the working document it was drafted from."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from loom.cli._common import EnvError, agent_marker
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.report import Progress, Report, counted
from loom.scan.quilt import NoAuthorError
from loom.sync import SyncError


@click.command()
@click.argument("document")
@click.argument("keys", nargs=-1)
@click.option("--document-changes", is_flag=True, help="Include proposed prose, preamble and ordering changes.")
@click.option("--document-only", is_flag=True, help="Include document-level changes while keeping every node version.")
@click.option("--incorporate", metavar="TOKEN", help="Incorporate exactly the previously inspected preview.")
@click.option(
    "--to",
    "output",
    default=None,
    metavar="FILE",
    help="Write the preview's patch to FILE without incorporating; never among the quilt's sources.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
def adopt(
    document: str,
    keys: tuple[str, ...],
    document_changes: bool,
    document_only: bool,
    incorporate: str | None,
    output: str | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Preview an agent document's changes to the working document it was drafted from, and incorporate them once confirmed; mathematics is never accepted.

    The preview is the dry run: without a terminal to confirm on, or with --json or --to, adopt stops there and names the `--incorporate TOKEN` that applies exactly it.
    """
    from loom.adopt import incorporate as apply
    from loom.adopt import prepare
    from loom.cli._common import destination

    if agent_marker():
        raise EnvError("Adoption is an author action. An agent proposes changes in its agent document.")
    if document_only and keys:
        raise EnvError("--document-only cannot be combined with node keys")
    if incorporate and (keys or document_changes or document_only or output):
        raise EnvError("--incorporate applies the saved preview; change selections by preparing a new preview")
    try:
        with Progress("scanning") as progress:
            result = open_scan(quilt_path)
            target = destination(result.quilt, output) if output else None
            if incorporate:
                progress.next_stage("checking the preview against the quilt")
                answer = apply(result, document, incorporate)
            else:
                preview = prepare(
                    result,
                    document,
                    [] if document_only else list(keys) if keys else None,
                    document_changes or document_only,
                    stage=progress.next_stage,
                )
        if incorporate:
            Report(answer["message"], data=answer).emit(as_json)
            return
        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(preview["patch"], encoding="utf-8")
        if as_json or not preview["patch"] or target is not None:
            Report(_previewed(preview, output), data=preview).emit(as_json)
            return
        asking = sys.stdin.isatty()
        Report(
            _previewed(preview, None),
            lines=["Unselected proposals remain in the agent document. Incorporation does not accept mathematics."],
        ).emit()
        if not asking:
            # one line however long: the token is an identifier, and a command broken across lines does not run
            click.echo(f"next: loom adopt {preview['copy']} --incorporate {preview['token']}")
        click.echo("")
        click.echo(preview["patch"], nl=False)
        if not asking:
            return
        if click.confirm("Incorporate selected changes?"):
            click.echo(apply(open_scan(quilt_path), document, preview["token"])["message"])
    except (SyncError, NoAuthorError, ValueError, OSError) as exc:
        raise EnvError(str(exc)) from exc


def _previewed(preview: dict[str, Any], output: str | None) -> str:
    """The verdict on a preview: what it would incorporate, or why nothing, and where the patch went."""
    from loom.adopt import nothing_to_incorporate

    if not preview["patch"]:
        return nothing_to_incorporate(preview)
    what = counted(len(preview["keys"]), "result") + (" and the document's prose" if preview["document"] else "")
    return f"preview of {what} from {Path(preview['copy']).name} into {preview['source']}; nothing incorporated yet" + (
        f"; the patch is in {output}" if output else ""
    )
