"""The harness itself: a crash is never a pass, a refusal is checked by its message, and the tier gates survive isolation (plan 0.14.1 phase 2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.conftest import leaking
from tests.helpers import edit, json_of, ok, refused, run


def test_a_crash_is_a_traceback_not_an_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """click reports an uncaught exception as exit 1, which is also loom's refusal for content; a test must never read one as the other."""
    ok("init", tmp_path / "q", "--demo")

    def boom(*_a: object, **_k: object) -> None:
        raise RuntimeError("the command crashed")

    monkeypatch.setattr("loom.cli.review.open_scan", boom)
    with pytest.raises(RuntimeError, match="the command crashed"):
        run("status", cwd=tmp_path / "q")


def test_ok_and_refused_say_what_happened(tmp_path: Path) -> None:
    with pytest.raises(AssertionError) as failed:
        ok("status", cwd=tmp_path)  # no quilt here
    assert "$ loom status" in str(failed.value) and "exit 2" in str(failed.value)
    refused("status", cwd=tmp_path, code=2, match="config.toml")
    with pytest.raises(AssertionError, match="expected 'no such words'"):
        refused("status", cwd=tmp_path, code=2, match="no such words")


def test_json_of_reads_stdout_alone(tmp_path: Path) -> None:
    ok("init", tmp_path / "q", "--demo")
    assert "dm-0001" in json_of("status", "--json", cwd=tmp_path / "q")["keys"]


def test_an_edit_that_finds_nothing_fails(tmp_path: Path) -> None:
    f = tmp_path / "f.tex"
    f.write_text("a widget\n", encoding="utf-8")
    edit(f, "widget", "gadget")
    assert f.read_text(encoding="utf-8") == "a gadget\n"
    with pytest.raises(AssertionError, match="is not in"):
        edit(f, "widget", "gadget")


def test_isolation_clears_loom_variables_but_not_the_tier_gates() -> None:
    """The paper and network tiers read their gate inside the test, after isolation has run; clearing it would skip them for ever."""
    shell = {
        "LOOM_SESSION": "s-1",
        "LOOM_FIXED_TIME": "t",
        "LOOM_PAPER_FIXTURES": "/p",
        "LOOM_NETWORK": "1",
        "HOME": "/h",
    }
    assert sorted(leaking(shell)) == ["LOOM_FIXED_TIME", "LOOM_SESSION"]
