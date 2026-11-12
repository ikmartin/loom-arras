"""TeX4ht's page rebuilt as fragment markup (plan 0.29.2): what a document can author never reaches the page as written, and what loom needs to place each block is kept."""

from __future__ import annotations

import re

from loom.render.normalise import normalise

PAGE = """<html><head><title>x</title><style>p{}</style><script>alert(1)</script></head><body>
<h3 class='sectionHead'><span class='titlemark'>1   </span> <a id='x1-10001'></a>One</h3>
<!-- l. 17 --><p class='noindent'>Plain <span class='cmbx-10'>bold</span> <span class='cmti-10'>it</span> <span class='cmtt-10'>tt</span> <span class='cmcsc-10'>S<span class='small-caps'>mall</span></span> \\(x^2 &lt; y\\).
</p><!-- l. 19 --><p class='indent'>   </p>
<!--loom-file parts/a.tex-->
<div class='loom-node' data-env='lemma' data-file='parts/a.tex' data-line='3'>
<div class='newtheorem'><!-- l. 3 --><p class='noindent'><span class='head'><a id='x1-1001r1'></a><span class='cmbx-10'>Lemma 1.1.</span></span> See <span class='loom-ref' data-label='eq:a'>(2)</span>.</p></div></div>
<div class='mathjax-env mathjax-align'>\\begin{align}a&amp;=b\\end{align}</div>
<dl class='enumerate-enumitem'><dt class='enumerate-enumitem'>(i)</dt><dd class='enumerate-enumitem'>first</dd></dl>
<table class='tabular'><tr class='hline'><td></td></tr><tr><td class='td11' style='white-space:nowrap; text-align:right;'>r</td></tr></table>
<a href='https://example.com'>out</a> <a href='#x1-10001'>in</a>
<!--loom-file-end--><p>Back home.</p>
</body></html>"""

HOSTILE = """<html><body><!-- l. 4 --><p>Before <script>window.loomHostile = 1</script><img src='x.png' onerror='window.loomHostile = 2'>
<a href='javascript:alert(3)' onclick='alert(4)'>click</a> <iframe src='https://evil.example'></iframe><svg onload='alert(5)'><circle/></svg>
<span style='position:fixed' class='loom-node'>dressed</span> <img src='../../etc/passwd'> <img src='https://evil.example/t.png'>
<div class='loom-node' data-env='lemma"><script>' data-line='1" onclick="x'>quoted</div> after.</p></body></html>"""


def test_a_document_s_own_html_is_rebuilt_and_nothing_it_wrote_runs() -> None:
    n = normalise(HOSTILE)
    for gone in (
        "<script",
        "onerror",
        "onclick",
        "javascript:",
        "<iframe",
        "<svg",
        "onload",
        "style=",
        "passwd",
        "evil.example",
        "loomHostile",
    ):
        assert gone not in n.html, (gone, n.html)
    assert "Before" in n.html and "click" in n.html and "dressed" in n.html and "after." in n.html
    assert '<img src="x.png" alt="">' in n.html
    # a stamp is kept only in the shape loom's configuration writes it, and every value is escaped besides
    assert '<div class="node" data-env="" data-file="" data-line="">quoted</div>' in n.html
    assert {"script", "iframe", "svg"} <= set(n.dropped)


def test_the_space_tex4ht_writes_inside_a_formula_stands_after_it() -> None:
    n = normalise(
        "<html><body><!-- l. 2 --><p>Let <span class='mathjax-inline'>\\(Y^T\\) </span><span class='ecti-10'>be</span> as.</p></body></html>"
    )
    assert '<span class="math inline">\\(Y^T\\)</span> <span data-font="it">be</span>' in n.html


