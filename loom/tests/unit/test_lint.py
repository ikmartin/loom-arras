"""Diagnostic codes on the demo (book 5.14): lint's exit code, one test per warning, and the codes `check` and `atomize` report."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.helpers import edit, exits, ok, refused, the
from tests.unit._quilts import demo


def test_lint_exit_codes(tmp_path: Path) -> None:
    q = demo(tmp_path)
    (q / "nodes" / "bad.tex").write_text("\\begin{lemma}\\label{dm-0001}\ndup\n\\end{lemma}\n")
    r = exits(1, "lint", cwd=q)
    assert "duplicate-id" in r.output and r.output.strip().endswith("infos")


def _stray_documentclass(q: Path) -> None:
    (q / "sections").mkdir()
    (q / "sections" / "stray.tex").write_text("\\documentclass{article}\n\\begin{document}\nx\n\\end{document}\n")


def _unreadable_log_line(q: Path) -> None:
    with (q / "annotations" / "log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{not json\n")


def _missing_main(q: Path) -> None:
    edit(q / "config.toml", 'main = "drafting/main.tex"', 'main = "drafting/missing.tex"')


def _unknown_table(q: Path) -> None:
    with (q / "config.toml").open("a", encoding="utf-8") as fh:
        fh.write("\n[colour]\nscheme = 1\n")


def _mac_roman_node(q: Path) -> None:
    (q / "nodes" / "old.tex").write_bytes(b"\\begin{remark}\\label{dm-0099}\nSee pages 989\xd01004.\n\\end{remark}\n")


#: code -> (what provokes it on the demo, what its line must name)
WARNINGS: dict[str, tuple[Callable[[Path], None], str]] = {
    "loom:documentclass-outside-drafts": (_stray_documentclass, "sections/stray.tex"),
    "loom:foreign-annotations": (_unreadable_log_line, "annotations/log.jsonl"),
    "loom:main-not-found": (_missing_main, "drafting/missing.tex"),
    "loom:unknown-config-key": (_unknown_table, "[colour]"),
    "loom:non-utf8-source": (_mac_roman_node, "nodes/old.tex"),
}


@pytest.mark.parametrize("code", sorted(WARNINGS))
def test_a_warning_is_reported_on_one_line_naming_where(tmp_path: Path, code: str) -> None:
    q = demo(tmp_path)
    provoke, where = WARNINGS[code]
    provoke(q)
    lint = ok("lint", cwd=q).output  # warnings and infos only: lint exits 0
    line = the(lint.splitlines(), lambda ln: code in ln.split(), f"{code} line")
    assert where in line, line


def test_check_reports_a_bundle_that_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    q = demo(tmp_path)
    monkeypatch.setenv("FAKE_TEX_FAIL_MATCH", "bundles/")  # the master compiles; every bundle fails
    r = exits(1, "check", "--bundles", "all", cwd=q)
    assert "loom:bundle-failed" in r.output and "ok      drafting/main.tex" in r.output


def test_atomize_refuses_a_target_file_that_exists(tmp_path: Path) -> None:
    q = demo(tmp_path)
    (q / "nodes" / "dm-0004.tex").write_text("% a file already sits where the inline node dm-0004 would move\n")
    refused("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q, code=1, match="loom:atomize-target-exists")
