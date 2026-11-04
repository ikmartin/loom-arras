"""`loom changes`: what changed in the open files since your last look, and the two verbs that act on a change, keep and undo."""

from __future__ import annotations

import click

from loom.cli._common import EnvError, refuse_under_agent
from loom.cli._quilt import open_quilt, quilt_option
from loom.cli.report import Report, counted


def _which(numbers: list[int]) -> str:
    """Changes by their numbers, as a report says them."""
    return f"change {numbers[0]}" if len(numbers) == 1 else "changes " + ", ".join(map(str, numbers))


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
@click.option(
    "--hunk",
    "hunks",
    type=click.IntRange(min=0),
    multiple=True,
    metavar="N",
    help="With --keep or --undo, act on PATH's change number N alone, as the list numbers them; may repeat.",
)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object.")
@quilt_option
def changes_command(
    keep_path: str | None,
    keep_all: bool,
    undo_path: str | None,
    hunks: tuple[int, ...],
    as_json: bool,
    quilt_path: str | None,
) -> None:
    """List what changed in the open files since your last look, or keep or undo a change.

    The open files are the ones the viewer shows that are text: Markdown, HTML, notebooks, LaTeX and the rest, at most 1 MB. Your look holds each one's text as you last saw it, and `loom serve` takes your first when it starts. Keeping and undoing are yours, never an agent's, for a whole file or one of its changes (`--hunk`); undoing keeps the text it replaces, and undoing a new file removes it. Keeping says nothing about whether the mathematics is right, which is `loom accept`'s.
    """
    from loom.looks import LookRefused, changes, keep, read_look, undo
    from loom.scan.quilt import reviewer_identity

    quilt = open_quilt(quilt_path)
    who = reviewer_identity(quilt.root)[0]
    if not who:
        raise EnvError('a look is yours by name: add name = "Your Name" under [author] in ~/.config/loom/config.toml')
    numbers = list(hunks) or None
    acting = sum(1 for x in (keep_path, keep_all, undo_path) if x)
    if acting > 1:
        raise click.UsageError("one of --keep, --keep-all and --undo at a time")
    if hunks and not (keep_path or undo_path):
        raise click.UsageError("--hunk names a change within the PATH of --keep or --undo")
    try:
        if acting:
            how = "Keep and undo in a terminal of your own, or in Review."
            refuse_under_agent("Keeping and undoing a change", how)
            if undo_path:
                back = undo(quilt, who, undo_path, hunks=numbers)
                if back is None:
                    said = f"removed {undo_path}, new since your look; its text is kept in the history"
                elif numbers:
                    said = f"put back {_which(numbers)} of {undo_path}; the text it replaced is kept in the history"
                else:
                    said = f"{undo_path} is back as it was at your look; its text before is kept in the history"
            else:
                keep(quilt, who, keep_path, hunks=numbers)
                said = (
                    (f"kept {_which(numbers)} of {keep_path}" if numbers else f"kept {keep_path}")
                    if keep_path
                    else "kept everything: a new look at the open files"
                )
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
    lines = [
        f"  {c.kind:<8} {c.path}" + (f"  ({counted(c.hunks, 'change')}, 0-{c.hunks - 1})" if c.hunks > 1 else "")
        for c in got
    ]
    data = {
        "look": look.to_json() | {"files": len(look.files)},
        "changes": [{"path": c.path, "kind": c.kind, "hunks": c.hunks, "diff": c.diff} for c in got],
    }
    Report(verdict, lines=lines, data=data).emit(as_json)
