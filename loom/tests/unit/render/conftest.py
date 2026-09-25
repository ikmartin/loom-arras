"""The running `loom serve` the serve and write-API tests talk to."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from loom.render import serve as serve_mod
from loom.render.serve import ServeSession
from loom.scan.quilt import load_quilt
from tests.unit._quilts import demo
from tests.unit.render._serve import QuickServer, fake_bundle


@pytest.fixture
def serve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[Path], ServeSession]]:
    """Start `loom serve` over any quilt: the stand-in bundle, a free port, no compiling masters; every server started is stopped at teardown."""
    monkeypatch.setattr(serve_mod, "ThreadingHTTPServer", QuickServer)
    started: list[ServeSession] = []
    bundle = fake_bundle(tmp_path)

    def start(q: Path) -> ServeSession:
        s = ServeSession(load_quilt(q), bundle, port=0, compile_masters=False, interval=0.2)
        started.append(s)
        s.start()
        return s

    yield start
    for s in started:
        s.stop()


@pytest.fixture
def session(tmp_path: Path, serve: Callable[[Path], ServeSession]) -> tuple[ServeSession, Path]:
    """`loom serve` over a fresh demo; the server and the quilt."""
    d = demo(tmp_path)
    return serve(d), d
