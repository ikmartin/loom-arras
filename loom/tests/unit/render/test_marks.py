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
    assert 'data-annotation="a-2"' in out and "annotation-block" in out  # crosses <em>
    assert out.count("<mark") == 2


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
