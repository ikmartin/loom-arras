"""`loom --help` by task (K6): every command in one section, every first line a sentence, and bare `loom` the help with exit 0."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

import click
import pytest

from loom.ai.layout import AGENT_COMMANDS, command_tree
from loom.cli import main
from loom.cli.help import SECTIONS
from tests.helpers import run


def commands(cmd: click.Command, path: list[str]) -> Iterator[tuple[str, click.Command]]:
    if path:
        yield " ".join(path), cmd
    if isinstance(cmd, click.Group):
        for name, sub in cmd.commands.items():
            yield from commands(sub, [*path, name])


def test_every_command_is_in_exactly_one_section() -> None:
    listed = Counter(n for _, _, names in SECTIONS for n in names)
    assert sorted(n for n, k in listed.items() if k > 1) == [], "listed twice"
    assert sorted(set(main.commands) - set(listed)) == [], "in no section"
    assert sorted(set(listed) - set(main.commands)) == [], "sections naming no command"


def test_every_first_help_line_is_a_sentence() -> None:
    bad = sorted(p for p, c in commands(main, []) if not c.get_short_help_str(10_000).endswith("."))
    assert bad == [], "first help lines that are not sentences"


def test_every_option_says_what_it_is() -> None:
    bare = sorted(
        f"{p} {o.opts[0]}"
        for p, c in commands(main, [])
        for o in c.params
        if isinstance(o, click.Option) and not o.help and o.opts[0] not in ("--help", "-h")
    )
    assert bare == [], "options without help"


def test_bare_loom_is_the_help_and_succeeds(tmp_path) -> None:  # type: ignore[no-untyped-def]
    r = run(cwd=tmp_path)
    assert r.exit_code == 0
    assert "Start:" in r.stdout and "Upkeep:" in r.stdout


def test_every_group_lists_its_commands_by_whole_first_sentence() -> None:
    from loom.cli.help import CommandGroup, LoomGroup

    groups = [p for p, c in commands(main, []) if isinstance(c, click.Group)]
    assert groups, "no groups found"
    plain = sorted(p for p, c in commands(main, []) if isinstance(c, click.Group) and not isinstance(c, CommandGroup))
    assert isinstance(main, LoomGroup)
    assert plain == [], "groups whose help cuts its commands' first sentences"


@pytest.mark.parametrize("group", ["sync", "ai", "session"])
def test_a_bare_group_prints_its_help_and_succeeds(group: str, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A group named alone asks for its help (T7): the help on stdout, exit 0, and no `Error:`."""
    r = run(group, cwd=tmp_path)
    assert r.exit_code == 0, r.output
    assert r.stdout.startswith("Usage: ") and f" {group} " in r.stdout.splitlines()[0] and "Commands:" in r.stdout
    assert "Error" not in r.output


#: An option no command has: a command the guard lets through refuses it while parsing, so its message says which happened.
PROBE = "--no-such-option-k5"


@pytest.mark.parametrize("path", sorted(c for c in command_tree() if c not in AGENT_COMMANDS))
def test_an_agent_may_not_run_an_author_command(path: str, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """K5: under an agent marker every command outside `AGENT_COMMANDS` refuses, exit 2, naming ai/rules.md, before it parses anything."""
    r = run(*path.split(), PROBE, cwd=tmp_path, env={"AI_AGENT": "1"})
    assert r.exit_code == 2, r.output
    assert f"may not run `loom {path}`" in r.stderr and "ai/rules.md" in r.stderr, r.output
    assert "No such option" not in r.output and r.stdout == ""


@pytest.mark.parametrize("path", sorted(AGENT_COMMANDS))
def test_an_agent_reaches_its_own_commands(path: str, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """K5's other half: every command in `AGENT_COMMANDS` gets past the guard to its own parsing under an agent marker."""
    r = run(*path.split(), PROBE, cwd=tmp_path, env={"AI_AGENT": "1"})
    assert "may not run" not in r.output
    assert "No such option" in r.stderr, r.output


def test_the_guard_reads_options_before_a_subcommand(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A group's own options before the subcommand do not hide which command runs: `library --session S add` is `library add`."""
    r = run("library", "--session", "x", "add", PROBE, cwd=tmp_path, env={"AI_AGENT": "1"})
    assert r.exit_code == 2 and "may not run `loom library add`" in r.stderr, r.output
    r = run("library", "--json", "search", PROBE, cwd=tmp_path, env={"AI_AGENT": "1"})
    assert "No such option" in r.stderr, r.output


def test_an_agent_may_read_the_help_of_any_command(tmp_path) -> None:  # type: ignore[no-untyped-def]
    r = run("upgrade", "--help", cwd=tmp_path, env={"AI_AGENT": "1"})
    assert r.exit_code == 0 and r.stdout.startswith("Usage: ") and " upgrade " in r.stdout.splitlines()[0], r.output


@pytest.mark.parametrize(
    ("typed", "replacement"),
    [
        ("review", "loom build"),
        ("review", "loom status --stale"),
        ("inline", "loom linearize"),
        ("unravel", "loom downstream"),
        ("reach", "loom downstream"),
        ("pop", "loom downstream"),
        ("refs", "loom library"),
        ("digest", "loom library"),
        ("agent check", "loom doctor --agents"),
        ("ai start", "loom session new"),
        ("ai name", "loom session rename"),
        ("ai check", "loom ai drafts"),
        ("session send", "loom session say"),
        ("sync patch", "loom sync status --patch"),
    ],
)
def test_a_removed_command_is_answered_by_its_replacement(typed: str, replacement: str, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """K1: a command loom no longer has is answered, exit 2, by the one that does its work."""
    r = run(*typed.split(), "x", cwd=tmp_path)
    assert r.exit_code == 2, r.output
    assert r.stdout == "" and r.stderr.startswith(f"Error: `loom {typed}`"), r.output
    assert replacement in r.stderr, r.output


def test_delete_names_what_was_typed_and_what_to_remove(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """`delete`, `rm` and `remove` name the argument; a result inside a document is removed as its environment, one in a file of its own with the file."""
    from tests.unit._quilts import demo

    q = demo(tmp_path)
    inside = run("rm", "dm-0004", cwd=q)
    assert inside.exit_code == 2 and inside.stdout == "", inside.output
    assert "dm-0004" in inside.stderr and "drafting/main.tex" in inside.stderr
    assert "environment" in inside.stderr and "loom downstream dm-0004" in inside.stderr
    own = run("delete", "dm-0001", cwd=q)
    assert own.exit_code == 2 and "nodes/dm-0001.tex" in own.stderr and "loom downstream dm-0001" in own.stderr
    assert "environment" not in own.stderr
    other = run("remove", "notes.txt", cwd=q)
    assert other.exit_code == 2 and "notes.txt" in other.stderr


def test_outside_a_quilt_names_how_to_get_into_one(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """T3: the refusal names `cd` and `loom init DIR`."""
    r = run("status", cwd=tmp_path)
    assert r.exit_code == 2 and r.stderr.startswith("Error: not inside a quilt"), r.output
    assert "cd " in r.stderr and "loom init DIR" in r.stderr, r.stderr
