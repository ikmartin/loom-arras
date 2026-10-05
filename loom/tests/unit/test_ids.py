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


def test_new_names_its_writer_and_says_where_to_place_the_node(tmp_path: Path) -> None:
    """The re-grade: under an agent marker `new` wrote the author's name into the node, and said nothing of the node being reached by no document or of the line that would place it."""
    q = demo(tmp_path)
    r = ok("new", "lemma", "Placed", "--as", "Referee Agent", cwd=q)
    assert "% !LOOM author: Referee Agent" in (q / "nodes" / "dm-0012.tex").read_text()
    assert "no document reaches it yet" in r.stdout
    assert "\\input{nodes/dm-0012}" in r.stdout and "drafting/main.tex" in r.stdout
    refused("new", "lemma", cwd=q, env={"AI_AGENT": "1"}, code=2, match="has not said who it is")
    assert not (q / "nodes" / "dm-0013.tex").exists()


def test_an_unknown_taxon_lists_what_each_document_declares(tmp_path: Path) -> None:
    """The demo's main.tex declares neither conjecture nor question; the outline does, so `new` takes them, and the refusal says whose they are."""
    q = demo(tmp_path)
    r = refused("new", "lemmma", cwd=q, code=2, match="unknown taxon 'lemmma'")
    said = " ".join(r.output.split())
    assert "drafting/main.tex declares definition, lemma, proposition, remark, theorem" in said
    assert "drafting/outline.tex also conjecture, question" in said
