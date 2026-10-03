"""Inspect and incorporate an AI contribution through the shared review workflow."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from loom.cli._common import EnvError, agent_marker
from loom.cli._quilt import open_scan, quilt_option
from loom.sync import SyncError


@click.command()
@click.argument("document")
@click.argument("keys", nargs=-1)
@click.option("--document-changes", is_flag=True, help="Include proposed prose and ordering changes.")
@click.option("--preamble-changes", is_flag=True, help="Include the separately reviewed preamble changes.")
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
    preamble_changes: bool,
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
    if incorporate and (keys or document_changes or document_only or preamble_changes or output):
        raise EnvError("--incorporate applies the saved preview; change selections by preparing a new preview")
    result = open_scan(quilt_path)
    try:
        if incorporate:
            answer = apply(result, document, incorporate)
            click.echo(json.dumps(answer, indent=2) if as_json else answer["message"])
            return
        preview = prepare(
            result,
            document,
            [] if document_only else list(keys) if keys else None,
            document_changes or document_only,
            preamble=preamble_changes,
        )
        if output:
            output.write_text(preview["patch"])
        if as_json:
            click.echo(json.dumps(preview, indent=2))
            return
        click.echo(preview["patch"] or "No changes to incorporate")
        if not preview["patch"] or output:
            return
        click.echo("Unselected proposals remain in the AI draft. Incorporation does not accept mathematics.")
        if not sys.stdin.isatty():
            click.echo(
                f"Preview saved. After inspection: loom adopt {preview['copy']} --incorporate {preview['token']}"
            )
            return
        if click.confirm("Incorporate selected changes?"):
            click.echo(apply(open_scan(quilt_path), document, preview["token"])["message"])
    except (SyncError, ValueError, OSError) as exc:
        raise EnvError(str(exc)) from exc
