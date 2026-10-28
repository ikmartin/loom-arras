"""`loom mcp`'s server: the agent commands as MCP tools over stdio, each call run as the `loom` command it stands for.

Every call is a `loom` subprocess in the quilt's root, under `AI_AGENT=1`, so the agent guard (K5) stands behind each one, and the command it ran is the command a person reruns. Reading tools run side by side; every other one takes one lock, so two writes never race for an id. The only module that imports the SDK.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import mcp.types as types

from loom.ai.layout import ACTS
from loom.mcp.tools import CallRefused, ToolSpec, argv, hints, schema, tools

#: A result longer than this many characters goes to a file the agent reads with its own tools: about ten thousand tokens, where Claude Code starts warning, and well under every client's own limit.
LARGE = 40_000


def serve(root: Path, name: str) -> None:
    """Serve the quilt at `root` to the agent `name` until the client closes stdin."""
    import anyio
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.shared.exceptions import MCPError

    from loom.ai.orient import instructions
    from loom.version import __version__

    specs = {s.name: s for s in tools()}
    listed = [
        types.Tool(
            name=s.name,
            description=s.description,
            input_schema=schema(s),
            annotations=_annotations(s),
        )
        for s in specs.values()
    ]
    lock = anyio.Lock()

    async def on_list_tools(ctx: Any, params: Any) -> types.ListToolsResult:
        return types.ListToolsResult(tools=listed)

    async def on_call_tool(ctx: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        spec = specs.get(params.name)
        if spec is None:
            raise MCPError(code=types.INVALID_PARAMS, message=f"no tool {params.name}; tools/list names them")
        arguments = dict(params.arguments or {})
        try:
            words = argv(spec, arguments, as_name=name)
        except CallRefused as exc:
            return _error(str(exc), "")
        command = "loom " + shlex.join(words)
        try:
            if ACTS[spec.path] == "read":
                done = await _run(root, words)
            else:
                async with lock:
                    done = await _run(root, words)
            _log(root, arguments.get("session"), command)
            return _result(root, spec, arguments, command, done)
        except Exception as exc:  # the SDK turns anything uncaught into a protocol error, which says nothing useful
            return _error(f"loom could not run {command}: {exc}", command)

    server = Server(
        "loom",
        version=__version__,
        instructions=instructions(root, name),
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )

    async def main() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(main)


async def _run(root: Path, words: list[str]) -> subprocess.CompletedProcess[bytes]:
    """`loom WORDS` in the quilt's root, as an agent: no progress lines, no log line of its own, and no standard input."""
    import anyio

    env = {**os.environ, "AI_AGENT": "1", "LOOM_PROGRESS": "off", "LOOM_LOGGED": "1"}
    return await anyio.run_process(
        [sys.executable, "-m", "loom", *words], cwd=root, env=env, check=False, stdin=subprocess.DEVNULL
    )


def _result(
    root: Path,
    spec: ToolSpec,
    arguments: dict[str, Any],
    command: str,
    done: subprocess.CompletedProcess[bytes],
) -> types.CallToolResult:
    """A finished command as a tool result: exit 2, or a crash, is an error carrying what it said; exit 0 or 1 is the report, the exit in `_meta`."""
    out = done.stdout.decode("utf-8", errors="replace")
    err = done.stderr.decode("utf-8", errors="replace").strip()
    meta = {"loom/command": command, "loom/exit": done.returncode}
    if done.returncode == 2 or (done.returncode != 0 and not out.strip()):
        return _error(err or f"{command} exited {done.returncode}", command, done.returncode)
    as_json = bool(arguments.get("json"))
    text = out if as_json or not err else out.rstrip("\n") + "\n\n" + err + "\n"
    if len(text) > LARGE:
        path = _keep(root, spec, arguments, text)
        first = next((ln for ln in out.splitlines() if ln.strip()), "")
        said = f"{first}\n\nThe whole result is {len(text):,} characters, so it is in {path}; read or search that file."
        return types.CallToolResult(content=[types.TextContent(text=said)], _meta={**meta, "loom/file": path})
    structured = None
    if as_json:
        try:
            structured = json.loads(out)
        except json.JSONDecodeError:
            structured = None
    return types.CallToolResult(
        content=[types.TextContent(text=text)],
        structured_content=structured if isinstance(structured, dict) else None,
        _meta=meta,
    )


def _annotations(spec: ToolSpec) -> types.ToolAnnotations:
    said = hints(spec)
    return types.ToolAnnotations(
        read_only_hint=said["read_only_hint"],
        destructive_hint=said["destructive_hint"],
        idempotent_hint=said["idempotent_hint"],
        open_world_hint=said["open_world_hint"],
    )


def _error(text: str, command: str, code: int = 2) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(text=text)], is_error=True, _meta={"loom/command": command, "loom/exit": code}
    )


def _session(root: Path, given: object) -> str | None:
    """The session a call names, or the active one; None when neither names one."""
    from loom.cli._common import find_session

    try:
        return str(find_session(root, str(given) if given else None).id)
    except Exception:
        return None


def _keep(root: Path, spec: ToolSpec, arguments: dict[str, Any], text: str) -> str:
    """Write a large result under `build/agent/<session>/`, which an agent may read and write and nothing commits; its quilt-relative path."""
    where = root / "build" / "agent" / (_session(root, arguments.get("session")) or "none")
    where.mkdir(parents=True, exist_ok=True)
    stem = datetime.now().strftime("%Y-%m-%dT%H-%M-%S") + "-" + spec.name.removeprefix("loom_")
    path, n = where / f"{stem}.txt", 2
    while path.exists():
        path, n = where / f"{stem}-{n}.txt", n + 1
    path.write_text(text, encoding="utf-8")
    return path.relative_to(root).as_posix()


def _log(root: Path, given: object, command: str) -> None:
    """One line per call in the session's run.log, the command a person would rerun; the commands' own logging steps aside under the server."""
    from loom.clock import stamp
    from loom.sessions import files_dir

    sid = _session(root, given)
    if sid is None:
        return
    from loom.sessions import sessions

    found = sessions(root).get(sid)
    if found is None:
        return
    p = files_dir(root, found)
    p.mkdir(parents=True, exist_ok=True)
    with (p / "run.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp()}  {command}  (over MCP)\n")
