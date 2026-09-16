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
