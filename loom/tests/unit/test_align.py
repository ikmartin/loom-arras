"""Rendered words placed in their LaTeX source (plan 0.29.2): the words a reader sees, mathematics as a gap, and the occurrence nearest where the renderer said it began."""

from __future__ import annotations

from loom.tex.align import Source, rendered_words, source_words

SRC = r"""\section{Widgets}\label{sec:w}
A \emph{widget} has a fixed point $x \in X$, by \cite[Theorem~4]{Arden24}; see~\eqref{eq:a}.
\begin{align}
  a &= b \label{eq:a}
\end{align}
The ﬁxed point is unique. % not this
\begin{lemma}[Uniqueness]
A widget has a fixed point.
\end{lemma}
"""


def test_a_reader_s_words_leave_out_names_mathematics_and_what_prints_no_words() -> None:
    words = [w.text for w in source_words(SRC.replace("% not this", "          "))]
    # a citation, `\cite[Theorem~4]{Arden24}`, is what TeX makes of a key and a note, as the rendering marks it
    said = "widgets a widget has a fixed point by see the fixed point is unique uniqueness a widget has a fixed point"
    assert words == said.split()


def test_rendered_words_fold_ligatures_and_case_and_drop_numbers() -> None:
    assert rendered_words("The ﬁxed Point 4.1 (2) is “unique”.") == ["the", "fixed", "point", "is", "unique"]


def test_a_run_of_words_is_placed_at_the_occurrence_nearest_its_hint() -> None:
    src = Source(SRC)
    first, second = SRC.index(r"A \emph{widget} has"), SRC.rindex("A widget has")
    early = src.place(rendered_words("A widget has a fixed point"), 0)
    late = src.place(rendered_words("A widget has a fixed point"), second)
    assert early is not None and early.exact and early.start == first
    assert SRC[early.start : early.end] == r"A \emph{widget} has a fixed point"
    assert late is not None and late.exact and late.start == second
    assert SRC[late.start : late.end] == "A widget has a fixed point"


def test_words_that_differ_a_little_are_placed_near_and_too_much_not_at_all() -> None:
    src = Source(SRC)
    near = src.place(rendered_words("The fixed point is surely unique"), 0)
    assert near is not None and not near.exact and SRC[near.start : near.end].startswith("The ﬁxed point")
    assert src.place(rendered_words("Nothing here was ever written"), 0) is None
