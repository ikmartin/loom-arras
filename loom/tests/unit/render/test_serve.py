"""loom serve: static routes with the SPA fallback, ETag on the manifest, republish on change, no outgoing requests."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.render.serve import ServeSession
from loom.scan.quilt import load_quilt


def demo(tmp_path: Path) -> Path:
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        r = CliRunner().invoke(main, ["init", str(tmp_path / "demo"), "--demo", "--no-git"])
    finally:
        os.chdir(old)
    assert r.exit_code == 0, r.output
    return tmp_path / "demo"


def fake_bundle(tmp_path: Path) -> Path:
    b = tmp_path / "bundle"
    (b / "_app").mkdir(parents=True)
    (b / "index.html").write_text("<!doctype html><title>arras</title><div id=app></div>")
    (b / "_app" / "x.js").write_text("console.log(1)")
    return b


def get(url: str, headers: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b""


@pytest.fixture
def session(tmp_path: Path):  # type: ignore[no-untyped-def]
    d = demo(tmp_path)
    s = ServeSession(load_quilt(d), fake_bundle(tmp_path), port=0, compile_masters=False, interval=0.2)
    s.start()
    yield s, d
    s.stop()


def test_serve_static_routes(session) -> None:  # type: ignore[no-untyped-def]
    s, d = session
    status, headers, body = get(s.url)
    assert status == 200 and b"<title>arras</title>" in body
    status, _, body = get(s.url + "node/dm-0003")
    assert status == 200 and b"<title>arras</title>" in body  # SPA fallback
    status, _, body = get(s.url + "_app/x.js")
    assert status == 200 and body == b"console.log(1)"
    status, headers, body = get(s.url + "build/manifest.json")
    assert status == 200 and headers["Content-Type"].startswith("application/json")
    manifest = json.loads(body)
    assert manifest["corpus"]["name"] == "demo"
    etag = headers["ETag"]
    status, _, _ = get(s.url + "build/manifest.json", {"If-None-Match": etag})
    assert status == 304
    status, _, body = get(s.url + "build/fragments/nodes/dm-0003.html")
    assert status == 200 and b'data-id="dm-0003"' in body
    assert get(s.url + "build/../config.toml")[0] == 404
    assert get(s.url + "missing.css")[0] == 404
    assert get(s.url + "_api")[0] == 404


def test_serve_republishes_on_change(session) -> None:  # type: ignore[no-untyped-def]
    s, d = session
    _, headers, _ = get(s.url + "build/manifest.json")
    before = headers["ETag"]
    node = d / "nodes" / "dm-0002.tex"
    time.sleep(0.3)
    node.write_text(node.read_text().replace("[Orbits]", "[Orbits, revised]"))
    os.utime(node, None)
    deadline = time.time() + 6
    after = before
    while time.time() < deadline:
        _, headers, body = get(s.url + "build/manifest.json")
        after = headers["ETag"]
        if after != before:
            break
        time.sleep(0.2)
    assert after != before, "manifest did not change within the deadline"
    assert json.loads(body)["nodes"]["dm-0002"]["title"] == "Orbits, revised"
    assert s.builds >= 2


def test_serve_no_notification_sent(session, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    s, d = session
    calls: list[str] = []
    import http.client

    original = http.client.HTTPConnection.request

    def spy(self, method, url, *a, **k):  # type: ignore[no-untyped-def]
        if self.host not in ("127.0.0.1", "localhost"):
            calls.append(f"{method} {self.host}{url}")
        return original(self, method, url, *a, **k)

    monkeypatch.setattr(http.client.HTTPConnection, "request", spy)
    s.rebuild([d / "nodes" / "dm-0001.tex"])
    assert calls == []


def test_serve_exit_2_without_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = demo(tmp_path)
    monkeypatch.delenv("LOOM_ARRAS_BUNDLE", raising=False)
    monkeypatch.setattr("loom.render.serve.find_bundle", lambda: None)
    old = os.getcwd()
    try:
        os.chdir(d)
        r = CliRunner().invoke(main, ["serve", "--port", "0"])
    finally:
        os.chdir(old)
    assert r.exit_code == 2 and "bundle" in r.output
