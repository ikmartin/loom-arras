"""Nothing loom or arras ships may be ignored by git or left untracked: CI checks out only what is committed, so such a file passes every local run and is missing everywhere else."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[3]
SHIPPED = ("loom/src", "loom/tests/quilts", "arras/src")


def _git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args, "--", *SHIPPED], cwd=WORKSPACE, capture_output=True, text=True, check=True)
    return [
        line for line in out.stdout.splitlines() if line and "__pycache__" not in line and not line.endswith(".pyc")
    ]


pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not (WORKSPACE / ".git").exists(), reason="not a git checkout"
)


def test_nothing_shipped_is_ignored() -> None:
    """A quilt's own `.gitignore` keeps its fetched papers out of the quilt's repository, as it would for an author; any other rule hiding a shipped file is a fault."""
    ignored = _git("ls-files", "--others", "--ignored", "--exclude-standard")
    rules = subprocess.run(
        ["git", "check-ignore", "-v", "--no-index", "--stdin"],
        cwd=WORKSPACE,
        input="\n".join(ignored),
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    hidden = [
        r.split("\t", 1)[1]
        for r in rules
        if not (WORKSPACE / r.split(":", 1)[0]).parent.joinpath("config.toml").is_file()
    ]
    assert hidden == [], "a workspace .gitignore line hides these"


def test_nothing_shipped_is_untracked() -> None:
    assert _git("ls-files", "--others", "--exclude-standard") == [], "git add these before committing"
