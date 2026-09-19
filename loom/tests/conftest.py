"""Shared fixtures: the fake TeX shim on PATH, an isolated environment for every test, and the guard that nothing under ~/notes is ever touched.

Tests marked `tex` get the real TeX distribution instead of the shim (and are skipped when none is installed); either way HOME and every TEXMF tree point at empty temporary directories so a test can only read what it created.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SHIM = REPO / "tests" / "fake_latex" / "fake_tex.py"
TOOLS = [
    "latexmk",
    "pdflatex",
    "latex",
    "lualatex",
    "xelatex",
    "dvisvgm",
    "bibtex",
    "biber",
    "pdftotext",
    "pdfinfo",
    "kpsewhich",
    "pdftocairo",
]


def _real_bin(tool: str) -> Path | None:
    found = shutil.which(tool)
    return Path(found).parent if found else None


REAL_TEX_BIN = _real_bin("latexmk")
REAL_POPPLER_BIN = _real_bin("pdftotext")
NOTES = Path.home() / "notes"


@pytest.fixture(scope="session")
def fake_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A directory holding the shim under every tool name, with the shebang pinned to this interpreter."""
    d = tmp_path_factory.mktemp("fakebin")
    body = SHIM.read_text(encoding="utf-8").split("\n", 1)[1]
    for tool in TOOLS:
        target = d / tool
        target.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
        target.chmod(0o755)
    return d


@pytest.fixture(autouse=True)
def isolated_env(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_bin: Path
) -> Path:
    """Isolate PATH, HOME, XDG_CONFIG_HOME, and every TeX tree; return the temporary HOME."""
    assert not str(tmp_path.resolve()).startswith(str(NOTES)), "tests must never run under ~/notes"
    home = tmp_path / "home"
    (home / ".config").mkdir(parents=True)
    texmf = tmp_path / "texmf-empty"
    texmf.mkdir()
    if request.node.get_closest_marker("tex"):
        if REAL_TEX_BIN is None:
            pytest.skip("TeX tier: no latexmk on PATH")
        parts = [str(REAL_TEX_BIN)]
        if REAL_POPPLER_BIN is not None:
            parts.append(str(REAL_POPPLER_BIN))
        parts += ["/usr/bin", "/bin"]
    else:
        parts = [str(fake_bin), "/usr/bin", "/bin"]
    monkeypatch.setenv("PATH", ":".join(parts))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    for var in ("TEXMFHOME", "TEXMFLOCAL", "TEXMFVAR", "TEXMFCONFIG"):
        monkeypatch.setenv(var, str(texmf))
    for var in ("TEXINPUTS", "BIBINPUTS", "BSTINPUTS", "LOOM_QUILT", "LOOM_RUN", "LOOM_ARRAS_BUNDLE", "FAKE_TEX_FAIL"):
        monkeypatch.delenv(var, raising=False)
    # an agent running the suite must not make loom refuse the author's verbs in every test that uses them
    from loom.cli._common import AGENT_MARKERS

    for var in AGENT_MARKERS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("FAKE_TEX_LOG", str(tmp_path / "fake-tex.log"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(home / ".gitconfig-none"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return home


@pytest.fixture
def home(isolated_env: Path) -> Path:
    return isolated_env
