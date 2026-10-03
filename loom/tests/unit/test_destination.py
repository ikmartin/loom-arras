"""The one rule every `--to` follows (plan 0.18.4, book 12.1): a working document goes in the drafting directory, anything else stays out of the quilt's sources, and nothing that exists is overwritten unless the command replaces by design."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.cli._common import EnvError, destination
from loom.scan.quilt import load_quilt
from tests.unit._quilts import demo


def test_a_working_document_goes_in_the_drafting_directory_and_nothing_else_among_the_sources(tmp_path: Path) -> None:
    q = load_quilt(demo(tmp_path))
    assert destination(q, "drafting/flat.tex", drafting=True) == (q.root / "drafting/flat.tex").resolve()
    with pytest.raises(EnvError, match="goes directly in drafting/"):
        destination(q, "nodes/flat.tex", drafting=True)
    with pytest.raises(EnvError, match="among the quilt's sources"):
        destination(q, "nodes/patched.tex")
    with pytest.raises(EnvError, match="among the quilt's sources"):
        destination(q, "drafting/notes.txt")
    assert destination(q, "build/plain.tex") == (q.root / "build/plain.tex").resolve()
    assert destination(q, tmp_path / "elsewhere.tex") == (tmp_path / "elsewhere.tex").resolve()


def test_what_exists_is_not_overwritten_unless_the_command_replaces_by_design(tmp_path: Path) -> None:
    q = load_quilt(demo(tmp_path))
    (tmp_path / "out.patch").write_text("x")
    with pytest.raises(EnvError, match="exists"):
        destination(q, tmp_path / "out.patch")
    assert destination(q, tmp_path / "out.patch", overwrite=True).name == "out.patch"
