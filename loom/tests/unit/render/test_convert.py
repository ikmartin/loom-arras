"""The converter on isolated LaTeX strings: each construct of book 9.4.1 maps to the dialect element the spec names."""

from __future__ import annotations

import re
import unicodedata

from loom.render.convert import Converter, RenderContext
from loom.scan.macros import parse_macros
from loom.scan.source import blank_comments
from loom.tex.aux import AuxNumber


def make(text: str, *, labels=None, numbers=None, macros="", children=None, cite_labels=None):  # type: ignore[no-untyped-def]
    calls: list[tuple[str, str]] = []

    def fallback(latex: str, css: str, src: str) -> str:
        calls.append((css, latex))
        return f'<figure class="{css}" data-src="{src}" data-src-text="x"><svg></svg></figure>'

    ctx = RenderContext(
        file="f.tex",
        text=text,
        clean=blank_comments(text),
        key="k-0001",
        labels=labels or {},
        regions={},
        numbers=numbers or {},
        macros=parse_macros(macros),
        taxa={},
        child_at=children or {},
        child_html=lambda key: f'<div class="include" data-key="{key}"></div>',
        include_html=lambda arg: f'<div class="include" data-key="{arg}"></div>',
        fallback=fallback,
        cite_target=lambda ck, post: "Man12-thm-4.1" if (ck, post) == ("Man12", "Theorem 4.1") else None,
        cite_labels=cite_labels or {},
    )
    conv = Converter(ctx)
    return conv.render_range(0, len(text)), ctx, calls


def test_convert_paragraphs_and_inline_markup() -> None:
    out, ctx, calls = make(
        "First \\emph{one} and \\textbf{two} -- three --- ``quoted''.\n\nSecond~para \\S 3, 50\\% done.\n"
    )
    assert out.count("<p ") == 2
    assert "<em>one</em>" in out and "<strong>two</strong>" in out
    assert "– three — “quoted”" in out and "Second\u00a0para § 3, 50% done" in out
    assert 'data-src="f.tex:0:' in out
    assert calls == [] and ctx.diagnostics == []


def test_convert_math_inline_display_labels() -> None:
    text = "Inline $x^2$ and \\(y\\).\n\\begin{equation}\\label{eq:main}\nx = y\n\\end{equation}\n\\[ z \\]\n$$ w $$\n\\begin{align}\na &= b \\label{eq:a} \\\\\nc &= d\n\\end{align}\n"
    out, ctx, _ = make(text, numbers={"eq:main": AuxNumber("3.2", 1), "eq:a": AuxNumber("3.3", 1)})
    assert '<span class="math inline">\\(x^2\\)</span>' in out and "\\(y\\)" in out
    assert 'class="math display"' in out
    assert 'id="k-0001-eq-main" data-label="eq:main" data-number="3.2"' in out
    assert "\\[\\tag{3.2}x = y\\]" in out
    assert "\\begin{align*}" in out and "\\tag{3.3}" in out and "\\label" not in out
    assert out.count('class="math display"') == 4


def test_convert_refs_cites_footnote_url() -> None:
    text = "See Lemma~\\ref{lem:a}, \\eqref{eq:b}, \\cref{lem:a,thm:c}, \\ref{nope}; \\cite[Theorem 4.1]{Man12} and \\cite{Har77}.\\footnote{A note with $m$.} \\url{https://x.org} \\href{https://y.org}{Y}."
    labels = {"lem:a": "k-0002", "eq:b": "k-0003#eq:b", "thm:c": "k-0004"}
    out, ctx, _ = make(text, labels=labels, numbers={"lem:a": AuxNumber("2.1", 1), "eq:b": AuxNumber("7", 2)})
    ctx.regions["k-0003#eq:b"] = "k-0003"
    out, ctx2, _ = make(text, labels=labels, numbers={"lem:a": AuxNumber("2.1", 1), "eq:b": AuxNumber("7", 2)})
    assert '<a class="ref" data-target="k-0002" href="#k-0002">2.1</a>' in out
    assert '<a class="ref ref-dangling" data-target="nope">??</a>' in out
    assert 'data-citekey="Man12" data-postnote="Theorem 4.1" data-target="Man12-thm-4.1"' in out
    assert 'data-citekey="Har77"' in out and 'data-target="Har77' not in out
    assert '<span class="footnote" data-n="1">A note with <span class="math inline">\\(m\\)</span>.</span>' in out
    assert (
        '<a class="url" href="https://x.org">https://x.org</a>' in out
        and '<a class="url" href="https://y.org">Y</a>' in out
    )


