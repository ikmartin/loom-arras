"""The terminal principles, held for every command (plan 0.18.3, book 1.10 and 12.1).

Every leaf command in the tree has a kind and its cases in `tests/output_cases`; each case runs on a fresh demo quilt, as text and, when the command takes it, with `--json`. A report leads with its verdict, keeps within 100 columns, and names no storage path and no hash; a refusal says `Error:` on stderr and nothing on stdout; `--json` is one envelope on stdout, on failure as on success; and every exit code is the case's, which is book 12.1's.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator

import click
import pytest

from loom.cli import main
from tests.helpers import describe, run
from tests.output_cases import CASES, KIND, Case
from tests.unit._quilts import demo

WIDTH = 100
HASH = re.compile(r"\b[0-9a-f]{12,}\b")


def leaves() -> Iterator[tuple[str, click.Command]]:
    """Every leaf command's path and the command, aliases included."""

    def walk(cmd: click.Command, path: list[str]) -> Iterator[tuple[str, click.Command]]:
        if isinstance(cmd, click.Group):
            for name, sub in cmd.commands.items():
                yield from walk(sub, [*path, name])
        else:
            yield " ".join(path), cmd

    yield from walk(main, [])


def takes_json(cmd: click.Command) -> bool:
    return any(isinstance(p, click.Option) and "--json" in p.opts for p in cmd.params)


COMMANDS = dict(leaves())
RUNS = [
    pytest.param(path, i, case, id=f"{path}[{i}]", marks=[pytest.mark.poppler] if case.poppler else [])
    for path, cases in sorted(CASES.items())
    for i, case in enumerate(cases)
]


def test_every_command_has_a_kind_and_its_cases() -> None:
    assert sorted(set(COMMANDS) - set(KIND)) == [], "commands with no kind in tests/output_cases"
    assert sorted(set(KIND) - set(COMMANDS)) == [], "kinds for commands that no longer exist"
    assert sorted(k for k in KIND if KIND[k] not in ("report", "raw", "running")) == []
    uncased = sorted(p for p, k in KIND.items() if k != "running" and not CASES.get(p))
    assert uncased == [], "commands with no case"


def test_every_command_that_reports_takes_json() -> None:
    """T8: whatever reports offers `--json`; a raw command takes it where its body has structure."""
    missing = sorted(p for p, k in KIND.items() if k == "report" and not takes_json(COMMANDS[p]))
    assert missing == [], "commands that report without --json"


def _env(case: Case) -> dict[str, str | None]:
    return dict(case.env)


@pytest.mark.parametrize(("path", "i", "case"), RUNS)
def test_the_text_leads_with_its_verdict_and_fits(path: str, i: int, case: Case, tmp_path) -> None:  # type: ignore[no-untyped-def]
    q = demo(tmp_path)
    case.setup(q)
    argv = [*path.split(), *case.args]
    r = run(*argv, cwd=q, env=_env(case))
    assert r.exit_code == case.exit, f"expected exit {case.exit}" + describe(argv, r)
    if not r.stdout.strip():
        # nothing on stdout: a refusal, said once on stderr in the one error style
        assert r.exit_code != 0, "succeeded and said nothing" + describe(argv, r)
        assert r.stderr.lstrip().startswith("Error: "), "a refusal not in the error style" + describe(argv, r)
        return
    if KIND[path] != "report":
        return
    lines = r.stdout.rstrip("\n").split("\n")
    assert lines[0].strip() and not lines[0].startswith(" "), "the first line is not a verdict" + describe(argv, r)
    long = [ln for ln in lines if len(ln) > WIDTH]
    assert long == [], f"lines over {WIDTH} columns" + describe(argv, r)
    text = r.stdout + r.stderr
    assert "digests/storage/" not in text, "a storage path in the text" + describe(argv, r)
    assert not HASH.search(r.stdout), f"a hash in the text: {HASH.search(r.stdout)}" + describe(argv, r)


JSON_RUNS = [p for p in RUNS if p.values[2].json and takes_json(COMMANDS[p.values[0]])]


@pytest.mark.parametrize(("path", "i", "case"), JSON_RUNS)
def test_json_is_one_envelope_on_stdout(path: str, i: int, case: Case, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """T8: stdout holds one JSON object carrying the verdict, whether the command succeeded or not."""
    q = demo(tmp_path)
    case.setup(q)
    argv = [*path.split(), *case.args, "--json"]
    r = run(*argv, cwd=q, env=_env(case))
    assert r.exit_code == case.exit, f"expected exit {case.exit}" + describe(argv, r)
    if not r.stdout.strip() and r.exit_code != 0:
        assert r.stderr.lstrip().startswith("Error: "), "a refusal not in the error style" + describe(argv, r)
        return
    try:
        doc = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"stdout is not one JSON document: {e}" + describe(argv, r)) from None
    assert isinstance(doc, dict), "--json printed something other than an object" + describe(argv, r)
    assert {"verdict", "ok", "exit"} <= set(doc), "not the envelope" + describe(argv, r)
    assert doc["exit"] == r.exit_code, "the envelope's exit is not the process's" + describe(argv, r)
