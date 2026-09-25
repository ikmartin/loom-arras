"""Sessions (plan 0.13 §8, §16): made, switched, retitled, closed, resumed and tombstoned, from the CLI and from the viewer's API alike; a command given `--session` logs itself there."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.render.api import CAPABILITIES, ApiError, handle
from loom.sessions import active, close, create, resume, sessions, set_active
from tests.helpers import ok, refused
from tests.unit._quilts import demo, new_session

WHO = "A. Author"


def test_the_viewer_names_switches_retitles_closes_and_tombstones_a_session(tmp_path: Path) -> None:
    """The panel writes through the same functions `loom session` calls, so the two surfaces cannot spell an event differently. Closing or tombstoning the active session empties the active slot; a closed one refuses to close again; purging is not reachable from the viewer."""
    q = demo(tmp_path)
    first = ok("session", "new", "morning", "--author", WHO, cwd=q).stdout.split()[0]
    assert active(q) == first

    made = handle(q, "session-new", {"title": "afternoon", "author": WHO})
    assert made["ok"] and "(active)" in made["result"], made
    second = made["result"].split()[0]
    assert active(q) == second and sessions(q)[second].title == "afternoon"
    shut = handle(q, "session-close", {"session": second, "author": WHO})
    assert shut["ok"] and sessions(q)[second].state == "closed" and active(q) is None
    with pytest.raises(ApiError, match="is closed"):
        handle(q, "session-close", {"session": second, "author": WHO})

    assert handle(q, "session-use", {"session": "morning", "author": WHO})["ok"]
    assert active(q) == first
    assert handle(q, "session-rename", {"session": first, "title": "early pass", "author": WHO})["ok"]
    assert sessions(q)[first].title == "early pass"
    # a tombstone leaves the log alone and stops being the write target
    assert handle(q, "session-delete", {"session": first, "author": WHO})["ok"]
    assert first not in sessions(q)
    assert active(q) is None
    assert "session-purge" not in CAPABILITIES


def test_a_resumed_session_starts_a_new_round(tmp_path: Path) -> None:
    """A round is what "changed since last time" is measured from, so resuming must open one rather than continue the last."""
    q = demo(tmp_path)
    s = create(q, "morning", WHO)
    assert len(sessions(q)[s.id].rounds) == 1
    close(q, s.id, WHO)
    assert sessions(q)[s.id].state == "closed" and sessions(q)[s.id].rounds[-1].closed
    resume(q, s.id, WHO)
    again = sessions(q)[s.id]
    assert again.state == "open" and len(again.rounds) == 2
    assert again.last_opened == again.rounds[-1].opened


def test_id_and_new_log_themselves_to_the_session(tmp_path: Path) -> None:
    """The orientation lists both among an agent's commands and says every command that takes --session logs the call (F7)."""
    d = demo(tmp_path)
    sid = ok("ai", "start", "Drafting", cwd=d).stdout.strip()
    run_dir = d / ".loom" / "sessions" / sid
    ok("id", "--next", "--session", sid, cwd=d)
    ok("new", "lemma", "Rigidity", "--session", sid, cwd=d)
    log = (run_dir / "run.log").read_text()
    assert "loom id --next" in log and "loom new lemma" in log


# --- `loom session delete --purge`: the one command that rewrites the annotation log ---------------------------------


def written(q: Path, sid: str, target: str, body: str) -> str:
    """One note written into `sid` by `loom annotate`; its id."""
    return ok("annotate", target, body, "--session", sid, "--author", WHO, cwd=q).stdout.split()[0]


