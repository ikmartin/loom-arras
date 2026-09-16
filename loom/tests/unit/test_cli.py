"""`loom --version` and `loom doctor` (book 12.2)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.version import INTERFACE_VERSION, __version__


def test_cli_version() -> None:
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"loom {__version__}"


def test_doctor_ok_on_shim() -> None:
    result = CliRunner().invoke(main, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "latexmk" in result.output
    assert "ok" in result.output.splitlines()[-1]


def test_doctor_json_shape() -> None:
    result = CliRunner().invoke(main, ["doctor", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["interface_version"] == INTERFACE_VERSION
    assert data["loom"] == __version__
    names = {t["name"] for t in data["tools"]}
    assert {"latexmk", "pdflatex", "dvisvgm", "pdftotext", "git"} <= names
    assert data["arras"]["path"] is None or data["arras"]["source"]


def test_doctor_missing_tool_exit_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_bin: Path) -> None:
    partial = tmp_path / "partial-bin"
    partial.mkdir()
    for tool in os.listdir(fake_bin):
        if tool != "latexmk":
            (partial / tool).symlink_to(fake_bin / tool)
    monkeypatch.setenv("PATH", f"{partial}:/usr/bin:/bin")
    result = CliRunner().invoke(main, ["doctor"])
    assert result.exit_code == 2, result.output
    assert "latexmk" in result.output and "MISSING" in result.output
