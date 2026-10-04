"""`loom library` (book 8; plan 0.18.5): the papers a quilt cites, what is known about each, and the results taken from them.

Bare, it reports what waits for the person and what for an agent; `loom library WORK` reports one work. The subcommands live one module per concern, each listing its commands in `COMMANDS`.
"""

from __future__ import annotations

import click

from loom.cli._quilt import quilt_option
from loom.cli.help import CommandGroup
from loom.cli.library import add, agent, decide, read, relate, state, update, upkeep


class _LibraryGroup(CommandGroup):
    """`loom library`: a word that names no subcommand is a WORK, which the hidden `_work` command reports."""

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            return args[0], _work, args[1:]
        return super().resolve_command(ctx, args)


@click.group(cls=_LibraryGroup, invoke_without_command=True, subcommand_metavar="[WORK | COMMAND [ARGS]...]")
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@click.option(
    "--session", "run_dir", default=None, envvar="LOOM_SESSION", metavar="SESSION", help="Log this call to the session."
)
@quilt_option
@click.pass_context
def library(ctx: click.Context, as_json: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """Report what the quilt's cited works need: from you, from an agent, and in review; `loom library WORK` reports one work.

    A WORK is a citekey, a fragment of one or of its author or title, or one of its result ids.
    """
    if ctx.invoked_subcommand is None:
        _show(quilt_path, None, as_json, run_dir)


@click.command(name="_work", hidden=True)
@click.option("--json", "as_json", is_flag=True, help="Print the report as one JSON object (book 12.9).")
@click.option(
    "--session", "run_dir", default=None, envvar="LOOM_SESSION", metavar="SESSION", help="Log this call to the session."
)
@quilt_option
@click.pass_context
def _work(ctx: click.Context, as_json: bool, run_dir: str | None, quilt_path: str | None) -> None:
    """One work's report: the word `library` was given in place of a subcommand."""
    parent = ctx.parent
    given = parent.params if parent is not None else {}
    _show(
        quilt_path or given.get("quilt_path"),
        ctx.info_name,
        as_json or bool(given.get("as_json")),
        run_dir or given.get("run_dir"),
    )


def _show(quilt_path: str | None, work: str | None, as_json: bool, run_dir: str | None) -> None:
    """`state.show`, logged to `run_dir` once it has answered, as every reader is (`_works.logged`)."""
    if not run_dir:
        state.show(quilt_path, work, as_json)
        return
    from loom.cli._quilt import open_quilt
    from loom.cli.build_cmds import log_run

    line = " ".join(["loom library", *([work] if work else [])])
    root = open_quilt(quilt_path).root
    try:
        state.show(quilt_path, work, as_json)
    except click.exceptions.Exit:
        log_run(run_dir, line, root)
        raise
    log_run(run_dir, line, root)


for _module in (update, add, decide, read, agent, relate, upkeep):
    for _command in _module.COMMANDS:
        library.add_command(_command)