def purgeable(tmp_path: Path) -> tuple[Path, str, str, str]:
    """The demo with two new sessions: `gone`, holding a note that was edited, and `stays`, holding a note of its own, a reply to gone's and a resolve of it; then a line that is not JSON. `gone` is active. Returns the quilt, the two ids, and gone's note."""
    q = demo(tmp_path)
    gone = new_session(q, "false start", WHO)
    stays = new_session(q, "keeper", WHO)
    ann = written(q, gone, "dm-0003", "Wrong from the start.")
    ok("annotate", "--edit", ann, "Still wrong.", "--session", gone, "--author", WHO, cwd=q)
    written(q, stays, "dm-0001", "A note worth keeping.")
    ok("annotate", "--reply", ann, "An answer to it.", "--session", stays, "--author", WHO, cwd=q)
    ok("annotate", "--resolve", ann, "Done.", "--session", stays, "--author", WHO, cwd=q)
    with (q / "annotations" / "log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("not json, kept as it stands\n")
    (q / ".loom" / "sessions" / gone).mkdir(parents=True, exist_ok=True)
    (q / ".loom" / "sessions" / gone / "run.log").write_text("x\n")
    set_active(q, gone)
    return q, gone, stays, ann


def records(q: Path) -> tuple[bytes, bytes, str | None]:
    return (
        (q / "annotations" / "log.jsonl").read_bytes(),
        (q / ".loom" / "sessions" / "index.jsonl").read_bytes(),
        active(q),
    )


def test_purge_erases_a_session_what_was_written_in_it_and_what_answers_it_and_nothing_else(tmp_path: Path) -> None:
    """The session's log events and index events go, with any other session's event that names one of its annotations, which would otherwise name nothing; every other line, unparsable ones included, is kept byte for byte. Its directory goes, and it stops being active."""
    import json

    from loom.records.log import replay

    q, gone, stays, ann = purgeable(tmp_path)
    before = (q / "annotations" / "log.jsonl").read_text().splitlines(keepends=True)
    said = ok("session", "delete", gone, "--purge", "--yes", cwd=q)
    # the note and the reply to it: the edit and the resolve are events on an annotation, not annotations
    assert said.stdout.strip() == f"erased {gone} and 2 annotation(s) from annotations/log.jsonl"
    after = (q / "annotations" / "log.jsonl").read_text().splitlines(keepends=True)
    events = [json.loads(x) for x in after if x.startswith("{")]
    assert not [e for e in events if e.get("session") == gone or ann in (e.get("id"), e.get("reply_to"))]
    # nothing else is touched: what is kept is the old log with the erased lines taken out, in order
    assert [x for x in before if x in after] == after
    assert "not json, kept as it stands\n" in after
    assert [e["body"] for e in events if e.get("session") == stays] == ["A note worth keeping."]
    assert len(after) == len(before) - 4
    # the log no longer names anything it does not hold
    assert [p for p in replay(q)[1] if "unknown annotation" in p] == []
    assert gone not in sessions(q, deleted=True) and stays in sessions(q)
    assert gone not in (q / ".loom" / "sessions" / "index.jsonl").read_text()
    assert not (q / ".loom" / "sessions" / gone).exists()
    assert active(q) is None


def test_purge_leaves_another_active_session_active(tmp_path: Path) -> None:
    q, gone, stays, _ = purgeable(tmp_path)
    set_active(q, stays)
    ok("session", "delete", gone, "--purge", "--yes", cwd=q)
    assert active(q) == stays


def test_purge_refuses_without_a_yes_where_nobody_can_answer(tmp_path: Path) -> None:
    """Off a terminal there is nobody to ask, so `--purge` without `--yes` refuses, counting what it would have erased, and changes nothing."""
    q, gone, _, _ = purgeable(tmp_path)
    was = records(q)
    refused(
        "session",
        "delete",
        gone,
        "--purge",
        cwd=q,
        code=2,
        match="erases 2 annotation(s) and cannot be undone; pass --yes",
    )
    assert records(q) == was and (q / ".loom" / "sessions" / gone).is_dir()


@pytest.mark.parametrize("answer", ["n", "y"])
def test_purge_at_a_terminal_asks_first(tmp_path: Path, answer: str) -> None:
    """At a terminal `--purge` counts what it will erase and asks; anything but yes aborts and changes nothing."""
    import os
    import pty
    import subprocess
    import sys

    q, gone, _, _ = purgeable(tmp_path)
    was = records(q)
    main, tty = pty.openpty()
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "loom", "session", "delete", gone, "--purge", "--author", WHO],
            cwd=q,
            stdin=tty,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        os.write(main, f"{answer}\n".encode())
        out, err = proc.communicate(timeout=60)
    finally:
        os.close(main)
        os.close(tty)
    said = out.decode() + err.decode()
    assert f"--purge erases {gone} and the 2 annotation(s)" in said, said
    if answer == "n":
        assert proc.returncode == 1 and "Aborted" in said, said
        assert records(q) == was
    else:
        assert proc.returncode == 0 and f"erased {gone}" in said, said
        assert gone not in sessions(q, deleted=True)
