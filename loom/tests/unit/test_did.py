"""What it did (plan 0.14 phase 6): `run.log` is the session's record of what was done through loom, and `loom comment` says in it which annotation each line made or changed."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main


def run(*args: str, cwd: Path, stdin: str | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), input=stdin)
    finally:
        os.chdir(old)


@pytest.fixture
def q(tmp_path: Path) -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    return tmp_path / "q"


def lines(q: Path, sid: str) -> list[str]:
    from loom.sessions import files_dir, sessions

    return [line.split("  ", 1)[1] for line in (files_dir(q, sessions(q)[sid]) / "run.log").read_text().splitlines()]


def test_each_comment_logs_the_annotation_it_touched(q: Path) -> None:
    sid = run("session", "new", "a sitting", "--author", "A. Author", cwd=q).output.split()[0]
    who = ("--session", sid, "--author", "A. Author")
    made = run("comment", "dm-0003", "Which orbit?", "--quote", "finite set", "--kind", "question", *who, cwd=q)
    assert made.exit_code == 0, made.output
    first = made.output.split()[0]
    reply = run("comment", "--reply", first, "The fixed ones.", *who, cwd=q).output.split()[0]
    assert run("comment", "--resolve", first, "Settled.", *who, cwd=q).exit_code == 0
    assert run("comment", "--resolve", first, "--undo", *who, cwd=q).exit_code == 0
    assert run("comment", "--edit", first, "Which orbits?", *who, cwd=q).exit_code == 0
    assert run("comment", "--discard", reply, "Said elsewhere.", *who, cwd=q).exit_code == 0
    batch = "\n".join(
        json.dumps(x)
        for x in ({"target": "dm-0002", "message": "One.", "kind": "note"}, {"reply": first, "message": "Two."})
    )
    assert run("comment", "--batch", *who, cwd=q, stdin=batch).exit_code == 0
    got = lines(q, sid)
    assert got[:6] == [
        f"loom comment dm-0003 --quote --kind question → {first}",
        f"loom comment --reply {first} → {reply}",
        f"loom comment --resolve {first} → {first}",
        f"loom comment --resolve {first} --undo → {first}",
        f"loom comment --edit {first} → {first}",
        f"loom comment --discard {reply} → {reply}",
    ]
    assert got[6].startswith("loom comment dm-0002 --kind note → a-") and got[7].startswith(
        f"loom comment --reply {first} → a-"
    )
    # a refused comment did nothing, so it is not in the record
    assert run("comment", "dm-9999", "Nowhere.", *who, cwd=q).exit_code != 0
    assert len(lines(q, sid)) == 8


def test_the_manifest_carries_the_annotation_apart_from_the_command(q: Path) -> None:
    from loom.render.threads import build_threads
    from loom.sessions import files_dir, sessions

    sid = run("session", "new", "a sitting", "--author", "A. Author", cwd=q).output.split()[0]
    ann = run(
        "comment", "dm-0003", "Which orbit?", "--kind", "question", "--session", sid, "--author", "A. Author", cwd=q
    ).output.split()[0]
    with (files_dir(q, sessions(q)[sid]) / "run.log").open("a") as fh:
        fh.write("2026-09-01T00:00:00Z  loom source dm-0003\n")  # a line from before, or from any other command
    log = build_threads(q)[sid]["log"]
    assert log[0]["command"] == "loom comment dm-0003 --kind question" and log[0]["annotation"] == ann
    assert log[1] == {"time": "2026-09-01T00:00:00Z", "command": "loom source dm-0003"}


def test_refs_commands_log_their_arguments_as_typed(q: Path) -> None:
    """F10 of the 0.14 study: `loom refs coverage ('Bellamy',)` in the log, and so in the status line and What it did."""
    sid = run("session", "new", "a sitting", "--author", "A. Author", cwd=q).output.split()[0]
    assert run("refs", "coverage", "Calloway14", "--session", sid, cwd=q).exit_code in (0, 1)
    assert "loom refs coverage Calloway14" in lines(q, sid)


def test_code_is_quoted_as_written() -> None:
    """F11 of the 0.14 study: a quote of source in backticks had its `$…$` turned into `\\(…\\)`."""
    from loom.records.store import render_markdown

    got = render_markdown("Quote: `Let $\\quiv$ be` and $x$.")
    assert "<code>Let $\\quiv$ be</code>" in got and '<span class="math inline">\\(x\\)</span>' in got
