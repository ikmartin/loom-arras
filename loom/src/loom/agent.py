"""Starting an agent for one turn (plan 0.14 phase 5): the person's own command, run by `loom serve` when a message lands and nobody is listening.

**Loom calls no model and holds no key.** It runs a command line the person wrote in `ai/ai-config.toml` (or their user config's `[agent]` table), fills in a few placeholders, and reads what the turn wrote through loom -- its messages in the inbox, its commands in `run.log`. It owns no vendor's argv convention and holds no process beyond the one turn, which is what keeps this from being the runner WQ-15 declined.

**A command a quilt carries is not trusted.** `ai/ai-config.toml` is gitignored; one that git tracks came from whoever committed it, and loom refuses to run it, since cloning a quilt must never mean running its author's command.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import tomllib
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.clock import stamp

CONFIG = "ai/ai-config.toml"
STATE = "agent.json"
LOG = "agent.log"

PROMPT = (
    "You are working in loom session {session} of the quilt at {quilt}. If you have not in this conversation, run "
    "`loom ai orient --session {session}` first. Read what is waiting with "
    '`loom session next --wait 0 --json --as "{name}"`, do what it asks, and answer with '
    '`loom session say "your answer" --as "{name}"`. Then stop: loom starts you again when the next message arrives.'
)

#: Added to the prompt when the last turn was stopped: stopping is the author cancelling the work, not pausing it.
AFTER_STOP = (
    " Your previous turn was stopped by the author before it finished: do not carry on with what it was doing "
    "unless the new message asks for it."
)

#: What `loom init` writes for each answer to "which AI do you use".
PRESETS: dict[str, dict[str, Any]] = {
    # `--settings` names the permission file every quilt with `ai/` has: Claude Code ignores a project's own settings until someone accepts its trust dialog there, which a turn nobody watches never does.
    "claude": {
        "name": "Claude Agent",
        "start": ["claude", "-p", "{prompt}", "--session-id", "{agent_session}", "--settings", ".claude/settings.json"],
        "resume": ["claude", "-p", "{prompt}", "--resume", "{agent_session}", "--settings", ".claude/settings.json"],
    },
    # Unverified: Codex was not installed where this was written. It cannot be told which conversation to use, so it has no resume and regains the thread from `loom ai orient --session` each turn.
    "codex": {"name": "Codex Agent", "start": ["codex", "exec", "{prompt}"]},
}

HEADER = """\
# How loom starts an agent in a session, for one turn, when config.toml says launch = true under [ai].
# Loom never calls a model itself: it runs this command, with these placeholders filled in:
#   {session}        the session id
#   {agent_session}  a conversation id loom chooses at a session's first turn and keeps, for an agent that resumes by id
#   {prompt}         what loom asks the agent to do this turn
#   {quilt}          the quilt's root
# `name` is who the agent says it is in the chat, and must include Agent or AI. `resume`, when given, is used from the
# second turn on. This file is yours: it is not committed, and loom refuses to run it if git tracks it.
# `loom agent check` tests it without running anything.
"""


def config_text(preset: str | None) -> str:
    """The `ai/ai-config.toml` `loom init` writes: a preset filled in, or every key commented out."""

    def lines(p: dict[str, Any]) -> list[str]:
        out = [f"name = {json.dumps(p['name'])}", f"start = {json.dumps(p['start'])}"]
        if "resume" in p:
            out.append(f"resume = {json.dumps(p['resume'])}")
        return out

    if preset in PRESETS:
        return HEADER + "\n" + "\n".join(lines(PRESETS[preset])) + "\n"
    return HEADER + "\n" + "\n".join("# " + x for x in lines(PRESETS["claude"])) + "\n"


#: What `load` says when neither the quilt nor the user config names an agent.
UNCONFIGURED = f"no agent is configured: fill in {CONFIG}"


@dataclass
class AgentConfig:
    """Who the agent is and how to start it; `source` says which file each came from."""

    name: str = ""
    start: list[str] = field(default_factory=list)
    resume: list[str] | None = None
    source: str = ""


def load(root: Path) -> tuple[AgentConfig | None, list[str]]:
    """The agent's config, the quilt's `ai/ai-config.toml` over the user config's `[agent]` table key by key, and what is wrong with it.

    Returns None with problems when there is nothing to run.
    """
    from loom.cli._common import is_agent
    from loom.scan.quilt import load_user_config, user_config_path

    problems: list[str] = []
    merged: dict[str, Any] = {}
    sources: list[str] = []
    user = load_user_config().get("agent")
    if isinstance(user, dict) and user:
        merged.update(user)
        sources.append(str(user_config_path()))
    path = root / CONFIG
    if path.is_file():
        try:
            mine = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            return None, [f"{CONFIG} is not valid TOML: {exc}"]
        if mine:
            merged.update(mine)
            sources.append(CONFIG)
    if not merged:
        return None, [UNCONFIGURED]
    name = merged.get("name")
    start = merged.get("start")
    resume = merged.get("resume")
    if not isinstance(name, str) or not name.strip():
        problems.append("name is missing")
    elif not is_agent(name):
        problems.append(f"name {name!r} must include Agent or AI, so what it writes says an agent wrote it")
    if not (isinstance(start, list) and start and all(isinstance(x, str) for x in start)):
        problems.append("start must be a list of strings, the command and its arguments")
    if resume is not None and not (isinstance(resume, list) and resume and all(isinstance(x, str) for x in resume)):
        problems.append("resume, when given, must be a list of strings")
    if problems:
        return None, problems
    return AgentConfig(
        str(name).strip(),
        [str(x) for x in start or []],
        list(resume) if resume else None,
        " over ".join(reversed(sources)),
    ), []


def tracked(root: Path) -> bool:
    """Whether git tracks the quilt's agent config, which makes it a command someone else wrote."""
    if shutil.which("git") is None or not (root / CONFIG).is_file():
        return False
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", CONFIG], cwd=root, capture_output=True, text=True, check=False
    )
    return proc.returncode == 0


