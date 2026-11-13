"""What waits on the person (`pending.py`): in-place edits since their look, cut by words, and suggested edits, combined on one key; each kept or discarded, a version kept before a write, and the look taking what loom writes on their word."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import edit, json_of, ok
from tests.unit._quilts import demo, track_edits

LEMMA = "drafting/nodes/dm-0002.tex"
WHO = "Tester"


@pytest.fixture
def q(tmp_path: Path) -> Path:
    from loom.scan.quilt import save_author

    save_author(WHO)
    root = track_edits(demo(tmp_path))
    ok("changes", "--keep-all", cwd=root)
    return root


def listed(q: Path, kind: str = "edit") -> list[dict[str, Any]]:
    """The changes `loom changes` lists of one kind: the demo carries a suggested edit of its own."""
    return [c for c in json_of("changes", "--json", cwd=q)["changes"] if c["kind"] == kind]


def scan(q: Path) -> Any:
    from loom.cli._quilt import open_scan

    return open_scan(str(q))


def test_cut_gives_each_text_back_exactly_and_merges_near_words() -> None:
    from loom.pending import cut

    old = "Every orbit of a widget has one or two points, and the union.\n\nA new paragraph here."
    new = "Each orbit of a widget has one or two points, and the set.\n\nA new paragraph there."
    got = cut(old, new)
    assert len(got) == 3
    for o0, o1, n0, n1 in got:
        assert new[:n0] + old[o0:o1] + new[n1:] != new
    # each stretch in place of the other gives the other text back, so keeping or discarding one alone is exact
    o0, o1, n0, n1 = got[1]
    assert old[:o0] + new[n0:n1] + old[o1:] == old.replace("the union", "the set")
    # words fewer than three apart are one change; a blank line keeps two apart
    assert len(cut("a b c d e f", "a X c Y e f")) == 1
    assert len(cut("a b c\n\nd e", "a X c\n\nY e")) == 2


def test_two_fixes_on_one_line_are_two_changes(q: Path) -> None:
    edit(q / LEMMA, "Every orbit", "Each orbit")
    edit(q / LEMMA, "the union of", "the set of")
    got = listed(q)
    assert [(c["kind"], c["old"], c["new"], c["key"]) for c in got] == [
        ("edit", "Every", "Each", "dm-0002"),
        ("edit", "union", "set", "dm-0002"),
    ]
    assert all(c["id"].startswith("c-") and len(c["id"]) == 10 for c in got)
    assert "drafting/main.tex" in got[0]["documents"] and got[0]["state"] == "ready"


def test_an_id_stands_while_its_change_does(q: Path) -> None:
    edit(q / LEMMA, "Every orbit", "Each orbit")
    first = listed(q)[0]["id"]
    edit(q / LEMMA, "the union of", "the set of")
    (q / "README.md").write_text((q / "README.md").read_text() + "\nA line more.\n")
    assert first in [c["id"] for c in listed(q)]
    said = ok("changes", first, cwd=q).stdout
    assert f"--- a/{LEMMA}" in said and "-Every orbit" in said and "+Each orbit" in said


def test_keeping_one_change_leaves_the_other_and_discarding_writes_it_back_with_a_version_kept(q: Path) -> None:
    from loom.history.ledger import load_history

    edit(q / LEMMA, "Every orbit", "Each orbit")
    edit(q / LEMMA, "the union of", "the set of")
    each, union = (c["id"] for c in listed(q))
    ok("changes", "--keep", each, cwd=q)
    assert [c["id"] for c in listed(q)] == [union]
    versions = len(load_history(q / ".loom/history").entries)
    ok("changes", "--discard", union, "--why", "not this", cwd=q)
    text = (q / LEMMA).read_text()
    assert "Each orbit" in text and "the union of" in text and listed(q) == []
    entries = load_history(q / ".loom/history").entries
    assert len(entries) > versions and entries[-1].action == "undo" and entries[-1].get("changes") == [union]
    # a path names every change in its file
    edit(q / LEMMA, "one or two points", "at most two points")
    ok("changes", "--keep", LEMMA, cwd=q)
    assert listed(q) == []


def test_suggested_edits_on_one_key_combine_and_one_on_the_same_words_waits(q: Path) -> None:
    def suggest(*args: str) -> str:
        return json_of("suggest", "dm-0002", *args, "--as", "Referee Agent", "--json", cwd=q, env={"AI_AGENT": "1"})[
            "edit"
        ]  # type: ignore[no-any-return]

    a = suggest("--quote", "one or two points", "--with", "at most two points")
    b = suggest("--quote", "one-point orbits", "--with", "orbits of size one")
    c = suggest("--quote", "two points", "--with", "two elements")
    got = {x["id"]: x for x in listed(q, "suggested")}
    assert (got[a]["state"], got[b]["state"], got[c]["state"]) == ("ready", "ready", "unplaced")
    assert a in got[c]["why"]
    ok("changes", "--keep", a, "--keep", b, cwd=q)
    text = (q / LEMMA).read_text()
    assert "at most two points" in text and "orbits of size one" in text
    # kept on the person's word: neither edit, nor an in-place change for its words, waits any more; the third stands on the kept words now
    left = [x for x in listed(q, "suggested") if x["id"] in (a, b, c)]
    assert [x["id"] for x in left] == [c] and left[0]["state"] == "ready" and listed(q) == []
    log = [json.loads(x) for x in (q / ".loom/edits/log.jsonl").read_text().splitlines()]
    assert {e["id"] for e in log if e["event"] == "kept"} == {a, b}


def test_a_tick_still_goes_into_the_look(q: Path) -> None:
    from loom.pending import pending
    from loom.tasks import tick

    (q / "notes").mkdir()
    (q / "notes/a.md").write_text("# A\n\n- [ ] one\n", encoding="utf-8")
    ok("changes", "--keep-all", cwd=q)
    from loom.scan.quilt import load_quilt
    from loom.tasks import items

    task = items((q / "notes/a.md").read_text(encoding="utf-8"))[0]
    assert tick(load_quilt(q), WHO, "notes/a.md", task.id, True)
    assert not [c for c in pending(scan(q), WHO) if c.path == "notes/a.md"]


def test_keeping_and_discarding_are_the_authors(q: Path) -> None:
    from tests.helpers import refused

    edit(q / LEMMA, "Every orbit", "Each orbit")
    (change,) = listed(q)
    refused("changes", "--keep", change["id"], cwd=q, env={"AI_AGENT": "1"}, code=2, match="the author's")
    refused("changes", "--keep", "c-00000000", cwd=q, code=2, match="no change c-00000000")
