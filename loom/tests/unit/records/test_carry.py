"""Annotations follow the text the person has kept (plan 0.30, decisions 11 and 12): one written before an in-place edit stays where it was until the edit is kept or discarded; keeping carries it onto the new words, with the words it was on, or to a point where they were all removed; discarding carries nothing."""

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


def annotate(q: Path, quote: str, *more: str) -> str:
    return ok(
        "annotate", "dm-0002", "Which?", "--quote", quote, "--type", "question", *more, "--as", WHO, cwd=q
    ).output.split()[0]


def row(q: Path, ann: str) -> dict[str, Any]:
    from loom.cli._quilt import open_scan
    from loom.records.store import Records

    result = open_scan(str(q))
    manifest: dict[str, Any] = {"nodes": {}, "keys": {}, "diagnostics": []}
    Records(q, result.quilt.history_dir).apply(result, manifest)
    return manifest["annotations"][ann]  # type: ignore[no-any-return]


def events(q: Path, ann: str) -> list[dict[str, Any]]:
    lines = (q / ".loom/annotations/log.jsonl").read_text().splitlines()
    return [e for e in map(json.loads, lines) if e.get("id") == ann]


def change(q: Path) -> str:
    (c,) = [c for c in json_of("changes", "--json", cwd=q)["changes"] if c["kind"] == "edit"]
    return str(c["id"])


def test_an_annotation_written_before_an_in_place_edit_stays_until_it_is_kept_or_discarded(q: Path) -> None:
    ann = annotate(q, "one or two points")
    edit(q / LEMMA, "one or two points", "at most two points")
    cid = change(q)
    got = row(q, ann)
    assert (got["detached"], got["anchored"], got["on_changes"], got["earlier"]) == (False, True, [cid], None)
    ok("changes", "--discard", cid, cwd=q)
    assert len(events(q, ann)) == 1, "a discard carries nothing"
    got = row(q, ann)
    assert (got["detached"], got["on_changes"]) == (False, [])


def test_keeping_carries_an_annotation_onto_the_new_words_with_the_words_it_was_on(q: Path) -> None:
    ann = annotate(q, "one or two points")
    edit(q / LEMMA, "one or two points", "at most two points")
    cid = change(q)
    ok("changes", "--keep", cid, cwd=q)
    carried = events(q, ann)[-1]
    assert carried["event"] == "edited" and carried["anchor"]["exact"] == "at most two points"
    assert carried["earlier"] == {"quote": "one or two points", "change": cid} and "against" not in carried
    got = row(q, ann)
    assert (got["detached"], got["quote"], got["earlier"]["quote"]) == (
        False,
        "at most two points",
        "one or two points",
    )


def test_words_all_removed_leave_a_point_where_they_were(q: Path) -> None:
    from loom.cli._quilt import open_scan
    from loom.records.store import Records

    ann = annotate(q, "of a widget")
    edit(q / LEMMA, "of a widget ", "")
    ok("changes", "--keep", change(q), cwd=q)
    carried = events(q, ann)[-1]
    assert carried["anchor"]["exact"] == "" and carried["anchor"]["prefix"].endswith("Every orbit ")
    result = open_scan(str(q))
    (res,) = [r for r in Records(q, result.quilt.history_dir).resolved(result) if r.annotation.id == ann]
    assert not res.detached and res.span is not None and res.span[0] == res.span[1]
    from loom.render.build import _marks_by_node

    (mark,) = [m for m in _marks_by_node(result, Records(q, result.quilt.history_dir))["dm-0002"] if m.ann_id == ann]
    assert mark.gone and mark.start == mark.end


def test_keeping_a_suggested_edit_carries_the_annotation_it_answers_and_resolves_it(q: Path) -> None:
    ann = annotate(q, "one or two points")
    made = json_of(
        "suggest", "dm-0002", "--quote", "one or two points", "--with", "at most two points", "--answers", ann,
        "--as", "Referee Agent", "--json", cwd=q, env={"AI_AGENT": "1"},
    )["edit"]  # fmt: skip
    ok("changes", "--keep", made, cwd=q)
    kinds = [e["event"] for e in events(q, ann)]
    assert kinds[-2:] == ["resolved", "edited"] or kinds[-2:] == ["edited", "resolved"]
    got = row(q, ann)
    assert got["status"] == "resolved" and got["earlier"] == {"quote": "one or two points", "change": made}
    assert got["quote"] == "at most two points" and not got["detached"]
