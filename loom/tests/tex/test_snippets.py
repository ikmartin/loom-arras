"""TeX tier: text that is never compiled, made HTML by TeX under its document's preamble: one run for many texts, a bad text costs only itself, a text made once is read from the cache; a node no document reaches is made so, and a diagram is a picture TeX drew."""

from __future__ import annotations

import re
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
def test_a_text_that_stops_tex_runs_alone_and_the_rest_once(tmp_path: Path) -> None:
    """An `\\input` of a file the document lacks stops TeX, and an argument left open reads to the end of the run; a cited paper's digest had a dozen of each, which cost the rest of its texts a run apiece."""
    q = tmp_path / "q"
    q.mkdir()
    stops = ["See \\input{nowhere.pspdftex} here.", "A note\\footnote{left open, as a digest's was."]
    texts = [*GOOD, stops[0], GOOD[1] + " Again.", stops[1], "A last good text."]
    made = _run(q, texts)
    assert [s.html is not None for s in made.made] == [True, True, True, True, False, True, False, True], [
        (s.error, (s.html or "")[:60]) for s in made.made
    ]
    assert made.runs == 3, made.runs  # the rest together, each stopping text alone


@pytest.mark.tex
def test_a_text_made_once_is_read_from_the_cache(tmp_path: Path) -> None:
    q = tmp_path / "q"
    q.mkdir()
    first = _run(q, GOOD[:2])
    again = _run(q, [*GOOD[:2], GOOD[1]])
    assert first.runs == 1 and again.runs == 0
    assert all(s.cached for s in again.made) and again.made[2].html == first.made[1].html


MASTER = r"""\documentclass{amsart}
\usepackage{amsmath,amsthm,tikz-cd}
\newtheorem{lemma}{Lemma}
\begin{document}
\begin{lemma}\label{pp-0001}
A square commutes:
\begin{equation}\label{eq:sq}
\begin{tikzcd} A \arrow[r] \arrow[d] & B \arrow[d] \\ C \arrow[r] & D \end{tikzcd}
\end{equation}
\end{lemma}
\end{document}
"""


def _quilt(tmp_path: Path) -> Path:
    from tests.helpers import ok

    q = tmp_path / "q"
    ok("init", str(q), "--prefix", "pp", "--yes", cwd=tmp_path)
    (q / "drafting" / "nodes").mkdir(parents=True)
    (q / "drafting" / "main.tex").write_text(MASTER, encoding="utf-8")
    # a statement no document includes, which no compile ever makes
    (q / "drafting" / "nodes" / "pp-0002.tex").write_text(
        "\\begin{lemma}[Loose]\\label{pp-0002}\nBy Lemma~\\ref{pp-0001}, \\(A \\to B\\) is \\textbf{fine}.\n\\end{lemma}\n",
        encoding="utf-8",
    )
    return q


@pytest.mark.tex
def test_a_diagram_is_a_picture_tex_drew_numbered_as_the_document_numbers_it(tmp_path: Path) -> None:
    from tests.helpers import ok

    q = _quilt(tmp_path)
    ok("compile", "drafting/main.tex", "--html", cwd=q)
    ok("build", cwd=q)
    frag = (q / ".loom/build/fragments/masters/drafting/main.html").read_text(encoding="utf-8")
    figure = re.search(r'<figure class="diagram"([^>]*)><img src="(svg/[^"]+)"', frag)
    assert figure is not None, frag
    assert 'data-label="eq:sq"' in figure.group(1) and 'data-number="1"' in figure.group(1)
    assert (q / ".loom/build" / figure.group(2)).is_file()


@pytest.mark.tex
def test_a_node_no_document_reaches_is_made_by_tex_in_the_default_documents_terms(tmp_path: Path) -> None:
    from tests.helpers import ok

    q = _quilt(tmp_path)
    ok("compile", "drafting/main.tex", "--html", cwd=q)
    ok("build", cwd=q)
    frag = (q / ".loom/build/fragments/nodes/pp-0002.html").read_text(encoding="utf-8")
    assert frag.startswith('<div data-from="tex" data-fragment="node" class="env env-lemma" id="pp-0002"'), frag[:200]
    assert '<span class="title">(Loose)</span>' in frag and "<strong>fine" in frag
    # its reference prints the number the default document's aux gives
    assert re.search(r'<a [^>]*data-target="pp-0001"[^>]*>1</a>', frag), frag
