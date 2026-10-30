"""`loom mcp` over the protocol, through the SDK's own client: the instructions, the tools and their hints, what a call returns for each exit, a write as the agent, the command log, a result too long for a reply, the modes as prompts and what a link names as resources."""

from __future__ import annotations

import os
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import anyio
import pytest

from loom.ai.layout import MODES
from tests.helpers import refused
from tests.unit._quilts import demo, new_session, showcase

AGENT = "Test Agent"


def attached(q: Path, body: Callable[[Any], Awaitable[None]], mode: str = "auto") -> None:
    """Start `loom mcp --as AGENT` in `q` as an agent's app would, and run `body` with the connected client."""
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    server = StdioServerParameters(
        command=sys.executable, args=["-m", "loom", "mcp", "--as", AGENT], cwd=q, env=dict(os.environ)
    )

    async def main() -> None:
        async with Client(server, mode=mode) as client:  # type: ignore[arg-type]
            await body(client)

    anyio.run(main)


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_an_attached_agent_is_told_where_to_start_and_offered_every_agent_command(tmp_path: Path, mode: str) -> None:
    """Either protocol era: the current one has no handshake and carries the instructions in `server/discover`."""
    from loom.mcp.tools import tools

    q = demo(tmp_path)

    async def body(client: Any) -> None:
        said = client.instructions or ""
        assert len(said) <= 4096, len(said)  # Claude Code keeps no more
        first = said.split("\n", 1)[0]
        assert len(first) <= 512 and "loom_ai_orient" in first and AGENT in first, first  # Codex's summary
        assert "loom_here" in said and "loom_since" in said
        assert all(f"**{m}**" in said for m in MODES)
        listed = {t.name: t for t in (await client.list_tools()).tools}
        assert set(listed) == {s.name for s in tools()}
        assert listed["loom_status"].annotations.read_only_hint is True
        assert listed["loom_annotate"].annotations.read_only_hint is False
        assert listed["loom_write"].annotations.destructive_hint is True

    attached(q, body, mode)


def test_a_call_returns_the_commands_report_and_each_exit_as_it_means(tmp_path: Path) -> None:
    q = demo(tmp_path)
    (q / "nodes" / "dm-0098.tex").write_text("\\begin{lemma}\\label{dm-0001}\nTwice.\n\\end{lemma}\n")  # lint exits 1

    async def body(client: Any) -> None:
        status = await client.call_tool("loom_status", {})
        assert not status.is_error and status.content[0].text.startswith("11 keys of yours: 1 conflicted")
        assert status.meta["loom/command"] == "loom status" and status.meta["loom/exit"] == 0
        lint = await client.call_tool("loom_lint", {"json": True})
        assert not lint.is_error and lint.meta["loom/exit"] == 1  # a report that found errors is still a result
        assert lint.structured_content["ok"] is False and "diagnostics" in lint.structured_content
        nothing = await client.call_tool("loom_deps", {"key": "dm-9999"})
        assert nothing.is_error and "no such key: dm-9999" in nothing.content[0].text  # exit 2: a refusal
        bad = await client.call_tool("loom_status", {"bogus": True})
        assert bad.is_error and "takes no bogus" in bad.content[0].text

    attached(q, body)


def test_a_write_is_the_agents_and_each_call_is_logged_once(tmp_path: Path) -> None:
    q = demo(tmp_path)

    async def body(client: Any) -> None:
        r = await client.call_tool(
            "loom_annotate", {"target": "dm-0002", "message": "Which orbits?", "kind": "question"}
        )
        assert not r.is_error and f"({AGENT})" in r.content[0].text, r.content[0].text

    attached(q, body)
    log = (q / "annotations" / "log.jsonl").read_text().splitlines()[-1]
    assert f'"author": "{AGENT}"' in log and '"kind": "agent"' in log
    runs = [ln for p in (q / ".loom" / "sessions").glob("*/run.log") for ln in p.read_text().splitlines()]
    mine = [ln for ln in runs if "(over MCP)" in ln]
    assert len(mine) == 1 and "loom annotate --kind question --as 'Test Agent' dm-0002 'Which orbits?'" in mine[0]
    assert not [ln for ln in runs if "annotate" in ln and "(over MCP)" not in ln and "Which orbits" in ln]


def test_a_result_too_long_for_a_reply_is_a_file_the_agent_reads(tmp_path: Path) -> None:
    q = demo(tmp_path)
    (q / "nodes" / "dm-0097.tex").write_text(
        "\\begin{remark}\\label{dm-0097}\n" + "A long remark. " * 4000 + "\n\\end{remark}\n"
    )

    async def body(client: Any) -> None:
        r = await client.call_tool("loom_source", {"target": "dm-0097"})
        assert not r.is_error and "so it is in build/agent/" in r.content[0].text, r.content[0].text[:300]
        kept = q / r.meta["loom/file"]
        assert kept.is_file() and "A long remark." in kept.read_text() and len(kept.read_text()) > 40_000

    attached(q, body)


