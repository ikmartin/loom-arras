import pytest

from loom.render.marks import MarkEntry, place_marks


def test_marks_placed_inline_and_block_level() -> None:
    html = '<div class="env" data-src="f.tex:0:200"><p class="env-label">Lemma</p><p data-src="f.tex:20:80">The inclusion is <em>open</em> by rigidity.</p><p data-src="f.tex:90:150">Second paragraph here.</p></div>'
    out = place_marks(
        html,
        [
            MarkEntry("a-1", "rigidity", "f.tex", 60, 68),
            MarkEntry("a-2", "inclusion is open", "f.tex", 24, 41),
            MarkEntry("a-3", "Second paragraph", "f.tex", 90, 106),
        ],
    )
    assert '<mark class="annotation" data-annotation="a-1">rigidity</mark>' in out
    assert '<mark class="annotation" data-annotation="a-3">Second paragraph</mark>' in out
    assert (
        '<mark class="annotation" data-annotation="a-2">inclusion is <em>open</em></mark>' in out
    )  # crosses <em>, whole
    assert out.count("<mark") == 3 and "annotation-block" not in out


def test_two_comments_on_the_same_words_are_one_mark() -> None:
    """Two annotations quoting the same phrase become one `mark` carrying both ids; two edits over one range were applied one inside the other and emitted the opening tag as body text."""
    html = '<p data-src="f.tex:0:60">Let X be a finite widget. Then the count is even.</p>'
    out = place_marks(
        html,
        [
            MarkEntry("a-1", "finite widget", "f.tex", 11, 24),
            MarkEntry("a-2", "finite widget", "f.tex", 11, 24),
        ],
    )
    assert out.count("<mark") == 1
    assert '<mark class="annotation" data-annotation="a-1 a-2">finite widget</mark>' in out
    assert 'annotation" data-annotation' not in out.replace('class="annotation" data-annotation', "")


def test_overlapping_quotes_join_one_mark() -> None:
    """A quote that overlaps another without matching it joins the earlier one's mark rather than cutting it in half."""
    html = '<p data-src="f.tex:0:60">Let X be a finite widget. Then the count is even.</p>'
    out = place_marks(
        html,
        [
            MarkEntry("a-1", "finite widget", "f.tex", 11, 24),
            MarkEntry("a-2", "a finite", "f.tex", 9, 17),
        ],
    )
    assert out.count("<mark") == 1
    assert 'data-annotation="a-2 a-1">a finite</mark>' in out  # the span that starts first is the one drawn


def test_a_quote_around_math_takes_the_formula_whole() -> None:
    """The quote is TeX and the block carries `\\(c\\)`; the mark wraps the whole formula, so MathJax still finds both delimiters in one text node."""
    html = '<p data-src="f.tex:0:90">the graph has <span class="math inline">\\(c\\)</span> connected components.</p>'
    out = place_marks(html, [MarkEntry("a-1", "graph has $c$ connected", "f.tex", 4, 27)])
    assert (
        '<mark class="annotation" data-annotation="a-1">graph has <span class="math inline">\\(c\\)</span> connected</mark>'
        in out
    )


def test_a_quote_inside_a_formula_never_puts_a_tag_inside_it() -> None:
    """Words that exist only inside a formula mark the formula whole; a quote inside a displayed formula marks the display as a block."""
    inline = '<p data-src="f.tex:0:40">Let <span class="math inline">\\(x+c\\)</span> be given.</p>'
    out = place_marks(inline, [MarkEntry("a-1", "c", "f.tex", 7, 8)])
    assert '<mark class="annotation" data-annotation="a-1"><span class="math inline">\\(x+c\\)</span></mark>' in out
    display = '<div class="math display" data-src="f.tex:0:40">\\[\\tag{3} a = b + c\\]</div>'
    out = place_marks(display, [MarkEntry("a-2", "b + c", "f.tex", 10, 15)])
    assert "<mark" not in out and 'class="math display annotation-block"' in out


