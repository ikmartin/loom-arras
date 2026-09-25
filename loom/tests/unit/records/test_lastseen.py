"""Anchors frozen against the last text loom saw (book 7.5, plan 0.10 Part B)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from loom.cli._quilt import open_scan
from loom.records.lastseen import current_texts, freeze_moved, read_last_seen, write_last_seen
from loom.scan.hashing import hash_text
from tests.helpers import edit, ok


def demo(tmp_path: Path) -> Path:
    ok("init", str(tmp_path / "q"), "--demo", cwd=tmp_path)
    q = tmp_path / "q"
    shutil.rmtree(q / "annotations", ignore_errors=True)
    shutil.rmtree(q / ".loom", ignore_errors=True)
    return q


def texts(q: Path, history: Path | None = None) -> list[Path]:
    d = (history or q / ".loom" / "history") / "texts"
    return sorted(d.iterdir()) if d.is_dir() else []


ORIGINAL = "Every orbit of a widget has one or two points"
LEMMA = Path("nodes") / "dm-0002.tex"


@pytest.mark.parametrize("history", [None, "records/history"], ids=["default", "configured"])
def test_an_edit_under_an_annotation_freezes_the_text_it_was_written_against(
    tmp_path: Path, history: str | None
) -> None:
    """The comment freezes the version it names; the cache moves on with the quilt. `[quilt] history` moves the ledger, the frozen texts and this cache together."""
    q = demo(tmp_path)
    if history:
        edit(q / "config.toml", "[refs]", f'history = "{history}"\n\n[refs]')
    hist = q / (history or ".loom/history")
    ok("annotate", "dm-0002", "Which orbits?", "--quote", ORIGINAL, "--author", "Tom", cwd=q)
    ok("build", cwd=q)
    # the comment froze the version it was written against, before anything moved
    assert len(texts(q, hist)) == 1 and ORIGINAL in texts(q, hist)[0].read_text()
    assert (hist.parent / "last-seen.json").is_file()
    cache = read_last_seen(q, hist)
    assert "dm-0002" in cache and ORIGINAL in cache["dm-0002"]

    edit(q / LEMMA, ORIGINAL, "Orbits of a widget have at most two points")
    ok("build", cwd=q)
    frozen = texts(q, hist)
    assert len(frozen) == 1 and ORIGINAL in frozen[0].read_text()  # kept once, however it was frozen
    assert ORIGINAL not in read_last_seen(q, hist)["dm-0002"]  # the cache moved on with the quilt


def test_a_moved_key_is_frozen_from_the_cache_when_an_annotation_names_its_old_text(tmp_path: Path) -> None:
    """The cache is where a version no writer froze is kept from: when a key's text moves and an annotation names the text loom last saw, that text is frozen and the cache moves on. A key that moved and that nothing names freezes nothing."""
    q = demo(tmp_path)
    before = current_texts(open_scan(str(q)))
    write_last_seen(q, before)
    edit(q / LEMMA, ORIGINAL, "Orbits have at most two points")
    edit(q / "nodes" / "dm-0001.tex", "Its \\emph{fixed locus} is", "Its \\emph{fixed locus}, a subset of $X$, is")
    named = [SimpleNamespace(annotations=[SimpleNamespace(target_hash=hash_text(before["dm-0002"]))])]

    assert freeze_moved(open_scan(str(q)), named) == ["dm-0002"]  # type: ignore[arg-type]
    frozen = texts(q)
    assert len(frozen) == 1 and ORIGINAL in frozen[0].read_text()
    assert ORIGINAL not in read_last_seen(q)["dm-0002"]
    assert freeze_moved(open_scan(str(q)), named) == []  # type: ignore[arg-type]  # nothing has moved since


def test_an_edit_nobody_annotated_freezes_nothing(tmp_path: Path) -> None:
    """A quilt nobody has reviewed pays for the cache and nothing else."""
    q = demo(tmp_path)
    ok("build", cwd=q)
    edit(q / LEMMA, ORIGINAL, "Orbits have at most two points")
    ok("build", cwd=q)
    assert texts(q) == []


def test_a_version_written_against_between_scans_is_kept(tmp_path: Path) -> None:
    """Edited before the comment and again after it, with no scan between: the version the annotation names was never in the cache, and the comment froze it itself. A version lost some other way is `test_recorded`'s."""
    q = demo(tmp_path)
    ok("build", cwd=q)  # last-seen holds the original

    edit(q / LEMMA, "the union of the one-point orbits", "the union of the one-point orbits, as we now check")
    ok("annotate", "dm-0002", "Which orbits?", "--quote", ORIGINAL, "--author", "Tom", cwd=q)
    # a second edit, far from the quote, before loom scans again
    edit(q / LEMMA, "as we now check", "as we verify below")
    ok("build", cwd=q)

    assert any("as we now check" in p.read_text() for p in texts(q))
    m = json.loads((q / "build" / "manifest.json").read_text())
    (a,) = m["annotations"].values()
    assert (a["detached"], a["recorded"], a["anchored"]) == (False, True, True)
