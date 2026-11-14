"""`loom mcp`'s server: the agent commands as MCP tools over stdio, each call run as the `loom` command it stands for; the modes as prompts; and what a link names as resources.

Every call is a `loom` subprocess in the quilt's root, under `AI_AGENT=1`, so the agent guard (K5) stands behind each one, and the command it ran is the command a person reruns. Reading tools run side by side; every other one takes one lock in the server, so an agent's own writes run in the order it sent them and not every write need be safe beside another. Ids are kept apart by the commands themselves (`loom.locks`), which is what holds across two servers or a shell beside one. A prompt and a resource read run reading commands the same way (`prompts.py`, `resources.py`); only the resource list, and the research state, which no command prints alone, are read in the server itself. The only module that imports the SDK.
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

from loom.ai.layout import ACTS, MODES
from loom.mcp.prompts import TARGET, TARGET_SAID, link_argv, message, mode_argv, prompts
from loom.mcp.resources import TEMPLATES, NotAResource, reading
from loom.mcp.resources import listed as resources_listed
from loom.mcp.tools import CallRefused, ToolSpec, argv, hints, schema, tools
from loom.paths import BUILD

#: A result longer than this many characters goes to a file the agent reads with its own tools: about ten thousand tokens, where Claude Code starts warning, and well under every client's own limit.
LARGE = 40_000
#: Commands whose result is never such a file: an agent attached over MCP may have no tool that reads one, and the orientation is what it works from.
WHOLE = frozenset({"ai orient"})
#: The most crops one result carries as images; the rest are counted.
MAX_IMAGES = 8


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

    async def read(words: list[str], why: str) -> tuple[str, str, int]:
        """Run a reading command for a prompt or a resource and log it with `why`; (stdout, stderr, exit), or MCPError when it refused or failed."""
        command = "loom " + shlex.join(words)
        done = await _run(root, words)
        _log(root, None, command, why)
        out = done.stdout.decode("utf-8", errors="replace")
        err = done.stderr.decode("utf-8", errors="replace").strip()
        if done.returncode == 2 or (done.returncode != 0 and not out.strip()):
            code = types.INVALID_PARAMS if done.returncode == 2 else types.INTERNAL_ERROR
            raise MCPError(code=code, message=err or f"{command} exited {done.returncode}")
        return out, err, done.returncode

    async def on_list_prompts(ctx: Any, params: Any) -> types.ListPromptsResult:
        argument = types.PromptArgument(name=TARGET, description=TARGET_SAID, required=False)
        return types.ListPromptsResult(
            prompts=[
                types.Prompt(name=p.name, title=p.name, description=p.description, arguments=[argument])
                for p in prompts(root)
            ]
        )

    async def on_get_prompt(ctx: Any, params: types.GetPromptRequestParams) -> types.GetPromptResult:
        if params.name not in MODES:
            raise MCPError(code=types.INVALID_PARAMS, message=f"no prompt {params.name}; prompts/list names them")
        given = dict(params.arguments or {})
        if set(given) - {TARGET}:
            raise MCPError(code=types.INVALID_PARAMS, message=f"{params.name} takes one argument, {TARGET}")
        target = str(given.get(TARGET) or "").strip()
        href, commands = "", []
        if target:
            out, _, _ = await read(link_argv(target), f"for the {params.name} prompt")
            href = out.strip().removeprefix("[](").removesuffix(")")
            commands.append("loom " + shlex.join(link_argv(target)))
        mode, _, _ = await read(mode_argv(params.name), f"for the {params.name} prompt")
        commands.append("loom " + shlex.join(mode_argv(params.name)))
        return types.GetPromptResult(
            description=f"loom's {params.name} mode" + (f" on {target}" if target else ""),
            messages=[
                types.PromptMessage(
                    role="user", content=types.TextContent(text=message(params.name, target, href, mode))
                )
            ],
            _meta={"loom/commands": commands},
        )

    async def on_list_resources(ctx: Any, params: Any) -> types.ListResourcesResult:
        from loom.scan.quilt import load_quilt
        from loom.scan.scan import scan

        try:
            result = await anyio.to_thread.run_sync(lambda: scan(load_quilt(root)))
        except Exception as exc:  # a quilt that does not read is said, not a protocol error
            raise MCPError(code=types.INTERNAL_ERROR, message=f"loom could not read the quilt: {exc}") from exc
        return types.ListResourcesResult(
            resources=[
                types.Resource(uri=r.uri, name=r.name, title=r.title, description=r.description, mime_type=r.mime)
                for r in resources_listed(result)
            ]
        )

    async def on_list_resource_templates(ctx: Any, params: Any) -> types.ListResourceTemplatesResult:
        return types.ListResourceTemplatesResult(
            resource_templates=[
                types.ResourceTemplate(
                    uri_template=t.uri, name=t.name, title=t.title, description=t.description, mime_type=t.mime
                )
                for t in TEMPLATES
            ]
        )

    async def on_read_resource(ctx: Any, params: types.ReadResourceRequestParams) -> types.ReadResourceResult:
        from loom.ai.orient import research_state
        from loom.scan.quilt import load_quilt

        quilt = load_quilt(root)
        try:
            how = reading(params.uri, quilt)
        except NotAResource as exc:
            raise MCPError(code=types.INVALID_PARAMS, message=str(exc)) from None
        if how.argv is None:
            # the research state, which no command prints alone: the block `loom ai orient` prints, its hash included
            lines = research_state(quilt)
            if lines[0].startswith("- research state: none yet"):
                raise MCPError(code=types.INVALID_PARAMS, message=lines[0].removeprefix("- "))
            command, text, code = "loom ai orient", "\n".join(lines).strip("\n") + "\n", 0
        else:
            command = "loom " + shlex.join(how.argv)
            out, err, code = await read(list(how.argv), f"reading {params.uri}")
            text = out if not err else out.rstrip("\n") + "\n\n" + err + "\n"
        meta: dict[str, Any] = {"loom/command": command, "loom/exit": code}
        if len(text) > LARGE:
            path = _keep(root, None, (how.argv or ("state",))[0], text)
            text = f"The whole text is {len(text):,} characters, so it is in {path}; read or search that file.\n"
            meta["loom/file"] = path
        return types.ReadResourceResult(
            contents=[types.TextResourceContents(uri=params.uri, mime_type=how.mime, text=text)], _meta=meta
        )

    server = Server(
        "loom",
        version=__version__,
        instructions=instructions(root, name),
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
        on_list_prompts=on_list_prompts,
        on_get_prompt=on_get_prompt,
        on_list_resources=on_list_resources,
        on_list_resource_templates=on_list_resource_templates,
        on_read_resource=on_read_resource,
    )

    async def main() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(main)


async def _run(root: Path, words: list[str]) -> subprocess.CompletedProcess[bytes]:
    """`loom WORDS` in the quilt's root, as an agent: no progress lines, no log line of its own, and no standard input.

    Python starts in safe-path mode (`-P`, and `PYTHONSAFEPATH` for any Python the command starts in turn): `-m` otherwise puts the working directory first on `sys.path`, and a `loom.py` or a `json.py` in the quilt's root, which an agent or a co-author can write, would run in loom's place on every call.
    """
    import anyio

    env = {**os.environ, "AI_AGENT": "1", "LOOM_PROGRESS": "off", "LOOM_LOGGED": "1", "PYTHONSAFEPATH": "1"}
    return await anyio.run_process(
        [sys.executable, "-P", "-m", "loom", *words], cwd=root, env=env, check=False, stdin=subprocess.DEVNULL
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
    images, more = _crops(root, out)
    if more:
        text = (
            text.rstrip("\n")
            + f"\n\n{more} more crop{'s' if more != 1 else ''} than the {MAX_IMAGES} shown; each path is above.\n"
        )
    if len(text) > LARGE and spec.path not in WHOLE:
        path = _keep(root, arguments.get("session"), spec.name.removeprefix("loom_"), text)
        first = next((ln for ln in out.splitlines() if ln.strip()), "")
        said = f"{first}\n\nThe whole result is {len(text):,} characters, so it is in {path}; read or search that file."
        return types.CallToolResult(content=[types.TextContent(text=said), *images], _meta={**meta, "loom/file": path})
    structured = None
    if as_json:
        try:
            structured = json.loads(out)
        except json.JSONDecodeError:
            structured = None
    return types.CallToolResult(
        content=[types.TextContent(text=text), *images],
        structured_content=structured if isinstance(structured, dict) else None,
        _meta=meta,
    )


def _crops(root: Path, out: str) -> tuple[list[types.ImageContent], int]:
    """The crops a result names, as images an agent sees: each `crop` value in its JSON and each `crop:` line of its text, in order and once, kept only when it is a file under `.loom/build/crops/`; at most `MAX_IMAGES`, and how many more there were.

    A crop is a picture of a page round a mark (`records.crops`), made by loom; what an agent reads off it is its own reading.
    """
    import base64
    import re

    from loom.records.crops import CROPS

    named: list[str] = []
    try:
        data: Any = json.loads(out)
    except json.JSONDecodeError:
        data = None

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "crop" and isinstance(v, str):
                    named.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    named += re.findall(r"^\s*crop: (\S+)", out, re.M)
    home = (root / CROPS).resolve()
    kept: list[Path] = []
    for rel in dict.fromkeys(named):
        path = (root / rel).resolve()
        if path.is_file() and path.parent == home and path.suffix == ".png":
            kept.append(path)
    images = [
        types.ImageContent(data=base64.b64encode(p.read_bytes()).decode("ascii"), mime_type="image/png")
        for p in kept[:MAX_IMAGES]
    ]
    return images, max(0, len(kept) - MAX_IMAGES)


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


def _keep(root: Path, session: object, what: str, text: str) -> str:
    """Write a large result under `.loom/build/agent/<session>/`, which an agent may read and write and nothing commits, named for `what` produced it; its quilt-relative path."""
    where = root / BUILD / "agent" / (_session(root, session) or "none")
    where.mkdir(parents=True, exist_ok=True)
    stem = datetime.now().strftime("%Y-%m-%dT%H-%M-%S") + "-" + what
    path, n = where / f"{stem}.txt", 2
    # created exclusively, so a second server keeping a result in the same second takes the next name
    while True:
        try:
            with path.open("x", encoding="utf-8") as fh:
                fh.write(text)
            return path.relative_to(root).as_posix()
        except FileExistsError:
            path, n = where / f"{stem}-{n}.txt", n + 1


def _log(root: Path, given: object, command: str, why: str = "") -> None:
    """One line per call in the session's run.log, the command a person would rerun, and `why` when a prompt or a resource read ran it; the commands' own logging steps aside under the server."""
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
        fh.write(f"{stamp()}  {command}  (over MCP{', ' + why if why else ''})\n")
