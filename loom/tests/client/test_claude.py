"""Client tier: the agent configuration loom generates, tried against the real Claude Code, which is the only place its two permission bugs ever showed.

`Write(...)` path rules were never enforced, because Claude Code matches only `Edit` rules against paths (DR-275-ikmartin); and passed with `--settings`, the file reads a leading `/` as `.claude/`, so allows written from the root refused every write a launched agent made (DR-343-ikmartin). Both passed every unit test, which read the generated file and never the client. Each test here makes a quilt with loom's own commands and starts the client from the quilt's root with the generated file passed as `--settings`, the reading DR-343-ikmartin measured. The command is built here rather than taken from loom's launch preset, which plan 0.20.1 retires, so the tier outlives it.

Both variants are tried: over MCP, the default, the client starts the server from the `.mcp.json` `loom ai init` wrote, a write is recorded under the name it gives, and a mode's prompt and a resource reach the server; what the person did since the agent last looked reaches it through `loom_since`; in the shell variant, the agent's own `loom` commands run and the author's are refused. Codex and Gemini CLI have their own files beside this one.

Every test calls a hosted model on the account of whoever runs it, so the tier is run by hand (`scripts/verify client`), never in CI, and skips unless LOOM_CLIENT_TESTS=1 and `claude` is on PATH.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.client._tier import gate, person_env
from tests.helpers import ok

pytestmark = pytest.mark.client

#: Read at import, before the isolation every test runs under narrows PATH: the client is the person's.
CLAUDE = shutil.which("claude")
#: The cheapest model the client names by alias: a turn here asks for two tool calls, not for thought.
MODEL = "haiku"
#: What one turn may spend, in dollars, before the client stops it; many times what two tool calls cost.
BUDGET = "1.00"

WRITES = (
    "This turn checks this folder's permission settings and nothing else; run no command. "
    "With the Write tool, create drafting-ai/client-check.txt and then drafting/client-check.txt, each holding the one word marker. "
    "The settings are expected to refuse one of the two: attempt both, never write either file another way, and stop once both are attempted."
)
OVER_MCP = (
    "This turn checks this folder's loom MCP server and nothing else. "
    "Call the loom server's tool loom_annotate with target dm-0002, message `client check` and kind question. "
    "Then, with the Bash tool, run `loom accept --help` exactly as written. "
    "The settings are expected to refuse the second: attempt both, never do either another way, and stop once both are attempted."
)
READ_A_RESOURCE = (
    "This turn checks this folder's loom MCP server and nothing else. "
    "With the ReadMcpResourceTool tool, read the resource quilt:dm-0002 from the server loom, "
    "then reply with the one line of it that holds \\label, exactly as it is, and nothing else."
)
HEAR_SINCE = (
    "This turn checks this folder's loom MCP server and nothing else. "
    "Call the loom server's tool loom_since, then reply with the body of the newest annotation it reports, exactly as it is, and nothing else."
)
#: What the person wrote before the agent looked, which the reply must quote.
LEFT = "Is the bound on the orbit count sharp?"
#: A mode's prompt, typed as Claude Code names an MCP prompt; whether print mode expands one is what the test finds out.
A_PROMPT = "/mcp__loom__quick dm-0002"
COMMANDS = (
    "This turn checks this folder's permission settings and nothing else. "
    "With the Bash tool, run `loom status` and then `loom accept --help`, each exactly as written and in a call of its own. "
    "The settings are expected to refuse one of the two: attempt both, never run either another way, and stop once both are attempted."
)


def quilt(tmp_path: Path, *flags: str) -> Path:
    """The demo with the agent layer for Claude, as `loom init --demo --ai claude` writes it, `.claude/settings.json` and `.mcp.json` included; `loom ai init FLAGS` after."""
    ok("init", str(tmp_path / "q"), "--demo", "--ai", "claude", "--yes", cwd=tmp_path)
    if flags:
        ok("ai", "init", *flags, cwd=tmp_path / "q")
    return tmp_path / "q"


def turn(q: Path, prompt: str) -> tuple[dict[str, Any], list[str]]:
    """Run one turn of the client in `q` with loom's generated settings, and return its JSON result and every loom command it ran, as the arguments after `loom`.

    The command passes `.claude/settings.json` as `--settings`, with four additions that leave its permissions alone: a cheap model, a spending cap, the result as JSON, and no transcript kept. A fifth, `--setting-sources project,local`, leaves out the person's own settings, since an allow of theirs would let through a write loom's file refuses, which is the failure this tier exists to see; the project's reading of the file, the one DR-343-ikmartin measured beside `--settings`, stays. The client runs with the person's HOME, where its login is, and their PATH, with a shim first on it that records each `loom` command before running this checkout's loom.
    """
    assert CLAUDE is not None
    cmd = [CLAUDE, "-p", prompt, "--settings", ".claude/settings.json"]
    cmd += ["--model", MODEL, "--max-budget-usd", BUDGET, "--output-format", "json", "--no-session-persistence"]
    cmd += ["--setting-sources", "project,local"]
    shims, log = q.parent / "bin", q.parent / "loom-commands.log"
    shims.mkdir(exist_ok=True)
    loom = Path(sys.executable).parent / "loom"
    assert loom.is_file(), f"no loom beside {sys.executable}"
    (shims / "loom").write_text(f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{log}"\nexec "{loom}" "$@"\n', encoding="utf-8")
    (shims / "loom").chmod(0o755)
    env = person_env(shims)
    proc = subprocess.run(cmd, cwd=q, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
    said = f"\n$ {' '.join(cmd)}\nexit {proc.returncode}\n--- stdout\n{proc.stdout.rstrip()}\n--- stderr\n{proc.stderr.rstrip()}\n"
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError("the client printed no JSON result" + said) from None
    assert isinstance(result, dict) and "permission_denials" in result, "the client's result names no refusals" + said
    ran = log.read_text(encoding="utf-8").splitlines() if log.is_file() else []
    return result, ran


def refusals(result: dict[str, Any], *tools: str) -> list[dict[str, Any]]:
    """The inputs of every call to one of `tools` the client's permissions refused this turn."""
    return [d.get("tool_input") or {} for d in result["permission_denials"] if d.get("tool_name") in tools]


