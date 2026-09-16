"""TeX tier: a block that falls back to SVG compiles against a real preamble, including one that loads xypic with `\\input xy`, which restores `@` to a non-letter (DR-84)."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.render.fallback import compile_svg

# xypic's `\input xy` leaves @ as an ordinary character, so any preamble rewriting that needs \makeatletter breaks after it
PREAMBLE_WITH_XY = (
    "\\PassOptionsToPackage{pass}{geometry}\n"
    "\\newcommand{\\loomgobble}[1]{}\n"
    "\\makeatletter\n"
    "\\usepackage{amsmath}\n"
    "\\usepackage{xy}\n"
    "\\input xy\n"
    "\\xyoption{all}\n"
    "\\loomgobble{Virtual pull-backs}\n"
    "\\loomgobble{C. Manolache}\n"
    "\\makeatother\n"
)


@pytest.mark.tex
def test_fallback_compiles_after_input_xy(tmp_path: Path) -> None:
    res = compile_svg("$1 + 1 = 2$", PREAMBLE_WITH_XY, tmp_path / "cache")
    assert res.svg is not None, res.error
    assert "<svg" in res.svg
    assert not list((tmp_path / "cache").glob("*.failed"))


@pytest.mark.tex
def test_fallback_records_and_reuses_a_failure(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    bad = "\\thisControlSequenceDoesNotExist"
    first = compile_svg(bad, "\\usepackage{amsmath}\n", cache)
    assert first.svg is None and first.error and not first.cached
    assert list(cache.glob("*.failed")), "the failure is written to the cache"
    again = compile_svg(bad, "\\usepackage{amsmath}\n", cache)
    assert again.svg is None and again.cached and again.error == first.error
