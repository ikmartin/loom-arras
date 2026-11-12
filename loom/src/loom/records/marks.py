"""Annotations on a page of a PDF: a project file the viewer shows, or a cited work's copy on this machine.

An annotation on a PDF page names its `page` and stands at `rects` (`[x0, y0, x1, y1]` in points from the page's top left) or along `strokes` (`x, y, x, y…` per stroke). One drawn with a tool says so in `mark`: a pin, ink, words on the page, a box, an oval or an arrow; one on words has no `mark`, and its look's style says how it is drawn. It records the hash of the PDF it was written on (`artifact`), so a changed file is noticed (A3), and the words under and around it, with a drawing's gap from them (`context_at`), by which it is found again anywhere in a changed file (`refind`); one that cannot be is detached. `origin` says where one taken in from a PDF's own annotations came from.

A text or box annotation on a cited work's page is anchored through the work's store instead (`refs/anchoring.py`); this module serves the drawn ones there and every one on a project PDF.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loom.records.selectors import Selector

#: The drawing tools: how an annotation that is not on words is drawn on a PDF page.
MARKS = ("pin", "ink", "text", "box", "oval", "arrow")
#: The tools held by strokes rather than a rectangle.
STROKED = ("ink", "arrow")
#: The tools that say nothing without words of their own.
SAYING = ("pin", "text")
#: How a PDF's own annotation on words is drawn, which an annotation keeps as its look's style.
ON_WORDS = ("highlight", "underline", "strike")
#: The most points one annotation's strokes may hold; the manifest carries them.
MAX_POINTS = 20000
#: Each of the nine colours as red, green and blue, for matching a PDF annotation's own colour to the nearest.
RGB = {
    "grey": (128, 128, 128),
    "brown": (140, 90, 50),
    "red": (220, 50, 50),
    "orange": (240, 140, 40),
    "yellow": (250, 220, 60),
    "green": (70, 170, 80),
    "blue": (60, 120, 220),
    "purple": (140, 80, 190),
    "pink": (230, 100, 170),
}


class MarkRefused(Exception):
    """An annotation on a PDF page that cannot be written as given, and why; `code` is the write API's."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


#: A PDF's hash by its path, size and modification time: an annotation is written and published far more often than a file changes, and a book takes a moment to hash.
_HASHES: dict[tuple[str, int, int], str] = {}


def artifact_of(pdf: Path) -> str:
    """The hash of `pdf`, read once for each version of the file."""
    at = pdf.stat()
    key = (str(pdf), at.st_size, at.st_mtime_ns)
    if key not in _HASHES:
        _HASHES[key] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    return _HASHES[key]


def project_pdf(result: Any, target: str) -> str | None:
    """`target` as a project PDF's quilt-relative path when it names one the viewer shows; None for anything else."""
    from loom.files import Shown

    rel = target.strip().strip("/")
    if not rel.lower().endswith(".pdf") or not (result.quilt.root / rel).is_file():
        return None
    return rel if Shown.of(result.quilt).is_shown(rel) else None


def pdf_of(result: Any, target: str, work: str = "") -> Path | None:
    """The PDF an annotation's target is on: a project PDF by its path, or the copy on this machine of the cited work `work` (a citekey); None for anything else."""
    root: Path = result.quilt.root
    if target.lower().endswith(".pdf"):
        return root / target
    entry = result.bib.get(work) if work else None
    if entry is None:
        return None
    from loom.refs.fetch import work_dir

    paper: Path = work_dir(root, entry) / "paper.pdf"
    return paper if paper.is_file() else None


def lines_of(pdf: Path, page: int, words: str, home: Path | None = None) -> list[list[float]] | None:
    """Where `words` stand on a page, one rectangle per line; None where they are not there or the page cannot be read. With `home`, a stored work's directory, the page's word boxes are read from the store's cache (`token_boxes`)."""
    from loom.refs.pages import MapRefused, token_boxes
    from loom.refs.search import locate_span

    try:
        hit = locate_span(token_boxes(pdf, page, home), words, page)
    except MapRefused:
        return None
    return [[float(v) for v in q] for q in hit.lines] if hit else None


def _numbers(raw: Any, what: str) -> list[float]:
    """A list of finite numbers from a write, each to a hundredth of a point; MarkRefused for anything else."""
    if not isinstance(raw, list) or not all(isinstance(v, int | float) and not isinstance(v, bool) for v in raw):
        raise MarkRefused("bad-field", f"{what} is a list of numbers")
    if not all(v == v and abs(v) < 1e7 for v in raw):
        raise MarkRefused("bad-field", f"{what} is a list of numbers")
    return [round(float(v), 2) for v in raw]


