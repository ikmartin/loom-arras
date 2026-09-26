"""Launching (plan 0.14 phase 5): `loom serve` starts the person's own agent command for one turn when a message waits and nobody is listening -- never an API, never a command the quilt carries."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import ok, refused
from tests.unit._fakes import FakeHandler, configure, sleeper
from tests.unit._quilts import demo, new_session


@pytest.fixture
def q(tmp_path: Path) -> Path:
    return demo(tmp_path)


def finish(launcher: Any, sid: str, timeout: float = 60) -> None:
    """Wait for the session's turn to end, then let the launcher see it end.

    A turn still running at `timeout` fails the test with the session's agent.log, which is where the turn's own output went.
    """
    from loom.mailbox import session_dir

    proc = launcher.running.get(sid)
    try:
        if proc is not None:
            proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        log = session_dir(launcher.root, sid) / "agent.log"
        said = log.read_text(encoding="utf-8") if log.exists() else "(no agent.log)"
        pytest.fail(f"the turn in {sid} was still running after {timeout}s\n--- agent.log\n{said}")
    launcher.tick()


def test_the_quilt_file_wins_over_the_user_config_key_by_key(q: Path, home: Path) -> None:
    from loom.agent import load

    user = home / ".config" / "loom" / "config.toml"
    user.parent.mkdir(parents=True, exist_ok=True)
    user.write_text('[agent]\nname = "Home Agent"\nstart = ["home"]\n')
    (q / "ai" / "ai-config.toml").write_text('name = "Quilt Agent"\n')
    cfg, problems = load(q)
    assert problems == [] and cfg is not None
    assert (cfg.name, cfg.start) == ("Quilt Agent", ["home"])
    (q / "ai" / "ai-config.toml").write_text('name = "Wren"\n')
    _, problems = load(q)
    assert any("Agent or AI" in p for p in problems)
    user.write_text("")
    (q / "ai" / "ai-config.toml").write_text('name = "Quilt Agent"\n')
    _, problems = load(q)
    assert any("start" in p for p in problems)


def test_placeholders_are_filled_item_by_item() -> None:
    from loom.agent import argv

    got = argv(
        ["claude", "-p", "{prompt}", "--session-id", "{agent_session}"], prompt="say $(rm -rf) {x}", agent_session="u"
    )
    assert got == ["claude", "-p", "say $(rm -rf) {x}", "--session-id", "u"]


def test_a_filled_value_is_never_filled_again() -> None:
    """A quilt path or a message that happens to hold a placeholder goes in as written, whatever order the values are given in."""
    from loom.agent import argv

    got = argv(["{quilt}", "{prompt}"], quilt="/q/{prompt}", prompt="read {quilt}")
    assert got == ["/q/{prompt}", "read {quilt}"]
    assert argv(["{quilt}"], prompt="p", quilt="/q/{prompt}") == ["/q/{prompt}"]


def test_nothing_starts_while_launching_is_off(q: Path) -> None:
    from loom.agent import Launcher
    from loom.mailbox import post

    configure(q, launch=False)
    sid = new_session(q)
    post(q, sid, "Anyone?", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    assert launcher.running == {}


def test_a_message_starts_a_turn_and_the_next_one_resumes(q: Path) -> None:
    from loom.agent import Launcher, state
    from loom.mailbox import post, read_events

    configure(q)
    sid = new_session(q)
    post(q, sid, "Have a look.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    assert sid in launcher.running and state(q, sid)["state"] == "running"
    finish(launcher, sid)
    assert read_events(q, sid)[-1].body == "echo (start): Have a look."
    now = state(q, sid)
    assert (now["state"], now["turns"], now["name"]) == ("done", 1, "Fake Agent")
    # the agent's commands were logged to the session, because the turn ran with LOOM_SESSION set
    from loom.sessions import files_dir, sessions

    log = (files_dir(q, sessions(q)[sid]) / "run.log").read_text()
    assert "loom source dm-0003" in log
    # its heartbeat went with it, so the next message is not taken for someone listening
    post(q, sid, "And again.", "A. Author")
    launcher.tick()
    finish(launcher, sid)
    assert read_events(q, sid)[-1].body == "echo (resume): And again."
    assert state(q, sid)["turns"] == 2
    # one conversation across the two turns, chosen when the first started
    assert state(q, sid)["conversation"] == now["conversation"]
    launcher.close()


def test_no_turn_starts_when_it_should_not(q: Path) -> None:
    from loom.agent import Launcher
    from loom.mailbox import attach, detach, post

    configure(q)
    sid = new_session(q)
    launcher = Launcher(q)
    # the last word is the agent's own
    post(q, sid, "I said this myself.", "Fake Agent")
    launcher.tick()
    assert sid not in launcher.running
    # someone else is listening
    post(q, sid, "Have a look.", "A. Author")
    attach(q, sid, "Somebody Agent", "agent")
    launcher.tick()
    assert sid not in launcher.running
    detach(q, sid, "Somebody Agent")
    # the command is one the quilt carries -- and a person reading along is no reason not to start one
    attach(q, sid, "A. Author", "person")
    subprocess.run(["git", "init", "-q"], cwd=q, check=True)
    subprocess.run(["git", "add", "-f", "ai/ai-config.toml"], cwd=q, check=True)
    launcher.tick()
    assert sid not in launcher.running
    subprocess.run(["git", "rm", "-q", "-f", "--cached", "ai/ai-config.toml"], cwd=q, check=True)
    launcher.tick()
    assert sid in launcher.running
    # and one turn at a time
    post(q, sid, "More.", "A. Author")
    first = launcher.running[sid]
    launcher.tick()
    assert launcher.running[sid] is first
    finish(launcher, sid)
    launcher.close()


def test_a_failed_turn_is_recorded_and_not_retried_until_the_next_message(q: Path) -> None:
    from loom.agent import Launcher, state
    from loom.mailbox import post

    configure(q, start=[sys.executable, "-c", "import sys; print('boom: no model'); sys.exit(3)"], resume=[])
    sid = new_session(q)
    post(q, sid, "Have a look.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    finish(launcher, sid)
    now = state(q, sid)
    assert (now["state"], now["code"], now["error"]) == ("failed", 3, "boom: no model")
    failed_in = now["conversation"]
    launcher.tick()
    assert sid not in launcher.running
    post(q, sid, "Try again.", "A. Author")
    launcher.tick()
    assert sid in launcher.running
    # a conversation no turn finished in is not resumed: the next turn starts afresh, under a new id, since the one the failed start named may already exist and would be refused as in use
    assert state(q, sid)["conversation"] != failed_in
    finish(launcher, sid)
    launcher.close()


def test_a_missing_command_is_named_and_when_it_was_tried(q: Path) -> None:
    """The turn fails naming the command, with the time it was tried, so the viewer can tell the failure came after the send (0.14 study F12)."""
    from loom.agent import Launcher, state
    from loom.mailbox import post

    configure(q, start=["no-such-agent-xyz", "{prompt}"], resume=[])
    sid = new_session(q)
    post(q, sid, "Hello?", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    now = state(q, sid)
    assert (now["state"], now["error"]) == ("failed", "no-such-agent-xyz is not on PATH") and now.get("started")
    launcher.close()


def test_stop_ends_a_turn(q: Path) -> None:
    from loom.agent import Launcher, state
    from loom.mailbox import post

    configure(q, start=[sys.executable, "-c", "import time; time.sleep(60)"], resume=[])
    sid = new_session(q)
    post(q, sid, "Take your time.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    proc = launcher.running[sid]
    assert launcher.stop(sid) is True
    assert proc.poll() is not None and state(q, sid)["state"] == "stopped"
    launcher.tick()
    assert state(q, sid)["state"] == "stopped"  # the reap does not overwrite a stop
    assert launcher.stop(sid) is False


def test_the_viewer_is_told_what_the_agent_is_doing(q: Path) -> None:
    from loom.agent import Launcher
    from loom.mailbox import post
    from loom.render.serve import LoomHandler

    configure(q, start=[sys.executable, "-c", "import time; time.sleep(60)"], resume=[])
    sid = new_session(q)
    ask = FakeHandler(q, f"/_api/events?session={sid}&since=0")
    LoomHandler._events(ask)  # type: ignore[arg-type]
    assert ask.answer is not None and ask.answer[1]["agent"] == {"launch": True, "name": "Fake Agent"}
    post(q, sid, "Go.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    try:
        ask = FakeHandler(q, f"/_api/events?session={sid}&since=0")
        LoomHandler._events(ask)  # type: ignore[arg-type]
        assert ask.answer is not None and ask.answer[1]["agent"]["state"] == "running"
        stop = FakeHandler(q, body={"session": sid}, launcher=launcher)
        LoomHandler._agent_stop(stop)  # type: ignore[arg-type]
        assert stop.answer == (200, {"ok": True, "result": "stopped", "session": sid})
    finally:
        launcher.close()


def test_stop_is_refused_where_nothing_is_launched(q: Path) -> None:
    from loom.render.serve import LoomHandler

    stop = FakeHandler(q, body={"session": "s-2026-09-16-0001"})
    LoomHandler._agent_stop(stop)  # type: ignore[arg-type]
    assert stop.answer is not None and stop.answer[0] == 409


def test_agent_check_tests_the_command_without_running_it(q: Path) -> None:
    configure(q)
    good = ok("agent", "check", cwd=q)
    assert "launching: on" in good.output and "name: Fake Agent" in good.output and "{session}" not in good.output
    configure(q, start=["no-such-agent-xyz"], resume=[])
    refused("agent", "check", cwd=q, code=1, match="no-such-agent-xyz is not on PATH")
    configure(q)
    subprocess.run(["git", "init", "-q"], cwd=q, check=True)
    subprocess.run(["git", "add", "-f", "ai/ai-config.toml"], cwd=q, check=True)
    refused("agent", "check", cwd=q, code=1, match="git tracks")
    (q / "ai" / "ai-config.toml").write_text('name = "Fake Agent"\n')
    subprocess.run(["git", "rm", "-q", "-f", "--cached", "ai/ai-config.toml"], cwd=q, check=True)
    refused("agent", "check", cwd=q, code=1, match="start must be")


def test_an_older_quilt_is_told_and_upgraded_to_keep_the_command_out_of_git(q: Path) -> None:
    from loom.gitignore import MANAGED, missing

    gi = q / ".gitignore"
    gi.write_text("build/\n")
    configure(q)
    checked = ok("agent", "check", cwd=q)
    assert "does not ignore ai/ai-config.toml" in checked.output
    ok("upgrade", cwd=q)
    assert missing(q) == [] and all(line in gi.read_text().splitlines() for line in MANAGED)
    assert "does not ignore" not in ok("agent", "check", cwd=q).output


def test_serving_starts_no_turn_for_what_was_already_said_nor_for_an_agent(q: Path) -> None:
    """Turning launching on must not wake every old session; and an agent's message -- this one's or another's -- asks this agent nothing."""
    from loom.agent import Launcher
    from loom.mailbox import post

    configure(q)
    sid = new_session(q)
    post(q, sid, "An old question nobody answered.", "A. Author")
    launcher = Launcher(q)
    launcher.settle()
    launcher.tick()
    assert launcher.running == {}
    post(q, sid, "Another agent's report.", "Survey Agent")
    launcher.tick()
    assert launcher.running == {}
    post(q, sid, "A new question.", "A. Author")
    launcher.tick()
    assert sid in launcher.running
    finish(launcher, sid)
    launcher.close()