def test_convert_lists_and_sectioning() -> None:
    text = "\\section{Setup}\n\\begin{itemize}\n\\item one\n\\item two with\n\nparagraphs\n\\end{itemize}\n\\begin{enumerate}[(a)]\n\\item[x] labelled\n\\end{enumerate}\n\\begin{description}\n\\item[Term] meaning\n\\end{description}\n"
    out, ctx, calls = make(text)
    assert "<h1 " in out and ">Setup</h1>" in out
    assert "<ul " in out and "<li>one</li>" in out and out.count("<li>") + out.count("<li ") == 3
    assert '<li data-label="x">labelled</li>' in out
    assert "<dt>Term</dt><dd>meaning</dd>" in out
    assert calls == []


def test_convert_env_fallback_diagram_verbatim_table() -> None:
    text = "\\begin{tikzcd}\nA \\arrow[r] & B\n\\end{tikzcd}\n\n\\parbox{3cm}{boxed}\n\n\\begin{verbatim}\nraw <text>\n\\end{verbatim}\n\\begin{tabular}{ll}\na & b \\\\\nc & d\n\\end{tabular}\n\\begin{tabular}{ll}\n\\multicolumn{2}{c}{x}\n\\end{tabular}\n\\begin{weird}\nz\n\\end{weird}\n"
    out, ctx, calls = make(text)
    kinds = [c for c, _ in calls]
    assert kinds == ["diagram", "fallback", "fallback", "fallback"]
    assert "<pre " in out and "raw &lt;text&gt;" in out
    assert "<table " in out and "<td>a</td><td>b</td>" in out
    codes = [d.code for d in ctx.diagnostics]
    assert codes.count("loom:converter-fallback") == 3


def test_convert_text_macros_expanded_and_math_macros_left() -> None:
    macros = "\\newcommand{\\GW}{Gromov--Witten}\n\\newcommand{\\red}[1]{\\textcolor{red}{#1}}\n\\newcommand{\\Res}{\\mathrm{Res}}\n\\newcommand{\\vir}{\\text{vir}}\n"
    out, ctx, calls = make("The \\GW{} theory; \\red{alert}; $\\Res$ and \\Res.", macros=macros)
    assert "Gromov–Witten theory" in out and "alert" in out and "textcolor" not in out
    assert "\\(\\Res\\)" in out and "\\(\\mathrm{Res}\\)" in out
    assert calls == []


def test_convert_nothing_dropped_unknown_command_falls_back() -> None:
    out, ctx, calls = make("A paragraph with \\mystery{arg} inside.\n\nA clean one.\n")
    assert len(calls) == 1 and "mystery" in calls[0][1]
    assert out.count("<p ") == 1 and "A clean one." in out
    assert ctx.diagnostics[0].code == "loom:converter-fallback"


def test_convert_children_and_inclusions_become_placeholders() -> None:
    text = "Intro.\n\\begin{lemma}\\label{k-0002}\nL\n\\end{lemma}\nAfter.\n\\input{nodes/k-0003}\nEnd.\n"
    start = text.index("\\begin{lemma}")
    end = text.index("\\end{lemma}") + len("\\end{lemma}")
    out, ctx, calls = make(text, children={start: (end, "k-0002")})
    assert (
        out.index("Intro.")
        < out.index('data-key="k-0002"')
        < out.index("After.")
        < out.index('data-key="nodes/k-0003"')
        < out.index("End.")
    )
    assert calls == []
    assert re.search(r'<p data-src="f.tex:\d+:\d+">After\.</p>', out)


def test_convert_conditionals_definitions_starred_sections() -> None:
    text = "\\section*{Overview}\nA \\let\\Hom\\undefined \\newcommand{\\Hom}{\\mathrm{Hom}} paragraph.\n\\iffalse\n\\input{nodes/missing} and \\mystery{x}\n\\fi\nAfter.\n"
    out, ctx, calls = make(text)
    assert "<h1 " in out and "Overview" in out
    assert "After." in out and "missing" not in out and "mystery" not in out
    assert calls == [] and ctx.diagnostics == []
    assert "paragraph." in out


def test_an_accent_without_braces_keeps_the_text_that_follows_it() -> None:
    # `\'e` takes its argument from the middle of the text after it; the rest of that text is still text (ACGS, acgs-002P). An accent is written as its combining character, so the comparison is on composed text.
    out, ctx, _ = make("branches at $q$ in the \\'etale topology. Then there exist lifts $s_x$ such that\n")
    assert "in the étale topology. Then there exist lifts" in unicodedata.normalize("NFC", out)
    assert ctx.diagnostics == []


