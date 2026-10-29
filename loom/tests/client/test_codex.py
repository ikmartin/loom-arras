"""Client tier, Codex: the server `.codex/config.toml` names starts, and a write over it is recorded under the name the file gives.

Codex reads a project's config only once the project is trusted, which a quilt made in a temporary directory never is, so the turn trusts it on the command line (`-c projects."<root>".trust_level`) rather than in the person's own config. Unverified: Codex was not installed where this was written. Skips unless LOOM_CLIENT_TESTS=1 and `codex` is on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tests.client._tier import gate, person_env
from tests.helpers import ok

pytestmark = pytest.mark.client

CODEX = shutil.which("codex")
PROMPT = (
    "This turn checks this folder's loom MCP server and nothing else. "
    "Call the loom server's tool loom_annotate with target dm-0002, message `client check` and kind question, then stop."
)


def test_codex_writes_over_the_server_its_config_names(tmp_path: Path) -> None:
    gate(CODEX, "codex")
    assert CODEX is not None
    ok("init", str(tmp_path / "q"), "--demo", "--ai", "codex", "--yes", cwd=tmp_path)
    q = tmp_path / "q"
    trust = f'projects."{q.resolve()}".trust_level="trusted"'
    cmd = [CODEX, "exec", "--skip-git-repo-check", "-c", trust, PROMPT]
    proc = subprocess.run(
        cmd, cwd=q, env=person_env(), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600
    )
    said = f"\n$ {' '.join(cmd)}\nexit {proc.returncode}\n--- stdout\n{proc.stdout}\n--- stderr\n{proc.stderr}"
    mine = [ln for ln in (q / "annotations" / "log.jsonl").read_text().splitlines() if "client check" in ln]
    assert mine and '"author": "Codex Agent"' in mine[-1], "no annotation over MCP as Codex Agent" + said
