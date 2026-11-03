"""Works a person adds by hand: written into loom's bibliography marked as added, read back by the scan, and taken out again while nothing cites them."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.refs.added import NotRemovable, add_entry, added, remove_entry
from loom.scan.bib import BIBLIOGRAPHY, parse_bib
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.unit._quilts import demo

FIELDS = {
    "author": "Ostrander, D. and Vale, E.",
    "title": "Widget categories and their duals",
    "year": "2018",
    "journal": "J. Widget Theory",
    "doi": "10.5555/widget.2018.031",
    "loom-file": "never a paste's",
}


def test_an_added_work_is_written_marked_and_read_back(tmp_path: Path) -> None:
    q = demo(tmp_path)
    before = (q / BIBLIOGRAPHY).read_text(encoding="utf-8")
    assert add_entry(load_quilt(q), FIELDS, "Ost18", "A. Author") == "Ost18"
    text = (q / BIBLIOGRAPHY).read_text(encoding="utf-8")
    # appended, nothing before it touched
    assert text.startswith(before) and "% from the viewer, added by hand" in text
    entry = scan(load_quilt(q)).bib["Ost18"]
    assert entry.type == "article" and entry.fields["journal"] == "J. Widget Theory"
    assert "loom-file" not in entry.fields
    when_who = added(entry)
    assert when_who is not None and when_who["who"] == "A. Author" and when_who["when"].endswith("Z")


def test_a_taken_key_or_an_entry_with_no_title_is_refused(tmp_path: Path) -> None:
    q = demo(tmp_path)
    with pytest.raises(ValueError, match="already has a work filed as Calloway14"):
        add_entry(load_quilt(q), FIELDS, "Calloway14", "A. Author")
    with pytest.raises(ValueError, match="no title"):
        add_entry(load_quilt(q), {"author": "Nobody"}, "Nob00", "A. Author")


def test_an_added_work_nothing_cites_is_removed_and_nothing_else_is(tmp_path: Path) -> None:
    q = demo(tmp_path)
    before = (q / BIBLIOGRAPHY).read_text(encoding="utf-8")
    add_entry(load_quilt(q), FIELDS, "Ost18", "A. Author")
    said = remove_entry(scan(load_quilt(q)), "Ost18", "A. Author")
    assert said == "removed Ost18 from the library"
    assert (q / BIBLIOGRAPHY).read_text(encoding="utf-8") == before


def test_a_gathered_work_a_cited_one_and_an_unknown_one_are_not_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    q = demo(tmp_path)
    with pytest.raises(NotRemovable) as caught:
        remove_entry(scan(load_quilt(q)), "Calloway14", "A. Author")
    assert caught.value.code == "not-added"
    with pytest.raises(NotRemovable) as caught:
        remove_entry(scan(load_quilt(q)), "Nobody99", "A. Author")
    assert caught.value.code == "no-such-work"
    add_entry(load_quilt(q), FIELDS, "Ost18", "A. Author")
    monkeypatch.setattr("loom.refs.build.cited_counts", lambda result: {"Ost18": 2})
    with pytest.raises(NotRemovable) as caught:
        remove_entry(scan(load_quilt(q)), "Ost18", "A. Author")
    assert caught.value.code == "cited" and "2 results" in caught.value.message
    assert "Ost18" in parse_bib((q / BIBLIOGRAPHY).read_text(encoding="utf-8"))
