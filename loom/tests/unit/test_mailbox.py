"""A session's mailbox and who is listening to it (plan 0.13 §8, §11): posts, cursors, heartbeats, and a parked `session next` waking."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from loom.mailbox import (
    ATTACHED,
    attach,
    attached,
    cursor,
    detach,
    pending,
    post,
    read_events,
    session_dir,
    set_cursor,
    waiting_on,
)
from loom.render.api import handle
from loom.sessions import create, sessions
from tests.helpers import ok
from tests.unit._quilts import demo, new_session

WHO = "A. Author"


def test_a_post_lands_with_nobody_listening_is_read_not_consumed_and_carries_what_changed(tmp_path: Path) -> None:
    """The viewer's composer and `loom session send` are one mechanism: both append, and both say who was listening. Refusing a message because nobody is attached would lose what the author typed; a post says what changed since the last one, so a parked agent needs no second call to learn what it is being asked about."""
    q = demo(tmp_path)
    sid = new_session(q, "referee pass", WHO)
    ok("comment", "dm-0002", "Orbits may be empty.", "--author", WHO, cwd=q)
    assert attached(q, sid) == []
    said = handle(q, "message", {"session": sid, "text": "Have a look at dm-0003.", "author": WHO})
    assert said["ok"] and said["session"] == sid and said["attached"] == []
    first = read_events(q, sid)
    assert [e.body for e in first] == ["Have a look at dm-0003."]
    assert [c["target"] for c in first[-1].changed] == ["dm-0002"]
    assert first[-1].changed[0]["by"] == WHO and first[-1].changed[0]["act"] == "created"

    # read, never consumed: a cursor moves and the message stays, so a second reader sees it and a crashed one resumes
    assert [e.body for e in read_events(q, sid, cursor(q, sid, "Referee Agent"))] == ["Have a look at dm-0003."]
    set_cursor(q, sid, "Referee Agent", first[-1].seq)
    assert read_events(q, sid, cursor(q, sid, "Referee Agent")) == []
    assert [e.body for e in read_events(q, sid, cursor(q, sid, "Tutor Agent"))] == ["Have a look at dm-0003."]

    attach(q, sid, "Referee Agent", "agent")
    again = handle(q, "message", {"session": sid, "text": "And the hypothesis.", "author": WHO})
    assert [r["who"] for r in again["attached"]] == ["Referee Agent"]
    # and the next post carries only what changed after the last one, rather than repeating itself
    assert read_events(q, sid)[-1].changed == []


def test_a_quiet_heartbeat_is_a_reader_at_work_and_not_one_listening(tmp_path: Path) -> None:
    """A reader that was killed writes no farewell, so a stale beat is not believed as listening; but the beat is written only while `session next` is parked, so a reader doing what it was asked is quiet too, and the composer must not tell its author to go and start a watcher."""
    q = demo(tmp_path)
    sid = create(q, "reading", WHO).id
    never = waiting_on(q, sid, WHO)
    assert "nobody is attached" in never and f"loom session watch {sid}" in never

    attach(q, sid, "Referee (Agent)", "agent")
    assert [r["who"] for r in attached(q, sid)] == ["Referee (Agent)"]
    assert waiting_on(q, sid, WHO) == ""  # somebody is listening; there is nothing to say

    p = session_dir(q, sid) / ATTACHED
    rows = json.loads(p.read_text())
    rows[0]["beat"] = "2020-01-01T00:00:00Z"
    p.write_text(json.dumps(rows))
    assert attached(q, sid) == []
    busy = waiting_on(q, sid, WHO)
    assert "Referee (Agent)" in busy and "probably working" in busy
    assert "session watch" not in busy

    attach(q, sid, "Referee (Agent)", "agent")
    detach(q, sid, "Referee (Agent)")
    assert attached(q, sid) == []