@dataclass
class Diagnosis:
    """What `loom agent check` finds, which `loom doctor` reports too: whether launching is on, the config, the commands it would run, and every fault that would stop it."""

    launch: bool
    config: AgentConfig | None
    faults: list[str] = field(default_factory=list)
    #: (label, argv with sample values) for `start` and, when given, `resume`
    commands: list[tuple[str, list[str]]] = field(default_factory=list)
    #: whether `.gitignore` lacks the agent config's line
    unignored: bool = False

    @property
    def configured(self) -> bool:
        """Whether anything names an agent, sound or not."""
        return self.config is not None or self.faults[:1] != [UNCONFIGURED]


#: What `diagnose` fills a command's placeholders with, since no session exists to fill them.
SAMPLE = {"session": "s-0000-00-00-0000", "agent_session": "<the session's conversation id>", "prompt": "<the prompt>"}


def diagnose(root: Path) -> Diagnosis:
    """Test the command `loom serve` would start an agent with, without running it.

    A fault is an incomplete config, a command not on PATH, or a config git tracks; each stops loom starting the agent.
    """
    cfg, problems = load(root)
    d = Diagnosis(launching(root), cfg, list(problems))
    if tracked(root):
        d.faults.append(f"git tracks {CONFIG}: loom will not run a command the quilt carries; git rm --cached it")
    if cfg is not None:
        fill = {**SAMPLE, "quilt": str(root)}
        for label, template in (("start", cfg.start), ("resume", cfg.resume)):
            if template:
                cmd = argv(template, **fill)
                d.commands.append((label, cmd))
                if shutil.which(cmd[0]) is None:
                    d.faults.append(f"{cmd[0]} is not on PATH")
    from loom.gitignore import missing

    d.unignored = CONFIG in missing(root)
    return d


_PLACEHOLDER = re.compile(r"\{(\w+)\}")


def argv(template: list[str], **fill: str) -> list[str]:
    """The command with its placeholders filled item by item; no shell ever sees it.

    One pass per item, so a value that itself contains `{quilt}` or `{prompt}` -- a path, a message -- is inserted as written and never expanded. An unknown placeholder is left as it stands.
    """
    return [_PLACEHOLDER.sub(lambda m: fill.get(m.group(1), m.group(0)), item) for item in template]


