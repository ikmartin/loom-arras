"""Inspect and incorporate an AI contribution through the shared review workflow."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from loom.cli._common import EnvError, agent_marker
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.report import Report, counted
from loom.sync import SyncError


@click.command()
@click.argument("document")
@click.argument("keys", nargs=-1)
@click.option("--document-changes", is_flag=True, help="Include proposed prose, preamble and ordering changes.")
@click.option("--document-only", is_flag=True, help="Include document-level changes while keeping every node version.")
@click.option("--incorporate", metavar="TOKEN", help="Incorporate exactly the previously inspected preview.")
@click.option("--to", "output", type=click.Path(path_type=Path), help="Export the preview patch without incorporating.")
@click.option("--json", "as_json", is_flag=True, help="Inspect and save a preview without modifying author files.")
@click.option("--as", "separate", hidden=True)
@quilt_option
def adopt(
    document: str,
    keys: tuple[str, ...],
    document_changes: bool,
    document_only: bool,
    incorporate: str | None,
    output: Path | None,
    as_json: bool,
    separate: str | None,
    quilt_path: str | None,
) -> None:
    """Inspect an AI draft's changes and incorporate them after confirmation; never accept mathematics."""
    from loom.adopt import incorporate as apply
    from loom.adopt import prepare

    if agent_marker():
        raise EnvError("Adoption is an author action. An agent proposes changes in its AI draft.")
    if separate:
        raise EnvError(
            "Creating a separate document is not supported by adoption; this command revises the original document"
        )
    if document_only and keys:
        raise EnvError("--document-only cannot be combined with node keys")
    if incorporate and (keys or document_changes or document_only or output):
        raise EnvError("--incorporate applies the saved preview; change selections by preparing a new preview")
    result = open_scan(quilt_path)
    try:
        if incorporate:
            answer = apply(result, document, incorporate)
            Report(answer["message"], data=answer).emit(as_json)
            return
        preview = prepare(
            result, document, [] if document_only else list(keys) if keys else None, document_changes or document_only
        )
        if output:
            output.write_text(preview["patch"])
        if as_json or not preview["patch"] or output:
            Report(_previewed(preview, output), dry_run=as_json, data=preview).emit(as_json)
            return
        asking = sys.stdin.isatty()
        Report(
            _previewed(preview, None),
            lines=["Unselected proposals remain in the AI draft. Incorporation does not accept mathematics."],
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
    except (SyncError, ValueError, OSError) as exc:
        raise EnvError(str(exc)) from exc


def _previewed(preview: dict[str, Any], output: Path | None) -> str:
    """The verdict on a preview: what it would incorporate, or why nothing, and where the patch went."""
    from loom.adopt import nothing_to_incorporate

    if not preview["patch"]:
        return nothing_to_incorporate(preview)
    what = counted(len(preview["keys"]), "result") + (" and the document's prose" if preview["document"] else "")
    return f"preview of {what} from {Path(preview['copy']).name} into {preview['source']}; nothing incorporated yet" + (
        f"; the patch is in {output}" if output else ""
    )
