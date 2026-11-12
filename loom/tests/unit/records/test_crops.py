"""A crop of a PDF page around a mark, for an agent: made once by pdftocairo under `.loom/build/crops/`, named by the copy, the page and the mark, a PNG with the mark drawn over it in its colour; none without pdftocairo."""

from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import ok
from tests.unit._pdfs import PROSE, lines_pdf
from tests.unit._quilts import demo


@pytest.fixture
def marked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The demo with a project PDF of prose, a red box drawn round its third line."""
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-10-01T09:00:00Z")
    q = demo(tmp_path)
    lines_pdf(q / "notes" / "paper.pdf", [PROSE])
    ok(
        "annotate",
        "notes/paper.pdf",
        "--page",
        "1",
        "--box",
        "70,117,330,133",
        "--mark",
        "box",
        "--color",
        "red",
        "--as",
        "Tester",
        cwd=q,
    )
    return q


def resolved(q: Path) -> tuple[Any, Any]:
    from loom.cli._quilt import open_scan
    from loom.records.store import Records

    result = open_scan(str(q))
    (ra,) = [
        r for r in Records(q, result.quilt.history_dir).resolved(result) if r.annotation.target_key == "notes/paper.pdf"
    ]
    return result, ra


def pixels(png: bytes) -> tuple[int, int, list[bytes]]:
    """A PNG's width, height and rows of RGB(A) bytes, every filter undone (`crops._decode` tested against itself would prove nothing, so this reads only what `_encode` writes)."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height, depth, colour = struct.unpack(">IIBB", png[16:26])
    assert depth == 8 and colour in (2, 6)
    raw = zlib.decompress(_idat(png))
    channels = 3 if colour == 2 else 4
    stride = width * channels
    rows = [raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)] for y in range(height)]
    assert all(raw[y * (stride + 1)] == 0 for y in range(height)), "a drawn crop is written unfiltered"
    return width, height, rows


def _idat(png: bytes) -> bytes:
    pos, out = 8, b""
    while pos < len(png):
        length, kind = struct.unpack(">I4s", png[pos : pos + 8])
        if kind == b"IDAT":
            out += png[pos + 8 : pos + 8 + length]
        pos += 12 + length
    return out


@pytest.mark.poppler
def test_a_crop_is_made_once_named_for_its_copy_and_place_with_the_mark_drawn(marked: Path) -> None:
    from loom.records import crops
    from loom.records.marks import artifact_of

    result, ra = resolved(marked)
    path = crops.crop_of(result, ra)
    assert path is not None and path.parent == marked / ".loom/build/crops"
    sha = artifact_of(marked / "notes" / "paper.pdf")
    assert re.fullmatch(rf"{sha[:16]}-p1-[0-9a-f]{{16}}\.png", path.name)
    width, height, rows = pixels(path.read_bytes())
    # 260 pt of box and 24 pt either side at 144 dpi, and the page's top clamps nothing here
    assert width == round((260 + 48) * 2) and height == round((16 + 48) * 2)

    # the box's top edge, 24 pt into the crop, is drawn in red at its opacity, and the page round it is not
    def reds(row: bytes) -> int:
        return sum(1 for i in range(0, len(row) - 2, 3) if row[i] - row[i + 1] > 60 and row[i] - row[i + 2] > 60)

    assert reds(rows[48]) > width // 2 and reds(rows[10]) == 0
    # made once: asked again, nothing runs
    stamp = path.stat().st_mtime_ns
    assert crops.crop_of(result, ra) == path and path.stat().st_mtime_ns == stamp


@pytest.mark.poppler
def test_a_detached_mark_is_given_the_crop_of_the_copy_it_was_written_on_only_when_one_was_made(marked: Path) -> None:
    from loom.records import crops

    result, ra = resolved(marked)
    first = crops.crop_of(result, ra)
    lines_pdf(marked / "notes" / "paper.pdf", [["Nothing that was marked is here any more."]])
    result, ra = resolved(marked)
    assert ra.detached and crops.crop_of(result, ra) == first
    assert first is not None
    first.unlink()
    assert crops.crop_of(result, ra) is None


def test_no_crop_without_pdftocairo(marked: Path) -> None:
    """The unit tier's PATH holds no poppler, which is how a machine without it looks."""
    from loom.records import crops

    result, ra = resolved(marked)
    assert crops.crop_of(result, ra) is None
    assert not (marked / ".loom/build/crops").exists() or not any((marked / ".loom/build/crops").iterdir())


@pytest.mark.poppler
def test_a_mark_on_words_is_drawn_in_its_style_and_a_region_gets_a_crop(marked: Path) -> None:
    from loom.records import crops

    ok(
        "annotate",
        "notes/paper.pdf",
        "--page",
        "1",
        "--quote",
        "the median polytope",
        "--style",
        "underline",
        "--color",
        "blue",
        "--as",
        "Tester",
        cwd=marked,
    )
    from loom.cli._quilt import open_scan
    from loom.records.store import Records

    result = open_scan(str(marked))
    under = [
        r
        for r in Records(marked, result.quilt.history_dir).resolved(result)
        if r.annotation.selector and r.annotation.selector.exact == "the median polytope"
    ]
    made = crops.crop_of(result, under[0])
    assert made is not None and made.name.endswith(".png")
    region = crops.crop_region(result, marked / "notes" / "paper.pdf", 1, [[70.0, 100.0, 200.0, 140.0]])
    assert region is not None and region != made and json.dumps(str(region)).endswith('.png"')
