"""TeX tier: bundles and the demo master compile with the real toolchain."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


@pytest.mark.tex
def test_bundle_compiles(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path).exit_code == 0
    d = tmp_path / "demo"
    for key in ("dm-0003", "dm-0003/proof", "dm-0005"):
        r = run("compile", key, cwd=d)
        assert r.exit_code == 0, r.output


@pytest.mark.tex
def test_demo_master_compiles_and_numbers(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path).exit_code == 0
    d = tmp_path / "demo"
    r = run("compile", cwd=d)
    assert r.exit_code == 0, r.output
    aux = (d / "build" / "main" / "main.aux").read_text()
    assert "\\newlabel{dm-0003}{{2.1}" in aux


@pytest.mark.tex
def test_bundle_failed_diagnostic(tmp_path: Path) -> None:
    assert run("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path).exit_code == 0
    d = tmp_path / "demo"
    (d / "nodes" / "dm-0003.tex").write_text(
        (d / "nodes" / "dm-0003.tex").read_text().replace("\\end{theorem}", "$unbalanced\n\\end{theorem}")
    )
    r = run("compile", "dm-0003", cwd=d)
    assert r.exit_code == 1 and "FAILED bundle dm-0003" in r.output
