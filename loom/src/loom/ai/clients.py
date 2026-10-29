"""The MCP client files: the file each agent's app reads to start `loom mcp` for a quilt, generated per machine and never committed.

Each holds one server, `loom`, started as `<loom> mcp --as "<App> Agent" --quilt <root>` with both paths absolute: apps differ on the working directory and the environment they give a server, and the file names this machine's loom anyway. The project files are gitignored (`loom.gitignore.MANAGED`), and `loom doctor` fails when git tracks one. A file that holds anything else is the person's: loom leaves it alone and says what to add.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Client:
    """One agent app that can start loom's server.

    Parameters
    ----------
    key : str
        Its name for `loom ai init --client`.
    label : str
        The app's own name; the server serves `<label> Agent`.
    file : str or None
        The quilt-relative file loom writes for it; None for an app configured outside the quilt.
    form : str
        The file's format: `json` (`mcpServers`), `codex` (TOML, `mcp_servers`) or `zed` (JSON, `context_servers`).
    where : str, default ''
        Where an app configured outside the quilt keeps the file, said with its entry.
    extra : tuple of (str, object), default ()
        Fields loom's entry carries beside the command: the transport, and the approval the shell allows grant.
    """

    key: str
    label: str
    file: str | None
    form: str
    where: str = ""
    extra: tuple[tuple[str, Any], ...] = ()

    @property
    def agent(self) -> str:
        return f"{self.label} Agent"


CLIENTS = (
    Client("claude-code", "Claude Code", ".mcp.json", "json", extra=(("type", "stdio"),)),
    Client("codex", "Codex", ".codex/config.toml", "codex", extra=(("default_tools_approval_mode", "approve"),)),
    Client("gemini-cli", "Gemini CLI", ".gemini/settings.json", "json", extra=(("trust", True),)),
    Client("cursor", "Cursor", ".cursor/mcp.json", "json"),
    Client(
        "claude-desktop",
        "Claude Desktop",
        None,
        "json",
        where="~/Library/Application Support/Claude/claude_desktop_config.json on macOS, %APPDATA%\\Claude\\claude_desktop_config.json on Windows",
    ),
    Client("lm-studio", "LM Studio", None, "json", where="~/.lmstudio/mcp.json"),
    Client("zed", "Zed", None, "zed", where="~/.config/zed/settings.json"),
    Client("jetbrains", "JetBrains", None, "json", where="Settings > Tools > AI Assistant > Model Context Protocol"),
)
#: The apps that read a file in the quilt, which `loom ai init` writes.
PROJECT = tuple(c for c in CLIENTS if c.file)
PROJECT_FILES = tuple(c.file for c in PROJECT if c.file)
BY_KEY = {c.key: c for c in CLIENTS}


@dataclass
class ClientReport:
    """What `write_clients` did, by quilt-relative file: `written` (or, writing nothing, would be), `current`, `foreign` (the person's, left alone), `tracked` (loom's entry under git, left alone) and `removed`."""

    written: list[str] = field(default_factory=list)
    current: list[str] = field(default_factory=list)
    foreign: list[str] = field(default_factory=list)
    tracked: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, list[str]]:
        return {
            "written": self.written,
            "current": self.current,
            "foreign": self.foreign,
            "tracked": self.tracked,
            "removed": self.removed,
        }


def command() -> tuple[str, list[str]]:
    """The absolute command that starts this loom: its script beside the running interpreter, else that interpreter with `-m loom`."""
    exe = Path(sys.executable)
    script = exe.parent / ("loom.exe" if sys.platform == "win32" else "loom")
    if script.is_file():
        return str(script), []
    return str(exe), ["-m", "loom"]


def render(client: Client, root: Path) -> str:
    """The whole file loom writes for `client` in the quilt at `root`, which is also the entry to add to a file of the person's."""
    cmd, pre = command()
    entry: dict[str, Any] = {
        "command": cmd,
        "args": [*pre, "mcp", "--as", client.agent, "--quilt", str(root.resolve())],
        **dict(client.extra),
    }
    if client.form == "codex":
        return "[mcp_servers.loom]\n" + "".join(f"{k} = {_toml(v)}\n" for k, v in entry.items())
    return json.dumps({_servers_key(client): {"loom": entry}}, indent=2, ensure_ascii=False) + "\n"


def _toml(value: Any) -> str:
    """`value` as TOML: JSON's string escapes are TOML's, and an array takes a line per item so no line outgrows the path in it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[\n" + "".join(f"  {_toml(v)},\n" for v in value) + "]"
    return json.dumps(value, ensure_ascii=False)


def _servers_key(client: Client) -> str:
    return {"codex": "mcp_servers", "zed": "context_servers"}.get(client.form, "mcpServers")


def _parsed(client: Client, text: str) -> Any:
    try:
        return tomllib.loads(text) if client.form == "codex" else json.loads(text)
    except ValueError:
        return None


def names_loom(client: Client, text: str) -> bool:
    """Whether the file names a server `loom`, loom's own or not: what the tracked guard looks for."""
    data = _parsed(client, text)
    servers = data.get(_servers_key(client)) if isinstance(data, dict) else None
    return isinstance(servers, dict) and "loom" in servers


def is_loom_file(client: Client, text: str) -> bool:
    """Whether the file is loom's to rewrite: it parses, and holds one server, `loom`, started as `mcp --as`, and nothing else."""
    data = _parsed(client, text)
    key = _servers_key(client)
    if (
        not isinstance(data, dict)
        or set(data) != {key}
        or not isinstance(data[key], dict)
        or set(data[key]) != {"loom"}
    ):
        return False
    args = data[key]["loom"].get("args") if isinstance(data[key]["loom"], dict) else None
    return isinstance(args, list) and "mcp" in args and "--as" in args[args.index("mcp") :]


def tracked(root: Path, files: tuple[str, ...]) -> set[str]:
    """Which of `files` git tracks in the quilt at `root`; none when it is not under git or git is not installed."""
    try:
        done = subprocess.run(["git", "ls-files", "-z", "--", *files], cwd=root, capture_output=True, check=False)
    except OSError:
        return set()
    if done.returncode != 0:
        return set()
    return {p for p in done.stdout.decode("utf-8", errors="replace").split("\0") if p}


def write_clients(root: Path, write: bool = True, *, shell: bool = False) -> ClientReport:
    """Write each project client file loom owns, or with `write` false say which it would; with `shell`, remove them instead.

    A file of the person's, or one git tracks with a loom server in it, is never written or removed: the first is reported `foreign`, the second `tracked`, and `loom doctor` fails on it.
    """
    rep = ClientReport()
    under_git = tracked(root, PROJECT_FILES)
    for c in PROJECT:
        assert c.file is not None
        p = root / c.file
        text = p.read_text(encoding="utf-8") if p.is_file() else None
        if text is not None and c.file in under_git and names_loom(c, text):
            rep.tracked.append(c.file)
            continue
        if text is not None and not is_loom_file(c, text):
            rep.foreign.append(c.file)
            continue
        if shell:
            if text is not None:
                rep.removed.append(c.file)
                if write:
                    p.unlink()
            continue
        want = render(c, root)
        if text == want:
            rep.current.append(c.file)
            continue
        rep.written.append(c.file)
        if write:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(want, encoding="utf-8")
    return rep
