"""The MCP client files: one per app that reads a file in the quilt, each starting this loom's server for this quilt as that app's agent; gitignored, never written over a file of the person's or one git tracks, and gone in the shell variant."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import anyio
import pytest

from loom.ai.clients import CLIENTS, PROJECT, PROJECT_FILES, command
from loom.ai.layout import CLAUDE_SETTINGS, MCP, SHELL, permissions_json, quilt_config, variant
from loom.cli._common import is_agent
from tests.helpers import flat, json_of, ok
from tests.unit._quilts import demo

GIT = shutil.which("git")


def entry(q: Path, file: str) -> dict[str, Any]:
    """The `loom` server a client file names."""
    text = (q / file).read_text()
    if file.endswith(".toml"):
        return tomllib.loads(text)["mcp_servers"]["loom"]  # type: ignore[no-any-return]
    return json.loads(text)["mcpServers"]["loom"]  # type: ignore[no-any-return]


def files(q: Path) -> dict[str, bytes]:
    return {p.relative_to(q).as_posix(): p.read_bytes() for p in sorted(q.rglob("*")) if p.is_file()}


def test_ai_init_writes_a_file_per_app_naming_its_agent_this_loom_and_this_quilt(tmp_path: Path) -> None:
    q = demo(tmp_path)
    for rel in PROJECT_FILES:
        (q / rel).unlink()
    r = ok("ai", "init", cwd=q)
    assert "starts the loom MCP server, gitignored" in r.stdout and all(rel in r.stdout for rel in PROJECT_FILES)
    cmd, pre = command()
    assert Path(cmd).is_absolute()
    for c in PROJECT:
        assert c.file is not None and is_agent(c.agent)
        got = entry(q, c.file)
        assert got["command"] == cmd and got["args"] == [*pre, "mcp", "--as", c.agent, "--quilt", str(q.resolve())]
    assert entry(q, ".mcp.json")["type"] == "stdio" and entry(q, ".gemini/settings.json")["trust"] is True
    assert entry(q, ".codex/config.toml")["default_tools_approval_mode"] == "approve"
    data = json_of("ai", "init", "--json", cwd=q)
    assert data["variant"] == MCP and data["clients"]["current"] == list(PROJECT_FILES)
    assert data["clients"]["written"] == [] and data["verdict"] == "the agent layer is current; nothing written"


@pytest.mark.skipif(GIT is None, reason="no git")
def test_every_client_file_is_gitignored(tmp_path: Path) -> None:
    q = demo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=q, check=True)
    done = subprocess.run(["git", "check-ignore", *PROJECT_FILES], cwd=q, capture_output=True, text=True)
    assert done.stdout.split() == list(PROJECT_FILES)
    assert (
        ".codex/rules/loom.rules"
        not in subprocess.run(
            ["git", "check-ignore", ".codex/rules/loom.rules"], cwd=q, capture_output=True, text=True
        ).stdout
    )  # the permission files are the quilt's, and committed


def test_the_file_written_for_claude_code_starts_the_server_from_anywhere(tmp_path: Path) -> None:
    """What the app does with `.mcp.json`: run its command, from a directory that is not the quilt, and call a tool."""
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    q = demo(tmp_path)
    got = entry(q, ".mcp.json")
    server = StdioServerParameters(command=got["command"], args=got["args"], cwd=tmp_path, env=dict(os.environ))

    async def main() -> None:
        async with Client(server) as client:  # type: ignore[arg-type]
            r = await client.call_tool("loom_annotate", {"target": "dm-0002", "message": "Which orbits?"})
            assert not r.is_error, r.content[0].text

    anyio.run(main)
    assert '"author": "Claude Code Agent"' in (q / "annotations" / "log.jsonl").read_text().splitlines()[-1]


def test_a_file_of_the_persons_is_left_alone_and_the_entry_printed(tmp_path: Path) -> None:
    q = demo(tmp_path)
    mine = q / ".gemini" / "settings.json"
    mine.write_text('{"theme": "Dracula"}\n')
    r = ok("ai", "init", cwd=q)
    assert mine.read_text() == '{"theme": "Dracula"}\n'
    assert "holds settings of yours, so left alone" in r.stdout and "loom ai init --client gemini-cli" in flat(r.stdout)
    r = ok("ai", "init", "--client", "gemini-cli", cwd=q)
    assert r.stdout.startswith("the loom server for Gemini CLI, serving Gemini CLI Agent: add it to .gemini/settings")
    server = json.loads(r.stdout.split("\n\n", 1)[1])["mcpServers"]["loom"]
    assert server["trust"] is True and "Gemini CLI Agent" in server["args"]
    # a file that is loom's own entry with more beside it is the person's too
    claude = q / ".mcp.json"
    claude.write_text(json.dumps({"mcpServers": {**json.loads(claude.read_text())["mcpServers"], "other": {}}}))
    assert ".mcp.json" in json_of("ai", "init", "--json", cwd=q)["clients"]["foreign"]


@pytest.mark.parametrize("client", [c for c in CLIENTS if c.file is None], ids=lambda c: c.key)
def test_the_entry_for_an_app_configured_elsewhere_is_printed_and_nothing_written(tmp_path: Path, client: Any) -> None:
    q = demo(tmp_path)
    before = files(q)
    r = ok("ai", "init", "--client", client.key, cwd=q)
    assert files(q) == before
    assert "loom writes nothing outside the quilt" in flat(r.stdout) and client.where in flat(r.stdout)
    data = json.loads(r.stdout.split("\n\n", 1)[1])
    server = data["context_servers" if client.key == "zed" else "mcpServers"]["loom"]
    assert server["args"][-4:] == ["--as", client.agent, "--quilt", str(q.resolve())] and is_agent(client.agent)
    got = json_of("ai", "init", "--client", client.key, "--json", cwd=q)
    assert got["client"] == client.key and json.loads(got["entry"]) == data


def test_the_shell_variant_writes_no_client_file_and_is_kept(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = ok("ai", "init", "--shell", cwd=q)
    assert "removed: agents here run loom in a shell" in r.stdout
    assert not [rel for rel in PROJECT_FILES if (q / rel).exists()] and variant(q) == SHELL
    assert (q / CLAUDE_SETTINGS).read_text() == permissions_json(quilt_config(q), shell=True)
    ok("upgrade", cwd=q)
    ok("ai", "init", cwd=q)
    assert variant(q) == SHELL and not [rel for rel in PROJECT_FILES if (q / rel).exists()]
    ok("ai", "init", "--mcp", cwd=q)
    assert variant(q) == MCP and all((q / rel).is_file() for rel in PROJECT_FILES)


@pytest.mark.skipif(GIT is None, reason="no git")
def test_a_client_file_git_tracks_is_not_written(tmp_path: Path) -> None:
    q = demo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=q, check=True)
    subprocess.run(["git", "add", "-f", ".mcp.json"], cwd=q, check=True)
    claude = q / ".mcp.json"
    claude.write_text(claude.read_text().replace(str(q.resolve()), "/elsewhere"))
    r = ok("ai", "init", cwd=q)
    assert "tracked by git, so not written" in r.stdout and "git rm --cached .mcp.json" in flat(r.stdout)
    assert "/elsewhere" in claude.read_text()
