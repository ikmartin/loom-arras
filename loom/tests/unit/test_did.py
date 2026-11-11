"""What it did (plan 0.14 phase 6): `run.log` is the session's record of what was done through loom; an annotation is no session's, so `loom annotate` writes nothing there."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers import ok
from tests.unit._quilts import demo, new_session


@pytest.fixture
def q(tmp_path: Path) -> Path:
    return demo(tmp_path)


def lines(q: Path, sid: str) -> list[str]:
    from loom.sessions import files_dir, sessions

    return [line.split("  ", 1)[1] for line in (files_dir(q, sessions(q)[sid]) / "run.log").read_text().splitlines()]


def test_annotating_writes_nothing_into_the_active_session(q: Path) -> None:
    """Every verb of `loom annotate`, a batch among them, leaves the active session's log as it was and names no session in the annotation log."""
    from loom.sessions import files_dir, sessions

    sid = new_session(q)
    log = files_dir(q, sessions(q)[sid]) / "run.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("2026-09-01T00:00:00Z  loom source dm-0003\n")
    who = ("--as", "A. Author")
    made = ok("annotate", "dm-0003", "Which orbit?", "--quote", "finite set", "--type", "question", *who, cwd=q)
    first = made.output.split()[0]
    reply = ok("annotate", "--reply", first, "The fixed ones.", *who, cwd=q).output.split()[0]
    ok("annotate", "--resolve", first, "Settled.", *who, cwd=q)
    ok("annotate", "--resolve", first, "--undo", *who, cwd=q)
    ok("annotate", "--edit", first, "Which orbits?", *who, cwd=q)
    ok("annotate", "--delete", reply, *who, cwd=q)
    batch = "\n".join(
        json.dumps(x)
        for x in ({"target": "dm-0002", "message": "One.", "type": "note"}, {"reply": first, "message": "Two."})
    )
    ok("annotate", "--batch", *who, cwd=q, stdin=batch)
    assert lines(q, sid) == ["loom source dm-0003"]
    logged = [json.loads(x) for x in (q / ".loom/annotations" / "log.jsonl").read_text().splitlines()]
    assert logged and not [e for e in logged if "session" in e]


def test_the_manifest_carries_the_annotation_apart_from_the_command(q: Path) -> None:
    from loom.render.threads import build_threads
    from loom.sessions import files_dir, sessions

    sid = new_session(q)
    ann = ok("annotate", "dm-0003", "Which orbit?", "--type", "question", "--as", "A. Author", cwd=q).output.split()[0]
    where = files_dir(q, sessions(q)[sid])
    where.mkdir(parents=True, exist_ok=True)
    with (where / "run.log").open("a") as fh:
        # a logged annotate line names the annotation after its arrow; any other line is a command alone
        fh.write(f"2026-09-01T00:00:00Z  loom annotate dm-0003 --type question → {ann}\n")
        fh.write("2026-09-01T00:00:00Z  loom source dm-0003\n")
    log = build_threads(q)[sid]["log"]
    assert log[0]["command"] == "loom annotate dm-0003 --type question" and log[0]["annotation"] == ann
    assert log[1] == {"time": "2026-09-01T00:00:00Z", "command": "loom source dm-0003"}


def test_each_line_says_what_it_names_and_the_session_when_it_was_last_active(q: Path) -> None:
    from loom.render.threads import build_threads
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan
    from loom.sessions import files_dir, sessions

    sid = new_session(q)
    where = files_dir(q, sessions(q)[sid])
    where.mkdir(parents=True, exist_ok=True)
    with (where / "run.log").open("a") as fh:
        fh.write("2099-09-01T00:00:00Z  loom source dm-0003 --closure\n")
        fh.write("2099-09-02T00:00:00Z  loom compile drafting/main.tex\n")
        fh.write("2099-09-03T00:00:00Z  loom search orbit\n")
    log = build_threads(q, result=scan(load_quilt(q)))[sid]["log"]
    assert [e.get("names") for e in log] == [[{"key": "dm-0003"}], [{"path": "drafting/main.tex"}], None]
    ok("build", cwd=q)
    m = json.loads((q / ".loom/build/manifest.json").read_text())
    row = next(s for s in m["sessions"] if s["id"] == sid)
    # the newest of what was done in it, which opening it never moves
    assert row["last"] == "2099-09-03T00:00:00Z" and row["opened"] != row["last"]


def test_library_commands_log_their_arguments_as_typed(q: Path) -> None:
    """The log, and so the status line and What it did, shows a library command as typed, not as a Python tuple (0.14 study F10)."""
    sid = new_session(q)
    ok("library", "search", "widget", "--work", "Calloway14", "--work", "Man12", "--session", sid, cwd=q)
    [line] = lines(q, sid)
    assert line.startswith("loom library search ") and "(" not in line and "'" not in line, line
    assert {"widget", "Calloway14", "Man12"} <= set(line.split()), line
