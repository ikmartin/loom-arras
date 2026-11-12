"""The manifest's `changes`: each change waiting on the person, its block drawn with its old words and its new, each side marked with the change's id, a formula taken whole, and the annotations on it drawn on the kept words and again, moved, on the new ones."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import edit, ok, run
from tests.unit._quilts import demo

LEMMA = "drafting/nodes/dm-0002.tex"
WHO = "Tester"


@pytest.fixture
def q(tmp_path: Path) -> Path:
    from loom.scan.quilt import save_author

    save_author(WHO)
    root = demo(tmp_path)
    ok("changes", "--keep-all", cwd=root)
    return root


def built(q: Path) -> dict[str, Any]:
    run("build", cwd=q)
    return json.loads((q / ".loom/build/manifest.json").read_text())  # type: ignore[no-any-return]


def test_a_change_is_drawn_in_its_block_with_its_old_and_new_words_marked_by_id(q: Path) -> None:
    ann = ok("annotate", "dm-0002", "Which?", "--quote", "one or two points", "--as", WHO, cwd=q).output.split()[0]
    edit(q / LEMMA, "one or two points", "at most two points")
    m = built(q)
    (row,) = [c for c in m["changes"] if c["kind"] == "edit"]
    assert (row["key"], row["old"], row["new"], row["state"]) == ("dm-0002", "one or", "at most", "ready")
    assert row["diff"] == f"changes/{row['id']}.diff" and (q / ".loom/build" / row["diff"]).is_file()
    assert row["block"]["src"].startswith(f"{LEMMA}:") and row["block"]["fragment"].startswith("fragments/changes/")
    assert m["changes_since"]["who"] == WHO
    html = (q / ".loom/build" / row["block"]["fragment"]).read_text()
    # TeX is the unit tier's shim, which refuses, so the block shows as its source, its sides marked
    assert html.startswith('<pre class="source"')
    import re

    plain = re.sub(r"</?mark[^>]*>", "", html)
    assert f'<span class="change" data-change="{row["id"]}" data-side="old">one or</span>' in plain
    assert f'<span class="change" data-change="{row["id"]}" data-side="new">at most</span>' in plain
    # the annotation on the changed words is drawn on the kept words, and moved, on the new
    assert f'<mark class="annotation" data-annotation="{ann}">one or</mark>' in html
    assert (
        f'<mark class="annotation moved" data-annotation="{ann}"><span class="change" data-change="{row["id"]}" data-side="new">at most</span> two points</mark>'
        in html
    )
    assert m["annotations"][ann]["on_changes"] == [row["id"]]


def test_a_change_inside_a_formula_takes_the_formula_whole(q: Path) -> None:
    edit(q / LEMMA, "$\\sigma x = x$", "$\\sigma x = y$")
    m = built(q)
    (row,) = [c for c in m["changes"] if c["kind"] == "edit"]
    html = (q / ".loom/build" / row["block"]["fragment"]).read_text()
    assert 'data-side="old">$\\sigma x = x$;</span>' in html and 'data-side="new">$\\sigma x = y$;</span>' in html


def test_a_suggested_edit_is_a_change_and_its_record_has_no_change_field(q: Path) -> None:
    m = built(q)
    (suggested,) = [c for c in m["changes"] if c["kind"] == "suggested"]
    record = m["suggested_edits"][suggested["id"]]
    assert "change" not in record and record["status"] == "open"
    assert suggested["author"] == record["author"]["id"] and suggested["block"]["fragment"].startswith(
        "fragments/changes/"
    )


@pytest.mark.tex
def test_a_block_is_made_by_tex_with_each_side_of_its_change_marked(q: Path) -> None:
    edit(q / LEMMA, "one or two points", "at most two points")
    ok("compile", "drafting/main.tex", "--html", cwd=q)
    m = built(q)
    (row,) = [c for c in m["changes"] if c["kind"] == "edit"]
    html = (q / ".loom/build" / row["block"]["fragment"]).read_text()
    # the leaf is the lemma's paragraph, made by TeX, and in the document's terms
    assert '<pre class="source"' not in html and f'data-src="{row["block"]["src"]}"' in html
    assert f'data-change="{row["id"]}" data-side="old"' in html and f'data-change="{row["id"]}" data-side="new"' in html
    assert row["new_html"] and "at most" in row["new_html"]


@pytest.fixture
def synthetic(tmp_path: Path) -> dict[str, Any]:
    """The synthetic quilt built by TeX as the fixture is, by the name its look was taken under: its manifest, and a reader of its build."""
    import shutil

    from loom.scan.quilt import save_author
    from tests.unit._quilts import REPO

    save_author("The synthetic quilt")
    q = tmp_path / "synthetic"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", q, ignore=shutil.ignore_patterns("build", ".git"))
    ok("compile", "drafting/main.tex", "--html", cwd=q)
    m = built(q)
    return {"m": m, "read": lambda rel: (q / ".loom/build" / rel).read_text()}


def _without_sides(html: str) -> str:
    """`html` with every `span.change` and what it holds taken out."""
    import re

    pattern = re.compile(
        r'<span class="change"[^>]*>(?:(?!<span class="change")(?:<span\b[^>]*>.*?</span>|.))*?</span>', re.S
    )
    while True:
        cut = pattern.sub("", html)
        if cut == html:
            return cut
        html = cut


@pytest.mark.tex
def test_references_in_a_changed_passage_stand_inside_its_sides(synthetic: dict[str, Any]) -> None:
    """The suggested edit on `compare \\eqref{eq:fix} in Definition~\\ref{sy-0001}`: TeX makes each reference an element, and each stands in the side it is on, so nothing of either side is drawn outside them."""
    row = next(c for c in synthetic["m"]["changes"] if c["id"] == "e-2026-09-17-zwvx4m")
    html = synthetic["read"](row["block"]["fragment"])
    assert html.count('data-side="old"') >= 2 and html.count('data-side="new"') >= 2
    rest = _without_sides(html)
    assert 'class="ref' not in rest, rest
    assert "compare" not in rest and "the fixed points are those of" not in rest


@pytest.mark.tex
def test_a_merged_block_carries_the_documents_offsets_ids_and_empty_marks(synthetic: dict[str, Any]) -> None:
    """The in-place edit in Definition 1.1 (sy-0001), in a paragraph whose annotation's words are gone: the block drawn with the change is that paragraph, by its own `data-src`, with the empty mark the document draws there."""
    import re

    row = next(c for c in synthetic["m"]["changes"] if c["kind"] == "edit" and c["path"] == "drafting/main.tex")
    html = synthetic["read"](row["block"]["fragment"])
    document = synthetic["read"](synthetic["m"]["nodes"]["sy-0001"]["fragment"])
    paragraph = re.search(r'<p class="noindent" data-src="([^"]+)"', document)
    assert paragraph is not None and row["block"]["src"] == paragraph.group(1)
    assert f'data-src="{paragraph.group(1)}"' in html and "review-" not in html, "every offset is the document's"
    gone = re.findall(r'<mark class="annotation gone" data-annotation="[^"]+"></mark>', document)
    assert gone and all(g in html for g in gone)