def test_the_structure_tex4ht_made_is_kept_in_the_dialect_s_names() -> None:
    n = normalise(PAGE)
    h = n.html
    assert "<title" not in h and "alert" not in h and "p{}" not in h
    assert '<h3 data-head="sectionHead" data-at=":0"><span class="number" data-made="">1   </span> One</h3>' in h
    assert (
        '<p class="noindent" data-at=":17">Plain <strong>bold</strong> <span data-font="it">it</span> <code>tt</code> <span class="smallcaps">S<span class="smallcaps">mall</span></span> <span class="math inline">\\(x^2 &lt; y\\)</span>.'
        in h
    )
    assert not re.search(r"<p[^>]*>\s*</p>", h)  # an empty paragraph is no block
    assert '<div class="node" data-env="lemma" data-file="parts/a.tex" data-line="3">' in h and n.nodes == 1
    assert (
        '<p class="noindent" data-at="parts/a.tex:3"><span class="head" data-made=""><strong>Lemma 1.1.</strong></span> See <a class="ref" data-label="eq:a" data-made="">(2)</a>.</p>'
        in h
    )
    assert '<div class="math display" data-at="parts/a.tex:3">\\begin{align}a&amp;=b\\end{align}</div>' in h
    assert '<dt data-made="">(i)</dt><dd data-at="parts/a.tex:3">first</dd>' in h
    assert '<tr class="rule">' in h and '<td data-align="right" data-at="parts/a.tex:3">r</td>' in h
    assert '<a class="url" href="https://example.com">out</a> in' in h
    # where an included file ends, the reader is back in the file that input it, at the place it had reached
    assert '<p data-at=":19">Back home.</p>' in h


#: A display as TeX Live 2024's TeX4ht writes it, between paragraphs, and as TeX Live 2026's does, inside its paragraph.
BETWEEN = """<html><body><!-- l. 7 --><p class='noindent'>A display </p><div class='mathjax-block'>\\[x^2\\]</div><p> and </p><div class='mathjax-env mathjax-equation'>\\begin{equation}\\label {e1} y = 1 \\end{equation}</div><p> after.</p></body></html>"""
INSIDE = """<html><body><!-- l. 7 --><p class='noindent'>A display <span class='mathjax-block'>\\[x^2\\]</span> and <span class='mathjax-env mathjax-equation'>\\begin{equation}\\label {e1} y = 1 \\end{equation}</span> after.</p></body></html>"""


def test_a_display_inside_its_paragraph_is_read_as_one_between_paragraphs() -> None:
    """TeX4ht since TeX Live 2026 writes a display as a `span` inside the paragraph it stands in: it is read as the display it is, the paragraph closed before it and begun again after, which is the page an earlier TeX4ht writes."""
    inside = normalise(INSIDE).html
    assert inside == normalise(BETWEEN).html
    assert '<div class="math display" data-at=":7">\\begin{equation}\\label {e1} y = 1 \\end{equation}</div>' in inside
    assert inside.count("<p") == 3 and "\\[" not in re.sub(r"<div class=\"math display\"[^>]*>[^<]*</div>", "", inside)


def test_a_paragraph_left_open_at_a_snippet_mark_is_closed_there() -> None:
    """A text ending in a display leaves its paragraph open past the next text's mark, closed only at the page's end (TeX Live 2026): it is closed at the mark, so the text stands whole between its marks, and its late `</p>` closes nothing else."""
    page = """<html><body><!-- loomsnippet 0 --><p> A diagram: <span class='mathjax-block'>\\[\\begin {tikzcd} A \\end {tikzcd}\\]</span>
<!-- loomsnippet 1 --><div class='loom-node' data-env='lemma' data-file='' data-line='3'><p>Kept.</p></p></div>
<!-- loomsnippet end --></body></html>"""
    html = normalise(page).html
    marks = [m.start() for m in re.finditer(r'<span class="loom-snippet"', html)]
    first = html[marks[0] : marks[1]]
    # balanced, and the paragraph begun again after the display, empty, gone as every empty paragraph is
    assert first.count("<p") == first.count("</p>") == 1 and first.endswith(
        '<div class="math display" data-at=":0">\\[\\begin {tikzcd} A \\end {tikzcd}\\]</div>'
    )
    assert re.search(r'<div class="node"[^>]*>\s*<p[^>]*>Kept\.</p>\s*</div>', html[marks[1] : marks[2]])