def test_an_agent_parked_on_session_next_wakes_when_a_message_lands_with_what_changed(tmp_path: Path) -> None:
    """The dispatch round trip against a fake agent (plan 0.13 §11): a real `loom session next --wait` process parked in the background, a post through the mailbox, and the process returning at once with the message and the changed-annotation block, not when its wait runs out.

    Parked is observed, not assumed: the process attaches before it waits, so the test posts only once its row is in `attached.json`. The row's beat carries the fixed clock, hence `stale=True`.
    """
    q = demo(tmp_path)
    sid = new_session(q, "reading", WHO)
    asked = ("comment", "dm-0003", "Is this the balanced case?", "--kind", "question")
    ok(*asked, "--session", sid, "--author", WHO, cwd=q)
    env = {**os.environ, "LOOM_FIXED_TIME": "2026-09-21T12:00:00Z"}
    agent = subprocess.Popen(
        [
            sys.executable, "-m", "loom", "session", "next", "--wait", "20", "--json",
            "--as", "Referee (Agent)", "--session", sid, "--quilt", str(q),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=q,
    )  # fmt: skip
    try:
        deadline = time.monotonic() + 15
        while not any(r["who"] == "Referee (Agent)" for r in attached(q, sid, stale=True)):
            assert agent.poll() is None, "the agent returned before anything landed: " + agent.communicate()[0]
            assert time.monotonic() < deadline, "the agent never attached"
            time.sleep(0.05)
        t0 = time.monotonic()
        changed = pending(q, sessions(q)[sid], WHO)
        post(q, sid, "Have another look at the balanced case.", WHO, kind="message", changed=changed)
        out, err = agent.communicate(timeout=15)
    finally:
        if agent.poll() is None:
            agent.kill()
    woke = time.monotonic() - t0
    assert agent.returncode == 0, err
    assert woke < 5, f"a parked agent took {woke:.1f}s to wake"
    got = json.loads(out)
    assert "Have another look" in got["text"]
    carried = got["events"][-1].get("changed") or []
    assert any("Is this the balanced case" in (c.get("body") or "") for c in carried), got


def test_session_next_returns_empty_handed_when_its_wait_runs_out(tmp_path: Path) -> None:
    """With nothing waiting, `next` parks for `--wait` seconds and then says so, leaving the cursor where it was; `--json` says the same as an empty span."""
    q = demo(tmp_path)
    sid = new_session(q, "quiet", WHO)
    who = ("--session", sid, "--as", "Probe Agent")
    t0 = time.monotonic()
    assert ok("session", "next", "--wait", "1", *who, cwd=q).stdout == "nothing yet\n"
    assert time.monotonic() - t0 >= 1, "returned before its wait ran out"
    got = json.loads(ok("session", "next", "--wait", "0", "--json", *who, cwd=q).stdout)
    assert (got["session"], got["from"], got["to"], got["events"], got["text"]) == (sid, 0, 0, [], "")
    assert cursor(q, sid, "Probe Agent") == 0


def test_session_next_since_reads_from_a_sequence_number_and_moves_the_cursor(tmp_path: Path) -> None:
    q = demo(tmp_path)
    sid = new_session(q, "busy", WHO)
    for body in ("one", "two", "three"):
        post(q, sid, body, WHO, kind="message")
    who = ("--session", sid, "--as", "Probe Agent")
    got = json.loads(ok("session", "next", "--wait", "0", "--json", "--since", "1", *who, cwd=q).stdout)
    assert [e["body"] for e in got["events"]] == ["two", "three"] and (got["from"], got["to"]) == (1, 3)
    assert cursor(q, sid, "Probe Agent") == 3
    assert ok("session", "next", "--wait", "0", *who, cwd=q).stdout == "nothing yet\n"


def test_session_watch_prints_what_lands_while_listening_and_detaches_on_interrupt(tmp_path: Path) -> None:
    """A person tailing a session: what was said before it started is not reprinted, what lands is, the watcher counts as listening while it runs, and Ctrl-C ends it cleanly and takes its heartbeat with it."""
    import signal

    q = demo(tmp_path)
    sid = new_session(q, "tailing", WHO)
    post(q, sid, "Said before anyone watched.", WHO, kind="message")
    watcher = subprocess.Popen(
        [sys.executable, "-m", "loom", "session", "watch", sid, "--as", "A Watcher"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=q,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    try:
        deadline = time.monotonic() + 15
        while not any(r["who"] == "A Watcher" for r in attached(q, sid, stale=True)):
            assert watcher.poll() is None, "the watcher exited: " + watcher.communicate()[1]
            assert time.monotonic() < deadline, "the watcher never attached"
            time.sleep(0.05)
        assert [r["kind"] for r in attached(q, sid) if r["who"] == "A Watcher"] == ["person"]
        post(q, sid, "Anyone there?", "Someone Else", kind="message")
        assert watcher.stdout is not None
        line = watcher.stdout.readline()  # blocks until the watcher prints; the timeout below bounds the test
        assert line.rstrip().endswith("Someone Else: Anyone there?"), line
        watcher.send_signal(signal.SIGINT)
        out, err = watcher.communicate(timeout=15)
    finally:
        if watcher.poll() is None:
            watcher.kill()
    assert watcher.returncode == 0, err
    assert "Said before anyone watched." not in line + out
    assert f"watching {sid} (tailing) as A Watcher" in err
    assert not [r for r in attached(q, sid, stale=True) if r["who"] == "A Watcher"]
