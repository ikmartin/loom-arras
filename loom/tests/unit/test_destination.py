"""The one rule every `--to` follows (plan 0.18.4): a working document goes anywhere in the quilt loom reads, anything else stays out of the quilt's sources, and nothing that exists is overwritten unless the command replaces by design."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.cli._common import EnvError, destination
from loom.scan.quilt import load_quilt
from tests.unit._quilts import demo


def test_a_working_document_goes_anywhere_loom_reads_and_nothing_else_among_the_sources(tmp_path: Path) -> None:
    q = load_quilt(demo(tmp_path))
    for there in (
        "drafting/flat.tex",
        "paper/main.tex",
        "flat.tex",
        "notes/flat.tex",
        "build/flat.tex",
        "drafting-ai/flat.tex",
    ):
        assert destination(q, there, document=True) == (q.root / there).resolve()
    for there, said in (
        (".loom/retired/flat.tex", "is inside .loom/"),
        (".loom/flat.tex", "is inside .loom/"),
        (".loom/build/flat.tex", "is inside .loom/"),
        (".loom/copies/flat.tex", "is inside .loom/"),
        ("paper/flat.md", "is a .tex file"),
    ):
        with pytest.raises(EnvError, match=said):
            destination(q, there, document=True)
    with pytest.raises(EnvError, match="outside the quilt"):
        destination(q, tmp_path / "elsewhere.tex", document=True)
    with pytest.raises(EnvError, match="among the quilt's sources"):
        destination(q, "drafting/nodes/patched.tex")
    assert destination(q, ".loom/build/plain.tex") == (q.root / ".loom/build/plain.tex").resolve()
    assert destination(q, tmp_path / "elsewhere.tex") == (tmp_path / "elsewhere.tex").resolve()


def test_what_exists_is_not_overwritten_unless_the_command_replaces_by_design(tmp_path: Path) -> None:
    q = load_quilt(demo(tmp_path))
    (tmp_path / "out.patch").write_text("x")
    with pytest.raises(EnvError, match="exists"):
        destination(q, tmp_path / "out.patch")
    assert destination(q, tmp_path / "out.patch", overwrite=True).name == "out.patch"


def test_an_agent_is_refused_what_the_quilt_protects_and_a_person_is_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = demo(tmp_path)
    config = root / "config.toml"
    config.write_text(config.read_text(encoding="utf-8") + '\n[agents]\ndeny = ["drafting/"]\n', encoding="utf-8")
    q = load_quilt(root)
    assert destination(q, "drafting/flat.tex", document=True).name == "flat.tex"
    monkeypatch.setenv("AI_AGENT", "1")
    with pytest.raises(EnvError, match=r"\[agents\] deny names drafting/"):
        destination(q, "drafting/flat.tex", document=True)
    for there, said in (
        ("config.toml", "config.toml is the person's"),
        ("research-state.md", "only through `loom write`"),
    ):
        with pytest.raises(EnvError, match=said):
            destination(q, there, overwrite=True)
    with pytest.raises(EnvError, match=r"\.loom/ is loom's"):
        destination(q, ".loom/annotations/x.txt")
    assert destination(q, "paper/flat.tex", document=True).name == "flat.tex"
    assert destination(q, ".loom/build/plain.tex").name == "plain.tex"
    assert destination(q, "notes.md").name == "notes.md"
