"""TeX tier: loom's build of the synthetic quilt equals the vendored conformance fixture (docs/specs/fixture.md §3), manifest structurally and fragments textually modulo timestamps and SVG bodies, which depend on the TeX Live version."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixture"
SVG = re.compile(r"<svg\b.*?</svg>", re.S)


def _run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def _norm_fragment(text: str) -> str:
    return SVG.sub("<svg/>", text)


def _norm_manifest(m: dict) -> dict:  # type: ignore[type-arg]
    m = json.loads(json.dumps(m))
    m.pop("generated", None)
    for master in m.get("masters", []):
        master.pop("compiled", None)
    m["publisher"].pop("version", None)
    return m


@pytest.mark.tex
def test_fixture_matches_vendored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not (FIXTURE / "manifest.json").exists():
        pytest.skip("no vendored fixture")
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-16T00:00:00Z")
    q = tmp_path / "synthetic"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", q)
    r = _run("compile", "drafting/main.tex", cwd=q)
    assert r.exit_code == 0, r.output
    assert _run("compile", "drafting/talk.tex", cwd=q).exit_code == 0
    _run("build", cwd=q)
    ours = json.loads((q / "build" / "manifest.json").read_text())
    theirs = json.loads((FIXTURE / "manifest.json").read_text())
    assert _norm_manifest(ours) == _norm_manifest(theirs)
    for f in sorted((FIXTURE / "fragments").rglob("*.html")):
        rel = f.relative_to(FIXTURE)
        mine = q / "build" / rel
        assert mine.exists(), rel
        assert _norm_fragment(mine.read_text()) == _norm_fragment(f.read_text()), rel
