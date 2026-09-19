"""Quilt discovery and config validation (book 4.1, 4.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.scan.quilt import NoQuiltError, QuiltConfig, find_quilt, load_quilt


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


def test_a_retired_table_is_accepted_and_ignored() -> None:
    """A quilt still carrying `[crawl]` (DR-144) must not start reporting it as unknown; `loom upgrade` removes it."""
    cfg = QuiltConfig.from_dict({"crawl": {"depth": 3, "subjects": ["14N"], "categories": ["math.AG"], "cap": 50}})
    assert cfg.warnings == []


def test_the_quilts_own_config_settles_the_author(tmp_path: Path) -> None:
    """A quilt that states an `[author]` table answers for itself, so a command records that name rather than the git identity of whatever machine or agent shell it ran in; empty means ask, and a quilt with no table falls back as before."""
    from loom.scan.quilt import NoAuthorError, no_author_in_quilt, resolve_author

    root = tmp_path / "q"
    root.mkdir()
    cfg = root / "config.toml"
    cfg.write_text('[quilt]\nprefix = "ab"\n\n[author]\nname = "Markas Hecht"\n', encoding="utf-8")
    assert resolve_author(None, root) == ("Markas Hecht", str(cfg))
    assert resolve_author("Someone Else", root) == ("Someone Else", "--author")  # the flag still wins

    cfg.write_text('[quilt]\nprefix = "ab"\n\n[author]\nname = ""\n', encoding="utf-8")
    with pytest.raises(NoAuthorError) as exc:
        resolve_author(None, root)
    assert str(exc.value) == no_author_in_quilt(root)
