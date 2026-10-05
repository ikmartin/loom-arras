"""`loom library relate` (plan 0.18.5): a typed relation between two results, asserted with a reason, and its removal."""

from __future__ import annotations

import click

from loom.cli._common import EnvError, NotFoundError
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.library._works import find_result, logged
from loom.cli.report import Report
from loom.refs.links import KINDS


@click.command(name="relate")
@click.argument("frm", metavar="FROM", required=False)
@click.argument("to", metavar="TO", required=False)
@click.option(
    "--kind", type=click.Choice(sorted(KINDS)), default=None, help="How FROM relates to TO; required unless --undo."
)
@click.option(
    "--why", required=True, help="One or two sentences: what you read six months later, or why a relation is removed."
)
@click.option(
    "--undo",
    "undo",
    default=None,
    metavar="LINK_ID",
    help="Remove this relation instead; an agent removes only an agent's.",
)
@click.option(
    "--as",
    "who",
    default=None,
    metavar="NAME",
    help="Who asserts it; an agent names itself, with Agent or AI in the name.",
)
@click.option("--dry-run", is_flag=True, help="Check everything and say what would change, writing nothing.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@quilt_option
@logged("relate")
def relate_command(
    frm: str | None,
    to: str | None,
    kind: str | None,
    why: str,
    undo: str | None,
    who: str | None,
    dry_run: bool,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """Assert a typed relation between two results, FROM and TO, with a reason; with --undo LINK_ID, remove one.

    **Nobody verifies this and it says so.** A relation has no page span to check it against, so a verification step would be theatre; it is an assertion, attributed to whoever made it: `--as`, else you as the quilt's reviewer. Relations are never citable, never enter a closure, and are never written into a digest: they are navigation, not mathematics. `loom library why ID` lists a result's relations.
    """
    if undo is not None:
        if frm is not None or to is not None or kind is not None:
            raise EnvError(
                "--undo removes the relation it names; give FROM TO --kind K to relate two results, or --undo LINK_ID, not both"
            )
        _undo(quilt_path, undo, why, who, dry_run, as_json)
        return
    if frm is None or to is None or kind is None:
        raise EnvError("give FROM TO --kind K to relate two results, or --undo LINK_ID to remove a relation")
    from loom.cli._common import agent_marker
    from loom.refs.links import add_link, check_link, next_id, read_links
    from loom.scan.quilt import NoAuthorError, resolve_author

    result = open_scan(quilt_path)
    root = result.quilt.root
    for end in (frm, to):
        find_result(result, end)
    # who asserted it, never the session it was asserted in: an assertion is somebody's, and a reader weighs it by whose
    if who and who.strip():
        by = who.strip()
    elif agent_marker():
        # an agent with no --session would otherwise be recorded as the author, by way of git: eleven links in the second study run were
        raise EnvError("an agent is running this shell: pass --as NAME, so the relation says who asserted it")
    else:
        try:
            by = resolve_author(None, root)[0]
        except NoAuthorError as exc:
            raise EnvError(str(exc)) from exc
    links = read_links(root)
    try:
        check_link(links, frm, to, kind, why)
    except ValueError as exc:
        raise EnvError(str(exc)) from exc
    if dry_run:
        made_id = next_id(links)
        Report(
            f"would relate {made_id}: {frm} {kind} {to}",
            dry_run=True,
            lines=[f"asserted by {by}; would be written to digests/links.jsonl"],
            data={"link": {"id": made_id, "from": frm, "to": to, "kind": kind, "why": why.strip(), "by": by}},
        ).emit(as_json)
        return
    try:
        made = add_link(root, frm, to, kind, why, by)
    except ValueError as exc:
        raise EnvError(str(exc)) from exc
    Report(
        f"related {made.id}: {frm} {kind} {to}",
        notes=["asserted, not checked: a relation is somebody's reading, and every surface that shows it says so"],
        data={"link": made.to_json()},
    ).emit(as_json)


def _undo(quilt_path: str | None, link_id: str, why: str, who: str | None, dry_run: bool, as_json: bool) -> None:
    """Remove one relation, recording who removed it and why; an agent is refused one a person asserted."""
    from loom.cli._common import agent_marker, is_agent, whoever
    from loom.cli._quilt import open_quilt
    from loom.refs.links import read_links, record_removal, remove_link

    root = open_quilt(quilt_path).root
    target = next((x for x in read_links(root) if x.id == link_id), None)
    if target is None:
        raise NotFoundError("link", f"no relation {link_id}; loom library why ID lists a result's relations")
    if not why.strip():
        raise EnvError("say why it is removed: the removal is recorded beside the relation")
    # a session's id is how an agent's relation records who asserted it
    by_agent = target.by.startswith("s-") or is_agent(target.by)
    marker = agent_marker()
    if not by_agent and (marker or (who and is_agent(who))):
        acting = f"an agent is running this shell ({marker} is set)" if marker else f"{who} is an agent"
        raise EnvError(
            f"{link_id} was asserted by {target.by}, and {acting}; removing someone else's relation is theirs to do"
        )
    by = whoever(root, who)
    if dry_run:
        Report(
            f"would remove {target.id}: {target.frm} {target.kind} {target.to}",
            dry_run=True,
            lines=["would be recorded in digests/links-removed.jsonl"],
            data={"link": target.to_json(), "removed_by": by, "why": why.strip()},
        ).emit(as_json)
        return
    gone = remove_link(root, link_id)
    record_removal(root, gone, by, why.strip())
    Report(
        f"removed {gone.id}: {gone.frm} {gone.kind} {gone.to}",
        data={"link": gone.to_json(), "removed_by": by, "why": why.strip()},
    ).emit(as_json)


#: The commands this module adds to `loom library`.
COMMANDS: list[click.Command] = [relate_command]
