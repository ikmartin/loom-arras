"""The fallback renderer's pure functions (book 9.4.2): id namespacing, sizing in em, and the prolog strip. Compiling a block is the TeX tier's (tests/tex/test_fallback_preamble.py)."""

from __future__ import annotations

from loom.render.fallback import _strip_prolog, namespace_ids, resize_svg

SVG = (
    "<svg width='20pt' height='10pt' viewBox='0 0 20 10'><defs><path id='g0-1'/><path id=\"g0-12\"/></defs>"
    "<use xlink:href='#g0-1'/><use xlink:href='#g0-12'/><use href=\"#g0-1\"/></svg>"
)


def test_namespacing_rewrites_every_id_and_reference_once_and_no_prefix_of_another() -> None:
    """Several SVGs share one page, so each glyph id takes the block's prefix; `g0-1` must not rewrite inside `g0-12`, nor be prefixed twice."""
    out = namespace_ids(SVG, "k1-")
    assert "id='k1-g0-1'" in out and 'id="k1-g0-12"' in out
    assert out.count("#k1-g0-1'") == 1 and out.count('#k1-g0-1"') == 1 and out.count("#k1-g0-12'") == 1
    assert "k1-k1-" not in out and "#g0-" not in out and "id='g0-" not in out
    assert namespace_ids("<svg><g/></svg>", "k1-") == "<svg><g/></svg>"


def test_resizing_states_the_width_in_em_and_drops_the_height() -> None:
    """The viewer scales the SVG with the text: width in em against a 10 pt base, height left to the viewBox."""
    out = resize_svg(SVG)
    assert out.startswith("<svg viewBox='0 0 20 10' width='2.0000em'>"), out
    assert "height=" not in out.split(">", 1)[0]
    assert resize_svg(SVG, base_pt=8.0).startswith("<svg viewBox='0 0 20 10' width='2.5000em'>")
    assert resize_svg("<svg viewBox='0 0 1 1'/>") == "<svg viewBox='0 0 1 1'/>"  # nothing to convert
    assert resize_svg("no svg here") == "no svg here"


def test_the_prolog_and_comments_are_stripped_before_the_svg_is_inlined() -> None:
    assert _strip_prolog("<?xml version='1.0'?>\n<!-- dvisvgm\n two lines -->\n<svg/>\n") == "<svg/>"
    assert _strip_prolog("<svg><!-- inner --><g/></svg>") == "<svg><g/></svg>"
