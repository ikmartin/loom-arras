"""Id allocation by `loom new` (book 5.3.2): the next free id, past every id the quilt defines or references, and `--print`, which allocates nothing."""

from __future__ import annotations

from pathlib import Path

from tests.helpers import ok, refused
from tests.unit._quilts import demo


def test_new_allocates_and_print(tmp_path: Path) -> None:
    q = demo(tmp_path)
    p = ok("new", "lemma", "Printed", "--print", cwd=q)
    assert "\\begin{lemma}[Printed]" in p.output and "\\label{" not in p.output and "\\begin{proof}" in p.output
    r = ok("new", "Lemma", "A new lemma", cwd=q)
    assert r.output.startswith("dm-0012 ")
    text = (q / "nodes" / "dm-0012.tex").read_text()
    assert "\\begin{lemma}[A new lemma]\\label{dm-0012}" in text and "% !LOOM created:" in text
    r2 = ok("new", "definition", cwd=q)
    assert r2.output.startswith("dm-0013 ")
    assert "\\begin{proof}" not in (q / "nodes" / "dm-0013.tex").read_text()
    refused("new", "nonsense", cwd=q, code=2, match="unknown taxon 'nonsense'")


def test_alloc_sees_references_and_never_reuses(tmp_path: Path) -> None:
    q = demo(tmp_path)
    (q / "nodes" / "scratch.tex").write_text("% dangling reference\nSee \\ref{dm-0020}.\n")
    r = ok("new", "lemma", cwd=q)
    assert r.output.startswith("dm-0021 "), r.output


def test_json_is_for_the_next_id_and_a_labelling_run_refuses_it(tmp_path: Path) -> None:
    """A file's labels are a diff; `--json` there would be ignored, so it is refused rather than dropped."""
    q = demo(tmp_path)
    ok("id", "--next", "--json", cwd=q)
    refused("id", "drafting/main.tex", "--json", cwd=q, code=2, match="--json applies to --next")