def clean_rects(raw: Any) -> list[list[float]] | None:
    """Rectangles from a write, each `[x0, y0, x1, y1]` with its corners in order; None for none."""
    if not raw:
        return None
    if not isinstance(raw, list):
        raise MarkRefused("bad-field", "rects is a list of [x0, y0, x1, y1]")
    out = []
    for r in raw:
        v = _numbers(r, "a rectangle")
        if len(v) != 4:
            raise MarkRefused("bad-field", "a rectangle is [x0, y0, x1, y1]")
        out.append([min(v[0], v[2]), min(v[1], v[3]), max(v[0], v[2]), max(v[1], v[3])])
    return out


def clean_strokes(raw: Any) -> list[list[float]] | None:
    """Strokes from a write, each `x, y, x, y…` of at least two points and no more than `MAX_POINTS` in all; None for none."""
    if not raw:
        return None
    if not isinstance(raw, list):
        raise MarkRefused("bad-field", "strokes is a list of x, y, x, y…")
    out = [_numbers(s, "a stroke") for s in raw]
    if any(len(s) < 4 or len(s) % 2 for s in out):
        raise MarkRefused("bad-field", "a stroke holds an x and a y for at least two points")
    if sum(len(s) for s in out) / 2 > MAX_POINTS:
        raise MarkRefused("too-large", f"an annotation holds at most {MAX_POINTS} points")
    return out


def bounds(strokes: list[list[float]]) -> list[list[float]]:
    """The one rectangle round every stroke, which is where a stroked annotation is found and landed at."""
    xs = [v for s in strokes for v in s[0::2]]
    ys = [v for s in strokes for v in s[1::2]]
    return [[min(xs), min(ys), max(xs), max(ys)]]


def placed(
    pdf: Path,
    page: int | None,
    mark: str | None,
    quote: str | None,
    rects: list[list[float]] | None,
    strokes: list[list[float]] | None,
    body: str,
) -> list[list[float]]:
    """Where an annotation on a PDF page stands, as recorded; MarkRefused when it cannot be placed.

    Strokes are placed at their bounds. An annotation on words given only as a quote is placed by the page's word boxes, and refused when they are not there.
    """
    if mark is not None and mark not in MARKS:
        raise MarkRefused("bad-field", f"a drawing tool is one of: {', '.join(MARKS)}")
    if page is None or page < 1:
        raise MarkRefused("missing-field", "an annotation on a PDF names its page, counted from 1")
    if mark in SAYING and not body:
        raise MarkRefused("empty", f"a {mark} says something")
    if strokes or mark in STROKED:
        if mark is not None and mark not in STROKED:
            raise MarkRefused("bad-field", "only ink and an arrow hold strokes")
        if not strokes:
            raise MarkRefused("missing-field", f"{mark} needs its strokes")
        return bounds(strokes)
    if mark is not None:
        if not rects or len(rects) != 1:
            raise MarkRefused("missing-field", f"a {mark} names its one rectangle")
        return rects
    if rects:
        return rects
    if not quote:
        raise MarkRefused("missing-field", "an annotation on a PDF page names its words, a rectangle or its strokes")
    found = lines_of(pdf, page, quote)
    if not found:
        raise MarkRefused("not-on-page", f"those words are not on page {page}")
    return found


def regeometry(result: Any, ann: Any, rects: Any, strokes: Any) -> dict[str, Any]:
    """The geometry an edit gives `ann`: strokes for ink or an arrow, whose rectangle follows, or one rectangle for a tool that is not on words; MarkRefused otherwise.

    The words around it and its gap from them are taken again where it now stands, on the PDF as it is now, whose hash comes too (`recorded_context`).
    """
    out: dict[str, Any] = {}
    if strokes:
        if ann.mark not in STROKED:
            raise MarkRefused("bad-field", "only ink and an arrow hold strokes")
        clean = clean_strokes(strokes) or []
        out["strokes"], out["rects"] = clean, bounds(clean)
    elif rects:
        if ann.mark is None or ann.mark in STROKED:
            raise MarkRefused("bad-field", "this annotation's place is not a rectangle of its own to move")
        clean_r = clean_rects(rects) or []
        if len(clean_r) != 1:
            raise MarkRefused("bad-field", f"a {ann.mark} stands in one rectangle")
        out["rects"] = clean_r
    _, pdf = pdf_target(result, ann.target_key)
    if out and pdf is not None and pdf.is_file() and ann.page:
        out.update(recorded_context(result, pdf, ann.page, out["rects"], drawn=True))
        out["artifact"] = artifact_of(pdf)
    return out