def test_texts_tex4ht_set_in_no_paragraph_are_each_given_one() -> None:
    """TeX Live 2026's TeX4ht opens no paragraph for a text of a run that follows another text's paragraph, and closes that one only after the run: each text is given a paragraph of its own, closed at the next mark."""
    page = """<html><body><!-- loomsnippet 36 --><p> By Lemma <span class='loom-ref' data-label='sy-0002'>1.2</span>, two.
<!-- loomsnippet 37 --> Kreschmer, Cycle groups, 1999
<!-- loomsnippet 38 --> any standard text
<!-- loomsnippet 39 --> </p><div class='loom-node' data-env='lemma' data-file='' data-line='3'><p>Kept.</p></div>
<!-- loomsnippet end --></body></html>"""
    html = normalise(page).html
    texts = re.split(r'<span class="loom-snippet" data-snippet="[^"]+"></span>', html)[1:]
    assert re.fullmatch(r'\s*<p data-at="[^"]*"> Kreschmer, Cycle groups, 1999\s*</p>\s*', texts[1])
    assert re.fullmatch(r'\s*<p data-at="[^"]*"> any standard text\s*</p>\s*', texts[2])
    assert re.search(r'<div class="node"[^>]*><p[^>]*>Kept\.</p></div>', texts[3])
    assert all(t.count("<p") == t.count("</p>") for t in texts)


def test_the_words_after_a_proof_s_last_display_stand_in_a_paragraph() -> None:
    """TeX4ht leaves the words after a display that ends a proof in the proof itself, outside any paragraph; they are given one, which ends with the proof."""
    page = """<html><body><div class='proof'><!-- l. 5 --><p class='indent'>Because </p><div class='mathjax-env mathjax-equation'>\\begin{equation} x \\end{equation}</div>by (1). <span class='qed'>&#x25A1;</span></div><p>After.</p></body></html>"""
    html = normalise(page).html
    assert '</div><p data-at=":5">by (1). □</p></div><p data-at=":5">After.</p>' in html, html


def test_a_title_is_a_second_level_heading_whichever_tex4ht_set_it_as() -> None:
    for level in ("h1", "h2"):
        html = normalise(f"<html><body><{level} class='titleHead'>A Title</{level}></body></html>").html
        assert html.startswith('<h2 data-head="titleHead"'), html


def test_a_bibliography_is_a_paragraph_to_an_entry_whichever_way_tex4ht_set_it() -> None:
    """TeX4ht before TeX Live 2026 sets each entry as a paragraph, its label first; TeX Live 2026's sets the bibliography as a list of labels and entries. Both read as a paragraph to an entry."""
    before = """<html><body><div class='thebibliography'><p class='bibitem'><span class='biblabel'><span class='cmr-8'>1. </span><span class='bibsp'>   </span></span><a id='XHar77'></a><span class='cmr-8'>Robin Hartshorne, </span><span class='cmti-8'>Algebraic geometry</span><span class='cmr-8'>, 1977.</span></p><p class='bibitem'><span class='biblabel'><span class='cmr-8'>2. </span></span><span class='cmr-8'>Andrew Kresch.</span></p></div></body></html>"""
    after = """<html><body><dl class='thebibliography'><dt id='X0-Har77' class='thebibliography'><span class='cmr-8'>1.</span></dt><dd id='bib-1' class='thebibliography'><a id='XHar77'></a><span class='cmr-8'>Robin Hartshorne, </span><span class='cmti-8'>Algebraic geometry</span><span class='cmr-8'>, 1977.</span></dd><dt id='X0-Kre99' class='thebibliography'><span class='cmr-8'>2.</span></dt><dd id='bib-2' class='thebibliography'><span class='cmr-8'>Andrew Kresch.</span></dd></dl></body></html>"""

    def entries(page: str) -> list[str]:
        html = normalise(page).html
        assert "<dl" not in html and "<dt" not in html and "<dd" not in html, html
        # whitespace aside, which TeX4ht writes differently from one TeX Live to the next
        return [re.sub(r"\s+", "", p) for p in re.findall(r"<p[^>]*>(.*?)</p>", html, re.S)]

    assert entries(after) == entries(before)
    assert [re.sub(r"<[^>]+>", "", e) for e in entries(after)] == [
        "1.RobinHartshorne,Algebraicgeometry,1977.",
        "2.AndrewKresch.",
    ]
