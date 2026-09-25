"""`render_markdown`: an annotation's or a report's Markdown as HTML, with its TeX lifted out before Commonmark sees it (plan 0.11 Part A)."""

from __future__ import annotations

from loom.records.store import render_markdown


def test_math_survives_markdown() -> None:
    """Commonmark has no math: `$a_i b_i$` loses both subscripts to emphasis unless the TeX is lifted out first."""
    out = render_markdown("The bound $O(n^2)$ is sharp for $a_i b_i$ when *this* holds.")
    assert '<span class="math inline">\\(O(n^2)\\)</span>' in out
    assert '<span class="math inline">\\(a_i b_i\\)</span>' in out  # not <em>i b</em>
    assert "<em>this</em>" in out  # emphasis outside the math still works


def test_math_is_escaped_for_html() -> None:
    out = render_markdown("Compare $x < y$ and $a \\& b$.")
    assert "&lt;" in out and "&amp;" in out


def test_display_math_is_a_block_not_a_div_inside_a_paragraph() -> None:
    """A sentence, a newline, `$$…$$`, a newline and another sentence is how an annotation is written; an equation inside the paragraph's `<p>` is not HTML, and a browser fixes it by closing the paragraph early."""
    out = render_markdown("The bound $n \\le 2$ needs it, and then\n$$\\int_0^1 f$$\nfollows.")
    assert out.count("<p>") == out.count("</p>") == 2
    before, after = out.split('<div class="math display">\\[\\int_0^1 f\\]</div>')
    assert before.rstrip().endswith("</p>")  # the paragraph is closed before the equation, not around it
    assert out.index('<span class="math inline">') < out.index('<div class="math display">')
    assert out.rstrip().endswith("<p>follows.</p>")
    # and a display set off by a blank line is the same block
    apart = render_markdown("Then:\n\n$$\\int_0^1 f = 1$$\n")
    assert '<div class="math display">\\[\\int_0^1 f = 1\\]</div>' in apart and "<p><div" not in apart


def test_code_is_quoted_as_written() -> None:
    """F11 of the 0.14 study: a quote of source in backticks had its `$…$` turned into `\\(…\\)`."""
    got = render_markdown("Quote: `Let $\\quiv$ be` and $x$.")
    assert "<code>Let $\\quiv$ be</code>" in got and '<span class="math inline">\\(x\\)</span>' in got
