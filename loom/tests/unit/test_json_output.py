"""Book 12.1's rule for `--json`: stdout is one JSON document and nothing else, whatever the command also has to say on stderr.

Every command in the tree that takes `--json` is run on a fresh demo with the least it needs; `test_every_json_command_is_covered` fails when a command gains `--json` without a row here.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import click
import pytest

from loom.cli import main
from tests.helpers import describe, run
from tests.unit._quilts import demo

Setup = Callable[[Path], None]


def solo_spine(q: Path) -> None:
    """A spine that shares no node with another document, which is what `linearize` accepts."""
    (q / "drafting" / "solo.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\input{drafting/solo-part}\n\\end{document}\n", encoding="utf-8"
    )
    (q / "drafting" / "solo-part.tex").write_text("Words.\n", encoding="utf-8")


def nothing(_: Path) -> None:
    return None


#: command path -> (arguments before `--json`, setup, exit code); each runs on its own fresh demo.
CASES: dict[str, tuple[list[str], Setup, int]] = {
    "ai annotations": ([], nothing, 0),
    "atomize": (["--key", "dm-0004"], nothing, 0),
    "canonicalize": (["drafting/main.tex", "--message", "m"], nothing, 0),
    "canonise": (["drafting/main.tex", "--message", "m"], nothing, 0),
    "canonize": (["drafting/main.tex", "--message", "m"], nothing, 0),
    "deps": (["dm-0003"], nothing, 0),
    "doctor": ([], nothing, 0),
    "downstream": (["dm-0001"], nothing, 0),
    "fork": (["dm-0001", "--in", "drafting/main.tex"], nothing, 0),
    "history": ([], nothing, 0),
    "id": (["--next"], nothing, 0),
    "linearize": (["drafting/solo.tex", "--to", "drafting/flat.tex"], solo_spine, 0),
    "lint": ([], nothing, 0),
    "pop": (["dm-0001"], nothing, 0),
    "reach": (["dm-0001"], nothing, 0),
    "refs build": ([], nothing, 0),
    "refs coverage": ([], nothing, 0),
    "refs find": (["widget"], nothing, 0),
    "refs grep": (["involution"], nothing, 0),
    "refs ingest": (["refs"], nothing, 0),
    "refs links": ([], nothing, 0),
    "refs locate": (["Calloway14", "Fixed loci of involutions", "--page", "1"], nothing, 0),
    "refs match": ([], nothing, 0),
    "refs page": (["Calloway14", "1"], nothing, 0),
    "refs propose": (
        [
            "Calloway14",
            "--local",
            "rem-9.1",
            "--level",
            "1",
            "--page",
            "1",
            "--source-text",
            "An involution of a topological space fixes a subspace",
            "--statement",
            "S",
        ],
        nothing,
        0,
    ),
    "refs recheck": ([], nothing, 0),
    "refs why": (["Calloway14-prop-3.2"], nothing, 0),
    "revert": (["dm-0001@1"], nothing, 0),
    "search": (["widget"], nothing, 0),
    "session list": ([], nothing, 0),
    "session next": (["--wait", "0", "--as", "Probe Agent"], nothing, 0),
    "stamp": (["--message", "m"], nothing, 0),
    "status": ([], nothing, 0),
    "unravel": (["dm-0001"], nothing, 0),
}

#: What reads a PDF's word boxes or first pages, which needs the real pdftotext.
POPPLER = {"refs ingest", "refs locate"}

#: Commands that cannot run offline, and why.
SKIPS = {
    "refs resolve": "it sends the bibliography's titles and authors to a lookup service; nothing it prints can be had offline",
}


def json_commands() -> Iterator[str]:
    """Every command path in the tree with a `--json` option, hidden ones included."""

    def walk(cmd: click.Command, path: list[str]) -> Iterator[str]:
        if isinstance(cmd, click.Group):
            for name, sub in cmd.commands.items():
                yield from walk(sub, [*path, name])
        elif any(isinstance(p, click.Option) and "--json" in p.opts for p in cmd.params):
            yield " ".join(path)

    yield from walk(main, [])


def test_every_json_command_is_covered() -> None:
    have = set(json_commands())
    assert sorted(have - set(CASES) - set(SKIPS)) == [], "commands with --json and no case in test_json_output"
    assert sorted((set(CASES) | set(SKIPS)) - have) == [], "cases for commands that no longer take --json"


@pytest.mark.parametrize(
    "command", [pytest.param(c, marks=pytest.mark.poppler) if c in POPPLER else c for c in sorted(CASES)]
)
def test_json_puts_one_document_on_stdout_and_nothing_else(command: str, tmp_path: Path) -> None:
    """The whole of stdout parses as one JSON value; `json.loads` refuses anything before or after it."""
    args, setup, code = CASES[command]
    q = demo(tmp_path)
    setup(q)
    argv = [*command.split(), *args, "--json"]
    r = run(*argv, cwd=q)
    assert r.exit_code == code, f"expected exit {code}" + describe(argv, r)
    assert r.stdout.strip(), "--json printed nothing" + describe(argv, r)
    try:
        json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"stdout is not one JSON document: {e}" + describe(argv, r)) from None
