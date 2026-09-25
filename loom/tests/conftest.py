"""Shared fixtures: the fake TeX shim on PATH, an isolated environment for every test, and the guard that nothing under ~/notes is ever touched.

Tests marked `tex` get the real TeX distribution instead of the shim (and are skipped when none is installed); either way HOME and every TEXMF tree point at empty temporary directories so a test can only read what it created.
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
from pathlib import Path
from typing import Any

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


#: What a tier reads to decide whether to run: the paper tier's sources, and permission to use the network.
TIER_GATES = ("LOOM_PAPER_FIXTURES", "LOOM_NETWORK")


def leaking(environ: dict[str, str] | os._Environ[str]) -> list[str]:
    """The LOOM_* variables a shell carries into the suite -- a session, a quilt, a fixed clock -- which isolation clears; the tier gates are the harness's, not loom's."""
    return [v for v in environ if v.startswith("LOOM_") and v not in TIER_GATES]


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


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Keep the tests of one module that share its `once` fixture on one xdist worker under `--dist loadgroup`, so the module's expensive quilt is built once rather than once per worker."""
    for item in items:
        if "once" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.xdist_group(f"once:{item.nodeid.split('::')[0]}"))


def _loopback_only(connect: Any) -> Any:
    """`socket.connect` refusing every address but this machine's, so a test not marked `network` that reaches the internet fails rather than passing slowly; in-process only, not in a subprocess."""

    def guarded(sock: socket.socket, address: Any) -> Any:
        host = address[0] if isinstance(address, tuple) else None
        if host is not None and host not in ("127.0.0.1", "::1", "localhost"):
            raise OSError(f"test tried to reach {address}; mark it network")
        return connect(sock, address)

    return guarded


@pytest.fixture(scope="session", autouse=True)
def templates(tmp_path_factory: pytest.TempPathFactory) -> None:
    """The worker's `helpers.templated` store; only a directory factory here, since anything built now would escape `isolated_env`."""
    from tests import helpers

    helpers.TEMPLATES = helpers.Once(tmp_path_factory)


@pytest.fixture(autouse=True)
def isolated_env(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_bin: Path
) -> Path:
    """Isolate PATH, HOME, XDG_CONFIG_HOME, every TeX tree and every LOOM_* variable but the tier gates; return the temporary HOME. `tex` puts the real TeX first on PATH, `poppler` the real pdftotext, and each skips when it is absent."""
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
    elif request.node.get_closest_marker("poppler"):
        # page text and word boxes from the real poppler; everything TeX is still the shim
        if REAL_POPPLER_BIN is None:
            pytest.skip("poppler: no pdftotext on PATH")
        parts = [str(REAL_POPPLER_BIN), str(fake_bin), "/usr/bin", "/bin"]
    else:
        parts = [str(fake_bin), "/usr/bin", "/bin"]
    monkeypatch.setenv("PATH", ":".join(parts))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    for var in ("TEXMFHOME", "TEXMFLOCAL", "TEXMFVAR", "TEXMFCONFIG"):
        monkeypatch.setenv(var, str(texmf))
    for var in ("TEXINPUTS", "BIBINPUTS", "BSTINPUTS", "FAKE_TEX_FAIL"):
        monkeypatch.delenv(var, raising=False)
    for var in leaking(os.environ):
        monkeypatch.delenv(var)
    # an agent running the suite must not make loom refuse the author's verbs in every test that uses them
    from loom.cli._common import AGENT_MARKERS

    for var in AGENT_MARKERS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("FAKE_TEX_LOG", str(tmp_path / "fake-tex.log"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(home / ".gitconfig-none"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    if not request.node.get_closest_marker("network"):
        monkeypatch.setattr(socket.socket, "connect", _loopback_only(socket.socket.connect))
    # a fresh shim's first run waits on macOS for the system's check of a new executable, which a parallel suite can make longer than doctor's timeout; the hang test sets its own
    monkeypatch.setattr("loom.doctor.PROBE_TIMEOUT", 120.0)
    # what kpsewhich answered belongs to the PATH it was asked on, which differs by tier
    from loom.scan.expand import _probe

    _probe.cache_clear()
    return home


@pytest.fixture
def home(isolated_env: Path) -> Path:
    return isolated_env
