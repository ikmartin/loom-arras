"""The `loom` group itself: how `loom --help` reads (K6) and what it answers for a name that is not a command."""

from __future__ import annotations

from pathlib import Path

import click

from loom.cli._common import EnvError, agent_marker, is_agent

#: Names a person reaches for that loom answers with a reason rather than a command (K1: a refusal is a line of help); `delete_answer` says it for what was typed.
DELETE = ("delete", "rm", "remove")

#: Commands loom no longer has, by the path a person types, each answered with the command that does its work (K1).
REMOVED = {
    "review": "`loom build` reports what needs review, and `loom status --stale` lists it",
    "inline": "`loom linearize SPINE` writes a document with its inclusions inlined",
    "unravel": "`loom downstream ID` shows what depends on a node and where it is included",
    "reach": "`loom downstream ID` shows what a node reaches and where it is included",
    "pop": "`loom downstream ID` shows where a node is included",
    "refs": "`loom library` reports the cited works; `loom library --help` lists its commands",
    "digest": "`loom library` holds the results taken from cited works; `loom library --help` lists its commands",
    "agent": "`loom doctor --agents` checks the agent loom serve would start",
    "agent check": "`loom doctor --agents` checks the agent loom serve would start",
    "ai start": '`loom session new --name "a name"` opens a session',
    "ai name": '`loom session rename WHICH --name "a name"` names one',
    "ai check": "loom cannot tell an agent's writes by their times; `loom ai drafts` lists its documents and what moved",
    "session send": "`loom session say` sends a message, with what you marked",
    "sync patch": "`loom sync status --patch` prints the incoming revision as a patch",
}


def removed_answer(path: str) -> str:
    """The refusal for a removed command: what it was, and what does its work now."""
    return f"`loom {path}` is gone: {REMOVED[path]}."


def delete_answer(args: list[str]) -> str:
    """The answer to `delete`, `rm` or `remove`, naming what was typed: a result in a file of its own goes with its file and `\\input` line, one inside a document as its environment."""
    typed = next((a for a in args if not a.startswith("-")), None)
    how = "after `loom downstream {}` shows what depends on it"
    if typed is None:
        return f"loom will not delete your notes; do it yourself with rm, {how.format('ID')}."
    try:
        from loom.cli._quilt import open_scan, resolve_key

        result = open_scan(None)
        key = resolve_key(result, typed)
        node = result.nodes[key]
    except (click.ClickException, KeyError):
        return f"loom will not delete your notes: remove {typed} yourself, {how.format('ID')}."
    if Path(node.file).stem == key:
        return f"loom will not delete your notes: {key} is {node.file}; remove the file and its \\input line yourself, {how.format(key)}."
    what = node.taxon or node.kind
    return f"loom will not delete your notes: {key} is a {what.lower()} inside {node.file}; remove its environment there, not the file, {how.format(key)}."


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
    ("Library", "The papers you cite and the results taken from them.", ("library",)),
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


def _path(ctx: click.Context) -> list[str]:
    """The command path below the root, as typed: `loom` under whatever name invoked the root (`main` under a test runner)."""
    return ctx.command_path.split()[1:]


class CommandGroup(click.Group):
    """A command group whose help lists each subcommand with its first sentence whole, as `loom --help` does (K6); every group but the top level's is one.

    Named alone it prints its help with exit 0, as bare `loom` does; a removed subcommand is answered with what replaced it (`REMOVED`).
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if not args and self.no_args_is_help and not ctx.resilient_parsing:
            click.echo(ctx.get_help(), color=ctx.color)
            ctx.exit(0)
        return super().parse_args(ctx, args)

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        typed = " ".join([*_path(ctx), args[0]]) if args else ""
        if args and args[0] not in self.commands and typed in REMOVED:
            raise EnvError(removed_answer(typed))
        return super().resolve_command(ctx, args)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        rows = [
            (n, c.get_short_help_str(FULL))
            for n in self.list_commands(ctx)
            if (c := self.get_command(ctx, n)) and not c.hidden
        ]
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)


def command_path(group: click.Group, args: list[str]) -> tuple[str, bool]:
    """(the path of the command `args` would run, whether it runs) read off the tree without parsing: a group's own options are stepped over, and a word no subcommand has ends the path at its group.

    A group that runs on its own (`history`, `library`) runs; one that only holds subcommands does not, and click answers it.
    """
    path: list[str] = []
    cmd: click.Command = group
    i = 0
    while isinstance(cmd, click.Group) and i < len(args):
        word = args[i]
        if word == "--":
            break
        if word.startswith("-"):
            opt = next((p for p in cmd.params if isinstance(p, click.Option) and word.split("=", 1)[0] in p.opts), None)
            if opt is None:
                break
            i += 1 if "=" in word or opt.is_flag or opt.count else 2
            continue
        sub = cmd.commands.get(word)
        if sub is None:
            break
        path.append(word)
        cmd = sub
        i += 1
    runs = bool(path) and (not isinstance(cmd, click.Group) or cmd.invoke_without_command)
    return " ".join(path), runs


def refuse_agent(group: click.Group, args: list[str]) -> None:
    """K5's one guard: under an agent marker, a command outside `AGENT_COMMANDS` refuses before anything is parsed.

    Its help alone (`loom X --help`) is answered, since it writes nothing. The per-command `refuse_under_agent` calls stay for a declared agent name without a marker.
    """
    marker = agent_marker()
    if marker is None:
        return
    from loom.ai.layout import AGENT_COMMANDS

    path, runs = command_path(group, args)
    if not runs or path in AGENT_COMMANDS or args[len(path.split()) :] in (["--help"], ["-h"]):
        return
    declared = next(
        (
            word.split("=", 1)[1] if "=" in word else (args[i + 1] if i + 1 < len(args) else "")
            for i, word in enumerate(args)
            if word.split("=", 1)[0] in ("--as", "--author")
        ),
        None,
    )
    named = (
        ""
        if declared is None
        else f", and {declared} is an agent"
        if is_agent(declared)
        else ", whatever --author or --as says"
    )
    raise EnvError(
        f"an agent is running this shell ({marker} is set) and may not run `loom {path}`, which is the author's{named}; "
        "ai/rules.md lists what it may."
    )


class LoomGroup(click.Group):
    """The top-level group: its help in task sections, bare `loom` printing it with exit 0, K5's agent guard, and a removed or refused name answered with its reason and exit 2."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if not args:
            click.echo(ctx.get_help(), color=ctx.color)
            ctx.exit(0)
        refuse_agent(self, args)
        return super().parse_args(ctx, args)

    def invoke(self, ctx: click.Context) -> object:
        try:
            return super().invoke(ctx)
        except click.UsageError as e:
            # click prints a usage block before its `Error:`; a refusal is one line (book 12.1), naming the help instead
            where = f"; see `{' '.join(['loom', *_path(e.ctx)])} --help`." if e.ctx is not None else ""
            raise EnvError(e.format_message().rstrip(".") + where) from None

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        if args and args[0] in DELETE:
            raise EnvError(delete_answer(args[1:]))
        if args and args[0] not in self.commands:
            typed = " ".join(args[:2])
            if typed in REMOVED or args[0] in REMOVED:
                raise EnvError(removed_answer(typed if typed in REMOVED else args[0]))
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
