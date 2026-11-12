"""`loom suggest`: file a suggested edit on a key, or withdraw one of your own. The person keeps or discards it with `loom changes`, which also prints its patch."""

from __future__ import annotations

from typing import Any

import click

from loom.cli._common import EnvError, NotFoundError, from_stdin
from loom.cli._quilt import open_scan, quilt_option, resolve_key
from loom.cli.report import Report
from loom.records.edits import EditRefused, find, replay


@click.command(name="suggest")
@click.argument("key", required=False)
@click.option(
    "--with",
    "with_text",
    default=None,
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
@click.option(
    "--withdraw", default=None, metavar="EDIT", help="Withdraw suggested edit EDIT, one of yours still open, instead."
)
@click.option("--why", default=None, help="With --withdraw, why.")
@click.option("--dry-run", is_flag=True, help="Say what would be filed, and write nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def suggest_command(
    key: str | None,
    with_text: str | None,
    quote: str | None,
    before: bool,
    after: bool,
    answers: str | None,
    comment: str | None,
    author: str | None,
    withdraw: str | None,
    why: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """File a suggested edit on KEY: --with NEW in place of --quote OLD, or beside it with --before or --after; without --quote, of the key's body.

    The person keeps or discards it with `loom changes`: keeping writes it into the file, discarding leaves the text as it is, and `loom changes ID` prints the patch that takes it. An edit that names the annotation it --answers resolves that annotation when it is kept. `--before` with no quote puts the text at the head of the body, which is how a `\\uses{…}` is proposed. `--withdraw EDIT` takes back one of your own while it is open; `loom changes --by NAME` lists the edits NAME suggested, in every state.
    """
    from loom.cli.review import _annotator, _version
    from loom.clock import stamp, today
    from loom.records.annotations import find_annotation, load_records
    from loom.records.edits import append_new
    from loom.records.selectors import find_quote, make_selector
    from loom.records.store import Records
    from loom.render.manifest import key_hash

    if withdraw is not None:
        _withdraw(withdraw, author, why, dry_run, as_json, quilt_path)
        return
    if key is None or with_text is None:
        raise click.UsageError("KEY and --with NEW name the edit; --withdraw EDIT takes one back")
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


def _withdraw(
    edit_id: str, author: str | None, why: str | None, dry_run: bool, as_json: bool, quilt_path: str | None
) -> None:
    """Withdraw one of your own suggested edits while it is open: it is recorded discarded, and the text stays as it is. An agent withdraws only its own."""
    from loom.cli.review import _annotator
    from loom.records.edits import discard

    root = open_scan(quilt_path).quilt.root
    edit = find(root, edit_id)
    if edit is None:
        raise NotFoundError("edit", f"no suggested edit {edit_id}; `loom changes --by NAME` lists one's edits")
    writer = _annotator(root, author)
    if edit.author_id != writer[1]:
        raise EnvError(f"{edit_id} is {edit.author_id}'s; you withdraw only your own, and the author discards any")
    if dry_run:
        Report(f"would withdraw {edit_id}", dry_run=True, data={"edit": edit_id}).emit(as_json)
        return
    try:
        said = discard(root, edit, writer, why)
    except EditRefused as exc:
        raise EnvError(exc.message) from None
    Report(said.replace("discarded", "withdrew"), data={"edit": edit_id}).emit(as_json)
