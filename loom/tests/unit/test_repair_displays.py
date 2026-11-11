"""A display whose braces do not balance, which pdflatex may set and TeX4ht cannot read, is held as a placeholder in the copy TeX4ht reads (plan 0.29.2): every later line keeps its number, and the counter steps as the display would have."""

from __future__ import annotations

from loom.tex.tex4ht import repair_displays

BAD = "\\begin{align}\na &= \\lambda^{c}d^n}\\langle e\\rangle^{f \\label{r1}\\\\\nb &= c \\nonumber\\\\\nd &= e \\label{r3}\n\\end{align}"


def test_a_balanced_display_is_left_as_written() -> None:
    text = "Before \\begin{equation}\\label{e} x^{2}\\end{equation} and \\[ y_{1} \\] after, \\\\[2pt] then."
    assert repair_displays(text) == (text, [])


def test_an_unbalanced_display_becomes_a_placeholder_on_the_same_lines_stepping_each_numbered_row() -> None:
    text = f"line one\n{BAD}\nline after\n"
    fixed, found = repair_displays(text, first=3)
    assert found == [(2, BAD)]
    assert (
        fixed.splitlines()[1]
        == "\\loomdisplay{3}\\refstepcounter{equation}\\label{r1}\\refstepcounter{equation}\\label{r3}"
    )
    assert fixed.count("\n") == text.count("\n") and fixed.splitlines()[-1] == "line after"


def test_a_comment_is_no_part_of_a_display_s_braces() -> None:
    text = "\\begin{equation} x^{2} % a stray } in a comment\n\\end{equation}"
    assert repair_displays(text)[1] == []
    starred = "\\begin{equation*} x^{2}} \\end{equation*}"
    fixed, found = repair_displays(starred)
    assert fixed == "\\loomdisplay{0}" and len(found) == 1  # unnumbered, so nothing steps
