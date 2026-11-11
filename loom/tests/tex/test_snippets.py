"""TeX tier: text that is never compiled, made HTML by TeX under its document's preamble (plan 0.29.4): one run for many texts, a bad text costs only itself, and a text made once is read from the cache."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.render.snippets import render_snippets

PREAMBLE = r"""\documentclass{amsart}
\usepackage{amsmath,amsthm,tikz-cd}
\newtheorem{lemma}{Lemma}
\newcommand{\R}{\mathbb{R}}
\newcommand{\widget}{gadget}"""

GOOD = [
    "\\begin{lemma}[Named]\\label{q1}\nEvery \\widget\\ on $\\R^n$ is \\emph{fine}.\n\\end{lemma}",
    "A paragraph with \\textbf{bold} words.\n\nAnd a second paragraph.",
    "\\begin{proof}\nBy \\ref{q1}.\n\\end{proof}",
    "A diagram:\n\\[\\begin{tikzcd} A \\arrow[r] & B \\end{tikzcd}\\]",
]


def _run(q: Path, texts: list[str]):  # type: ignore[no-untyped-def]
    return render_snippets(q, "", PREAMBLE, texts, q / ".loom/build/cache/snippets", envs=["lemma", "proof"])


@pytest.mark.tex
def test_texts_are_made_in_one_run_each_in_its_document_s_terms(tmp_path: Path) -> None:
    q = tmp_path / "q"
    q.mkdir()
    made = _run(q, GOOD)
    assert made.runs == 1 and all(s.html is not None for s in made.made), [s.error for s in made.made]
    lemma, para, proof, _diagram = (s.html or "" for s in made.made)
    # a macro in text prints what the preamble defines; one in a formula stays for the viewer's typesetter, as on a document's page
    assert '<div class="node" data-env="lemma"' in lemma and "gadget" in lemma and "\\(\\R ^n\\)" in lemma
    assert "<strong>bold" in para and para.count("<p") == 2
    assert '<div class="node" data-env="proof"' in proof and "Named" not in proof
    # each text holds its own words and no other's
    assert "bold" not in lemma and "gadget" not in para


@pytest.mark.tex
def test_a_bad_text_costs_only_itself(tmp_path: Path) -> None:
    """An undefined command fails in the run; an unclosed list and an `\\end{document}` break it, run again alone, and fail there; every good text is made."""
    q = tmp_path / "q"
    q.mkdir()
    bad = [
        "Has \\undefinedthing{x} in it.",
        "Opens \\begin{itemize}\\item and never closes.",
        "Ends it all \\end{document} early.",
    ]
    texts = [GOOD[0], bad[0], GOOD[1], bad[1], GOOD[2], bad[2], "A last good text."]
    made = _run(q, texts)
    assert [s.html is not None for s in made.made] == [True, False, True, False, True, False, True], [
        (s.error, (s.html or "")[:60]) for s in made.made
    ]
    assert "Undefined control sequence" in made.made[1].error
    assert "A last good text." in (made.made[6].html or "")
    assert made.runs <= 5, made.runs


@pytest.mark.tex
def test_a_text_made_once_is_read_from_the_cache(tmp_path: Path) -> None:
    q = tmp_path / "q"
    q.mkdir()
    first = _run(q, GOOD[:2])
    again = _run(q, [*GOOD[:2], GOOD[1]])
    assert first.runs == 1 and again.runs == 0
    assert all(s.cached for s in again.made) and again.made[2].html == first.made[1].html