def test_each_mode_is_a_prompt_expanding_to_the_quilts_own_copy_and_its_checked_target(tmp_path: Path) -> None:
    q = demo(tmp_path)
    mode = q / "ai" / "modes" / "audit.md"
    mode.write_text(mode.read_text() + "\nThis quilt's own line.\n")
    new_session(q)

    async def body(client: Any) -> None:
        listed = (await client.list_prompts()).prompts
        assert [p.name for p in listed] == MODES
        assert all([(a.name, a.required) for a in p.arguments] == [("target", False)] for p in listed)
        got = await client.get_prompt("audit", {"target": "dm-0002"})
        text = got.messages[0].content.text
        assert text.startswith("Work in loom's audit mode on `dm-0002` (quilt:dm-0002).") and "loom_ai_orient" in text
        assert text.rstrip().endswith("This quilt's own line.")
        assert got.meta["loom/commands"] == ["loom link dm-0002", "loom ai mode audit"]
        assert "ask me what to work on" in (await client.get_prompt("flow")).messages[0].content.text
        with pytest.raises(Exception, match="no key dm-9999"):
            await client.get_prompt("audit", {"target": "dm-9999"})
        with pytest.raises(Exception, match="no prompt brainstorm"):
            await client.get_prompt("brainstorm")

    attached(q, body)
    runs = [ln for p in (q / ".loom" / "sessions").glob("*/run.log") for ln in p.read_text().splitlines()]
    assert [ln for ln in runs if "loom ai mode audit  (over MCP, for the audit prompt)" in ln]


def test_what_a_link_names_is_a_resource_read_by_the_command_it_stands_for(tmp_path: Path) -> None:
    q = showcase(tmp_path)
    reads = {
        "quilt:sh-0007": ("loom source sh-0007", "\\label{sh-0007}"),
        "quilt:sh-0007?closure": ("loom source --closure sh-0007", "\\label{sh-0007}"),
        "quilt:drafting/main-atomic.tex": ("loom source drafting/main-atomic.tex", "\\documentclass"),
        "quilt:.loom/history/0001-flows-v1/flows-v1.tex": ("loom history show flows-v1", "\\documentclass"),
        "quilt:state": ("loom ai orient", "# Research state"),
        "cited:doi:10.4171/showcase/19-2": ("loom library read doi:10.4171/showcase/19-2", "Bellamy19's overview"),
        "cited:doi:10.4171/showcase/19-2?page=3": ("loom library read doi:10.4171/showcase/19-2 3", "Bellamy19 p.3"),
    }

    async def body(client: Any) -> None:
        listed = {r.uri for r in (await client.list_resources()).resources}
        assert set(reads) - listed == {"quilt:sh-0007?closure", "cited:doi:10.4171/showcase/19-2?page=3"}
        assert len((await client.list_resource_templates()).resource_templates) == 4
        for uri, (command, said) in reads.items():
            r = await client.read_resource(uri)
            assert r.meta["loom/command"] == command and said in r.contents[0].text, (uri, r.contents[0].text[:300])
        with pytest.raises(Exception, match="loom_ai_annotations"):
            await client.read_resource("quilt:a-2026-01-01-1")
        with pytest.raises(Exception, match="no such key: sh-9999"):
            await client.read_resource("quilt:sh-9999")

    attached(q, body)


def test_a_resource_too_long_for_a_reply_is_a_file_the_agent_reads(tmp_path: Path) -> None:
    q = demo(tmp_path)
    (q / "nodes" / "dm-0097.tex").write_text(
        "\\begin{remark}\\label{dm-0097}\n" + "A long remark. " * 4000 + "\n\\end{remark}\n"
    )

    async def body(client: Any) -> None:
        r = await client.read_resource("quilt:dm-0097")
        assert "so it is in build/agent/" in r.contents[0].text, r.contents[0].text[:300]
        assert "A long remark." in (q / r.meta["loom/file"]).read_text()

    attached(q, body)


def test_the_server_serves_only_an_agent_and_says_what_it_needs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    q = demo(tmp_path)
    refused("mcp", "--as", "Isaac", cwd=q, code=2, match="Isaac does not say it is an agent")
    import builtins

    real = builtins.__import__

    def no_sdk(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "mcp":
            raise ImportError(name)
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_sdk)
    refused("mcp", "--as", AGENT, cwd=q, code=2, match="pip install 'loomtex[mcp]'")