def test_a_launched_claude_writes_in_the_agents_drafting_directory_and_not_the_authors(tmp_path: Path) -> None:
    """DR-343-ikmartin and DR-275-ikmartin: the allow must hold where a launched turn reads it, under `--settings` from the quilt's root, and the deny on the author's drafting directory must refuse the Write tool, not only Edit. The unit tier checks the rules as text; only the client says what they do."""
    gate(CLAUDE, "claude")
    q = quilt(tmp_path)
    result, _ = turn(q, WRITES)
    tried = [Path(str(i.get("file_path", ""))).parts[-2:] for i in refusals(result, "Write", "Edit", "MultiEdit")]
    assert ("drafting-ai", "client-check.txt") not in tried, f"the allow on drafting-ai/ did not hold: {result}"
    assert (q / "drafting-ai" / "client-check.txt").is_file(), f"nothing was written in drafting-ai/: {result}"
    assert not (q / "drafting" / "client-check.txt").exists(), f"the deny on drafting/ did not hold: {result}"
    # the file's absence proves nothing unless the write was tried and refused
    assert ("drafting", "client-check.txt") in tried, f"no write to drafting/ was refused: {result}"


def test_a_launched_claude_runs_the_agents_loom_commands_and_not_the_authors(tmp_path: Path) -> None:
    """The shell variant, DR-275-ikmartin: an agent started for a turn cannot answer a prompt, so its own commands are allowed outright and the author's are denied; the shim on PATH tells a command the client refused from one loom refused after it ran."""
    gate(CLAUDE, "claude")
    q = quilt(tmp_path, "--shell")
    result, ran = turn(q, COMMANDS)
    words = [line.split()[:1] for line in ran]
    assert ["status"] in words, f"loom status, which the agent may run, never ran: {ran}, {result}"
    assert ["accept"] not in words, f"loom accept, which is the author's, ran: {ran}"
    tried = [str(i.get("command", "")) for i in refusals(result, "Bash")]
    assert any("loom accept" in c for c in tried), f"no loom accept was refused: {result}"


