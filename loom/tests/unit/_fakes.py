"""Stand-ins: `loom serve`'s request handler, so one of its methods can be called without a server, and an agent a quilt is configured to launch."""

from __future__ import annotations

import io
import json
import sys
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


#: A stand-in agent: reads what waits with `session next`, runs one loom command, and answers `echo (<mode>): <what it read>`.
FAKE_AGENT = """
import json, subprocess, sys
session, mode = sys.argv[1], sys.argv[2]
loom = [sys.executable, "-m", "loom"]
out = subprocess.run(loom + ["session", "next", "--wait", "0", "--json", "--session", session, "--as", "Fake Agent"],
                     capture_output=True, text=True, check=True).stdout
said = " / ".join(e.get("body", "") for e in json.loads(out)["events"])
subprocess.run(loom + ["source", "dm-0003"], capture_output=True, check=False)
subprocess.run(loom + ["session", "say", f"echo ({mode}): {said}", "--session", session, "--as", "Fake Agent"], check=True)
"""


def sleeper(ready: Path, *, ignore_term: bool = False) -> list[str]:
    """A turn that writes its pid to `ready` and sleeps a minute; with `ignore_term`, one that ignores SIGTERM, installed before `ready` is written so a test never signals it early."""
    trap = "signal.signal(signal.SIGTERM, signal.SIG_IGN); " if ignore_term else ""
    code = f"import os, signal, time; {trap}open({str(ready)!r}, 'w').write(str(os.getpid())); time.sleep(60)"
    return [sys.executable, "-c", code]


def configure(q: Path, *, start: list[str] | None = None, resume: list[str] | None = None, launch: bool = True) -> None:
    """Configure `Fake Agent` in the quilt's `ai/ai-config.toml` and turn launching on or off; the default command is FAKE_AGENT, started and resumed."""
    fake = q.parent / "fake_agent.py"
    fake.write_text(FAKE_AGENT, encoding="utf-8")
    start = start if start is not None else [sys.executable, str(fake), "{session}", "start"]
    resume = resume if resume is not None else [sys.executable, str(fake), "{session}", "resume"]
    lines = ['name = "Fake Agent"', f"start = {json.dumps(start)}"]
    if resume:
        lines.append(f"resume = {json.dumps(resume)}")
    (q / "ai" / "ai-config.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    from loom.cli.quilt import _set_launch

    _set_launch(q, launch)
