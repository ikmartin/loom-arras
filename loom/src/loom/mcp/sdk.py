"""Whether this loom's environment has the MCP SDK `loom mcp` needs, and the command that restores it; nothing here imports the SDK.

The SDK is a dependency of loom, so it is missing only from an environment older than that dependency: an editable install takes new code but not new dependencies, and nothing else tells its owner to reinstall.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import shlex
import sys
from pathlib import Path


def has_sdk() -> bool:
    """Whether `loom mcp` can start: the SDK is importable in loom's own environment.

    Returns
    -------
    bool
        True when `mcp` can be found; it is not imported.

    See Also
    --------
    reinstall_hint : the command that restores it.
    """
    return importlib.util.find_spec("mcp") is not None


def _source() -> tuple[str, bool]:
    """Where this loom was installed from, and whether it is editable, from the record of how it was installed.

    A directory install keeps its path and a git or archive install its url; `loomtex` alone would swap either for what an index holds. No record means an index install.
    """
    try:
        text = importlib.metadata.distribution("loomtex").read_text("direct_url.json")
    except importlib.metadata.PackageNotFoundError:
        text = None
    said = json.loads(text) if text else {}
    url = said.get("url", "")
    if "dir_info" in said:
        from urllib.parse import urlparse
        from urllib.request import url2pathname

        return url2pathname(urlparse(url).path), bool(said["dir_info"].get("editable"))
    if url:
        vcs = said.get("vcs_info", {}).get("vcs")
        return f"{vcs}+{url}" if vcs else url, False
    return "loomtex", False


def reinstall_hint() -> str:
    """The shell command that reinstalls this loom the way it was installed, which brings the SDK with it.

    Returns
    -------
    str
        A `uv tool` or `pipx` reinstall where one of them manages loom's environment, else an install into that environment by its absolute interpreter, since a bare `pip` can belong to another.
    """
    source, editable = _source()
    prefix = Path(sys.prefix)
    if (prefix / "uv-receipt.toml").is_file():
        tool = "uv tool install --force"
    elif (prefix / "pipx_metadata.json").is_file():
        tool = "pipx install --force"
    elif importlib.util.find_spec("pip") is not None:
        tool = f"{shlex.quote(sys.executable)} -m pip install"
    else:
        tool = f"uv pip install --python {shlex.quote(sys.executable)}"
    return f"{tool} {'--editable ' if editable else ''}{shlex.quote(source)}"
