"""`loom suggestion ID`: a suggestion's payload, as the patch that takes it (plan 0.20.7)."""

from __future__ import annotations

import click

from loom.cli._common import ContentError, NotFoundError, note
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.report import Report
from loom.records.annotations import find_annotation, load_records
from loom.records.suggestions import Unplaced, is_taken, patch, place


@click.command()
@click.argument("annotation")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def suggestion(annotation: str, as_json: bool, quilt_path: str | None) -> None:
    """Print the patch that takes suggestion ANNOTATION: its payload in place, against its key's text now; the file is the author's to change.

    `replace` takes exactly the quoted words' place; `after` and `before` go right beside them; with no quote, of the key's body. Refused when the quote no longer stands in the text exactly once. Once the key reads as the suggestion taken, `loom annotate --resolve ANNOTATION --applied` records it.
    """
    result = open_scan(quilt_path)
    records, _ = load_records(result.quilt.root)
    found = find_annotation(records, annotation)
    if found is None:
        raise NotFoundError("annotation", f"no annotation {annotation}")
    _, ann = found
    if is_taken(result, ann):
        Report(
            f"{ann.target_key} already reads as {ann.id} taken; nothing to apply",
            data={"annotation": ann.id, "taken": True},
        ).emit(as_json)
        return
    try:
        placed = place(result, ann)
    except Unplaced as exc:
        raise ContentError(str(exc)) from exc
    diff = patch(result, placed)
    moved = (
        f"; {placed.key} has changed since it was written, though the words it quotes still stand"
        if placed.moved
        else ""
    )
    if as_json:
        Report(
            f"the patch takes {ann.id} in {placed.file}{moved}",
            data={"annotation": ann.id, "key": placed.key, "file": placed.file, "moved": placed.moved, "diff": diff},
        ).emit(True)
        return
    # Nothing is recorded: applying the patch is the author's act, and whether it was taken is read from the text afterwards.
    click.echo(diff, nl=False)
    note(
        f"Apply the patch to {placed.file} to take {ann.id}{moved}; then `loom annotate --resolve {ann.id} --applied`."
    )
