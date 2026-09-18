"""Anchors frozen against the last text loom saw (book 7.5, plan 0.10 Part B)."""

from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner

from loom.cli import main
from loom.records.lastseen import read_last_seen


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def demo(tmp_path: Path) -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    import shutil

    shutil.rmtree(q / "annotations", ignore_errors=True)
    shutil.rmtree(q / ".loom", ignore_errors=True)
    return q


def texts(q: Path) -> list[Path]:
    d = q / ".loom" / "history" / "texts"
    return sorted(d.iterdir()) if d.is_dir() else []


def edit(q: Path, old: str, new: str) -> None:
    p = q / "nodes" / "dm-0002.tex"
    t = p.read_text()
    assert old in t, old
    p.write_text(t.replace(old, new))


ORIGINAL = "Every orbit of a widget has one or two points"


def test_an_edit_under_an_annotation_freezes_the_text_it_was_written_against(tmp_path: Path) -> None:
    q = demo(tmp_path)
    assert run("comment", "dm-0002", "Which orbits?", "--quote", ORIGINAL, "--author", "Tom", cwd=q).exit_code == 0
    assert run("build", cwd=q).exit_code == 0
    assert texts(q) == []  # nothing has moved yet, so nothing is kept

    cache = read_last_seen(q)
    assert "dm-0002" in cache and ORIGINAL in cache["dm-0002"]

    edit(q, ORIGINAL, "Orbits of a widget have at most two points")
    assert run("build", cwd=q).exit_code == 0
    frozen = texts(q)
    assert len(frozen) == 1 and ORIGINAL in frozen[0].read_text()
    assert ORIGINAL not in read_last_seen(q)["dm-0002"]  # the cache moved on with the quilt


def test_an_edit_nobody_annotated_freezes_nothing(tmp_path: Path) -> None:
    """A quilt nobody has reviewed pays for the cache and nothing else."""
    q = demo(tmp_path)
    assert run("build", cwd=q).exit_code == 0
    edit(q, ORIGINAL, "Orbits have at most two points")
    assert run("build", cwd=q).exit_code == 0
    assert texts(q) == []


def test_two_edits_between_scans_keep_what_loom_saw_and_not_what_it_did_not(tmp_path: Path) -> None:
    """The honest failure: loom freezes the last text it recorded, and never invents the one it missed."""
    q = demo(tmp_path)
    assert run("comment", "dm-0002", "Which orbits?", "--quote", ORIGINAL, "--author", "Tom", cwd=q).exit_code == 0
    assert run("build", cwd=q).exit_code == 0

    edit(q, ORIGINAL, "Every orbit has one or two points")  # loom never sees this one
    edit(q, "Every orbit has one or two points", "Orbits have at most two points")
    assert run("build", cwd=q).exit_code == 0

    frozen = texts(q)
    assert len(frozen) == 1
    kept = frozen[0].read_text()
    assert ORIGINAL in kept  # the version the annotation was written against
    assert "Every orbit has one or two points" not in kept  # the one loom never recorded


def test_the_cache_survives_a_nondefault_history_directory(tmp_path: Path) -> None:
    """`[quilt] history` moves the ledger, the frozen texts and this cache together."""
    q = demo(tmp_path)
    cfg = q / "config.toml"
    cfg.write_text(cfg.read_text().replace("[refs]", 'history = "records/history"\n\n[refs]', 1))
    assert run("comment", "dm-0002", "Which orbits?", "--quote", ORIGINAL, "--author", "Tom", cwd=q).exit_code == 0
    assert run("build", cwd=q).exit_code == 0
    assert (q / "records" / "last-seen.json").is_file()

    edit(q, ORIGINAL, "Orbits have at most two points")
    assert run("build", cwd=q).exit_code == 0
    kept = sorted((q / "records" / "history" / "texts").iterdir())
    assert len(kept) == 1 and ORIGINAL in kept[0].read_text()


def test_an_annotation_written_against_a_lost_version_is_not_reported_anchored(tmp_path: Path) -> None:
    """The quote can still match while the text it was written against is gone; `anchored` says so rather than reading only the quote."""
    import json

    q = demo(tmp_path)
    assert run("build", cwd=q).exit_code == 0  # last-seen holds the original

    edit(q, "the union of the one-point orbits", "the union of the one-point orbits, as we now check")
    assert run("comment", "dm-0002", "Which orbits?", "--quote", ORIGINAL, "--author", "Tom", cwd=q).exit_code == 0
    edit(q, "as we now check", "as we verify below")  # a second edit, far from the quote, before loom scans again
    assert run("build", cwd=q).exit_code == 0

    assert texts(q) == []  # the version the annotation names was never in the cache, so there was nothing to freeze
    m = json.loads((q / "build" / "manifest.json").read_text())
    (a,) = m["annotations"].values()
    assert a["detached"] is False  # the quote still finds its sentence
    assert a["recorded"] is False  # but the text it was written about is unrecoverable
    assert a["anchored"] is False  # so loom does not claim the annotation is in good order
