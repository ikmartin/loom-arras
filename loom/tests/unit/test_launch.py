"""Launching (plan 0.14 phase 5): `loom serve` starts the person's own agent command for one turn when a message waits and nobody is listening -- never an API, never a command the quilt carries."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from loom.cli import main

FAKE = """
import json, subprocess, sys
session, mode = sys.argv[1], sys.argv[2]
loom = [sys.executable, "-m", "loom"]
out = subprocess.run(loom + ["session", "next", "--wait", "0", "--json", "--session", session, "--as", "Fake Agent"],
                     capture_output=True, text=True, check=True).stdout
said = " / ".join(e.get("body", "") for e in json.loads(out)["events"])
subprocess.run(loom + ["source", "dm-0003"], capture_output=True, check=False)
subprocess.run(loom + ["session", "say", f"echo ({mode}): {said}", "--session", session, "--as", "Fake Agent"], check=True)
"""


def run(*args: str, cwd: Path, env: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), env=env)
    finally:
        os.chdir(old)


@pytest.fixture(autouse=True)
def _user_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))


@pytest.fixture
def q(tmp_path: Path) -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    return tmp_path / "q"


def configure(q: Path, *, start: list[str] | None = None, resume: list[str] | None = None, launch: bool = True) -> None:
    fake = q.parent / "fake_agent.py"
    fake.write_text(FAKE, encoding="utf-8")
    start = start if start is not None else [sys.executable, str(fake), "{session}", "start"]
    resume = resume if resume is not None else [sys.executable, str(fake), "{session}", "resume"]
    lines = ['name = "Fake Agent"', f"start = {json.dumps(start)}"]
    if resume:
        lines.append(f"resume = {json.dumps(resume)}")
    (q / "ai" / "ai-config.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    from loom.cli.quilt import _set_launch

    _set_launch(q, launch)


def sitting(q: Path) -> str:
    return run("session", "new", "a sitting", "--author", "A. Author", cwd=q).output.split()[0]


def finish(launcher: Any, sid: str, timeout: float = 60) -> None:
    """Wait for the session's turn to end, then let the launcher see it end."""
    proc = launcher.running.get(sid)
    deadline = time.monotonic() + timeout
    while proc is not None and proc.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    launcher.tick()


def test_the_quilt_file_wins_over_the_user_config_key_by_key(q: Path, tmp_path: Path) -> None:
    from loom.agent import load

    (tmp_path / "xdg" / "loom").mkdir(parents=True, exist_ok=True)
    (tmp_path / "xdg" / "loom" / "config.toml").write_text('[agent]\nname = "Home Agent"\nstart = ["home"]\n')
    (q / "ai" / "ai-config.toml").write_text('name = "Quilt Agent"\n')
    cfg, problems = load(q)
    assert problems == [] and cfg is not None
    assert (cfg.name, cfg.start) == ("Quilt Agent", ["home"])
    (q / "ai" / "ai-config.toml").write_text('name = "Wren"\n')
    _, problems = load(q)
    assert any("Agent or AI" in p for p in problems)
    (tmp_path / "xdg" / "loom" / "config.toml").write_text("")
    (q / "ai" / "ai-config.toml").write_text('name = "Quilt Agent"\n')
    _, problems = load(q)
    assert any("start" in p for p in problems)


def test_placeholders_are_filled_item_by_item(q: Path) -> None:
    from loom.agent import argv

    got = argv(
        ["claude", "-p", "{prompt}", "--session-id", "{agent_session}"], prompt="say $(rm -rf) {x}", agent_session="u"
    )
    assert got == ["claude", "-p", "say $(rm -rf) {x}", "--session-id", "u"]


def test_a_filled_value_is_never_filled_again(q: Path) -> None:
    """A quilt path or a message that happens to hold a placeholder goes in as written, whatever order the values are given in."""
    from loom.agent import argv

    got = argv(["{quilt}", "{prompt}"], quilt="/q/{prompt}", prompt="read {quilt}")
    assert got == ["/q/{prompt}", "read {quilt}"]
    assert argv(["{quilt}"], prompt="p", quilt="/q/{prompt}") == ["/q/{prompt}"]