def launching(root: Path) -> bool:
    """Whether `config.toml` says loom may start agents here (`[ai] launch`)."""
    try:
        data = tomllib.loads((root / "config.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    ai = data.get("ai")
    return bool(ai.get("launch", False)) if isinstance(ai, dict) else False


def state(root: Path, sid: str) -> dict[str, Any]:
    """What the last turn in a session came to, from `agent.json`; empty when there has been none."""
    from loom.mailbox import session_dir

    try:
        got = json.loads((session_dir(root, sid) / STATE).read_text(encoding="utf-8"))
        return got if isinstance(got, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(root: Path, sid: str, **fields: Any) -> dict[str, Any]:
    """Merge `fields` into the session's `agent.json`, replacing the file whole so a reader never sees it half written."""
    from loom.mailbox import session_dir
    from loom.render.publish import write_atomic

    d = session_dir(root, sid)
    d.mkdir(parents=True, exist_ok=True)
    now = {**state(root, sid), **fields}
    write_atomic(d / STATE, json.dumps(now, indent=1, sort_keys=True) + "\n")
    return now


def activity(root: Path, sid: str, since: str = "") -> str:
    """The last loom command the session's log records since `since`: what a running turn is doing, as far as loom can know. Empty before the turn has run one."""
    from loom.sessions import files_dir, sessions

    s = sessions(root).get(sid)
    log = files_dir(root, s) / "run.log" if s else None
    try:
        last = log.read_text(encoding="utf-8").strip().splitlines()[-1] if log else ""
    except (OSError, IndexError):
        return ""
    when, _, command = last.partition("  ")
    if since and when < since:
        return ""
    return command or last


def report(root: Path, sid: str) -> dict[str, Any]:
    """What the viewer's status line needs: whether launching is on, the agent's name, and the last turn's state."""
    cfg, problems = load(root)
    out: dict[str, Any] = {"launch": launching(root), "name": cfg.name if cfg else ""}
    # what keeps loom from starting the agent at all, said where the person is waiting for it
    if out["launch"] and (problems or tracked(root)):
        out["blocked"] = (
            f"git tracks {CONFIG}, so loom will not run it" if tracked(root) else f"{CONFIG}: {problems[0]}"
        )
    now = state(root, sid)
    for key in ("state", "error", "started"):
        if now.get(key):
            out[key] = now[key]
    if now.get("name") and not out["name"]:
        out["name"] = now["name"]
    if now.get("state") == "running":
        out["activity"] = activity(root, sid, str(now.get("started", "")))
    return out


def policy_line(cmd: list[str]) -> str:
    """The first line of `agent.log`: where the turn's rules came from, so a tool's own word on them reads in context.

    Claude Code opens the log saying it ignores the project's settings until the folder is trusted; the same file passed with `--settings` holds regardless (0.14 study, F19), and a person reading the log after a fault should not conclude the rules failed.
    """
    from loom.ai.layout import CODEX_RULES

    tool = Path(cmd[0]).name if cmd else ""
    if "--settings" in cmd[:-1]:
        where = cmd[cmd.index("--settings") + 1]
        return f"loom: what this turn may run is loom's policy in {where}, passed with --settings, so it holds whether or not {tool} trusts this folder.\n"
    if tool == "codex":
        return f"loom: what this turn may run is loom's policy in {CODEX_RULES}, which Codex reads once this folder is trusted.\n"
    return ""


class Launcher:
    """Starts a turn when a message is waiting for the configured agent and no other agent is listening; one process per session at a time.

    Owned by `loom serve`. `tick` is the whole policy and runs once a second on its thread; tests call it directly.
    """

    def __init__(self, root: Path, interval: float = 1.0) -> None:
        self.root = root
        self.interval = interval
        self.running: dict[str, subprocess.Popen[bytes]] = {}
        #: The highest seq a turn was started for, per session, so a turn that fails is not retried until a new message.
        self.launched_for: dict[str, int] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._settled = False

    def settle(self) -> None:
        """Take every open session's inbox as already answered: only what arrives while serving starts a turn.

        Called by `loom serve` before its socket accepts a write, so a message posted during the first build starts a turn rather than being taken as old. Turning launching on must not wake every old session whose last message nobody answered -- that is a turn per session, at once, for messages nobody is waiting on.
        """
        self._settled = True
        from loom.mailbox import last_seq
        from loom.sessions import sessions

        for sid, s in sessions(self.root).items():
            if s.state == "open":
                self.launched_for[sid] = last_seq(self.root, sid)
            # a turn a server that is no longer running started: nothing owns it, so it is ended and said to be
            now = state(self.root, sid)
            if now.get("state") == "running":
                pid = int(now.get("pid") or 0)
                if pid:
                    try:
                        os.killpg(pid, signal.SIGTERM)
                    except (ProcessLookupError, PermissionError):
                        pass
                write_state(
                    self.root, sid, state="stopped", error="loom serve stopped while this turn ran", ended=stamp()
                )

    def start(self) -> None:
        """Begin ticking on a thread, settling first unless `settle` already ran."""
        if not self._settled:
            self.settle()
        self._thread = threading.Thread(target=self._loop, name="loom-launcher", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        for sid in list(self.running):
            self.stop(sid)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001
                print(f"loom serve: launcher error: {exc}", file=sys.stderr)
            self._stop.wait(self.interval)

    def tick(self) -> None:
        """Reap finished turns, then start any turn a waiting message calls for."""
        self._reap()
        if not launching(self.root):
            return
        cfg, problems = load(self.root)
        if cfg is None or tracked(self.root):
            return
        from loom.cli._common import is_agent
        from loom.mailbox import attached, cursor, read_events
        from loom.sessions import sessions

        for sid, s in sessions(self.root).items():
            if s.state != "open" or sid in self.running:
                continue
            # a person's message: an agent's -- this one's, or another's -- is nobody asking this agent anything
            waiting = [
                e
                for e in read_events(self.root, sid, cursor(self.root, sid, cfg.name))
                if e.who != cfg.name and not is_agent(e.who)
            ]
            if not waiting:
                continue
            top = waiting[-1].seq
            if top <= self.launched_for.get(sid, 0):
                continue
            # an agent someone else started is listening, and would answer; a person reading or tailing is not an agent
            if any(r.get("kind") == "agent" and r.get("who") != cfg.name for r in attached(self.root, sid)):
                continue
            self.launched_for[sid] = top
            self._launch(sid, cfg)

    def _launch(self, sid: str, cfg: AgentConfig) -> None:
        from loom.mailbox import session_dir

        before = state(self.root, sid)
        turns = int(before.get("turns", 0)) if before.get("name") == cfg.name else 0
        # Resume only a conversation a turn finished in; otherwise start a new one under a new id. An id derived from the quilt and the session was the same after a re-clone or a lost `agent.json`, and the agent refused it as already in use -- and a start that failed may or may not have made the conversation it named.
        resumable = bool(cfg.resume and before.get("conversation") and before.get("resumable"))
        conversation = str(before["conversation"]) if resumable else str(uuid.uuid4())
        template = cfg.resume if resumable and cfg.resume else cfg.start
        fill = {"session": sid, "agent_session": conversation, "quilt": str(self.root)}
        fill["prompt"] = argv([PROMPT], **fill, name=cfg.name)[0] + (
            AFTER_STOP if before.get("state") == "stopped" else ""
        )
        cmd = argv(template, **fill)
        d = session_dir(self.root, sid)
        d.mkdir(parents=True, exist_ok=True)
        log = (d / LOG).open("wb")
        log.write(policy_line(cmd).encode())
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=self.root,
                env={**os.environ, "LOOM_SESSION": sid},
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except FileNotFoundError:
            log.close()
            now = stamp()
            write_state(
                self.root, sid, name=cfg.name, state="failed", error=f"{cmd[0]} is not on PATH", started=now, ended=now
            )
            return
        except OSError as exc:
            log.close()
            now = stamp()
            write_state(self.root, sid, name=cfg.name, state="failed", error=str(exc), started=now, ended=now)
            return
        log.close()
        with self._lock:
            self.running[sid] = proc
        write_state(
            self.root,
            sid,
            name=cfg.name,
            state="running",
            pid=proc.pid,
            started=stamp(),
            ended="",
            code=None,
            error="",
            turns=turns + 1,
            conversation=conversation,
        )

    def _reap(self) -> None:
        from loom.mailbox import detach, session_dir

        with self._lock:
            done = [(sid, p) for sid, p in self.running.items() if p.poll() is not None]
            for sid, _ in done:
                del self.running[sid]
        for sid, proc in done:
            now = state(self.root, sid)
            if now.get("state") == "stopped":
                continue
            code = proc.returncode
            error = ""
            if code != 0:
                try:
                    tail = (session_dir(self.root, sid) / LOG).read_text(encoding="utf-8", errors="replace").strip()
                    error = tail.splitlines()[-1] if tail else f"exited with code {code}"
                except OSError:
                    error = f"exited with code {code}"
            write_state(
                self.root,
                sid,
                state="done" if code == 0 else "failed",
                code=code,
                error=error,
                ended=stamp(),
                resumable=code == 0 or bool(now.get("resumable")),
            )
            # the turn's heartbeat outlives it by up to 90 s; left standing, it would read as someone listening
            if now.get("name"):
                detach(self.root, sid, str(now["name"]))

    def stop(self, sid: str) -> bool:
        """End a running turn: its process group is asked to stop, then made to. Returns whether one was running."""
        with self._lock:
            proc = self.running.pop(sid, None)
        if proc is None:
            return False
        write_state(self.root, sid, state="stopped", ended=stamp())
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            deadline = time.monotonic() + 3
            while proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
        except (ProcessLookupError, PermissionError):
            pass
        name = state(self.root, sid).get("name")
        if name:
            from loom.mailbox import detach

            detach(self.root, sid, str(name))
        return True
