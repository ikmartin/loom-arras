"""Author-name resolution order and the exact refusal message (book 4.3)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from loom.scan.quilt import NO_AUTHOR_MESSAGE, NoAuthorError, resolve_author


def test_userconfig_author_resolution_order(home: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(NoAuthorError) as exc:
        resolve_author(None, cwd=repo)
    assert str(exc.value) == NO_AUTHOR_MESSAGE
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Git Person"], check=True)
    assert resolve_author(None, cwd=repo) == ("Git Person", "git config user.name")
    cfg = home / ".config" / "loom" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text('[author]\nname = "Config Person"\n', encoding="utf-8")
    assert resolve_author(None, cwd=repo) == ("Config Person", str(cfg))
    assert resolve_author("Flag Person", cwd=repo) == ("Flag Person", "--author")
