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


def test_the_structure_tex4ht_made_is_kept_in_the_dialect_s_names() -> None:
    n = normalise(PAGE)
    h = n.html
    assert "<title" not in h and "alert" not in h and "p{}" not in h
    assert '<h3 data-at=":0"><span class="number" data-made="">1   </span> One</h3>' in h
    assert (
        '<p data-at=":17">Plain <strong>bold</strong> <em>it</em> <code>tt</code> <span class="smallcaps">S<span class="smallcaps">mall</span></span> <span class="math inline">\\(x^2 &lt; y\\)</span>.'
        in h
    )
    assert not re.search(r"<p[^>]*>\s*</p>", h)  # an empty paragraph is no block
    assert '<div class="node" data-env="lemma" data-file="parts/a.tex" data-line="3">' in h and n.nodes == 1
    assert (
        '<p data-at="parts/a.tex:3"><span class="head" data-made=""><strong>Lemma 1.1.</strong></span> See <a class="ref" data-label="eq:a" data-made="">(2)</a>.</p>'
        in h
    )
    assert '<div class="math display" data-at="parts/a.tex:3">\\begin{align}a&amp;=b\\end{align}</div>' in h
    assert '<dt data-made="">(i)</dt><dd data-at="parts/a.tex:3">first</dd>' in h
    assert '<tr class="rule">' in h and '<td data-align="right" data-at="parts/a.tex:3">r</td>' in h
    assert '<a class="url" href="https://example.com">out</a> in' in h
    # where an included file ends, the reader is back in the file that input it, at the place it had reached
    assert '<p data-at=":19">Back home.</p>' in h
