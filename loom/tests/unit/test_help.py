"""`loom --help` by task (K6): every command in one section, every first line a sentence, and bare `loom` the help with exit 0."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

import click

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
