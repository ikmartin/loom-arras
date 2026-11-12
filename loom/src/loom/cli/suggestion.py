"""`loom suggest`: file a suggested edit on a key. `loom suggestion`: list them, print one's patch, or apply or discard one."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, NotFoundError, from_stdin, note, refuse_under_agent
from loom.cli._quilt import open_scan, quilt_option, resolve_key
from loom.cli.help import CommandGroup
from loom.cli.report import Group, Item, Report, counted, table
from loom.records.edits import STATUSES, Edit, EditRefused, Unplaced, find, is_taken, patch, place, replay
from loom.scan.scan import ScanResult


@click.command(name="suggest")
@click.argument("key")
@click.option(
    "--with",
    "with_text",
    required=True,
    metavar="NEW",
    help="The new text; '' deletes the quoted words, and - reads it from stdin.",
)
@click.option(
    "--quote",
    default=None,
    metavar="OLD",
    help="The words it replaces, once in the key's own text; without it, the key's body.",
)
@click.option(
    "--before", is_flag=True, help="Put the new text right before the quoted words, or at the head of the body."
)
@click.option("--after", is_flag=True, help="Put the new text right after the quoted words, or at the end of the body.")
@click.option("--answers", default=None, metavar="ID", help="The annotation it answers; keeping the edit resolves it.")
@click.option("--comment", default=None, metavar="TEXT", help="What to say beside it, in Markdown.")
@click.option(
    "--as",
    "author",
    default=None,
    metavar="NAME",
    help="Who suggests it; an agent names itself, with Agent or AI in the name.",
)
@click.option("--dry-run", is_flag=True, help="Say what would be filed, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def suggest_command(
    key: str,
    with_text: str,
    quote: str | None,
    before: bool,
    after: bool,
    answers: str | None,
    comment: str | None,
    author: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """File a suggested edit on KEY: --with NEW in place of --quote OLD, or beside it with --before or --after; without --quote, of the key's body.

    The person keeps or discards it: `loom suggestion apply ID` writes it into the file and keeps it, `loom suggestion discard ID` leaves the text as it is. An edit that names the annotation it --answers resolves that annotation when it is kept. `--before` with no quote puts the text at the head of the body, which is how a `\\uses{…}` is proposed.
    """
    from loom.cli.review import _annotator, _version
    from loom.clock import stamp, today
    from loom.records.annotations import find_annotation, load_records
    from loom.records.edits import append_new
    from loom.records.selectors import find_quote, make_selector
    from loom.records.store import Records
    from loom.render.manifest import key_hash

    (given,) = from_stdin({"--with": with_text})
    with_text = given or ""
    if before and after:
        raise EnvError("--before and --after say two places; give one")
    placement = "before" if before else "after" if after else "replace"
    result = open_scan(quilt_path)
    root = result.quilt.root
    target = resolve_key(result, key)
    node_key = result.assembly.regions[target].container if target in result.assembly.regions else target
    node = result.nodes[node_key]
    if answers and find_annotation(load_records(root)[0], answers) is None:
        raise NotFoundError("annotation", f"--answers {answers}: no annotation {answers}")
    selector = None
    if quote:
        own, _ = Records.own_pieces(result, node)
        spans = find_quote(own, quote)
        if not spans:
            raise NotFoundError("quote", f"quote not found in {target}; `loom source {target}` prints its text")
        if len(spans) > 1:
            raise EnvError(f"quote is ambiguous ({len(spans)} occurrences); give a longer quote")
        selector = make_selector(own, quote)
        if placement == "replace" and with_text.strip() == quote.strip():
            raise EnvError("--with is the quoted text itself, so the edit changes nothing")
    elif not with_text.strip():
        raise EnvError(
            "an empty --with deletes the quoted words, so it needs --quote; with none, it would empty the body"
        )
    if not with_text and placement != "replace":
        raise EnvError("an empty --with deletes the quoted words, so it goes with neither --before nor --after")
    akind, aid = _annotator(root, author)
    if comment and akind == "agent":
        from loom.links import refuse_bad_links

        refuse_bad_links(result, root, comment)
    event: dict[str, Any] = {
        "event": "created",
        "when": stamp(),
        "author": aid,
        "kind": akind,
        "target": target,
        "against": _version(result, target, dry_run=dry_run) or key_hash(result, node_key),
        "anchor": selector.to_dict() if selector else None,
        "with": with_text,
        "placement": placement,
    }
    if comment:
        event["comment"] = comment
    if answers:
        event["answers"] = answers
    from loom.records.ids import draw

    edit_id = draw(f"e-{today()}-", {e.id for e in replay(root)[0]}) if dry_run else append_new(root, event, today())
    where = f"{placement} “{_short(quote)}”" if quote else f"{placement} the body of"
    said = f"{edit_id}  {where} {target}  ({aid})"
    Report(
        f"would file {said}" if dry_run else said,
        dry_run=dry_run,
        data={"edit": edit_id, "target": target, "placement": placement},
    ).emit(as_json)


def _short(text: str | None, n: int = 40) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= n else flat[: n - 1] + "…"


class _SuggestionGroup(CommandGroup):
    """`loom suggestion`: a word that names no subcommand is an edit's id, whose patch the hidden `_patch` command prints. `apply` is a path of its own, so an agent's grant of `suggestion` never reaches it as a tool."""

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            return args[0], _patch, args[1:]
        return super().resolve_command(ctx, args)


@click.group(cls=_SuggestionGroup, invoke_without_command=True, subcommand_metavar="[EDIT | apply EDIT | discard EDIT]")
@click.option("--by", "f_by", default=None, metavar="NAME", help="Only the edits NAME suggested.")
@click.option("--target", "f_target", default=None, metavar="KEY", help="Only the edits on KEY.")
@click.option(
    "--status",
    "f_status",
    type=click.Choice(STATUSES),
    default="open",
    show_default=True,
    help="Only the edits in this state.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
@click.pass_context
def suggestion(
    ctx: click.Context, f_by: str | None, f_target: str | None, f_status: str, as_json: bool, quilt_path: str | None
) -> None:
    """List suggested edits, or with EDIT print the patch that takes it: its new text in place, against its key's text now.

    `replace` takes exactly the quoted words' place; `before` and `after` go right beside them; with no quote, of the key's body. `loom suggestion apply EDIT` writes it in and keeps it, and is the author's; `loom suggestion discard EDIT` discards it, which an agent may do to its own.
    """
    if ctx.invoked_subcommand is not None:
        return
    result = open_scan(quilt_path)
    target = resolve_key(result, f_target) if f_target else None
    edits = [
        e
        for e in replay(result.quilt.root)[0]
        if e.status == f_status and (f_by is None or e.author_id == f_by) and (target is None or e.target_key == target)
    ]
    cells = [
        (
            e.id,
            e.target_key,
            e.placement + (f" “{_short(e.selector.exact, 30)}”" if e.selector else " the body"),
            f"by {e.author_id}",
            ("taken already" if e.status == "open" and is_taken(result, e) else "") or (e.why or ""),
        )
        for e in edits
    ]
    narrowed = f_by is not None or target is not None
    Report(
        counted(len(edits), f"{f_status} edit") if edits else f"no {f_status} edits" + (" match" if narrowed else ""),
        groups=[Group("", [Item(line) for line in table(cells)], limit=None)] if cells else [],
        data={"edits": [e.to_dict() for e in edits]},
    ).emit(as_json)


def _inherited(quilt_path: str | None, as_json: bool) -> tuple[str | None, bool]:
    """`--quilt` and `--json` given before the id (`loom suggestion --json e-…`) count as given after it."""
    parent = click.get_current_context().parent
    given = parent.params if parent is not None else {}
    return quilt_path or given.get("quilt_path"), as_json or bool(given.get("as_json"))


def _found(result: ScanResult, edit_id: str) -> Edit:
    """The edit by its id, or the not-found refusal."""
    edit = find(result.quilt.root, edit_id)
    if edit is None:
        raise NotFoundError("edit", f"no suggested edit {edit_id}")
    return edit


@click.command(name="EDIT", hidden=True)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def _patch(as_json: bool, quilt_path: str | None) -> None:
    """Print the patch that takes suggested edit EDIT."""
    quilt_path, as_json = _inherited(quilt_path, as_json)
    result = open_scan(quilt_path)
    edit = _found(result, click.get_current_context().info_name or "")
    if is_taken(result, edit):
        Report(
            f"{edit.target_key} already reads as {edit.id} taken; nothing to apply",
            data={"edit": edit.id, "taken": True, "status": edit.status},
        ).emit(as_json)
        return
    try:
        placed = place(result, edit)
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
            f"the patch takes {edit.id} in {placed.file}{moved}",
            data={
                "edit": edit.id,
                "key": placed.key,
                "file": placed.file,
                "moved": placed.moved,
                "diff": diff,
                "status": edit.status,
            },
        ).emit(True)
        return
    # Printing records nothing: whether the patch was taken is read from the text afterwards.
    click.echo(diff, nl=False)
    note(
        f"Apply the patch to {placed.file} to take {edit.id}{moved}; `loom suggestion apply {edit.id}` writes it in and keeps it."
    )


@suggestion.command("apply")
@click.argument("edit_id", metavar="EDIT")
@click.option("--as", "as_name", metavar="NAME", help="Who is applying it; default your [author] name.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def apply_cmd(edit_id: str, as_name: str | None, as_json: bool, quilt_path: str | None) -> None:
    """Write suggested edit EDIT into its file and keep it, keeping a version of each document it changes first.

    The author's act. Refused for an edit that is not open, one whose quote no longer stands once, and one on an agent's copy, whose changes come in with the copy. An edit whose key reads as it taken already is kept without writing. Keeping one that answers an open annotation resolves that annotation.
    """
    from loom.cli.review import _annotator
    from loom.records.edits import apply, keep

    refuse_under_agent(
        "Applying a suggested edit", "An agent suggests; the author puts a suggested edit into the text.", as_name
    )
    quilt_path, as_json = _inherited(quilt_path, as_json)
    result = open_scan(quilt_path)
    edit = _found(result, edit_id)
    root = result.quilt.root
    writer = _annotator(root, as_name)
    documents: list[str] = []
    said = ""
    kept_said = ""
    try:
        if not (edit.status == "open" and is_taken(result, edit)):
            documents, kept = apply(result, edit, writer[1])
            said = f"applied {edit.id} in {' and '.join(Path(d).name for d in documents) or edit.target_key}"
            kept_said = kept.said()
        recorded = keep(open_scan(str(root)), edit, writer)
    except EditRefused as exc:
        raise ContentError(exc.message) from exc
    Report(
        "; ".join(x for x in (said, recorded, kept_said) if x),
        data={"edit": edit.id, "documents": documents},
    ).emit(as_json)


@suggestion.command("discard")
@click.argument("edit_id", metavar="EDIT")
@click.option("--why", default=None, help="Why it is discarded, which the agent that suggested it reads.")
@click.option("--undo", is_flag=True, help="Open a kept or discarded edit again.")
@click.option("--as", "as_name", metavar="NAME", help="Who is discarding it; an agent discards only its own.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def discard_cmd(
    edit_id: str, why: str | None, undo: bool, as_name: str | None, as_json: bool, quilt_path: str | None
) -> None:
    """Discard suggested edit EDIT, leaving the text as it is; a person discards any edit, an agent only its own. --undo opens it again."""
    from loom.cli.review import _annotator
    from loom.records.edits import discard

    quilt_path, as_json = _inherited(quilt_path, as_json)
    result = open_scan(quilt_path)
    edit = _found(result, edit_id)
    try:
        said = discard(result.quilt.root, edit, _annotator(result.quilt.root, as_name), why, undo=undo)
    except EditRefused as exc:
        raise EnvError(exc.message) from exc
    Report(said, data={"edit": edit.id}).emit(as_json)
