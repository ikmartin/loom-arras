"""`loom suggestion ID`: a suggestion's payload, as the patch that takes it; `loom suggestion apply ID`, the author's, writes it in."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import ContentError, NotFoundError, note, refuse_under_agent
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.help import CommandGroup
from loom.cli.report import Report
from loom.records.annotations import Annotation, find_annotation, load_records
from loom.records.suggestions import Unplaced, is_taken, patch, place
from loom.scan.scan import ScanResult


class _SuggestionGroup(CommandGroup):
    """`loom suggestion`: a word that names no subcommand is a suggestion's id, whose patch the hidden `_patch` command prints. `apply` is a path of its own, so an agent's grant of `suggestion` never reaches it as a tool."""

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            return args[0], _patch, args[1:]
        return super().resolve_command(ctx, args)


@click.group(cls=_SuggestionGroup, invoke_without_command=True, subcommand_metavar="[ANNOTATION | apply ANNOTATION]")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
@click.pass_context
def suggestion(ctx: click.Context, as_json: bool, quilt_path: str | None) -> None:
    """Print the patch that takes suggestion ANNOTATION: its payload in place, against its key's text now.

    `replace` takes exactly the quoted words' place; `after` and `before` go right beside them; with no quote, of the key's body. Refused when the quote no longer stands in the text exactly once. Once the key reads as the suggestion taken, `loom annotate --resolve ANNOTATION --applied` records it; `loom suggestion apply ANNOTATION` does both, and is the author's.
    """
    if ctx.invoked_subcommand is None:
        raise click.UsageError("name a suggestion: loom suggestion ANNOTATION")


def _inherited(quilt_path: str | None, as_json: bool) -> tuple[str | None, bool]:
    """`--quilt` and `--json` given before the id (`loom suggestion --json a-…`) count as given after it."""
    parent = click.get_current_context().parent
    given = parent.params if parent is not None else {}
    return quilt_path or given.get("quilt_path"), as_json or bool(given.get("as_json"))


def _found(result: ScanResult, annotation: str) -> Annotation:
    """The annotation by its id, or the not-found refusal."""
    records, _ = load_records(result.quilt.root)
    found = find_annotation(records, annotation)
    if found is None:
        raise NotFoundError("annotation", f"no annotation {annotation}")
    return found[1]


@click.command(name="ANNOTATION", hidden=True)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def _patch(as_json: bool, quilt_path: str | None) -> None:
    """Print the patch that takes suggestion ANNOTATION."""
    quilt_path, as_json = _inherited(quilt_path, as_json)
    result = open_scan(quilt_path)
    ann = _found(result, click.get_current_context().info_name or "")
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
    # Printing records nothing: whether the patch was taken is read from the text afterwards.
    click.echo(diff, nl=False)
    note(
        f"Apply the patch to {placed.file} to take {ann.id}{moved}; then `loom annotate --resolve {ann.id} --applied`. `loom suggestion apply {ann.id}` does both."
    )


@suggestion.command("apply")
@click.argument("annotation")
@click.option("--as", "as_name", metavar="NAME", help="Who is applying it; default your [author] name.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def apply_cmd(annotation: str, as_name: str | None, as_json: bool, quilt_path: str | None) -> None:
    """Write suggestion ANNOTATION into its file and resolve it as applied, keeping a version of each document it changes first.

    The author's act. Refused for a suggestion with no text to put in, one whose quote no longer stands once, one already resolved or withdrawn, and one on an agent's copy, whose changes come in with the copy.
    """
    from loom.cli.review import _annotator, _one_comment
    from loom.records.suggestions import ApplyRefused, apply

    refuse_under_agent(
        "Applying a suggestion", "An agent suggests; the author puts a suggestion into the text.", as_name
    )
    quilt_path, as_json = _inherited(quilt_path, as_json)
    result = open_scan(quilt_path)
    ann = _found(result, annotation)
    root = result.quilt.root
    writer = _annotator(root, as_name)
    try:
        documents, kept = apply(result, ann, writer[1])
    except ApplyRefused as exc:
        raise ContentError(exc.message) from exc
    _one_comment(open_scan(str(root)), writer, None, None, None, None, None, ann.id, applied=True)
    said = "; ".join(
        x
        for x in (f"applied {ann.id} in {' and '.join(Path(d).name for d in documents) or ann.target_key}", kept.said())
        if x
    )
    Report(said, data={"annotation": ann.id, "documents": documents, "kept": kept.kept}).emit(as_json)
