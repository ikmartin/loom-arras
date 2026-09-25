"""Quilt discovery, config validation and who the author is (book 4.1, 4.2, 4.3)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from loom.scan.quilt import (
    NO_AUTHOR_MESSAGE,
    NoAuthorError,
    NoQuiltError,
    QuiltConfig,
    find_quilt,
    load_quilt,
    no_author_in_quilt,
    resolve_author,
)


def _make(root: Path, body: str = '[quilt]\nmain = "drafting/main.tex"\n') -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.toml").write_text(body, encoding="utf-8")
    return root


def test_quilt_discovery_walks_up(tmp_path: Path) -> None:
    root = _make(tmp_path / "q")
    deep = root / "nodes" / "deeper"
    deep.mkdir(parents=True)
    assert find_quilt(deep).root == root.resolve()


def test_quilt_discovery_fails_outside(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text("[notaquilt]\nx = 1\n", encoding="utf-8")
    with pytest.raises(NoQuiltError):
        find_quilt(tmp_path)


def test_quilt_discovery_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _make(tmp_path / "q")
    monkeypatch.setenv("LOOM_QUILT", str(root))
    monkeypatch.chdir(tmp_path)
    assert find_quilt().root == root.resolve()


def test_quilt_config_unknown_key_warns(tmp_path: Path) -> None:
    root = _make(tmp_path / "q", '[quilt]\nmain = "drafting/main.tex"\nbogus = 1\n[extra]\ny = 2\n')
    q = load_quilt(root)
    assert any("quilt.bogus" in w for w in q.config.warnings)
    assert any("[extra]" in w for w in q.config.warnings)
    assert q.config.main == "drafting/main.tex"
    assert q.config.prefix == "q"


def test_a_table_that_is_not_a_table_warns() -> None:
    cfg = QuiltConfig.from_dict({"quilt": {"name": "Q"}, "refs": "yes"})
    assert cfg.name == "Q"
    assert any("[refs] is not a table" in w for w in cfg.warnings)


def test_the_author_is_the_flag_then_the_quilt_then_the_user_config_then_git(home: Path, tmp_path: Path) -> None:
    """`resolve_author`'s order (book 4.3). A quilt that states an `[author]` table answers for itself, so a command records that name rather than the git identity of whatever machine or agent shell it ran in; an empty name there means ask, and a quilt with no table falls through to the user config."""
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(NoAuthorError) as exc:
        resolve_author(None, cwd=repo)
    assert str(exc.value) == NO_AUTHOR_MESSAGE
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Git Person"], check=True)
    assert resolve_author(None, cwd=repo) == ("Git Person", "git config user.name")
    user = home / ".config" / "loom" / "config.toml"
    user.parent.mkdir(parents=True)
    user.write_text('[author]\nname = "Config Person"\n', encoding="utf-8")
    assert resolve_author(None, cwd=repo) == ("Config Person", str(user))
    assert resolve_author("Flag Person", cwd=repo) == ("Flag Person", "--author")

    cfg = repo / "config.toml"
    cfg.write_text('[quilt]\nprefix = "ab"\n', encoding="utf-8")
    assert resolve_author(None, repo) == ("Config Person", str(user))  # no [author] table: the user config answers
    cfg.write_text('[quilt]\nprefix = "ab"\n\n[author]\nname = "Markas Hecht"\n', encoding="utf-8")
    assert resolve_author(None, repo) == ("Markas Hecht", str(cfg))
    assert resolve_author("Someone Else", repo) == ("Someone Else", "--author")  # the flag still wins

    cfg.write_text('[quilt]\nprefix = "ab"\n\n[author]\nname = ""\n', encoding="utf-8")
    with pytest.raises(NoAuthorError) as exc:
        resolve_author(None, repo)
    assert str(exc.value) == no_author_in_quilt(repo)
