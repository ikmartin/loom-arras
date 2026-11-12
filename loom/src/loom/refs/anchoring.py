"""From a place on a page to the anchor loom records (plan 0.13 item 2).

One function, called by everything that turns a selection or a drawn rectangle into an anchor: the `locate` endpoint, which answers and writes nothing; `loom annotate` on a page of a cited work; and the same write over the API. **They cannot disagree, because they do not each map.** The client's text layer is a third extraction of the page, after the committed page text and the word boxes; only loom holds the other two, and only loom can say what the committed text says, which is what an anchor is checked against.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loom.anchors import Anchor
from loom.records.selectors import CONTEXT, Selector


@dataclass
class Placed:
    """What mapping a place gives back: the anchor of record, the text triple beside it, and the words a person reads."""

    anchor: Anchor
    selector: Selector
    #: Whether the text asked for was found on the page at all. A box is always "found": what was drawn is the record.
    found: bool
    #: The page's width and height in points, for a caller drawing against it.
    page_box: tuple[float, float] | None
    #: `text` or `box`: the one word that says which description is of record.
    said: str
    #: A box's top left less its pin word's (`records.marks.context_at`), by which a changed copy of the work places it again; None for text, or a page with no words.
    gap: list[float] | None = None


def anchor_on_page(
    home: Path,
    page: int,
    text: str | None = None,
    rects: list[list[float]] | None = None,
    span: tuple[int, int] | None = None,
) -> Placed:
    """Map a selection or a drawn rectangle on one page of a stored work to the anchor loom would record.

    Parameters
    ----------
    home : Path
        The work's directory in the store, holding `paper.pdf`, `sections.json` and `pages/`.
    page : int
        The page, from 1.
    text : str, optional
        What was selected. Matched against the word boxes with the tolerance `library locate` has for hyphenation and ligatures, and then located in the committed page text for offsets.
    rects : list of [x0, y0, x1, y1], optional
        What was drawn, in points with the origin at the top left, when there was no text worth selecting.
    span : (start, end), optional
        Offsets into the page's committed text, as a `span=` locator carries them; the text between them is what is mapped, so a link written by offsets lights the same place a selection would.

    Returns
    -------
    Placed
        Basis `text` when the selection located in the committed page text, with `start`/`end` and derived quads; basis `box` otherwise, carrying the rectangles as the record and whatever words they cover as the triple's `exact`. Recording never fails: a selection found on the boxes but not in the committed text is a box, and a rectangle is a box.

    Notes
    -----
    The caller has already checked the work is readable (`read_map` and `paper.pdf`); this raises nothing of its own beyond what `token_boxes` raises for a missing poppler.
    """
    from loom.refs.pages import page_box, read_map, read_page, token_boxes
    from loom.refs.search import locate_offsets, locate_span

    m = read_map(home)
    xml = token_boxes(home / "paper.pdf", page, home)
    page_text = read_page(home, page) or ""
    if span and not text:
        a, b = max(0, span[0]), min(len(page_text), span[1])
        text = page_text[a:b].strip() or None
    anchor = Anchor(kind="pdf", sha256=m.sha256 if m else "", page=page)
    rects = [[float(v) for v in r] for r in rects or []]
    hit = locate_span(xml, text, page) if text else None
    found = hit is not None or bool(rects)
    if hit is not None:
        offsets = locate_offsets(page_text, text or "")
        anchor.quads = [list(q) for q in hit.lines]
        if offsets:
            a, b = offsets
            anchor.basis, anchor.start, anchor.end = "text", a, b
            selector = Selector(page_text[a:b], page_text[max(0, a - CONTEXT) : a], page_text[b : b + CONTEXT])
        else:
            # found on the page's boxes and not in its committed text: geometry is what can honestly be recorded
            anchor.basis = "box"
            selector = Selector(text or "")
    else:
        # a formula, a figure, a scan: what the reader drew is the record, and the words under and around it are how a changed copy finds it again
        anchor.basis, anchor.quads = "box", rects
        selector, gap = _around(home, page, rects)
        if not selector.exact and text:
            # a box on no words, given the words it means: they are its quote, and nothing pins it
            selector, gap = Selector(text, selector.prefix, selector.suffix), None
        return Placed(anchor, selector, found, page_box(xml), anchor.basis, gap)
    return Placed(anchor, selector, found, page_box(xml), anchor.basis)


def _around(home: Path, page: int, rects: list[list[float]]) -> tuple[Selector, list[float] | None]:
    """The words under and around a box on a stored work's page, and its gap from them, from the work's words cached in the store (`records.marks.context_at`); nothing when the box is drawn on nothing or pdftotext cannot read the file."""
    from loom.records.marks import DocumentWords, context_at
    from loom.refs.pages import MapRefused, document_boxes, store_boxes

    if not rects:
        return Selector(""), None
    try:
        return context_at(DocumentWords(document_boxes(home / "paper.pdf", store_boxes(home))), page, rects)
    except MapRefused:
        return Selector(""), None