EXERCISES = """\\section{Exercises}\\label{dm-0090}

\\begin{enumerate}[1.]
\\item Why does a widget have a fixed point?
\\begin{proof}
Because its underyling set is odd.
\\end{proof}
\\item And why only one?
\\begin{proof}
It need not have only one.
\\end{proof}
\\end{enumerate}
"""


def test_a_change_with_no_leaf_has_a_place_and_one_inside_a_proof_a_block_no_larger_than_its_text(
    tmp_path: Path,
) -> None:
    """A list's options are no leaf, since the list holds proofs: that change is published with no block, at its own words; a change inside one item's proof is drawn in the proof's own text, and no block holds another block."""
    from loom.scan.quilt import save_author

    save_author(WHO)
    q = demo(tmp_path)
    (q / "drafting/exercises.tex").write_text(EXERCISES)
    edit(q / "drafting/main.tex", "\\end{document}", "\\input{exercises}\n\\end{document}")
    ok("changes", "--keep-all", cwd=q)
    edit(q / "drafting/exercises.tex", "\\begin{enumerate}[1.]", "\\begin{enumerate}[{1.}1.]")
    edit(q / "drafting/exercises.tex", "underyling", "underlying")
    m = built(q)
    rows = {c["new"]: c for c in m["changes"] if c["path"] == "drafting/exercises.tex"}
    options, word = rows["\\begin{enumerate}[{1.}1.]"], rows["underlying"]
    assert options["block"] is None
    start, end = (int(x) for x in options["place"]["src"].rsplit(":", 2)[1:])
    text = (q / "drafting/exercises.tex").read_text()
    assert (
        options["place"]["src"].startswith("drafting/exercises.tex:")
        and text[start:end] == "\\begin{enumerate}[{1.}1.]"
    )
    b0, b1 = (int(x) for x in word["block"]["src"].rsplit(":", 2)[1:])
    assert "underlying" in text[b0:b1] and "\\item" not in text[b0:b1] and len(text[b0:b1]) < 60
    # no block holds another block: no statement or proof of the file starts and ends inside it
    from loom.cli._quilt import open_scan

    result = open_scan(str(q))
    for c in m["changes"]:
        if c["block"] is None:
            continue
        path, a, b = c["block"]["src"].rsplit(":", 2)
        inside = [
            n.key
            for n in result.nodes.values()
            if n.file == path
            and n.kind in ("environment", "proof")
            and int(a) <= n.start
            and n.end <= int(b)
            and (n.start, n.end) != (int(a), int(b))
        ]
        assert inside == [], (c["id"], inside)