def test_an_accent_without_braces_keeps_the_paragraph_it_starts() -> None:
    out, _, _ = make("\\'Etale descent is proved below.\n\nThe \\v{c}ech complex follows.\n")
    composed = unicodedata.normalize("NFC", out)
    assert "Étale descent is proved below." in composed and "čech complex follows." in composed
    assert out.count("<p ") == 2


def test_a_macro_inside_text_is_written_between_dollars() -> None:
    # MathJax's text mode has no \underline, so `\text{nodes of \ul C}` cost the whole formula (ACGS, acgs-002P)
    macros = "\\newcommand\\ul[1]{\\underline{#1}}\n\\newcommand\\NN{\\mathbb{N}}\n\\newcommand\\etc{etc.}\n"
    out, _, _ = make("$\\bigoplus_{\\text{nodes of \\ul C}} \\NN$ and $x + \\text{and so on, \\etc}$\n", macros=macros)
    assert "\\text{nodes of $\\ul C$}" in out
    assert "\\text{and so on, \\etc}" in out  # a macro whose body is words is left as it is


def test_a_macro_already_inside_math_within_text_is_left_alone() -> None:
    macros = "\\newcommand\\ul[1]{\\underline{#1}}\n"
    # the outer math is written \(…\), since a $ inside \text{} would close a $-delimited formula
    out, _, _ = make("\\(\\text{already $\\ul C$ here}\\)\n", macros=macros)
    assert out.count("$\\ul C$") == 1


def test_a_reference_inside_a_text_argument_is_not_wrapped_in_text() -> None:
    """`\\tag{Equation \\eqref{…}}` is ordinary to write and its argument is already text, so the `\\text{…}` that keeps a label upright everywhere else made MathJax refuse the whole formula — "\\text is only supported in math mode" — and the aligned chain published as its own source on a yellow ground."""
    text = (
        "\\begin{align*}\na &= b \\tag{Lemma~\\ref{lem:a}}\\\\\nc &= d \\tag{Equation \\eqref{eq:b}}\\\\\n"
        "e &= f \\tag{by hand}\n\\end{align*}\nIn prose, \\(g = \\ref{lem:a}\\) still wants it.\n"
    )
    labels = {"lem:a": "k-0002", "eq:b": "k-0003"}
    out, _, _ = make(text, labels=labels, numbers={"lem:a": AuxNumber("2.1", 1), "eq:b": AuxNumber("7", 2)})
    assert "\\tag{Lemma~2.1}" in out and "\\tag{Equation (7)}" in out
    assert "\\tag{by hand}" in out  # a tag with no reference is untouched
    assert "\\tag{Lemma~\\text{" not in out and "\\tag{Equation \\text{" not in out
    assert "\\text{2.1}" in out  # and a reference in math mode keeps its upright wrapper


def test_a_citation_prints_the_compiled_label() -> None:
    """A citation reads as the compiled paper prints it, `[GP99, Theorem 1]`; the citekey stays in `data-citekey`, and an uncompiled document shows the key rather than a guess."""
    text = "\\cite[Theorem 1]{graber-pandharipande_Localization1999} and \\cite{Har77}."
    out, _, _ = make(text, cite_labels={"graber-pandharipande_Localization1999": "GP99"})
    assert 'data-citekey="graber-pandharipande_Localization1999"' in out
    assert ">[GP99, Theorem 1]</span>" in out and ">[Har77]</span>" in out


def test_a_comment_inside_a_formula_does_not_reach_the_renderer() -> None:
    r"""MathJax reads `%` as TeX does, to the end of the line, so a commented-out line of an `align` swallowed the `\end{align*}` after it and the block reached the page as an error; the commented-out `\label` also claimed the block's number (seen on the mZK paper, where every deleted line was kept in a comment)."""
    text = "\\begin{align}\nx &= y \\label{eq:real}\\\\\n%z &= w \\label{eq:dead}\n\\end{align}\n"
    out, _, _ = make(text, numbers={"eq:real": AuxNumber("2.1", 1), "eq:dead": AuxNumber("9.9", 1)})
    assert "%" not in out and "\\end{align*}" in out
    assert 'data-label="eq:real" data-number="2.1"' in out and "eq:dead" not in out and "9.9" not in out

    inline, _, _ = make("Take $x % the good one\n+ y$ here.\n")
    assert re.search(r"\\\(x\s+\+ y\\\)", inline) and "the good one" not in inline


def test_qedhere_is_dropped_from_a_formula() -> None:
    """`\\qedhere` moves amsthm's tombstone into the last display; the viewer has no tombstone to move and the renderer has no such command, so the whole formula reached the page in error colour (seen on the 10/8 paper)."""
    out, _, _ = make("\\[ a = b. \\qedhere \\]\n")
    assert "qedhere" not in out and "a = b." in out
