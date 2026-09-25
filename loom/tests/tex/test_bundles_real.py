"""TeX tier: bundles and the demo master compile with the real toolchain."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import ok, refused


@pytest.mark.tex
def test_bundle_compiles(tmp_path: Path) -> None:
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    d = tmp_path / "demo"
    for key in ("dm-0003", "dm-0003/proof", "dm-0005"):
        ok("compile", key, cwd=d)


@pytest.mark.tex
def test_demo_master_compiles_and_numbers(tmp_path: Path) -> None:
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    d = tmp_path / "demo"
    ok("compile", cwd=d)
    aux = (d / "build" / "main" / "main.aux").read_text()
    assert "\\newlabel{dm-0003}{{2.1}" in aux


@pytest.mark.tex
def test_bundle_failed_diagnostic(tmp_path: Path) -> None:
    ok("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    d = tmp_path / "demo"
    (d / "nodes" / "dm-0003.tex").write_text(
        (d / "nodes" / "dm-0003.tex").read_text().replace("\\end{theorem}", "$unbalanced\n\\end{theorem}")
    )
    refused("compile", "dm-0003", cwd=d, code=1, match="FAILED bundle dm-0003")
