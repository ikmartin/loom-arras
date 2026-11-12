"""A crop of a PDF page around a mark, for an agent reading the mark: what it is on, as an image, beside its words.

Made once by `pdftocairo` into `.loom/build/crops/`, named by the copy of the file it shows, the page, and the mark's place and look, so a crop is never made twice and never stands for another place. The mark is drawn over it in its own colour with a PNG reader and writer of the standard library's; one that takes longer than `DRAW_SECONDS` is left plain, its place said by the rectangles beside it. Loom calls no model: what an agent reads off a crop, TeX included, is its own reading (P8).
"""

from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any

from loom.paths import BUILD

#: Where crops are made, under the build directory, which nothing commits.
CROPS = f"{BUILD}/crops"
#: Points of the page kept round a mark on every side.
MARGIN = 24.0
#: The narrowest crop, in points, and the shortest, as lines of text.
MIN_WIDTH = 240.0
LINE = 14.0
#: Pixels per inch of a crop, and the widest one in pixels.
RESOLUTION = 144
MAX_PIXELS = 1200
#: How long drawing a mark over its crop may take before the crop is left plain.
DRAW_SECONDS = 1.0


def crop_of(result: Any, ra: Any) -> Path | None:
    """The crop of the page around a resolved annotation on a PDF page, made when first asked for.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned.
    ra : ResolvedAnnotation
        The annotation as it stands now (`Records.resolved`): where it was found again on a changed file, or detached.

    Returns
    -------
    Path or None
        The PNG under `.loom/build/crops/`. None without `pdftocairo`, without the PDF on this machine, for an annotation not on a page, and for a detached one unless the crop of the copy it was written on was made while it stood there.
    """
    from loom.records.marks import artifact_of, pdf_of

    a = ra.annotation
    root: Path = result.quilt.root
    look = _look(root, a)
    anchor = a.anchor
    if ra.detached:
        written = a.artifact or (anchor.sha256 if anchor else "")
        page = a.page or (anchor.page if anchor else None)
        rects = a.rects or (anchor.quads if anchor else None)
        if not written or not page or not rects:
            return None
        kept = root / CROPS / _name(written, page, rects, a.strokes, look, a.mark)
        return kept if kept.is_file() else None
    page = ra.page or a.page or (anchor.page if anchor else None)
    pdf = pdf_of(result, a.target_key, ra.work)
    rects = rects_of(result, ra)
    if not page or pdf is None or not pdf.is_file() or not rects:
        return None
    strokes = ra.strokes or a.strokes
    return _made(root, pdf, artifact_of(pdf), page, rects, strokes, look, a.mark)


def rects_of(result: Any, ra: Any) -> list[list[float]] | None:
    """Where a resolved annotation on a PDF page stands now, one rectangle per line.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned.
    ra : ResolvedAnnotation
        The annotation as it stands now.

    Returns
    -------
    list of [x0, y0, x1, y1] or None
        Its own place, a box anchor's, or a text anchor's words found on its page as the work's sidecar finds them; None when it stands nowhere.
    """
    from loom.records.marks import lines_of, pdf_of

    a, anchor = ra.annotation, ra.annotation.anchor
    rects = ra.rects or a.rects or (anchor.quads if anchor else None)
    if rects or ra.detached or a.selector is None or not a.selector.exact:
        return rects
    page = ra.page or a.page or (anchor.page if anchor else None)
    pdf = pdf_of(result, a.target_key, ra.work)
    if not page or pdf is None or not pdf.is_file():
        return None
    # a stored work's word boxes are cached in the store, so asking again reads no PDF
    return lines_of(pdf, page, a.selector.exact, pdf.parent if ra.work else None)


def crop_region(result: Any, pdf: Path, page: int, rects: list[list[float]]) -> Path | None:
    """The crop of the page around a region a person drew, its outline drawn.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned.
    pdf : Path
        The PDF it was drawn on.
    page : int
        Its page, from 1.
    rects : list of [x0, y0, x1, y1]
        The region, in points from the page's top left.

    Returns
    -------
    Path or None
        The PNG under `.loom/build/crops/`; None without `pdftocairo` or the PDF.
    """
    from loom.records.marks import artifact_of

    if not pdf.is_file() or not rects:
        return None
    look = {"color": "grey", "style": "underline", "weight": 2, "opacity": 100}
    return _made(result.quilt.root, pdf, artifact_of(pdf), page, rects, None, look, "box")


def _look(root: Path, a: Any) -> dict[str, Any]:
    """The look `a` is drawn with, as the manifest publishes it (`Records.look`)."""
    from loom.records.types import drawn_look, load_types

    t = load_types(root).get(a.type)
    if t is None and a.drawn:
        return dict(a.drawn)
    return drawn_look(t, a.own_look)