def test_nothing_starts_while_launching_is_off(q: Path) -> None:
    from loom.agent import Launcher
    from loom.mailbox import post

    configure(q, launch=False)
    sid = sitting(q)
    post(q, sid, "Anyone?", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    assert launcher.running == {}


def test_a_message_starts_a_turn_and_the_next_one_resumes(q: Path) -> None:
    from loom.agent import Launcher, state
    from loom.mailbox import post, read_events

    configure(q)
    sid = sitting(q)
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
    sid = sitting(q)
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
    sid = sitting(q)
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
    # a conversation no turn finished in is not resumed: the next turn starts afresh, under a new id, since the one
    # the failed start named may already exist and would be refused as in use
    assert state(q, sid)["conversation"] != failed_in
    finish(launcher, sid)
    launcher.close()


def test_a_missing_command_is_named(q: Path) -> None:
    from loom.agent import Launcher, state
    from loom.mailbox import post

    configure(q, start=["no-such-agent-xyz", "{prompt}"], resume=[])
    sid = sitting(q)
    post(q, sid, "Hello?", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    assert state(q, sid)["error"] == "no-such-agent-xyz is not on PATH"
    launcher.close()


def test_stop_ends_a_turn(q: Path) -> None:
    from loom.agent import Launcher, state
    from loom.mailbox import post

    configure(q, start=[sys.executable, "-c", "import time; time.sleep(60)"], resume=[])
    sid = sitting(q)
    post(q, sid, "Take your time.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    proc = launcher.running[sid]
    assert launcher.stop(sid) is True
    assert proc.poll() is not None and state(q, sid)["state"] == "stopped"
    launcher.tick()
    assert state(q, sid)["state"] == "stopped"  # the reap does not overwrite a stop
    assert launcher.stop(sid) is False


class Fake:
    """Enough of LoomHandler to call one of its methods."""

    def __init__(self, q: Path, path: str = "", body: dict[str, Any] | None = None, launcher: Any = None) -> None:
        self.quilt_root = q
        self.path = path
        self.launcher = launcher
        raw = json.dumps(body or {}).encode()
        self.rfile = io.BytesIO(raw)
        self.headers = {"Content-Length": str(len(raw))}
        self.answer: tuple[int, Any] | None = None

    def _json(self, status: int, body: Any) -> None:
        self.answer = (int(status), body)

    def send_error(self, status: int) -> None:
        self.answer = (int(status), None)


def test_the_viewer_is_told_what_the_agent_is_doing(q: Path) -> None:
    from loom.agent import Launcher
    from loom.mailbox import post
    from loom.render.serve import LoomHandler

    configure(q, start=[sys.executable, "-c", "import time; time.sleep(60)"], resume=[])
    sid = sitting(q)
    ask = Fake(q, f"/_api/events?session={sid}&since=0")
    LoomHandler._events(ask)  # type: ignore[arg-type]
    assert ask.answer is not None and ask.answer[1]["agent"] == {"launch": True, "name": "Fake Agent"}
    post(q, sid, "Go.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    try:
        ask = Fake(q, f"/_api/events?session={sid}&since=0")
        LoomHandler._events(ask)  # type: ignore[arg-type]
        assert ask.answer is not None and ask.answer[1]["agent"]["state"] == "running"
        stop = Fake(q, body={"session": sid}, launcher=launcher)
        LoomHandler._agent_stop(stop)  # type: ignore[arg-type]
        assert stop.answer == (200, {"ok": True, "result": "stopped", "session": sid})
    finally:
        launcher.close()


def test_stop_is_refused_where_nothing_is_launched(q: Path) -> None:
    from loom.render.serve import LoomHandler

    refused = Fake(q, body={"session": "s-2026-09-16-0001"})
    LoomHandler._agent_stop(refused)  # type: ignore[arg-type]
    assert refused.answer is not None and refused.answer[0] == 409


def test_agent_check_tests_the_command_without_running_it(q: Path) -> None:
    configure(q)
    ok = run("agent", "check", cwd=q)
    assert ok.exit_code == 0, ok.output
    assert "launching: on" in ok.output and "name: Fake Agent" in ok.output and "{session}" not in ok.output
    configure(q, start=["no-such-agent-xyz"], resume=[])
    missing = run("agent", "check", cwd=q)
    assert missing.exit_code == 1 and "no-such-agent-xyz is not on PATH" in missing.output
    configure(q)
    subprocess.run(["git", "init", "-q"], cwd=q, check=True)
    subprocess.run(["git", "add", "-f", "ai/ai-config.toml"], cwd=q, check=True)
    tracked = run("agent", "check", cwd=q)
    assert tracked.exit_code == 1 and "git tracks" in tracked.output
    (q / "ai" / "ai-config.toml").write_text('name = "Fake Agent"\n')
    subprocess.run(["git", "rm", "-q", "-f", "--cached", "ai/ai-config.toml"], cwd=q, check=True)
    empty = run("agent", "check", cwd=q)
    assert empty.exit_code == 1 and "start must be" in empty.output


def test_init_asks_which_ai_and_says_whether_it_will_be_started(tmp_path: Path) -> None:
    import tomllib

    r = run("init", str(tmp_path / "c"), "--ai", "claude", "--launch-agents", "--author", "A. Author", cwd=tmp_path)
    assert r.exit_code == 0, r.output
    c = tmp_path / "c"
    cfg = tomllib.loads((c / "ai" / "ai-config.toml").read_text())
    assert cfg["name"] == "Claude Agent" and cfg["start"][0] == "claude" and "{agent_session}" in cfg["resume"]
    assert tomllib.loads((c / "config.toml").read_text())["ai"]["launch"] is True
    perms = json.loads((c / ".claude" / "settings.json").read_text())["permissions"]
    assert "Bash(loom session say*)" in perms["allow"] and "Bash(loom accept*)" in perms["deny"]
    assert "ai/ai-config.toml" in (c / ".gitignore").read_text()
    assert "Agents will be launched by loom serve" in r.output
    # no terminal, no flag: no AI, and nothing will be started
    n = run("init", str(tmp_path / "n"), "--author", "A. Author", cwd=tmp_path)
    assert n.exit_code == 0, n.output
    assert "AI: none" in n.output and "Agents will not be launched" in n.output
    assert not (tmp_path / "n" / ".claude").exists()
    assert tomllib.loads((tmp_path / "n" / "ai" / "ai-config.toml").read_text()) == {}


def test_the_showcase_referee_findings_are_the_agents() -> None:
    """The referee's first findings were written with no agent named, so they were recorded as the author's and went back to the agent in the author's packet."""
    log = Path(__file__).resolve().parents[1] / "quilts" / "showcase" / "annotations" / "log.jsonl"
    events = [json.loads(line) for line in log.read_text().splitlines()]
    first = {f"a-2026-09-16-000{i}" for i in range(1, 6)}
    got = {e["id"]: (e["author"], e["kind"]) for e in events if e.get("event") == "created" and e.get("id") in first}
    assert got == {i: ("Referee (Agent)", "agent") for i in first}


def test_an_older_quilt_is_told_and_upgraded_to_keep_the_command_out_of_git(q: Path) -> None:
    from loom.agent import IGNORED, unignored

    gi = q / ".gitignore"
    gi.write_text("build/\n")
    configure(q)
    checked = run("agent", "check", cwd=q)
    assert "does not ignore ai/ai-config.toml" in checked.output
    assert run("upgrade", cwd=q).exit_code == 0
    assert unignored(q) == [] and all(line in gi.read_text().splitlines() for line in IGNORED)
    assert "does not ignore" not in run("agent", "check", cwd=q).output


def test_serving_starts_no_turn_for_what_was_already_said_nor_for_an_agent(q: Path) -> None:
    """Turning launching on must not wake every old session; and an agent's message -- this one's or another's -- asks this agent nothing."""
    from loom.agent import Launcher
    from loom.mailbox import post

    configure(q)
    sid = sitting(q)
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


# ---- faults the 0.14 study found (docs/reports/0.14-chat-overhaul.md) ---------------------------------------------


def test_the_activity_is_what_this_turn_ran_not_the_last_line_of_the_log(q: Path) -> None:
    """F8: as a turn started, the status line showed a command from days before."""
    from loom.agent import activity
    from loom.sessions import files_dir, sessions

    sid = sitting(q)
    log = files_dir(q, sessions(q)[sid]) / "run.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("2026-09-01T00:00:00Z  loom comment --reply a-1 → a-2\n")
    assert activity(q, sid, "2026-09-23T10:00:00Z") == ""
    with log.open("a") as fh:
        fh.write("2026-09-23T10:00:05Z  loom source sh-0009\n")
    assert activity(q, sid, "2026-09-23T10:00:00Z") == "loom source sh-0009"


def test_a_command_not_on_path_records_when_it_was_tried(q: Path) -> None:
    """F12: with no start time, the viewer could not tell the failure came after the send."""
    from loom.agent import Launcher, state
    from loom.mailbox import post

    configure(q, start=["no-such-agent-xyz"], resume=[])
    sid = sitting(q)
    post(q, sid, "Hello?", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    now = state(q, sid)
    assert now["state"] == "failed" and now.get("started")
    launcher.close()


def test_the_viewer_is_told_what_keeps_the_agent_from_starting(q: Path) -> None:
    """F13: with the config tracked, nothing started and the Chat said the agent would start."""
    from loom.agent import report

    configure(q)
    sid = sitting(q)
    assert "blocked" not in report(q, sid)
    subprocess.run(["git", "init", "-q"], cwd=q, check=True)
    subprocess.run(["git", "add", "-f", "ai/ai-config.toml"], cwd=q, check=True)
    assert "git tracks ai/ai-config.toml" in report(q, sid)["blocked"]
    subprocess.run(["git", "rm", "-q", "-f", "--cached", "ai/ai-config.toml"], cwd=q, check=True)
    (q / "ai" / "ai-config.toml").write_text('name = "Wren"\nstart = ["x"]\n')
    assert "Agent or AI" in report(q, sid)["blocked"]


def test_a_turn_a_stopped_server_left_running_is_ended_and_said_to_be(q: Path) -> None:
    """F15: a server stopped by a signal left its turn running, owned by nothing, and `agent.json` saying so."""
    from loom.agent import Launcher, state, write_state

    configure(q)
    sid = sitting(q)
    orphan = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    write_state(q, sid, name="Fake Agent", state="running", pid=orphan.pid, started="2026-09-23T10:00:00Z")
    Launcher(q).settle()
    assert orphan.wait(timeout=10) is not None
    now = state(q, sid)
    assert now["state"] == "stopped" and "loom serve stopped" in now["error"]


def test_the_turn_after_a_stop_is_told_not_to_carry_on(q: Path) -> None:
    """F16: the next turn resumed the conversation in which the stopped request was made, and carried on with it."""
    from loom.agent import AFTER_STOP, Launcher, state, write_state
    from loom.mailbox import post

    said = q.parent / "prompt.txt"
    record = [sys.executable, "-c", f"import sys; open({str(said)!r}, 'w').write(sys.argv[1])", "{prompt}"]
    configure(q, start=record, resume=[])
    sid = sitting(q)
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
    """F14: a message rebuilds nothing, so the build's pages went stale under a server and the Chat pulled the whole tail."""
    from loom.mailbox import PAGE, post
    from loom.render.serve import LoomHandler

    sid = sitting(q)
    for i in range(PAGE + 3):
        post(q, sid, f"m{i}", "Seed Agent")
    ask = Fake(q, f"/build/transcripts/{sid}/2.json")
    assert LoomHandler._page(ask) is True  # type: ignore[arg-type]
    assert ask.answer is not None and [e["seq"] for e in ask.answer[1]["events"]] == [PAGE + 1, PAGE + 2, PAGE + 3]
    assert LoomHandler._page(Fake(q, "/build/manifest.json")) is False  # type: ignore[arg-type]


def test_the_log_says_where_the_turns_rules_came_from(q: Path) -> None:
    """The 0.14 study (F19): Claude Code opens the log with "Ignoring … permissions.allow … not trusted" though the file passed with `--settings` holds."""
    from loom.agent import Launcher
    from loom.mailbox import post, session_dir

    fake = q.parent / "fake_agent.py"
    configure(
        q, start=[sys.executable, str(fake), "{session}", "start", "--settings", ".claude/settings.json"], resume=[]
    )
    sid = sitting(q)
    post(q, sid, "Have a look.", "A. Author")
    launcher = Launcher(q)
    launcher.tick()
    finish(launcher, sid)
    first = (session_dir(q, sid) / "agent.log").read_text().splitlines()[0]
    assert first.startswith(
        "loom: what this turn may run is loom's policy in .claude/settings.json, passed with --settings"
    )
    launcher.close()


def test_codex_is_given_the_same_policy_as_claude(tmp_path: Path) -> None:
    """One policy, loom's own, rendered per tool (DR-283-ikmartin); a quilt does not change it."""
    from loom.ai.layout import AGENT_COMMANDS, CODEX_RULES, author_commands, codex_rules

    rules = codex_rules()
    for c in AGENT_COMMANDS:
        assert (
            f'prefix_rule(pattern = [{", ".join(json.dumps(w) for w in ["loom", *c.split()])}], decision = "allow")'
            in rules
        )
    for c in author_commands():
        assert f'"{c.split()[-1]}"], decision = "forbidden")' in rules
    assert run("init", str(tmp_path / "c"), "--ai", "codex", "--yes", cwd=tmp_path).exit_code == 0
    assert (tmp_path / "c" / CODEX_RULES).read_text() == rules
    assert not (tmp_path / "c" / ".claude" / "settings.json").exists()
