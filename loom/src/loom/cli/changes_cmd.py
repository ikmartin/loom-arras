"""`loom changes`: what waits on the person, in-place edits since their look and suggested edits, by document; one change's patch; and the two verbs on a change, keep and discard."""

from __future__ import annotations

from typing import Any

import click

from loom.cli._common import EnvError, NotFoundError, refuse_under_agent
from loom.cli._quilt import open_scan, quilt_option
from loom.cli.report import Group, Item, Report, counted, table


def _short(text: str | None, n: int = 40) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= n else flat[: n - 1] + "…"


@click.command(name="changes")
@click.argument("change", required=False, metavar="[ID]")
@click.option("--document", default=None, metavar="DOC", help="Only the changes in the files DOC is made of.")
@click.option(
    "--keep",
    "keeping",
    multiple=True,
    metavar="ID|PATH",
    help="Keep the change ID, or every change in PATH; may repeat.",
)
@click.option(
    "--discard",
    "discarding",
    multiple=True,
    metavar="ID|PATH",
    help="Discard the change ID, or every change in PATH; may repeat.",
)
@click.option("--keep-all", is_flag=True, help="Keep every change; before your first look, take it.")
@click.option("--discard-all", is_flag=True, help="Discard every change.")
@click.option("--why", default=None, help="With a discard, why, which the agent that suggested an edit reads.")
@click.option("--by", "f_by", default=None, metavar="NAME", help="NAME's suggested edits, in every state.")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def changes_command(
    change: str | None,
    document: str | None,
    keeping: tuple[str, ...],
    discarding: tuple[str, ...],
    keep_all: bool,
    discard_all: bool,
    why: str | None,
    f_by: str | None,
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """List what waits on you, by document: each in-place edit to an open file since your last look, cut by words, and each open suggested edit; with ID, print the change's patch, which `git apply` takes as it stands.

    The open files are the ones the viewer shows that are text, at most 1 MB; your look holds each one's text as you last saw it, and `loom serve` takes your first when it starts. Keeping and discarding are yours, never an agent's: keeping an in-place edit puts it into your look, keeping a suggested edit writes it into its file; discarding an in-place edit puts its old words back, discarding a suggested edit leaves the text as it is. A version of each document a write changes is kept first. Keeping says nothing about whether the mathematics is right, which is `loom accept`'s.
    """
    from loom.cli.review import _annotator
    from loom.looks import keep_all as take_all
    from loom.looks import read_look
    from loom.pending import PendingRefused, discard, keep, patch_of, pending, reviewer

    result = open_scan(quilt_path)
    root = result.quilt.root
    who = reviewer(result)
    acting = bool(keeping or discarding or keep_all or discard_all)
    if acting and sum(1 for x in (keeping, discarding, keep_all, discard_all) if x) > 1:
        raise click.UsageError("one of --keep, --discard, --keep-all and --discard-all at a time")
    if why and not (discarding or discard_all):
        raise click.UsageError("--why goes with a discard")
    if f_by is not None:
        _by(result, f_by, as_json)
        return
    if acting:
        refuse_under_agent(
            "Keeping and discarding a change", "Keep and discard in a terminal of your own, or in the viewer."
        )
        if keep_all and who and read_look(root, who) is None:
            take_all(result.quilt, who)
            Report("took your first look at the open files", data={"done": [], "refused": []}).emit(as_json)
            return
        listed = pending(result, who)
        named = keeping or discarding
        ids = [c.id for c in listed] if keep_all or discard_all else _ids(listed, named)
        writer = ("human", who) if who else _annotator(root, None)
        try:
            if keeping or keep_all:
                done, refused = keep(result, who, ids, writer)
            else:
                done, refused = discard(result, who, ids, writer, why)
        except PendingRefused as exc:
            raise (
                NotFoundError("change", exc.message) if exc.code == "no-such-change" else EnvError(exc.message)
            ) from None
        verb = "kept" if keeping or keep_all else "discarded"
        said = f"{verb} {counted(len(done), 'change')}" if done else f"{verb} nothing"
        lines = [f"  {r['id']} not {verb}: {r['why']}" for r in refused]
        Report(said, ok=not refused, lines=lines, data={"done": done, "refused": refused}).emit(as_json)
        return
    listed = pending(result, who)
    if change is not None:
        found = next((c for c in listed if c.id == change), None)
        if found is None:
            raise NotFoundError("change", f"no change {change} waits on you; `loom changes` lists them")
        patch = patch_of(result, found, who)
        if not as_json:
            # the patch as it stands, which `git apply` takes: never wrapped as a report is
            click.echo(patch, nl=False)
            return
        Report(
            f"{found.id}  {found.kind} on {found.key or found.path}"
            + (f" ({found.state}: {found.why})" if found.why else ""),
            lines=patch.splitlines(),
            data={"change": found.to_dict(), "patch": patch},
        ).emit(as_json)
        return
    if document is not None:
        listed = [c for c in listed if document in c.documents]
    look = read_look(root, who) if who else None
    since = f"since your look ({look.when[:16].replace('T', ' ')})" if look else "before your first look"
    verdict = f"{since}: " + (counted(len(listed), "change") if listed else "nothing waits on you")
    groups = []
    for doc in sorted({d for c in listed for d in c.documents}) + (
        [""] if any(not c.documents for c in listed) else []
    ):
        mine = [c for c in listed if (doc in c.documents if doc else not c.documents)]
        cells = [
            (
                c.id,
                c.kind,
                c.key or c.path,
                f"“{_short(c.old, 30)}” → “{_short(c.new, 30)}”",
                (f"by {c.author}" if c.author else "") + (f" ({c.state})" if c.state != "ready" else ""),
            )
            for c in mine
        ]
        groups.append(Group(doc or "in no document", [Item(line) for line in table(cells)], limit=None))
    data: dict[str, Any] = {"look": look.to_json() | {"files": len(look.files)} if look else None}
    data["changes"] = [c.to_dict() for c in listed]
    Report(verdict, groups=groups, data=data).emit(as_json)


def _ids(listed: list[Any], named: tuple[str, ...]) -> list[str]:
    """The changes named, each an id or a path, every change in the file for a path."""
    out: list[str] = []
    for name in named:
        in_file = [c.id for c in listed if c.path == name.strip().strip("/")]
        out += in_file or [name]
    return out


def _by(result: Any, name: str, as_json: bool) -> None:
    """`--by NAME`: NAME's suggested edits, in every state."""
    from loom.records.edits import is_taken, replay

    edits = [e for e in replay(result.quilt.root)[0] if e.author_id == name]
    cells = [
        (
            e.id,
            e.target_key,
            e.status,
            e.placement + (f" “{_short(e.selector.exact, 30)}”" if e.selector else " the body"),
            ("taken already" if e.status == "open" and is_taken(result, e) else "") or (e.why or ""),
        )
        for e in edits
    ]
    Report(
        counted(len(edits), "suggested edit") + f" by {name}" if edits else f"no suggested edits by {name}",
        groups=[Group("", [Item(line) for line in table(cells)], limit=None)] if cells else [],
        data={"edits": [e.to_dict() for e in edits]},
    ).emit(as_json)