def recorded_context(result: Any, pdf: Path, page: int, rects: list[list[float]], *, drawn: bool) -> dict[str, Any]:
    """What a mark written at `rects` on `page` of `pdf` records of the words around it, as its event carries it.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned.
    pdf : Path
        The PDF it is written on.
    page : int
        Its page, from 1.
    rects : list of [x0, y0, x1, y1]
        Where it stands.
    drawn : bool
        Whether it is drawn with a tool rather than on words, so its gap is recorded.

    Returns
    -------
    dict
        `anchor`, the text triple (`context_at`), when there are words, and `gap` for a drawing; {} when pdftotext cannot read the file.
    """
    from loom.refs.pages import MapRefused

    try:
        said, gap = context_at(words_of(result, pdf), page, rects)
    except MapRefused:
        return {}
    out: dict[str, Any] = {"anchor": said.to_dict()} if said.exact or said.prefix or said.suffix else {}
    if drawn and gap is not None:
        out["gap"] = gap
    return out


#: How many words either side of a mark it records, in reading order and across a page break.
AROUND = 8


@dataclass(frozen=True)
class PdfWord:
    """One word of a PDF as `pdftotext -bbox-layout` places it: its page, its box in points from the page's top left, its text, and its letters folded (`tex.align.fold`), '' for a token with none, which is a gap."""

    page: int
    box: tuple[float, float, float, float]
    text: str
    letters: str


class DocumentWords:
    """Every word of a PDF in reading order, with the lettered ones indexed for placing a run of them (`tex.align.place_run`)."""

    def __init__(self, pages: list[str]) -> None:
        from loom.refs.pages import page_box
        from loom.refs.search import _words
        from loom.tex.align import rendered_words

        self.words: list[PdfWord] = []
        self.sizes: dict[int, tuple[float, float] | None] = {}
        for n, xml in enumerate(pages, 1):
            self.sizes[n] = page_box(xml)
            for x0, y0, x1, y1, text in _words(xml):
                self.words.append(PdfWord(n, (x0, y0, x1, y1), text, "".join(rendered_words(text))))
        #: the index in `words` of each lettered word, and its letters: what a run is placed in
        self.lettered = [i for i, w in enumerate(self.words) if w.letters]
        self.texts = [self.words[i].letters for i in self.lettered]
        self.at: dict[str, list[int]] = {}
        for i, t in enumerate(self.texts):
            self.at.setdefault(t, []).append(i)

    def on(self, page: int) -> list[int]:
        """The indices of the words on `page`, in reading order."""
        return [i for i, w in enumerate(self.words) if w.page == page]

    def near(self, page: int, y: float) -> int:
        """The lettered word a mark at height `y` on `page` is expected beside, as an index into `texts`: the first on its page that reaches that height, else the first after it."""
        for k, i in enumerate(self.lettered):
            w = self.words[i]
            if w.page > page or (w.page == page and w.box[3] >= y):
                return k
        return max(len(self.lettered) - 1, 0)


def words_of(result: Any, pdf: Path) -> DocumentWords:
    """The words of `pdf` (`refs.pages.document_boxes`), kept by the file's hash under the build's cache, or a stored work's under the store's.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned.
    pdf : Path
        A project PDF, or a stored work's `paper.pdf`.

    Returns
    -------
    DocumentWords
        Every word in reading order; MapRefused when pdftotext cannot read the file.
    """
    from loom.paths import BUILD
    from loom.refs.pages import document_boxes, storage_root, store_boxes

    root: Path = result.quilt.root
    try:
        pdf.resolve().relative_to(storage_root(root).resolve())
        cache = store_boxes(pdf.parent)
    except ValueError:
        cache = root / BUILD / "cache" / "boxes" / "files" / artifact_of(pdf)[:16]
    return DocumentWords(document_boxes(pdf, cache))


def _top_left(rects: list[list[float]]) -> tuple[float, float]:
    return min(r[0] for r in rects), min(r[1] for r in rects)


def _after(w: PdfWord, x: float, y: float) -> bool:
    """Whether `w` comes after the point (x, y) of its page in reading: on the line through it and to its right, or below it."""
    if w.box[1] <= y <= w.box[3]:
        return w.box[0] >= x
    return w.box[1] > y


