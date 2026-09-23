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
    assert '<mark class="annotation" data-annotation="a-2">inclusion is <em>open</em></mark>' in out  # crosses <em>, whole
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
    assert '<mark class="annotation" data-annotation="a-1">graph has <span class="math inline">\\(c\\)</span> connected</mark>' in out


def test_a_quote_inside_a_formula_never_puts_a_tag_inside_it() -> None:
    """Words that exist only inside a formula mark the formula whole; a quote inside a displayed formula marks the display as a block."""
    inline = '<p data-src="f.tex:0:40">Let <span class="math inline">\\(x+c\\)</span> be given.</p>'
    out = place_marks(inline, [MarkEntry("a-1", "c", "f.tex", 7, 8)])
    assert '<mark class="annotation" data-annotation="a-1"><span class="math inline">\\(x+c\\)</span></mark>' in out
    display = '<div class="math display" data-src="f.tex:0:40">\\[\\tag{3} a = b + c\\]</div>'
    out = place_marks(display, [MarkEntry("a-2", "b + c", "f.tex", 10, 15)])
    assert "<mark" not in out and 'class="math display annotation-block"' in out
