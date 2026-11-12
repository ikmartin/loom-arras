"""The version an annotation was written on, for one whose quoted words are gone: its fragment, made with the build's previews and marking every annotation quoted from it, and the empty mark where its words were in the text now."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from loom.render.marks import MarkEntry, place_marks
from loom.render.versions import aligned
from tests.helpers import edit, ok
from tests.unit._quilts import demo

LEMMA = "drafting/nodes/dm-0002.tex"
WHO = ("--as", "A. Author")


def annotate(q: Path, quote: str, body: str = "Which points?") -> str:
    return ok("annotate", "dm-0002", body, "--quote", quote, "--type", "note", *WHO, cwd=q).output.split()[0]


def built(q: Path) -> dict[str, Any]:
    ok("build", cwd=q)
    return json.loads((q / ".loom/build/manifest.json").read_text())  # type: ignore[no-any-return]


def fragment(q: Path, m: dict[str, Any], key: str) -> str:
    """A node's fragment, or a document's by its path."""
    entry = m["nodes"].get(key) or next(d for d in m["masters"] if d["path"] == key)
    return (q / ".loom/build" / entry["fragment"]).read_text()


def gone(ann: str) -> str:
    return f'<mark class="annotation gone" data-annotation="{ann}"></mark>'


def test_an_annotation_whose_words_were_edited_carries_its_version(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ann = annotate(q, "one or two points")
    edit(q / LEMMA, "one or two points", "at most two elements")
    m = built(q)
    row = m["annotations"][ann]
    assert row["detached"] and row["recorded"]
    version = row["version"]
    digest = row["target"]["hash"]
    assert version == {
        "hash": digest,
        "fragment": f"fragments/versions/{digest.split(':')[-1][:16]}.html",
        "at": True,
    }
    old = (q / ".loom/build" / version["fragment"]).read_text()
    assert f'<mark class="annotation" data-annotation="{ann}">one or two points</mark>' in old
    assert "at most two elements" not in old
    # where its words were, in the node's fragment and in the document's
    for key in ("dm-0002", "drafting/main.tex"):
        assert gone(ann) + "at most two elements" in flat(fragment(q, m, key)), key


def test_an_annotation_whose_words_stand_has_no_version(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ann = annotate(q, "one or two points")
    edit(q / LEMMA, "Every orbit", "Each orbit")
    m = built(q)
    assert m["annotations"][ann]["version"] is None
    assert "annotation gone" not in fragment(q, m, "dm-0002")


def test_two_annotations_on_one_version_share_its_fragment(tmp_path: Path) -> None:
    q = demo(tmp_path)
    first = annotate(q, "one or two points")
    second = annotate(q, "the one-point orbits", "Name them.")
    edit(q / LEMMA, "one or two points", "at most two elements")
    edit(q / LEMMA, "the one-point orbits", "the orbits of size one")
    m = built(q)
    one, two = m["annotations"][first]["version"], m["annotations"][second]["version"]
    assert one == two
    assert [p.name for p in (q / ".loom/build/fragments/versions").iterdir()] == [Path(one["fragment"]).name]
    old = (q / ".loom/build" / one["fragment"]).read_text()
    assert f'data-annotation="{first}"' in old and f'data-annotation="{second}"' in old
    html = flat(fragment(q, m, "dm-0002"))
    assert gone(first) + "at most two elements" in html
    assert gone(second) + "the orbits of size one" in html


def test_a_cut_marks_the_word_after_it(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ann = annotate(q, "of a widget ")
    edit(q / LEMMA, "of a widget ", "")
    m = built(q)
    assert m["annotations"][ann]["version"]["at"] is True
    assert re.search(r"Every orbit\s*" + re.escape(gone(ann)) + r"\s*has", fragment(q, m, "dm-0002"))


def flat(html: str) -> str:
    return re.sub(r"\s+", " ", html)


@pytest.mark.parametrize(
    ("old", "new", "at", "want"),
    [
        ("a b c d", "a x c d", 2, 2),  # replaced: what replaced it
        ("a b c d", "a c d", 2, 2),  # cut: the word after it
        ("a b c d", "z a b c d", 4, 6),  # kept: the same word
        ("a b c", "a b", 4, 3),  # cut at the end: after the last word
    ],
)
def test_aligned_places_a_word_in_the_new_text(old: str, new: str, at: int, want: int) -> None:
    assert aligned(old, new, at) == want


def test_aligned_says_nothing_when_no_word_aligns() -> None:
    assert aligned("one two three", "four five six", 4) is None


def test_a_gone_mark_stands_beside_its_words_and_never_inside_a_mark() -> None:
    html = '<p data-src="f.tex:0:40">Every orbit has two elements here.</p>'
    after = MarkEntry("x", "Every orbit has", "f.tex", 16, 16, gone=True)
    before = MarkEntry("y", "two elements", "f.tex", 16, 16, gone=True, lead=True)
    around = MarkEntry("z", "orbit has two", "f.tex", 6, 19)
    got = place_marks(html, [after, before, around])
    assert got == (
        '<p data-src="f.tex:0:40">Every <mark class="annotation" data-annotation="z">orbit has two</mark>'
        f"{gone('x')}{gone('y')} elements here.</p>"  # two at one place in the order given
    )


def test_a_gone_mark_in_source_stands_at_its_offset_and_before_a_display() -> None:
    source = '<pre class="source" data-src="f.tex:10:20">abc &amp; def</pre>'
    got = place_marks(source, [MarkEntry("x", "", "f.tex", 14, 14, gone=True)])
    assert got == f'<pre class="source" data-src="f.tex:10:20">abc {gone("x")}&amp; def</pre>'
    display = '<div class="math display" data-src="f.tex:0:9">\\[x^2\\]</div>'
    got = place_marks(display, [MarkEntry("y", "x", "f.tex", 3, 3, gone=True)])
    assert got == gone("y") + display


@pytest.mark.tex
def test_a_version_is_made_by_tex_and_its_place_kept_in_the_page_tex_made(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ann = annotate(q, "one or two points")
    edit(q / LEMMA, "one or two points", "at most two elements")
    ok("compile", "--html", cwd=q)
    m = built(q)
    version = m["annotations"][ann]["version"]
    old = (q / ".loom/build" / version["fragment"]).read_text()
    assert '<pre class="source"' not in old and "env-lemma" in old
    assert f'<mark class="annotation" data-annotation="{ann}">one or two points</mark>' in old
    for key in ("dm-0002", "drafting/main.tex"):
        html = fragment(q, m, key)
        assert '<pre class="source"' not in html, key
        assert re.search(r"has\s*" + re.escape(gone(ann)) + r"\s*at most two elements", html), key