def context_at(words: DocumentWords, page: int, rects: list[list[float]]) -> tuple[Selector, list[float] | None]:
    """What a mark at `rects` on `page` records of the words around it, and its gap from them.

    Parameters
    ----------
    words : DocumentWords
        The PDF's words.
    page : int
        The mark's page, from 1.
    rects : list of [x0, y0, x1, y1]
        Where it stands, in points from the page's top left.

    Returns
    -------
    (Selector, list of float or None)
        `exact` the words whose middles are under it (as `search.words_under`), `prefix` and `suffix` up to `AROUND` words either side in reading order, across a page break; and its top left less its pin word's: the first lettered word under it, else the first after it on its page, else the last before it there. The gap is None when its page has no word to pin it to; a mark on words records none.
    """
    ws = words.words
    on_page = words.on(page)
    under = [
        i
        for i in on_page
        if any(
            x0 <= (ws[i].box[0] + ws[i].box[2]) / 2 <= x1 and y0 <= (ws[i].box[1] + ws[i].box[3]) / 2 <= y1
            for x0, y0, x1, y1 in rects
        )
    ]
    x, y = _top_left(rects)
    if under:
        exact, prefix, suffix = under, list(range(max(0, under[0] - AROUND), under[0])), []
        suffix = list(range(under[-1] + 1, min(len(ws), under[-1] + 1 + AROUND)))
    else:
        after = next((i for i in on_page if _after(ws[i], x, y)), None)
        k = after if after is not None else (on_page[-1] + 1 if on_page else _first_after(words, page))
        exact, prefix, suffix = [], list(range(max(0, k - AROUND), k)), list(range(k, min(len(ws), k + AROUND)))
    # the pin is the word `refind` finds it by: the first lettered of its words, else of the words after, else the last of those before
    pin = next((i for i in exact if ws[i].letters), None)
    if pin is None:
        pin = next((i for i in suffix if ws[i].letters), None)
        if pin is None or ws[pin].page != page:
            # the next word is on another page and says nothing of where it stands, so the words after are dropped and the one before pins it
            suffix = []
            pin = next((i for i in reversed(prefix) if ws[i].letters), None)
    said = Selector(*(" ".join(ws[i].text for i in group) for group in (exact, prefix, suffix)))
    if pin is None or ws[pin].page != page:
        return said, None
    return said, [round(x - ws[pin].box[0], 2), round(y - ws[pin].box[1], 2)]


def _first_after(words: DocumentWords, page: int) -> int:
    """The index of the first word on a page after `page`, or the end."""
    return next((i for i, w in enumerate(words.words) if w.page > page), len(words.words))


@dataclass
class Refound:
    """Where a mark stands on a changed PDF: its page, its rectangles and its strokes there."""

    page: int
    rects: list[list[float]]
    strokes: list[list[float]] | None = None


def refind(words: DocumentWords, a: Any) -> Refound | None:
    """Find a mark again on a changed PDF by the words it recorded around it, anywhere in the document; None when they are not there.

    `prefix`, `exact` and `suffix` are placed as one run (`tex.align.place_run`) nearest the mark's own page and height. A mark on words stands on its words found again, one rectangle per line; any other stands at its gap from its pin word, its strokes moved with it, and one that records no gap is not placed: an older drawing stays detached. An older mark on words, which recorded its words alone, is found by them.
    """
    from loom.refs.search import _by_line
    from loom.tex.align import place_run, rendered_words, run_positions

    sel = a.selector
    anchor = getattr(a, "anchor", None)
    page = a.page or (anchor.page if anchor else None)
    rects = a.rects or (anchor.quads if anchor else None)
    drawn = bool(a.mark or a.strokes or (anchor is not None and anchor.basis == "box"))
    if sel is None or not page or not rects or (drawn and a.gap is None):
        return None

    def letters(text: str) -> list[str]:
        return [w for w in ("".join(rendered_words(t)) for t in text.split()) if w]

    before, exact, after = letters(sel.prefix), letters(sel.exact), letters(sel.suffix)
    needle = before + exact + after
    if not needle or (not drawn and not exact):
        return None
    found = place_run(words.texts, needle, words.near(page, _top_left(rects)[1]), at=words.at)
    if found is None:
        return None
    first, last, whole = found
    at = list(range(first, first + len(needle))) if whole else run_positions(words.texts, needle, first, last)
    ws = words.words
    if not drawn:
        hit = sorted({words.lettered[i] for i in at[len(before) : len(before) + len(exact)] if i is not None})
        if not hit:
            return None
        on = ws[hit[0]].page
        boxes = [(*ws[i].box, ws[i].text) for i in range(hit[0], hit[-1] + 1) if ws[i].page == on]
        return Refound(on, [[round(v, 2) for v in q] for q in _by_line(boxes)])
    k = len(before) if (exact or after) else len(before) - 1
    j = at[k] if k >= 0 else None
    if j is None:
        return None
    pin = ws[words.lettered[j]]
    old = _top_left(rects)
    dx = round(pin.box[0] + a.gap[0] - old[0], 2)
    dy = round(pin.box[1] + a.gap[1] - old[1], 2)
    moved = [[round(r[0] + dx, 2), round(r[1] + dy, 2), round(r[2] + dx, 2), round(r[3] + dy, 2)] for r in rects]
    strokes = (
        [[round(v + (dx if j % 2 == 0 else dy), 2) for j, v in enumerate(s)] for s in a.strokes] if a.strokes else None
    )
    return Refound(pin.page, moved, strokes)


