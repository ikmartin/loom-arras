"""Client tier, Gemini CLI: the server `.gemini/settings.json` names starts, and a write over it is recorded under the name the file gives.

Gemini CLI reads a workspace's settings only in a trusted folder when folder trust is on; the tier changes nothing of the person's, so with trust on and the temporary quilt untrusted this test fails, saying so. Unverified: Gemini CLI was not installed where this was written. Skips unless LOOM_CLIENT_TESTS=1 and `gemini` is on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tests.client._tier import gate, person_env
from tests.helpers import ok

pytestmark = pytest.mark.client

GEMINI = shutil.which("gemini")
PROMPT = (
    "This turn checks this folder's loom MCP server and nothing else. "
    "Call the loom server's tool loom_annotate with target dm-0002, message `client check` and kind question, then stop."
)


def test_gemini_writes_over_the_server_its_settings_name(tmp_path: Path) -> None:
    gate(GEMINI, "gemini")
    assert GEMINI is not None
    ok("init", str(tmp_path / "q"), "--demo", "--ai", "other", "--yes", cwd=tmp_path)
    q = tmp_path / "q"
    cmd = [GEMINI, "-p", PROMPT]
    proc = subprocess.run(
        cmd, cwd=q, env=person_env(), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600
    )
    said = f"\n$ {' '.join(cmd)}\nexit {proc.returncode}\n--- stdout\n{proc.stdout}\n--- stderr\n{proc.stderr}"
    said += "\n(a folder Gemini CLI does not trust has its .gemini/settings.json ignored)"
    mine = [ln for ln in (q / "annotations" / "log.jsonl").read_text().splitlines() if "client check" in ln]
    assert mine and '"author": "Gemini CLI Agent"' in mine[-1], "no annotation over MCP as Gemini CLI Agent" + said
