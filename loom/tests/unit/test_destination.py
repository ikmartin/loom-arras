"""The one rule every `--to` follows (plan 0.18.4): a working document goes anywhere in the quilt loom reads, anything else stays out of the quilt's sources, and nothing that exists is overwritten unless the command replaces by design."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.cli._common import EnvError, destination
from loom.scan.quilt import load_quilt
from tests.unit._quilts import demo


def test_a_working_document_goes_anywhere_loom_reads_and_nothing_else_among_the_sources(tmp_path: Path) -> None:
    q = load_quilt(demo(tmp_path))
    for there in ("drafting/flat.tex", "paper/main.tex", "flat.tex"):
        assert destination(q, there, document=True) == (q.root / there).resolve()
    for there, said in (
        ("notes/flat.tex", "is inside notes/"),
        ("retired/flat.tex", "is inside retired/"),
        (".loom/flat.tex", "is inside .loom/"),
        ("build/flat.tex", "is inside build/"),
        ("refs/flat.tex", "is inside refs/"),
        ("drafting-ai/flat.tex", "where agents' documents are kept"),
        ("paper/flat.md", "is a .tex file"),
    ):
        with pytest.raises(EnvError, match=said):
            destination(q, there, document=True)
    with pytest.raises(EnvError, match="outside the quilt"):
        destination(q, tmp_path / "elsewhere.tex", document=True)
    assert destination(q, "drafting-ai/flat.tex", document=True, agent=True).name == "flat.tex"
    with pytest.raises(EnvError, match="among the quilt's sources"):
        destination(q, "nodes/patched.tex")
    assert destination(q, "build/plain.tex") == (q.root / "build/plain.tex").resolve()
    assert destination(q, tmp_path / "elsewhere.tex") == (tmp_path / "elsewhere.tex").resolve()


def test_what_exists_is_not_overwritten_unless_the_command_replaces_by_design(tmp_path: Path) -> None:
    q = load_quilt(demo(tmp_path))
    (tmp_path / "out.patch").write_text("x")
    with pytest.raises(EnvError, match="exists"):
        destination(q, tmp_path / "out.patch")
    assert destination(q, tmp_path / "out.patch", overwrite=True).name == "out.patch"
