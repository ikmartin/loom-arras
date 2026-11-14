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
    (q / "drafting" / "nodes" / "dm-0098.tex").write_text(
        "\\begin{lemma}\\label{dm-0001}\nTwice.\n\\end{lemma}\n"
    )  # lint exits 1

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


#: A module that says it ran, for a quilt's root: what `python -m loom` there would import in loom's place.
SHADOW = "import pathlib\npathlib.Path('SHADOW_RAN').write_text('ran')\nprint('SHADOW')\n"


@pytest.mark.parametrize("planted", ["loom.py", "loom/__init__.py", "json.py"])
def test_a_module_planted_in_the_quilts_root_never_runs_in_looms_place(tmp_path: Path, planted: str) -> None:
    """A tool call starts Python in the quilt's root, where an agent or a co-author can leave a file named for loom or for a module it imports. The server here is started as an app starts it (`ai.clients.command`), which the same file must not become either."""
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    from loom.ai.clients import command

    q = demo(tmp_path)
    (q / planted).parent.mkdir(exist_ok=True)
    (q / planted).write_text(SHADOW)
    cmd, pre = command()
    server = StdioServerParameters(command=cmd, args=[*pre, "mcp", "--as", AGENT], cwd=q, env=dict(os.environ))

    async def main() -> None:
        async with Client(server) as client:  # type: ignore[arg-type]
            status = await client.call_tool("loom_status", {})
            assert not status.is_error and "SHADOW" not in status.content[0].text, status.content[0].text
            assert status.content[0].text.startswith("11 keys of yours")

    anyio.run(main)
    assert not (q / "SHADOW_RAN").exists()


def test_a_write_is_the_agents_and_each_call_is_logged_once(tmp_path: Path) -> None:
    q = demo(tmp_path)

    async def body(client: Any) -> None:
        r = await client.call_tool(
            "loom_annotate", {"target": "dm-0002", "message": "Which orbits?", "type": "question"}
        )
        assert not r.is_error and f"({AGENT})" in r.content[0].text, r.content[0].text

    attached(q, body)
    log = (q / ".loom/annotations" / "log.jsonl").read_text().splitlines()[-1]
    assert f'"author": "{AGENT}"' in log and '"kind": "agent"' in log
    runs = [ln for p in (q / ".loom" / "sessions").glob("*/run.log") for ln in p.read_text().splitlines()]
    mine = [ln for ln in runs if "(over MCP)" in ln]
    assert len(mine) == 1 and "loom annotate --type question --as 'Test Agent' dm-0002 'Which orbits?'" in mine[0]
    assert not [ln for ln in runs if "annotate" in ln and "(over MCP)" not in ln and "Which orbits" in ln]


def test_the_orientation_is_never_a_file_however_long_the_research_state(tmp_path: Path) -> None:
    """An agent attached over MCP may have no tool that reads a file, and a real quilt's research state already carries the orientation past the length that sends a result to one."""
    q = demo(tmp_path)
    (q / "research-state.md").write_text("A long state. " * 800)

    async def body(client: Any) -> None:
        r = await client.call_tool("loom_ai_orient", {})
        said = r.content[0].text
        assert not r.is_error and len(said) > 40_000 and "so it is in" not in said, said[:300]
        assert said.startswith("# Orientation: working in a quilt") and "# Live state" in said

    attached(q, body)


def test_a_result_too_long_for_a_reply_is_a_file_the_agent_reads(tmp_path: Path) -> None:
    q = demo(tmp_path)
    (q / "drafting" / "nodes" / "dm-0097.tex").write_text(
        "\\begin{remark}\\label{dm-0097}\n" + "A long remark. " * 4000 + "\n\\end{remark}\n"
    )

    async def body(client: Any) -> None:
        r = await client.call_tool("loom_source", {"target": "dm-0097"})
        assert not r.is_error and "so it is in .loom/build/agent/" in r.content[0].text, r.content[0].text[:300]
        kept = q / r.meta["loom/file"]
        assert kept.is_file() and "A long remark." in kept.read_text() and len(kept.read_text()) > 40_000

    attached(q, body)


def test_each_mode_is_a_prompt_expanding_to_the_quilts_own_copy_and_its_checked_target(tmp_path: Path) -> None:
    q = demo(tmp_path)
    mode = q / ".loom/ai" / "modes" / "audit.md"
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
    (q / "drafting" / "nodes" / "dm-0097.tex").write_text(
        "\\begin{remark}\\label{dm-0097}\n" + "A long remark. " * 4000 + "\n\\end{remark}\n"
    )

    async def body(client: Any) -> None:
        r = await client.read_resource("quilt:dm-0097")
        assert "so it is in .loom/build/agent/" in r.contents[0].text, r.contents[0].text[:300]
        assert "A long remark." in (q / r.meta["loom/file"]).read_text()

    attached(q, body)


def test_the_server_serves_only_an_agent_and_says_what_it_needs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    q = demo(tmp_path)
    refused("mcp", "--as", "Isaac", cwd=q, code=2, match="Isaac does not say it is an agent")
    monkeypatch.setattr("loom.mcp.sdk.has_sdk", lambda: False)
    refused("mcp", "--as", AGENT, cwd=q, code=2, match="loom mcp needs the MCP SDK")