def test_a_quote_across_a_reference_and_a_formula_is_marked_where_it_is() -> None:
    """A quote copied from the source names a reference as `\\ref{..}`, which the page draws as its number; read as the command it carries, the reference no longer stops the quote being found, and the mark stays on the phrase rather than falling back to the whole list (a draft4-ai.tex remark, 2026-09-28)."""
    html = (
        '<ol data-src="f.tex:0:300"><li>by Proposition <a class="ref" data-target="zk-0020" data-tex="\\ref{lem:nice}" data-at="40" href="#zk-0020">2.7</a> '
        '<span class="math inline">\\(\\eta:Y^T\\to Y\\)</span> is representable, and more.</li></ol>'
    )
    out = place_marks(
        html,
        [MarkEntry("a-1", "by Proposition \\ref{lem:nice} \\(\\eta:Y^T\\to Y\\) is representable", "f.tex", 10, 120)],
    )
    assert "annotation-block" not in out
    assert out.count('<mark class="annotation" data-annotation="a-1">') == 1
    assert '>by Proposition <a class="ref"' in out and "is representable</mark>" in out


#: The converter's own output for `As shown in (\S~\ref{sec:x}) the results follow -- mostly, ``quoted'' and a\,b.`: § and nbsp, an en dash, curly quotes, a thin space.
PRINTED = (
    '<p data-src="f.tex:0:79">As shown in (§ <a class="ref ref-dangling" data-target="sec:x" data-tex="\\ref{sec:x}" data-at="16">??</a>)'
    " the results follow – mostly, “quoted” and a b.</p>"
)


@pytest.mark.parametrize(
    ("quote", "marked"),
    [
        ("(\\S~\\ref{sec:x})", '(§ <a class="ref'),
        ("follow -- mostly", "follow – mostly"),
        ("``quoted''", "“quoted”"),
        ("a\\,b", "a b"),
    ],
)
def test_a_quote_copied_from_the_source_is_marked_as_the_page_prints_it(quote: str, marked: str) -> None:
    """`annotate` reads a quote as the page prints it (book 7.4.3), so the mark does too: a symbol, a tie, a dash, TeX quotes and a thin space were each found by the one and missed by the other, and the quote marked its whole paragraph (the anchoring critique, 2026-10-03)."""
    out = place_marks(PRINTED, [MarkEntry("a-1", quote, "f.tex", 12, 30)])
    assert "annotation-block" not in out
    assert f'<mark class="annotation" data-annotation="a-1">{marked}' in out


def test_a_quote_that_opens_with_a_layout_command_is_marked_inside_its_paragraph() -> None:
    """`\\noindent` prints nothing; the paragraph's source starts at it, so the quote's span lies in the paragraph and the mark takes the words after it, never the whole section."""
    html = '<section data-src="f.tex:0:200"><p data-src="f.tex:50:86"><strong>Problem 1:</strong> decide.</p></section>'
    out = place_marks(html, [MarkEntry("a-1", "\\noindent\\textbf{Problem 1:}", "f.tex", 50, 78)])
    assert "annotation-block" not in out
    assert '<strong><mark class="annotation" data-annotation="a-1">Problem 1:</mark></strong>' in out


def test_a_formula_is_read_as_the_quote_is() -> None:
    """The formula's TeX and the quote are read by one function, so a prime the prose would print as ’ still matches inside a formula, and so does a quote that starts in the middle of one."""
    html = '<p data-src="f.tex:0:40">so <span class="math inline">\\(f\'(x)\\)</span> is big</p>'
    whole = '<mark class="annotation" data-annotation="a-1"><span class="math inline">\\(f\'(x)\\)</span> is</mark>'
    assert whole in place_marks(html, [MarkEntry("a-1", "$f'(x)$ is", "f.tex", 3, 15)])
    assert whole in place_marks(html, [MarkEntry("a-1", "f'(x)\\) is", "f.tex", 5, 15)])
