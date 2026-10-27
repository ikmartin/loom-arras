"""`loom adopt`: inspect an agent document's changes and incorporate them into the working document it was drafted from."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click

from loom.cli._common import EnvError, agent_marker
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.report import Group, Item, Progress, Report, counted
from loom.scan.quilt import NoAuthorError
from loom.sync import SyncError


@click.command()
@click.argument("document")
@click.argument("keys", nargs=-1)
@click.option("--document-changes", is_flag=True, help="Include proposed prose and ordering changes.")
@click.option("--preamble-changes", is_flag=True, help="Include the separately reviewed preamble changes.")
@click.option("--document-only", is_flag=True, help="Include document-level changes while keeping every node version.")
@click.option("--incorporate", metavar="TOKEN", help="Incorporate exactly the previously inspected preview.")
@click.option(
    "--to",
    "output",
    default=None,
    metavar="FILE",
    help="Write the preview's patch to FILE without incorporating; never among the quilt's sources. For an agent document written from scratch, the working document to start from it.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def adopt(
    document: str,
    keys: tuple[str, ...],
    document_changes: bool,
    document_only: bool,
    preamble_changes: bool,
    incorporate: str | None,
    output: str | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Preview an agent document's changes to the working document it was drafted from, and incorporate them once confirmed; mathematics is never accepted.

    The preview is the dry run: without a terminal to confirm on, or with --json or --to, adopt stops there and names the `--incorporate TOKEN` that applies exactly it. An agent document written from scratch (`loom draft --ai NAME --new`) has no working document to incorporate into: `--to FILE` starts one from it, every id it defines made plain.
    """
    from loom.adopt import from_scratch, prepare, start
    from loom.adopt import incorporate as apply
    from loom.cli._common import destination

    if agent_marker():
        raise EnvError("Adoption is an author action. An agent proposes changes in its agent document.")
    if document_only and keys:
        raise EnvError("--document-only cannot be combined with node keys")
    if incorporate and (keys or document_changes or document_only or preamble_changes or output):
        raise EnvError("--incorporate applies the saved preview; change selections by preparing a new preview")
    try:
        with Progress("scanning") as progress:
            result = open_scan(quilt_path)
            scratch = from_scratch(result, document)
            if scratch:
                drafting = result.quilt.config.drafting
                if keys or document_changes or document_only or preamble_changes or incorporate:
                    raise EnvError(
                        f"{document} was written from scratch, so it has no changes to choose among; --to FILE starts a working document from it"
                    )
                if not output:
                    raise EnvError(
                        f"{document} was written from scratch, so it has no working document to incorporate into; --to {drafting}/NAME.tex names the one to start from it"
                    )
                written = destination(result.quilt, output, drafting=True)
                progress.next_stage(f"writing {written.name}")
                started = start(result, scratch, written.relative_to(Path(result.quilt.root).resolve()).as_posix())
            else:
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
                        preamble=preamble_changes,
                        stage=progress.next_stage,
                    )
        if scratch:
            Report(
                started["message"],
                ok=not started["twice"],
                groups=[
                    Group(
                        "defined twice, with no text until loom fork or retiring one document resolves each",
                        [Item("", key=k, fixes=[f"loom fork {k} --in {started['to']}"]) for k in started["twice"]],
                        problem=True,
                    )
                ]
                if started["twice"]
                else [],
                data=started,
            ).emit(as_json)
            return
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