def _suggest(q: Path, key: str, quote: str, new: str) -> str:
    from tests.helpers import json_of

    said = json_of(
        "suggest", key, "--quote", quote, "--with", new, "--as", "Referee Agent", "--json", cwd=q, env={"AI_AGENT": "1"}
    )
    return str(said["edit"])


@pytest.mark.tex
def test_a_suggested_edit_keeps_its_last_old_word_and_first_new_word_apart_and_the_documents_offsets(q: Path) -> None:
    """Old words ending in a letter and new ones beginning with one stay two words, each on its own side; the file holds the old side, so the block carries the document's `data-src`, and a display keeps its id."""
    import re

    edit_id = _suggest(q, "dm-0002", "one or two points", "notional value")
    display = _suggest(q, "dm-0001", "\\sigma x = x", "\\sigma x = x \\text{ for every } x")
    ok("compile", "drafting/main.tex", "--html", cwd=q)
    m = built(q)
    rows = {c["id"]: c for c in m["changes"]}
    html = (q / ".loom/build" / rows[edit_id]["block"]["fragment"]).read_text()
    plain = re.sub(r"</?mark[^>]*>", "", html)
    old = " ".join(re.findall(rf'data-change="{edit_id}" data-side="old">([^<]*)<', plain)).split()
    new = " ".join(re.findall(rf'data-change="{edit_id}" data-side="new">([^<]*)<', plain)).split()
    assert (old, new) == (["one", "or", "two", "points"], ["notional", "value"]), plain
    assert f'data-src="{rows[edit_id]["block"]["src"]}"' in html and "review-" not in html
    # a display is its own leaf, and keeps the document's id
    shown = (q / ".loom/build" / rows[display]["block"]["fragment"]).read_text()
    document = (q / ".loom/build" / m["nodes"]["dm-0001"]["fragment"]).read_text()
    src = re.escape(rows[display]["block"]["src"])
    ident = re.search(rf'data-src="{src}"[^>]*\bid="([^"]+)"', document) or re.search(
        rf'\bid="([^"]+)"[^>]*data-src="{src}"', document
    )
    assert ident is not None and f'id="{ident.group(1)}"' in shown