def _name(
    artifact: str,
    page: int,
    rects: list[list[float]],
    strokes: list[list[float]] | None,
    look: dict[str, Any],
    mark: str | None,
) -> str:
    """`<artifact[:16]>-p<page>-<hash>.png`, the hash of the place, the strokes, the look and the tool."""
    said = json.dumps([rects, strokes, look, mark], sort_keys=True)
    return f"{artifact[:16]}-p{page}-{hashlib.sha256(said.encode()).hexdigest()[:16]}.png"


def _made(
    root: Path,
    pdf: Path,
    artifact: str,
    page: int,
    rects: list[list[float]],
    strokes: list[list[float]] | None,
    look: dict[str, Any],
    mark: str | None,
) -> Path | None:
    """The crop, made by `pdftocairo` unless it is made already, the mark drawn over it; None when it cannot be made."""
    out = root / CROPS / _name(artifact, page, rects, strokes, look, mark)
    if out.is_file():
        return out
    tool = shutil.which("pdftocairo")
    if tool is None:
        return None
    box = _bounds(rects, strokes)
    x0, y0, x1, y1 = box[0] - MARGIN, box[1] - MARGIN, box[2] + MARGIN, box[3] + MARGIN
    if x1 - x0 < MIN_WIDTH:
        grow = (MIN_WIDTH - (x1 - x0)) / 2
        x0, x1 = x0 - grow, x1 + grow
    if y1 - y0 < 3 * LINE:
        grow = (3 * LINE - (y1 - y0)) / 2
        y0, y1 = y0 - grow, y1 + grow
    size = _page_size(pdf, page)
    if size is not None:
        x0, y0 = max(0.0, x0), max(0.0, y0)
        x1, y1 = min(size[0], x1), min(size[1], y1)
    if x1 - x0 < 1 or y1 - y0 < 1:
        return None
    dpi = min(float(RESOLUTION), MAX_PIXELS * 72 / (x1 - x0))
    scale = dpi / 72
    px = [round(x0 * scale), round(y0 * scale), max(1, round((x1 - x0) * scale)), max(1, round((y1 - y0) * scale))]
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent) as tmp:
        base = Path(tmp) / "crop"
        argv = [tool, "-png", "-singlefile", "-r", f"{dpi:g}", "-f", str(page), "-l", str(page)]
        argv += ["-x", str(px[0]), "-y", str(px[1]), "-W", str(px[2]), "-H", str(px[3]), str(pdf), str(base)]
        try:
            done = subprocess.run(argv, capture_output=True, timeout=60, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
        made = base.with_suffix(".png")
        if done.returncode != 0 or not made.is_file():
            return None
        plain = made.read_bytes()
        drawn = _drawn(plain, rects, strokes, look, mark, (x0, y0), scale)
        made.write_bytes(drawn if drawn is not None else plain)
        made.replace(out)
    return out


def _bounds(rects: list[list[float]], strokes: list[list[float]] | None) -> list[float]:
    xs = [v for r in rects for v in (r[0], r[2])] + [v for s in strokes or [] for v in s[0::2]]
    ys = [v for r in rects for v in (r[1], r[3])] + [v for s in strokes or [] for v in s[1::2]]
    return [min(xs), min(ys), max(xs), max(ys)]


def _page_size(pdf: Path, page: int) -> tuple[float, float] | None:
    """A page's width and height in points, from `pdfinfo`; None when it cannot say."""
    import re

    try:
        done = subprocess.run(
            ["pdfinfo", "-f", str(page), "-l", str(page), str(pdf)], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"^Page\s+\d+\s+size:\s*([\d.]+)\s*x\s*([\d.]+)", done.stdout, re.M)
    if m is None:
        m = re.search(r"^Page size:\s*([\d.]+)\s*x\s*([\d.]+)", done.stdout, re.M)
    return (float(m.group(1)), float(m.group(2))) if m else None


# ---- drawing --------------------------------------------------------------------------------------------------


class _Image:
    """An 8-bit RGB or RGBA image, its rows decoded, to draw on."""

    def __init__(self, width: int, height: int, channels: int, rows: list[bytearray]) -> None:
        self.width, self.height, self.channels, self.rows = width, height, channels, rows

    def blend(self, x: int, y: int, rgb: tuple[int, int, int], alpha: float, multiply: bool = False) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        row, at = self.rows[y], x * self.channels
        for k in range(3):
            old = row[at + k]
            new = old * rgb[k] // 255 if multiply else rgb[k]
            row[at + k] = round(old + (new - old) * alpha)

    def dot(self, x: float, y: float, r: int, rgb: tuple[int, int, int], alpha: float) -> None:
        for yy in range(int(y) - r // 2, int(y) - r // 2 + max(r, 1)):
            for xx in range(int(x) - r // 2, int(x) - r // 2 + max(r, 1)):
                self.blend(xx, yy, rgb, alpha)

    def line(
        self, a: tuple[float, float], b: tuple[float, float], r: int, rgb: tuple[int, int, int], alpha: float
    ) -> None:
        steps = max(1, int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))))
        seen: set[tuple[int, int]] = set()
        for i in range(steps + 1):
            x, y = a[0] + (b[0] - a[0]) * i / steps, a[1] + (b[1] - a[1]) * i / steps
            if (int(x), int(y)) not in seen:
                seen.add((int(x), int(y)))
                self.dot(x, y, r, rgb, alpha)


