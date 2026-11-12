"""Annotations on a page of a PDF: a project file the viewer shows, or a cited work's copy on this machine.

An annotation on a PDF page names its `page` and stands at `rects` (`[x0, y0, x1, y1]` in points from the page's top left) or along `strokes` (`x, y, x, y…` per stroke). One drawn with a tool says so in `mark`: a pin, ink, words on the page, a box, an oval or an arrow; one on words has no `mark`, and its look's style says how it is drawn. It records the hash of the PDF it was written on (`artifact`), so a changed file is noticed (A3): one with quoted words is found again on its page, and one that cannot be is detached. `origin` says where one taken in from a PDF's own annotations came from.

A text or box annotation on a cited work's page is anchored through the work's store instead (`refs/anchoring.py`); this module serves the drawn ones there and every one on a project PDF.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

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


def lines_of(pdf: Path, page: int, words: str) -> list[list[float]] | None:
    """Where `words` stand on a page, one rectangle per line; None where they are not there or the page cannot be read."""
    from loom.refs.pages import MapRefused, token_boxes
    from loom.refs.search import locate_span

    try:
        hit = locate_span(token_boxes(pdf, page, None), words, page)
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


def regeometry(ann: Any, rects: Any, strokes: Any) -> dict[str, Any]:
    """The geometry an edit gives `ann`: strokes for ink or an arrow, whose rectangle follows, or one rectangle for a tool that is not on words; MarkRefused otherwise."""
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
    return out


def on_the_pdf_now(
    pdf: Path, artifact: str | None, page: int | None, quote: str | None
) -> tuple[bool, list[list[float]] | None]:
    """Whether an annotation on a PDF is detached, and where its words stand when the file has changed under them.

    Unchanged bytes keep the place as written, so nothing reads the file. A changed file puts words back through the page's word boxes, and anything else is detached (A3). One that names no hash was written with nothing to compare, and nothing is claimed of it.
    """
    if not pdf.is_file():
        return bool(artifact), None
    if artifact is None or artifact == artifact_of(pdf):
        return False, None
    lines = lines_of(pdf, page, quote) if quote and page else None
    return lines is None, lines


def nearest_color(rgb: Any) -> str | None:
    """The nearest of the nine colours to a PDF annotation's own, given as three numbers from 0 to 1 or 0 to 255; None for no colour."""
    if not isinstance(rgb, list | tuple) or len(rgb) != 3 or not all(isinstance(v, int | float) for v in rgb):
        return None
    scale = 255 if max(rgb) <= 1 else 1
    r, g, b = (float(v) * scale for v in rgb)
    return min(RGB, key=lambda c: (RGB[c][0] - r) ** 2 + (RGB[c][1] - g) ** 2 + (RGB[c][2] - b) ** 2)


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
    from loom.refs.pages import MapRefused, token_boxes
    from loom.refs.search import words_under

    on, pdf = pdf_target(result, target)
    if pdf is None or not pdf.is_file():
        raise MarkRefused("not-a-pdf", f"{target} is not a PDF held on this machine")
    akind, aid = writer
    root = result.quilt.root
    out = {"taken": 0, "already": 0, "skipped": 0}
    boxes: dict[int, str] = {}
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
            quote = None
            if mark is None and not strokes:
                if page not in boxes:
                    try:
                        boxes[page] = token_boxes(pdf, page, None)
                    except MapRefused:
                        boxes[page] = ""
                quote = words_under(boxes[page], here) or None
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
            if quote:
                event["anchor"] = {"exact": quote, "prefix": "", "suffix": ""}
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
