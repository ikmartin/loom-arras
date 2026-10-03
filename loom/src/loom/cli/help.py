"""The `loom` group itself: how `loom --help` reads (K6) and what it answers for a name that is not a command."""

from __future__ import annotations

import click

from loom.cli._common import EnvError

#: Names a person reaches for that loom answers with a reason rather than a command (K1: a refusal is a line of help).
REFUSED = {
    name: "loom will not delete your notes; do it yourself with rm, after `loom downstream ID` shows what depends on it."
    for name in ("delete", "rm", "remove")
}

#: The help's sections, the person's work first: a title, one line of what it is for, and its commands in the order a person meets them.
SECTIONS: list[tuple[str, str, tuple[str, ...]]] = [
    (
        "Start",
        "Make a quilt, bring a paper into it, and check what loom needs.",
        ("init", "import", "atomize", "doctor"),
    ),
    (
        "Write",
        "Make and find nodes, and see what state each is in.",
        ("new", "id", "lint", "status", "source", "search", "link"),
    ),
    ("Review", "Annotate, accept, and see what rests on what.", ("annotate", "accept", "deps", "downstream")),
    (
        "History",
        "Record steps, read and restore earlier text, and move documents.",
        ("stamp", "history", "revert", "mv", "fork", "linearize", "deloom"),
    ),
    ("Library", "The papers you cite and the results taken from them.", ("refs", "digest")),
    (
        "Agents",
        "Hand a document to an agent, take its changes back, and the sessions you both work in.",
        ("draft", "adopt", "session", "ai"),
    ),
    (
        "Publish",
        "Build the site and the PDFs, serve them, and exchange sources with a workspace.",
        ("build", "serve", "compile", "check", "sync"),
    ),
    ("Upkeep", "Keep loom's own files current, and documents live.", ("upgrade", "live")),
]

#: How a command an agent may run is marked in the help, and the line that says so.
AGENT_MARK = "*"
#: Long enough that a first sentence is never cut; the help wraps it instead.
FULL = 10_000
AGENT_LEGEND = "* an agent may run it, or some of its subcommands (ai/rules.md lists which)."


def agent_runs(path: str) -> bool:
    """Whether an agent may run the command at `path`, or one of its subcommands, by `AGENT_COMMANDS`."""
    from loom.ai.layout import AGENT_COMMANDS

    return any(c == path or c.startswith(path + " ") for c in AGENT_COMMANDS)


class LoomGroup(click.Group):
    """The top-level group: its help in task sections, bare `loom` printing it with exit 0, and a name in `REFUSED` answered with its reason and exit 2."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if not args:
            click.echo(ctx.get_help(), color=ctx.color)
            ctx.exit(0)
        return super().parse_args(ctx, args)

    def invoke(self, ctx: click.Context) -> object:
        try:
            return super().invoke(ctx)
        except click.UsageError as e:
            # click prints a usage block before its `Error:`; a refusal is one line (book 12.1), naming the help instead, under `loom` whatever name invoked the root (`main` under a test runner)
            where = (
                f"; see `{' '.join(['loom', *e.ctx.command_path.split()[1:]])} --help`." if e.ctx is not None else ""
            )
            raise EnvError(e.format_message().rstrip(".") + where) from None

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args and args[0] in REFUSED:
            raise EnvError(REFUSED[args[0]])
        return super().resolve_command(ctx, args)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        listed = set()
        for title, purpose, names in SECTIONS:
            rows = []
            for name in names:
                cmd = self.get_command(ctx, name)
                if cmd is None or cmd.hidden:
                    continue
                listed.add(name)
                rows.append((name + (AGENT_MARK if agent_runs(name) else ""), cmd.get_short_help_str(FULL)))
            if rows:
                with formatter.section(title):
                    formatter.write_text(purpose)
                    formatter.write_dl(rows)
        rest = [
            (n, c.get_short_help_str(FULL))
            for n in self.list_commands(ctx)
            if n not in listed and (c := self.get_command(ctx, n)) and not c.hidden
        ]
        if rest:
            with formatter.section("Other"):
                formatter.write_dl(rest)
        formatter.write_paragraph()
        formatter.write_text(AGENT_LEGEND)
