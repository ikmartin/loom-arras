"""`loom mcp --as NAME`: the MCP server an agent's app starts for this quilt."""

from __future__ import annotations

import click

from loom.cli._common import EnvError, is_agent
from loom.cli._quilt import open_quilt, quilt_option


@click.command(name="mcp")
@click.option(
    "--as",
    "as_name",
    required=True,
    metavar="NAME",
    help="The agent this server serves, with Agent or AI in the name; every write is recorded under it.",
)
@quilt_option
def mcp_command(as_name: str, quilt_path: str | None) -> None:
    """Serve this quilt's agent commands as MCP tools over stdio, for an agent's app to start; it runs until the app closes it.

    One tool per agent command, named for it (`loom status` is `loom_status`), its options its arguments; the author's commands are not tools. Each call runs the command it names, as NAME, and its result is that command's report. The instructions tell the agent to call `loom_ai_orient` first. A result too long for a reply is written under `build/agent/` and the tool returns its path.
    """
    if not is_agent(as_name):
        raise EnvError(
            f"{as_name} does not say it is an agent; give a name with Agent or AI in it, such as --as 'Claude Agent'"
        )
    try:
        import mcp  # noqa: F401
    except ImportError:
        raise EnvError(
            "loom mcp needs the MCP SDK, which loom installs only when asked: pip install 'loomtex[mcp]', "
            "or uv tool install 'loomtex[mcp]'"
        ) from None
    from loom.mcp.server import serve

    serve(open_quilt(quilt_path).root, as_name)
