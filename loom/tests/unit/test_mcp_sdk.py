"""An environment older than the MCP SDK dependency lacks it, so loom says so before an agent finds out: the reinstall command follows how loom was installed, and every command that writes what starts the server warns."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from loom.cli.ai import NO_SERVER
from loom.mcp.sdk import has_sdk, reinstall_hint
from tests.helpers import flat, json_of, ok, refused
from tests.unit._quilts import demo

AGENT = "Claude Code Agent"
HINT = "uv tool install --force loomtex"
EDITABLE = {"url": "file:///x/loom", "dir_info": {"editable": True}}
GIT = {"url": "https://github.com/ikmartin/loom", "vcs_info": {"vcs": "git", "commit_id": "abc"}}


class Installed:
    """A stand-in for loom's distribution, whose only record is its `direct_url.json`."""

    def __init__(self, record: dict[str, Any] | None) -> None:
        self.record = record

    def read_text(self, name: str) -> str | None:
        assert name == "direct_url.json"
        return json.dumps(self.record) if self.record else None


@pytest.mark.parametrize(
    ("marker", "record", "want"),
    [
        ("uv-receipt.toml", EDITABLE, "uv tool install --force --editable /x/loom"),
        ("uv-receipt.toml", None, "uv tool install --force loomtex"),
        ("pipx_metadata.json", GIT, "pipx install --force git+https://github.com/ikmartin/loom"),
        ("pipx_metadata.json", EDITABLE, "pipx install --force --editable /x/loom"),
        (None, None, "/v/bin/python -m pip install loomtex"),
        (None, EDITABLE, "/v/bin/python -m pip install --editable /x/loom"),
        (None, {"url": "file:///a%20b/loom", "dir_info": {}}, "/v/bin/python -m pip install '/a b/loom'"),
        (
            None,
            {"url": "file:///w.whl", "archive_info": {}},
            "/v/bin/python -m pip install file:///w.whl",
        ),
    ],
)
def test_the_reinstall_command_follows_how_loom_was_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, marker: str | None, record: dict[str, Any] | None, want: str
) -> None:
    if marker:
        (tmp_path / marker).touch()
    real = importlib.util.find_spec
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(sys, "executable", "/v/bin/python")
    monkeypatch.setattr(importlib.metadata, "distribution", lambda name: Installed(record))
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a: object() if name == "pip" else real(name, *a))
    assert reinstall_hint() == want


def test_an_environment_without_pip_is_told_uv_pip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real = importlib.util.find_spec
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    monkeypatch.setattr(sys, "executable", "/v/bin/python")
    monkeypatch.setattr(importlib.metadata, "distribution", lambda name: Installed(None))
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a: None if name == "pip" else real(name, *a))
    assert reinstall_hint() == "uv pip install --python /v/bin/python loomtex"


def test_a_loom_with_no_installed_distribution_falls_back_to_the_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def missing(name: str) -> None:
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    (tmp_path / "uv-receipt.toml").touch()
    monkeypatch.setattr(importlib.metadata, "distribution", missing)
    assert reinstall_hint() == "uv tool install --force loomtex"


def test_has_sdk_reads_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    assert has_sdk()
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a: None if name == "mcp" else real(name, *a))
    assert not has_sdk()


@pytest.fixture
def no_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("loom.mcp.sdk.has_sdk", lambda: False)
    monkeypatch.setattr("loom.mcp.sdk.reinstall_hint", lambda: HINT)


def warned(data: dict[str, Any]) -> bool:
    """Whether a command's JSON report carries the warning, with the command that clears it, as not ok."""
    fixes = [f for g in data["groups"] for i in g["items"] for f in i.get("fixes", [])]
    return data["ok"] is False and HINT in fixes


@pytest.mark.usefixtures("no_sdk")
def test_the_server_refuses_with_the_command(tmp_path: Path) -> None:
    refused("mcp", "--as", AGENT, cwd=demo(tmp_path), code=2, match=HINT)


@pytest.mark.usefixtures("no_sdk")
@pytest.mark.parametrize(
    "command", [("ai", "init"), ("ai", "init", "--dry-run"), ("upgrade",), ("upgrade", "--dry-run")]
)
def test_refreshing_a_quilt_warns_in_the_verdict_and_names_the_command(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    data = json_of(*command, "--json", cwd=demo(tmp_path))
    assert warned(data) and NO_SERVER in data["verdict"]


@pytest.mark.usefixtures("no_sdk")
def test_the_first_ai_init_puts_the_reinstall_before_starting_the_agent(tmp_path: Path) -> None:
    q = tmp_path / "q"
    ok("init", str(q), "--prefix", "zz", "--ai", "none", "--yes")
    data = json_of("ai", "init", "--json", cwd=q)
    assert warned(data) and "reinstall loom as below, then start your agent here" in data["verdict"]


@pytest.mark.usefixtures("no_sdk")
def test_printing_an_entry_warns_and_the_entry_still_prints(tmp_path: Path) -> None:
    q = demo(tmp_path)
    data = json_of("ai", "init", "--client", "zed", "--json", cwd=q)
    assert warned(data) and "context_servers" in data["entry"]
    assert HINT in ok("ai", "init", "--client", "zed", cwd=q).stdout


@pytest.mark.usefixtures("no_sdk")
@pytest.mark.parametrize("choice", ["claude", "codex", "other"])
def test_loom_init_with_an_ai_says_to_reinstall_first(tmp_path: Path, choice: str) -> None:
    r = ok("init", str(tmp_path / "q"), "--prefix", "zz", "--ai", choice, "--yes")
    assert f"First reinstall loom, whose environment lacks the MCP SDK the loom server needs: {HINT}" in flat(r.stdout)


@pytest.mark.usefixtures("no_sdk")
def test_a_quilt_that_needs_no_server_is_not_warned(tmp_path: Path) -> None:
    r = ok("init", str(tmp_path / "plain"), "--prefix", "zz", "--ai", "none", "--yes")
    assert "MCP SDK" not in r.stdout
    q = demo(tmp_path)
    for command in (("ai", "init", "--shell"), ("upgrade",)):
        data = json_of(*command, "--json", cwd=q)
        assert data["ok"] is True and NO_SERVER not in data["verdict"] and not warned(data)


def test_with_the_sdk_nothing_is_said(tmp_path: Path) -> None:
    q = demo(tmp_path)
    for command in (("ai", "init"), ("upgrade",)):
        data = json_of(*command, "--json", cwd=q)
        assert data["ok"] is True and NO_SERVER not in data["verdict"]
    assert "MCP SDK" not in ok("init", str(tmp_path / "plain"), "--prefix", "zz", "--ai", "claude", "--yes").stdout