def test_two_servers_on_one_quilt_never_lose_a_node(tmp_path: Path) -> None:
    """Measured before the lock: 16 calls over two servers all reported success, and 8 files existed. The server's own lock is one server's, so what holds here is the command's."""
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    q = demo(tmp_path)
    nodes = q / "drafting" / "nodes"
    before = {p.name for p in nodes.glob("*.tex")}
    calls = 6
    reports: list[Any] = []

    def server(name: str) -> StdioServerParameters:
        return StdioServerParameters(
            command=sys.executable, args=["-m", "loom", "mcp", "--as", name], cwd=q, env=dict(os.environ)
        )

    async def main() -> None:
        async with Client(server("First Agent")) as a, Client(server("Second Agent")) as b:  # type: ignore[arg-type]

            async def call(client: Any, i: int) -> None:
                reports.append(await client.call_tool("loom_new", {"taxon": "definition", "title": f"Race {i}"}))

            async with anyio.create_task_group() as tasks:
                for i in range(calls):
                    tasks.start_soon(call, a if i % 2 else b, i)

    anyio.run(main)
    assert not [r.content[0].text for r in reports if r.is_error]
    made = {p.name for p in nodes.glob("*.tex")} - before
    assert len(made) == calls, made
    assert {f"[Race {i}]" for i in range(calls)} == {
        f"[{line.split('[', 1)[1].split(']', 1)[0]}]"
        for name in made
        for line in (nodes / name).read_text().splitlines()
        if line.startswith("\\begin{definition}")
    }


def test_two_large_results_in_one_second_are_kept_in_two_files(tmp_path: Path) -> None:
    from loom.mcp.server import _keep

    first, second = _keep(tmp_path, None, "status", "one"), _keep(tmp_path, None, "status", "two")
    assert first != second
    assert (tmp_path / first).read_text() == "one" and (tmp_path / second).read_text() == "two"


def test_thirty_annotations_on_an_unchanged_key_keep_one_frozen_text_by_batch_or_by_call(tmp_path: Path) -> None:
    """Plan 0.30's acceptance: the text an annotation is written on is frozen once for each version, so thirty annotations on an unchanged key name one frozen text and add at most one copy, whether one `--batch` carries them or thirty calls over MCP do."""
    import json

    from tests.helpers import ok

    said = [{"target": "dm-0002", "message": f"Point {n}.", "type": "question"} for n in range(30)]

    def frozen(q: Path) -> set[str]:
        d = q / ".loom" / "history" / "texts"
        return {p.name for p in d.iterdir()} if d.is_dir() else set()

    def lines(q: Path) -> list[str]:
        log = q / ".loom" / "annotations" / "log.jsonl"
        return log.read_text().splitlines() if log.is_file() else []

    for d in ("batch", "calls"):
        (tmp_path / d).mkdir()
    batched, called = demo(tmp_path / "batch"), demo(tmp_path / "calls")
    starts = {q: (frozen(q), len(lines(q))) for q in (batched, called)}
    ok("annotate", "--batch", "--as", AGENT, cwd=batched, stdin="".join(json.dumps(s) + "\n" for s in said))

    async def body(client: Any) -> None:
        for s in said:
            r = await client.call_tool("loom_annotate", s)
            assert not r.is_error, r.content[0].text

    attached(called, body)
    for q, (texts_before, lines_before) in starts.items():
        made = [e for e in map(json.loads, lines(q)[lines_before:]) if e["event"] == "created"]
        assert len(made) == 30 and len({e["against"] for e in made}) == 1, q.parent.name
        assert len(frozen(q) - texts_before) <= 1, q.parent.name


def test_a_result_carries_the_crops_it_names_as_images(tmp_path: Path) -> None:
    """From a `crop` value in JSON and a `crop:` line in text, once each and in order; a path outside `.loom/build/crops/` is no crop; at most eight, the rest counted."""
    import base64
    import json

    from loom.mcp.server import MAX_IMAGES, _crops

    crops = tmp_path / ".loom" / "build" / "crops"
    crops.mkdir(parents=True)
    names = [f"{n:016x}-p1-{n:016x}.png" for n in range(10)]
    for name in names:
        (crops / name).write_bytes(b"\x89PNG\r\n\x1a\n" + name.encode())
    (tmp_path / "elsewhere.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    data = {"annotations": [{"crop": f".loom/build/crops/{names[0]}"}, {"crop": "elsewhere.png"}, {"crop": None}]}
    images, more = _crops(tmp_path, json.dumps(data))
    assert [i.mime_type for i in images] == ["image/png"] and more == 0
    lines = [f"      crop: .loom/build/crops/{n}" for n in [names[1], names[1], *names[2:]]]
    images, more = _crops(tmp_path, "\n".join([*lines, "      crop: ../x.png"]))
    assert len(images) == MAX_IMAGES and more == 1
    assert base64.b64decode(images[0].data).endswith(names[1].encode())


@pytest.mark.poppler
def test_an_agent_over_mcp_is_given_a_crop_for_a_mark(tmp_path: Path) -> None:
    """The author marks a project PDF; the agent asks for the annotations and sees the page round the mark as an image beside the text."""
    from tests.helpers import ok
    from tests.unit._pdfs import PROSE, lines_pdf

    q = demo(tmp_path)
    lines_pdf(q / "notes" / "paper.pdf", [PROSE])
    words = ("--quote", "the median polytope is integral", "--type", "question", "--as", "Tester")
    ok("annotate", "notes/paper.pdf", "Is this used later?", "--page", "1", *words, cwd=q)

    async def body(client: Any) -> None:
        got = await client.call_tool("loom_ai_annotations", {"target": "notes/paper.pdf"})
        assert not got.is_error
        text, *images = got.content
        assert "crop: .loom/build/crops/" in text.text and "notes/paper.pdf p.1" in text.text, text.text
        assert [c.type for c in images] == ["image"] and images[0].mime_type == "image/png"
        as_json = await client.call_tool("loom_ai_annotations", {"target": "notes/paper.pdf", "json": True})
        (row,) = as_json.structured_content["annotations"]
        assert (row["page"], row["file"], row["refound"]) == (1, "notes/paper.pdf", False)
        assert row["crop"].startswith(".loom/build/crops/") and len(as_json.content) == 2

    attached(q, body)
