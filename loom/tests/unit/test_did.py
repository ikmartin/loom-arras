"""What it did (plan 0.14 phase 6): `run.log` is the session's record of what was done through loom, and `loom comment` says in it which annotation each line made or changed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers import ok, refused
from tests.unit._quilts import demo, new_session


@pytest.fixture
def q(tmp_path: Path) -> Path:
    return demo(tmp_path)


def lines(q: Path, sid: str) -> list[str]:
    from loom.sessions import files_dir, sessions

    return [line.split("  ", 1)[1] for line in (files_dir(q, sessions(q)[sid]) / "run.log").read_text().splitlines()]


def test_each_comment_logs_the_annotation_it_touched(q: Path) -> None:
    sid = new_session(q)
    who = ("--session", sid, "--author", "A. Author")
    made = ok("comment", "dm-0003", "Which orbit?", "--quote", "finite set", "--kind", "question", *who, cwd=q)
    first = made.output.split()[0]
    reply = ok("comment", "--reply", first, "The fixed ones.", *who, cwd=q).output.split()[0]
    ok("comment", "--resolve", first, "Settled.", *who, cwd=q)
    ok("comment", "--resolve", first, "--undo", *who, cwd=q)
    ok("comment", "--edit", first, "Which orbits?", *who, cwd=q)
    ok("comment", "--discard", reply, "Said elsewhere.", *who, cwd=q)
    batch = "\n".join(
        json.dumps(x)
        for x in ({"target": "dm-0002", "message": "One.", "kind": "note"}, {"reply": first, "message": "Two."})
    )
    ok("comment", "--batch", *who, cwd=q, stdin=batch)
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
    refused("comment", "dm-9999", "Nowhere.", *who, cwd=q, code=2, match="no such key: dm-9999")
    assert len(lines(q, sid)) == 8


def test_the_manifest_carries_the_annotation_apart_from_the_command(q: Path) -> None:
    from loom.render.threads import build_threads
    from loom.sessions import files_dir, sessions

    sid = new_session(q)
    ann = ok(
        "comment", "dm-0003", "Which orbit?", "--kind", "question", "--session", sid, "--author", "A. Author", cwd=q
    ).output.split()[0]
    with (files_dir(q, sessions(q)[sid]) / "run.log").open("a") as fh:
        fh.write("2026-09-01T00:00:00Z  loom source dm-0003\n")  # a line from before, or from any other command
    log = build_threads(q)[sid]["log"]
    assert log[0]["command"] == "loom comment dm-0003 --kind question" and log[0]["annotation"] == ann
    assert log[1] == {"time": "2026-09-01T00:00:00Z", "command": "loom source dm-0003"}


def test_refs_commands_log_their_arguments_as_typed(q: Path) -> None:
    """The log, and so the status line and What it did, shows a refs command as typed, not as a Python tuple (0.14 study F10)."""
    sid = new_session(q)
    ok("refs", "coverage", "Calloway14", "--session", sid, cwd=q)
    assert "loom refs coverage Calloway14" in lines(q, sid)
