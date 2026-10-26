"""A stand-in for `loom serve`'s request handler, so one of its methods can be called without a server."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any


class FakeHandler:
    """Enough of `LoomHandler` to call one of its methods unbound: the quilt, the request path and JSON body, and the answer given.

    `answer` is `(status, body)`, the body None after `send_error`; `launcher` is what `_agent_stop` stops through.
    """

    def __init__(self, q: Path, path: str = "", body: dict[str, Any] | None = None, launcher: Any = None) -> None:
        self.quilt_root = q
        self.path = path
        self.launcher = launcher
        raw = json.dumps(body or {}).encode()
        self.rfile = io.BytesIO(raw)
        self.headers = {"Content-Length": str(len(raw))}
        self.answer: tuple[int, Any] | None = None

    def _json(self, status: int, body: Any) -> None:
        self.answer = (int(status), body)

    def send_error(self, status: int) -> None:
        self.answer = (int(status), None)
