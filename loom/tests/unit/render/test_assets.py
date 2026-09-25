"""Graphics for fragments (book 9.4.1): a PDF figure becomes SVG by pdftocairo, else `dvisvgm --pdf`; a raster or SVG is copied; everything lands content-addressed under build/svg/."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from loom.render.assets import publish_graphic, resolve_graphic


def calls() -> list[str]:
    """The tools the fake toolchain was run as, in order."""
    log = Path(os.environ["FAKE_TEX_LOG"])
    return [line.split()[0] for line in log.read_text().splitlines()] if log.exists() else []


def test_a_graphic_is_found_with_or_without_its_extension(tmp_path: Path) -> None:
    (tmp_path / "fig").mkdir()
    (tmp_path / "fig" / "cone.pdf").write_bytes(b"%PDF-1.4\n")
    assert resolve_graphic(tmp_path, " fig/cone ") == tmp_path / "fig" / "cone.pdf"
    assert resolve_graphic(tmp_path, "fig/cone.pdf") == tmp_path / "fig" / "cone.pdf"
    assert resolve_graphic(tmp_path, "fig/none") is None
    assert publish_graphic(tmp_path, "fig/none", tmp_path / "svg") == (None, "graphic fig/none not found")


def test_a_raster_is_copied_under_its_content_hash(tmp_path: Path) -> None:
    (tmp_path / "a.png").write_bytes(b"\x89PNG one")
    (tmp_path / "b.PNG").write_bytes(b"\x89PNG one")
    out = tmp_path / "build" / "svg"
    rel, err = publish_graphic(tmp_path, "a", out)
    assert err is None and rel is not None and rel.startswith("svg/") and rel.endswith(".png")
    assert (out.parent / rel).read_bytes() == b"\x89PNG one"
    assert publish_graphic(tmp_path, "b.PNG", out) == (rel, None)  # same bytes, same asset, lower-cased suffix
    assert calls() == []  # nothing converted


def test_a_pdf_is_converted_by_pdftocairo_once(tmp_path: Path) -> None:
    (tmp_path / "cone.pdf").write_bytes(b"%PDF-1.4\n%FAKE-LOOM\nx\n")
    out = tmp_path / "build" / "svg"
    rel, err = publish_graphic(tmp_path, "cone", out)
    assert err is None and rel is not None and rel.endswith(".svg") and "<svg" in (out.parent / rel).read_text()
    assert calls() == ["pdftocairo"]
    assert publish_graphic(tmp_path, "cone", out) == (rel, None)
    assert calls() == ["pdftocairo"]  # already converted: nothing runs again


def test_without_pdftocairo_dvisvgm_converts_and_without_either_it_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "cone.pdf").write_bytes(b"%PDF-1.4\n%FAKE-LOOM\nx\n")
    real_which = shutil.which
    monkeypatch.setattr(shutil, "which", lambda tool: None if tool == "pdftocairo" else real_which(tool))
    rel, err = publish_graphic(tmp_path, "cone", tmp_path / "svg1")
    assert err is None and rel is not None and calls() == ["dvisvgm"]
    monkeypatch.setattr(shutil, "which", lambda tool: None)
    assert publish_graphic(tmp_path, "cone", tmp_path / "svg2") == (
        None,
        "could not convert cone to SVG (pdftocairo or dvisvgm --pdf needed)",
    )