def refound(result: Any, pdf: Path, a: Any, artifact: str) -> Refound | None:
    """`refind` on the PDF as it is now, kept under `.loom/build/cache/refound/` by what it reads, so a build after the first reads nothing.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned.
    pdf : Path
        The PDF as it is now.
    a : Annotation
        The mark, written on another copy.
    artifact : str
        The hash of `pdf`, which the kept answer is filed under.

    Returns
    -------
    Refound or None
        Where it stands now; None when its words are not found, it is an older drawing with no gap, or pdftotext cannot read the file.
    """
    import json

    from loom.paths import BUILD
    from loom.refs.pages import MapRefused

    sel = a.selector.to_dict() if a.selector else None
    anchor = a.anchor.to_dict() if getattr(a, "anchor", None) else None
    given = [REFIND, artifact, a.page, a.rects, a.strokes, a.mark, a.gap, sel, anchor]
    path = (
        result.quilt.root
        / BUILD
        / "cache"
        / "refound"
        / (hashlib.sha256(json.dumps(given).encode()).hexdigest()[:32] + ".json")
    )
    try:
        got = json.loads(path.read_text(encoding="utf-8"))
        return Refound(**got) if isinstance(got, dict) else None
    except (OSError, ValueError, TypeError):
        pass
    try:
        out = refind(words_of(result, pdf), a)
    except MapRefused:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out.__dict__ if out else None) + "\n", encoding="utf-8")
    except OSError:
        pass
    return out


#: Read with the inputs of every `refound` kept, so a change to how marks are found again is not answered from the cache.
REFIND = 1


#: Where the chromatic colours stand on the wheel, in degrees, as the viewer's `nearestColor` places them.
HUES = {"red": 0, "orange": 30, "yellow": 55, "green": 125, "blue": 210, "purple": 268, "pink": 326}


def nearest_color(rgb: Any) -> str | None:
    """The nearest of the nine colours to a PDF annotation's own, given as three numbers from 0 to 1 or 0 to 255, by hue as the viewer's `nearestColor` finds it; None for no colour.

    A colour with almost no hue is grey, and an orange that is dark or dull is brown.
    """
    if not isinstance(rgb, list | tuple) or len(rgb) != 3 or not all(isinstance(v, int | float) for v in rgb):
        return None
    scale = 255 if max(rgb) <= 1 else 1
    r, g, b = (float(v) * scale for v in rgb)
    most, least = max(r, g, b), min(r, g, b)
    spread = most - least
    if most == 0 or spread / most < 0.15:
        return "grey"
    if most == r:
        hue = 60 * (((g - b) / spread + 6) % 6)
    elif most == g:
        hue = 60 * ((b - r) / spread + 2)
    else:
        hue = 60 * ((r - g) / spread + 4)
    name = min(HUES, key=lambda c: min(abs(hue - HUES[c]), 360 - abs(hue - HUES[c])))
    return "brown" if name == "orange" and (most / 255 < 0.6 or spread / most < 0.45) else name


def _bound(rects: list[list[float]]) -> list[float]:
    """The one rectangle round `rects`."""
    return [min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)]


def same_place(a: list[list[float]], b: list[list[float]]) -> bool:
    """Whether two lists of rectangles bound one place, within the two points a rewrite of the file may move it."""
    return bool(a and b) and all(abs(x - y) <= 2 for x, y in zip(_bound(a), _bound(b), strict=True))


