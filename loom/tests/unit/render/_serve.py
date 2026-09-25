"""What the `loom serve` tests share: a stand-in bundle, a server that stops at once, and GET and POST that answer with the status rather than raising."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any


class QuickServer(ThreadingHTTPServer):
    """`serve_forever` checks for shutdown every 0.5 s by default and `ServeSession.stop` waits that out; a test's server checks ten times as often."""

    def serve_forever(self, poll_interval: float = 0.05) -> None:
        super().serve_forever(poll_interval)


def fake_bundle(tmp_path: Path) -> Path:
    """An arras bundle of two files: the app shell and one script."""
    b = tmp_path / "bundle"
    (b / "_app").mkdir(parents=True)
    (b / "index.html").write_text("<!doctype html><title>arras</title><div id=app></div>")
    (b / "_app" / "x.js").write_text("console.log(1)")
    return b


def get(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    """GET `url`; an HTTP error is returned as its status with an empty body."""
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b""


def post(url: str, body: dict[str, Any], token: str | None = None) -> tuple[int, Any]:
    """POST `body` as JSON with the token the running server minted, read from `/_api` as the viewer reads it; `token=""` sends none."""
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is None:
        base = url.split("/_api/")[0] + "/_api"
        token = json.loads(urllib.request.urlopen(base, timeout=5).read()).get("token", "")
    if token:
        headers["X-Loom-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def log(q: Path) -> list[dict[str, Any]]:
    """Every event in the quilt's annotation log, in order."""
    return [
        json.loads(x) for x in (q / "annotations" / "log.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()
    ]