def test_the_activity_is_what_this_turn_ran_not_the_last_line_of_the_log(q: Path) -> None:
    """The activity is the last command this turn ran, never a log line from before it started (0.14 study F8)."""
    from loom.agent import activity
    from loom.sessions import files_dir, sessions

    sid = new_session(q)
    log = files_dir(q, sessions(q)[sid]) / "run.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("2026-09-01T00:00:00Z  loom annotate --reply a-1 → a-2\n")
    assert activity(q, sid, "2026-09-23T10:00:00Z") == ""
    with log.open("a") as fh:
        fh.write("2026-09-23T10:00:05Z  loom source sh-0009\n")
    assert activity(q, sid, "2026-09-23T10:00:00Z") == "loom source sh-0009"


def test_the_viewer_is_told_what_keeps_the_agent_from_starting(q: Path) -> None:
    """The report says what keeps a turn from starting, so the Chat does not promise one that will not come (0.14 study F13)."""
    from loom.agent import report

    configure(q)
    sid = new_session(q)
    assert "blocked" not in report(q, sid)
    subprocess.run(["git", "init", "-q"], cwd=q, check=True)
    subprocess.run(["git", "add", "-f", "ai/ai-config.toml"], cwd=q, check=True)
    assert "git tracks ai/ai-config.toml" in report(q, sid)["blocked"]
    subprocess.run(["git", "rm", "-q", "-f", "--cached", "ai/ai-config.toml"], cwd=q, check=True)
    (q / "ai" / "ai-config.toml").write_text('name = "Wren"\nstart = ["x"]\n')
    assert "Agent or AI" in report(q, sid)["blocked"]


