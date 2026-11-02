"""`loom changes`: what changed in the open files since your last look, and the two verbs that act on a change, keep and undo."""

from __future__ import annotations

import click

from loom.cli._common import EnvError, refuse_under_agent
from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.report import Report, counted


@click.command(name="changes")
@click.option(
    "--keep", "keep_path", default=None, metavar="PATH", help="Keep the change to PATH: your look takes its text now."
)
@click.option("--keep-all", is_flag=True, help="Keep every change: a new look at every open file.")
@click.option(
    "--undo",
    "undo_path",
    default=None,
    metavar="PATH",
    help="Put PATH back as it was at your look, keeping its text now in the history first.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def changes_command(
    keep_path: str | None, keep_all: bool, undo_path: str | None, as_json: bool, quilt_path: str | None
) -> None:
    """List what changed in the open files since your last look, or keep or undo a change.

    The open files are the ones the viewer shows that are text: Markdown, HTML, notebooks, LaTeX and the rest, at most 1 MB. Your look holds each one's text as you last saw it, and `loom serve` takes your first when it starts. Keeping and undoing are yours, never an agent's; undoing keeps the text it replaces. Keeping says nothing about whether the mathematics is right, which is `loom accept`'s.
    """
    from loom.looks import LookRefused, changes, keep, read_look, undo
    from loom.scan.quilt import reviewer_identity

    quilt = open_quilt(quilt_path)
    who = reviewer_identity(quilt.root)[0]
    if not who:
        raise EnvError('a look is yours by name: add name = "Your Name" under [author] in ~/.config/loom/config.toml')
    acting = sum(1 for x in (keep_path, keep_all, undo_path) if x)
    if acting > 1:
        raise click.UsageError("one of --keep, --keep-all and --undo at a time")
    try:
        if acting:
            how = "Keep and undo in a terminal of your own, or in Review."
            refuse_under_agent("Keeping and undoing a change", how)
            if undo_path:
                undo(quilt, who, undo_path)
                said = f"{undo_path} is back as it was at your look; its text before is kept in the history"
            else:
                keep(quilt, who, keep_path)
                said = f"kept {keep_path}" if keep_path else "kept everything: a new look at the open files"
            Report(said, data={"result": said}).emit(as_json)
            return
    except LookRefused as exc:
        raise EnvError(exc.message) from None
    look = read_look(quilt.root, who)
    if look is None:
        Report(f"no look yet for {who}: `loom changes --keep-all` takes one", data={"look": None, "changes": []}).emit(
            as_json
        )
        return
    got = changes(quilt, who)
    at = look.when[:16].replace("T", " ")
    verdict = f"since your look ({at}): " + (
        counted(len(got), "file changed", "files changed") if got else "nothing changed"
    )
    lines = [f"  {c.kind:<8} {c.path}" for c in got]
    data = {
        "look": look.to_json() | {"files": len(look.files)},
        "changes": [{"path": c.path, "kind": c.kind, "diff": c.diff} for c in got],
    }
    Report(verdict, lines=lines, data=data).emit(as_json)