def test_a_claude_attached_over_mcp_writes_as_its_agent_and_runs_no_loom_in_a_shell(tmp_path: Path) -> None:
    """The default variant: the client starts the server from the `.mcp.json` loom wrote, its tools are allowed outright, and `loom` typed in a shell is refused; the record's author is the name the file gave the server, so the shim on PATH, which the server's absolute command never passes through, logs no `loom` at all."""
    gate(CLAUDE, "claude")
    q = quilt(tmp_path)
    result, ran = turn(q, OVER_MCP)
    mine = [ln for ln in (q / "annotations" / "log.jsonl").read_text().splitlines() if "client check" in ln]
    assert mine and '"author": "Claude Code Agent"' in mine[-1], (
        f"no annotation over MCP as Claude Code Agent: {result}"
    )
    refused_tools = [d for d in result["permission_denials"] if str(d.get("tool_name", "")).startswith("mcp__loom__")]
    assert not refused_tools, f"a loom tool was refused: {result}"
    assert not [line for line in ran if line.split()[:1] == ["accept"]], f"loom accept ran in a shell: {ran}"
    tried = [str(i.get("command", "")) for i in refusals(result, "Bash")]
    assert any("loom accept" in c for c in tried), f"no loom accept was refused: {result}"


def test_a_claude_attached_over_mcp_reads_a_resource_and_expands_a_modes_prompt(tmp_path: Path) -> None:
    """The two surfaces a person uses rather than the agent: a resource the model reads by its `quilt:` address, which needs no permission rule, and a mode's prompt; the session's command log says which surface ran each command, so a prompt that never expanded, leaving the model to call `loom_ai_mode` itself, does not pass."""
    gate(CLAUDE, "claude")
    q = quilt(tmp_path)
    ok("session", "new", "--name", "client check", "--as", "A. Author", cwd=q)
    result, ran = turn(q, READ_A_RESOURCE)
    assert "\\label{dm-0002}" in str(result.get("result", "")), f"the reply has no label from quilt:dm-0002: {result}"
    assert not result["permission_denials"], f"something was refused: {result}"
    prompted, ran_too = turn(q, A_PROMPT)
    assert not prompted["permission_denials"], f"something was refused: {prompted}"
    assert not [line for line in ran + ran_too if line.split()[:1]], f"loom ran in a shell: {ran + ran_too}"
    log = "\n".join(p.read_text() for p in (q / ".loom" / "sessions").glob("*/run.log"))
    assert "loom source dm-0002  (over MCP, reading quilt:dm-0002)" in log, f"no resource read was logged: {log}"
    assert "loom ai mode quick  (over MCP, for the quick prompt)" in log, (
        f"the prompt did not expand: {log}, {prompted}"
    )


def test_a_claude_attached_over_mcp_hears_what_the_person_did_since_it_last_looked(tmp_path: Path) -> None:
    """The bridge: the person annotates before the agent looks, and `loom_since`, run as the agent the server names, hands it the annotation whole; the marker it moves is the agent's own."""
    gate(CLAUDE, "claude")
    q = quilt(tmp_path)
    ok("session", "new", "--name", "client check", "--as", "A. Author", cwd=q)
    ok("annotate", "dm-0002", LEFT, "--kind", "question", "--as", "A. Author", cwd=q)
    result, ran = turn(q, HEAR_SINCE)
    assert LEFT in str(result.get("result", "")), f"the reply does not quote the person's annotation: {result}"
    assert not result["permission_denials"], f"something was refused: {result}"
    assert not [line for line in ran if line.split()[:1]], f"loom ran in a shell: {ran}"
    log = "\n".join(p.read_text() for p in (q / ".loom" / "sessions").glob("*/run.log"))
    assert "loom since --as 'Claude Code Agent'  (over MCP)" in log, f"no loom since was logged: {log}"
    assert (q / ".loom" / "since" / "claude-code-agent.json").is_file(), "the agent's marker did not move"