def _drawn(
    png: bytes,
    rects: list[list[float]],
    strokes: list[list[float]] | None,
    look: dict[str, Any],
    mark: str | None,
    origin: tuple[float, float],
    scale: float,
) -> bytes | None:
    """`png` with the mark drawn over it in its colour and style; None when the image is not one this reads, or drawing passes `DRAW_SECONDS`."""
    from loom.records.marks import RGB

    began = time.monotonic()
    image = _decode(png, began)
    if image is None:
        return None
    rgb = RGB.get(str(look.get("color")), RGB["grey"])
    alpha = max(0.2, min(1.0, float(look.get("opacity", 65)) / 100))
    width = max(2, round(float(look.get("weight", 2)) * scale / 2))

    def at(x: float, y: float) -> tuple[float, float]:
        return (x - origin[0]) * scale, (y - origin[1]) * scale

    if strokes:
        for s in strokes:
            points = [at(s[i], s[i + 1]) for i in range(0, len(s) - 1, 2)]
            for p, q in zip(points, points[1:], strict=False):
                image.line(p, q, width, rgb, alpha)
    for r in rects if not strokes else []:
        (ax, ay), (bx, by) = at(r[0], r[1]), at(r[2], r[3])
        if mark == "oval":
            import math

            cx, cy, rx, ry = (ax + bx) / 2, (ay + by) / 2, (bx - ax) / 2, (by - ay) / 2
            n = max(24, int(2 * math.pi * max(rx, ry)))
            ring = [
                (cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n + 1)
            ]
            for p, q in zip(ring, ring[1:], strict=False):
                image.line(p, q, width, rgb, alpha)
        elif mark is not None:
            for p, q in (((ax, ay), (bx, ay)), ((bx, ay), (bx, by)), ((bx, by), (ax, by)), ((ax, by), (ax, ay))):
                image.line(p, q, width, rgb, alpha)
        elif look.get("style") == "underline":
            image.line((ax, by), (bx, by), width, rgb, alpha)
        elif look.get("style") == "strike":
            image.line((ax, (ay + by) / 2), (bx, (ay + by) / 2), width, rgb, alpha)
        else:
            for y in range(int(ay), int(by) + 1):
                for x in range(int(ax), int(bx) + 1):
                    image.blend(x, y, rgb, alpha, multiply=True)
        if time.monotonic() - began > DRAW_SECONDS:
            return None
    return _encode(image) if time.monotonic() - began <= DRAW_SECONDS else None


def _decode(png: bytes, began: float) -> _Image | None:
    """An 8-bit, non-interlaced RGB or RGBA PNG's rows; None for any other, or past `DRAW_SECONDS`."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, idat, head = 8, bytearray(), None
    while pos + 8 <= len(png):
        length, kind = struct.unpack(">I4s", png[pos : pos + 8])
        body = png[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            head = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        pos += 12 + length
    if head is None:
        return None
    width, height, depth, colour, _c, _f, interlace = head
    channels = {2: 3, 6: 4}.get(colour)
    if depth != 8 or channels is None or interlace:
        return None
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    rows: list[bytearray] = []
    prev = bytearray(stride)
    for y in range(height):
        kind = raw[y * (stride + 1)]
        row = bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        if kind == 1:
            for i in range(channels, stride):
                row[i] = (row[i] + row[i - channels]) & 0xFF
        elif kind == 2:
            row = bytearray((v + p) & 0xFF for v, p in zip(row, prev, strict=True))
        elif kind == 3:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif kind == 4:
            for i in range(stride):
                a = row[i - channels] if i >= channels else 0
                b, c = prev[i], prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                row[i] = (row[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 0xFF
        rows.append(row)
        prev = row
        if time.monotonic() - began > DRAW_SECONDS:
            return None
    return _Image(width, height, channels, rows)


def _encode(image: _Image) -> bytes:
    """`image` as a PNG, every row unfiltered."""

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    colour = 2 if image.channels == 3 else 6
    head = struct.pack(">IIBBBBB", image.width, image.height, 8, colour, 0, 0, 0)
    body = zlib.compress(b"".join(b"\x00" + bytes(r) for r in image.rows), 6)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", body) + chunk(b"IEND", b"")