def take_in(
    result: Any, target: str, items: Iterable[dict[str, Any]], writer: tuple[str, str], *, dry_run: bool = False
) -> dict[str, int]:
    """Write a PDF's own annotations as annotations on `target`, skipping what is already here.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned.
    target : str
        The PDF they are taken onto: a project PDF's path or a cited work's citekey.
    items : iterable of dict
        Each `{page, mark?, style?, rects?, strokes?, body?, color?, origin?}`, in points from the page's top left. A `mark` of highlight, underline or strike, or an `origin.subtype` of StrikeOut, is the look's style; a `color` that is not one of the nine is matched to the nearest from `origin.color`.
    writer : (str, str)
        Who takes them in, as `_annotator` gives it; what wrote each one stays in its `origin`.
    dry_run : bool, default False
        Count, and write nothing.

    Returns
    -------
    dict
        `{taken, already, skipped}`: how many were written, how many stand here already by page, place and words, and how many could not be placed. Taking one PDF in twice adds nothing the second time.
    """
    import json

    from loom.clock import stamp, today
    from loom.locks import locked
    from loom.records.ids import draw
    from loom.records.log import log_path, replay
    from loom.records.types import COLORS, drawn_look

    on, pdf = pdf_target(result, target)
    if pdf is None or not pdf.is_file():
        raise MarkRefused("not-a-pdf", f"{target} is not a PDF held on this machine")
    akind, aid = writer
    root = result.quilt.root
    out = {"taken": 0, "already": 0, "skipped": 0}
    # one lock over the whole run, so no writer beside it draws an id from it
    with locked(log_path(root)):
        records, _ = replay(root)
        held = [(a.page, a.body or "", a.rects or []) for r in records for a in r.annotations if a.target_key == on]
        ids = {a.id for r in records for a in r.annotations}
        when, day = stamp(), today()
        lines: list[dict[str, Any]] = []
        for item in items:
            try:
                page = item.get("page")
                body = str(item.get("body") or "").strip()
                origin = dict(item["origin"]) if isinstance(item.get("origin"), dict) else None
                mark = item.get("mark") if isinstance(item.get("mark"), str) else None
                style = item.get("style") if isinstance(item.get("style"), str) else None
                if mark in ON_WORDS:
                    style, mark = mark, None
                if origin and origin.get("subtype") == "StrikeOut":
                    style = "strike"
                if not isinstance(page, int) or isinstance(page, bool):
                    raise MarkRefused("bad-field", "an item names its page")
                rects = clean_rects(item.get("rects"))
                strokes = clean_strokes(item.get("strokes"))
                here = placed(pdf, page, mark, None, rects, strokes, body)
            except MarkRefused:
                out["skipped"] += 1
                continue
            if any(p == page and b == body and same_place(r, here) for p, b, r in held):
                out["already"] += 1
                continue
            around = recorded_context(result, pdf, page, here, drawn=mark is not None or bool(strokes))
            color = item.get("color") if item.get("color") in COLORS else nearest_color((origin or {}).get("color"))
            look = {k: v for k, v in (("color", color), ("style", style)) if v}
            artifact = artifact_of(pdf)
            if origin and origin.get("ref"):
                origin["sha"] = artifact
            ann_id = draw(f"a-{day}-", ids)
            ids.add(ann_id)
            event: dict[str, Any] = {
                "event": "created",
                "id": ann_id,
                "when": when,
                "author": aid,
                "kind": akind,
                "target": on,
                "page": page,
                "rects": here,
                "artifact": artifact,
                "type": None,
                "look": look,
                "drawn": drawn_look(None, look),
                "body": body,
            }
            event.update(around)
            for k, v in (("strokes", strokes), ("mark", mark), ("origin", origin)):
                if v:
                    event[k] = v
            lines.append(event)
            held.append((page, body, here))
            out["taken"] += 1
        if lines and not dry_run:
            with log_path(root).open("a", encoding="utf-8") as fh:
                for e in lines:
                    fh.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")
    return out


def pdf_target(result: Any, target: str) -> tuple[str, Path | None]:
    """What an annotation on `target`'s pages names as its target -- a project PDF's path, or a cited work's identifier -- and the PDF it is drawn on; (target, None) when `target` is neither."""
    from loom.cli.review import _work_target

    rel = project_pdf(result, target)
    if rel is not None:
        return rel, result.quilt.root / rel
    work = _work_target(result, target)
    if work is None:
        return target, None
    return str(work[1]), pdf_of(result, "", work[0])