def test_a_turn_a_stopped_server_left_running_is_ended_and_said_to_be(q: Path) -> None:
    """A turn left running by a server that stopped is ended when the next one settles, and its state says why (0.14 study F15)."""
    from loom.agent import Launcher, state, write_state

    configure(q)
    sid = new_session(q)
    orphan = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    try:
        write_state(q, sid, name="Fake Agent", state="running", pid=orphan.pid, started="2026-09-23T10:00:00Z")
        Launcher(q).settle()
        assert orphan.wait(timeout=10) == -signal.SIGTERM  # ended by settle, not by the timeout
    finally:
        if orphan.poll() is None:
            orphan.kill()
    now = state(q, sid)
    assert now["state"] == "stopped" and "loom serve stopped" in now["error"]


def test_the_turn_after_a_stop_is_told_not_to_carry_on(q: Path) -> None:
    """The first turn after a stop is told not to carry on with what was stopped; the turn after that is not (0.14 study F16)."""
    from loom.agent import AFTER_STOP, Launcher, state, write_state
    from loom.mailbox import post

    said = q.parent / "prompt.txt"
    record = [sys.executable, "-c", f"import sys; open({str(said)!r}, 'w').write(sys.argv[1])", "{prompt}"]
    configure(q, start=record, resume=[])
    sid = new_session(q)
    write_state(q, sid, name="Fake Agent", state="stopped")
    post(q, sid, "Something else.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    finish(launcher, sid)
    assert AFTER_STOP.strip() in said.read_text()
    assert state(q, sid)["state"] == "done"
    post(q, sid, "And more.", "A. Author")
    launcher.tick()
    finish(launcher, sid)
    assert AFTER_STOP.strip() not in said.read_text()
    launcher.close()


def test_serve_answers_a_transcript_page_from_the_inbox(q: Path) -> None:
    """`loom serve` answers a transcript page from the inbox itself, since a message rebuilds nothing (0.14 study F14)."""
    from loom.mailbox import PAGE, post
    from loom.render.serve import LoomHandler

    sid = new_session(q)
    for i in range(PAGE + 3):
        post(q, sid, f"m{i}", "Seed Agent")
    ask = FakeHandler(q, f"/build/transcripts/{sid}/2.json")
    assert LoomHandler._page(ask) is True  # type: ignore[arg-type]
    assert ask.answer is not None and [e["seq"] for e in ask.answer[1]["events"]] == [PAGE + 1, PAGE + 2, PAGE + 3]
    assert LoomHandler._page(FakeHandler(q, "/build/manifest.json")) is False  # type: ignore[arg-type]


def test_the_log_says_where_the_turns_rules_came_from(q: Path) -> None:
    """The turn's log opens by naming the policy passed with `--settings`, which holds whether or not the tool trusts the folder, so the tool's own "Ignoring … not trusted" line below it is read in context (0.14 study F19)."""
    from loom.agent import Launcher
    from loom.mailbox import post, session_dir

    fake = q.parent / "fake_agent.py"
    configure(
        q, start=[sys.executable, str(fake), "{session}", "start", "--settings", ".claude/settings.json"], resume=[]
    )
    sid = new_session(q)
    post(q, sid, "Have a look.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    finish(launcher, sid)
    first = (session_dir(q, sid) / "agent.log").read_text().splitlines()[0]
    assert first.startswith(
        "loom: what this turn may run is loom's policy in .claude/settings.json, passed with --settings"
    )
    launcher.close()


def wait_running(q: Path, sid: str, ready: Path, timeout: float = 20) -> int:
    """Wait for the turn in `sid` to be recorded running and to have written its pid to `ready`; the pid."""
    from loom.agent import state

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if state(q, sid).get("state") == "running" and ready.exists() and ready.read_text():
            return int(ready.read_text())
        time.sleep(0.05)
    raise AssertionError(f"no turn was running in {sid} after {timeout}s: {state(q, sid)}")


def gone(pid: int, timeout: float = 10) -> bool:
    """Whether the process has ended within `timeout`."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.05)
    return False


def test_stop_makes_a_turn_that_ignores_sigterm_stop(q: Path, tmp_path: Path) -> None:
    """A turn's process group is asked to stop and, when it ignores that for three seconds, killed."""
    from loom.agent import Launcher, state
    from loom.mailbox import post

    ready = tmp_path / "turn.pid"
    configure(q, start=sleeper(ready, ignore_term=True), resume=[])
    sid = new_session(q)
    post(q, sid, "Take your time.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    proc = launcher.running[sid]
    wait_running(q, sid, ready)
    t0 = time.monotonic()
    assert launcher.stop(sid) is True
    assert proc.returncode == -signal.SIGKILL, proc.returncode
    assert time.monotonic() - t0 >= 3, "killed without first being asked to stop"
    assert state(q, sid)["state"] == "stopped"


def test_a_message_posted_while_the_server_first_builds_starts_a_turn(
    q: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What was waiting when `loom serve` started is old, but the socket takes writes from the moment it listens, before the first build is done: a message posted then starts a turn."""
    from loom.render import serve as serve_mod
    from loom.render.serve import ServeSession
    from loom.scan.quilt import load_quilt
    from tests.unit.render._serve import QuickServer, fake_bundle

    monkeypatch.setattr(serve_mod, "ThreadingHTTPServer", QuickServer)
    ready = tmp_path / "turn.pid"
    configure(q, start=sleeper(ready), resume=[])
    sid = new_session(q)
    from loom.mailbox import post

    post(q, sid, "An old question.", "A. Author")
    s = ServeSession(load_quilt(q), fake_bundle(tmp_path), port=0, compile_masters=False, interval=0.1)
    s.listen()
    try:
        post(q, sid, "Asked while it builds.", "A. Author")
        s.start()
        pid = wait_running(q, sid, ready)
    finally:
        s.stop()
    assert gone(pid)


def test_serve_on_sigterm_ends_the_turn_it_started(q: Path, tmp_path: Path) -> None:
    """A terminal closed or a `kill` stops `loom serve` with SIGTERM; the turn it started, in a process group of its own, stops with it and is recorded stopped, and the server says it is no longer listening."""
    from loom.agent import state
    from loom.mailbox import post
    from tests.unit.render._serve import fake_bundle

    ready = tmp_path / "turn.pid"
    configure(q, start=sleeper(ready), resume=[])
    sid = new_session(q)
    said = tmp_path / "serve.log"
    with said.open("wb") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "loom", "serve", "--port", "0", "--no-compile"],
            cwd=q,
            env={**os.environ, "LOOM_ARRAS_BUNDLE": str(fake_bundle(tmp_path))},
            stdout=log,
            stderr=log,
        )
    try:
        deadline = time.monotonic() + 30
        while not (q / ".loom" / "serve.json").exists():
            assert server.poll() is None and time.monotonic() < deadline, said.read_text()
            time.sleep(0.05)
        post(q, sid, "Take your time.", "A. Author")
        pid = wait_running(q, sid, ready)
        server.send_signal(signal.SIGTERM)
        assert server.wait(timeout=20) == 0, said.read_text()
    finally:
        if server.poll() is None:
            server.kill()
    assert gone(pid), "the turn outlived the server"
    assert state(q, sid)["state"] == "stopped"
    assert "loom serve: stopping" in said.read_text()
    assert not (q / ".loom" / "serve.json").exists()


def test_codex_uses_the_reported_conversation_for_continuation(
    q: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from loom.agent import PRESETS, Launcher, state
    from loom.mailbox import post

    fake = tmp_path / "codex"
    fake.write_text(
        f"#!{sys.executable}\n"
        + """import json, sys
conversation = "12345678-1234-4234-8234-123456789abc"
if "resume" in sys.argv:
    assert conversation in sys.argv
print(json.dumps({"type": "thread.started", "thread_id": conversation}))
print(json.dumps({"type": "turn.completed"}))
"""
    )
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    configure(q, start=PRESETS["codex"]["start"], resume=PRESETS["codex"]["resume"])
    sid = new_session(q)
    post(q, sid, "First message", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    finish(launcher, sid)
    assert state(q, sid)["conversation"] == "12345678-1234-4234-8234-123456789abc"
    post(q, sid, "Second message", "A. Author")
    launcher.tick()
    finish(launcher, sid)
    assert state(q, sid)["state"] == "done"
    assert state(q, sid)["turns"] == 2
    launcher.close()


def test_codex_event_reader_ignores_message_bodies_and_invalid_ids(tmp_path: Path) -> None:
    from loom.agent import codex_conversation

    log = tmp_path / "agent.log"
    log.write_text(
        'diagnostic\n{"type":"item.completed","item":{"thread_id":"wrong"}}\n{"type":"thread.started","thread_id":"not-a-uuid"}\n'
    )
    assert codex_conversation(log) is None
