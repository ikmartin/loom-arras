"""What a log says when it is wrong, and what a cycle does to a build (docs/reports/hostile-demo.md)."""

from __future__ import annotations

import json
from pathlib import Path

from loom.records.log import replay


def write(root: Path, *events: dict[str, object]) -> None:
    (root / ".loom/annotations").mkdir(parents=True, exist_ok=True)
    (root / ".loom/annotations" / "log.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )


def created(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "a-2026-09-18-fy08sq",
        "event": "created",
        "when": "2026-09-18T00:00:00Z",
        "author": "A Reader",
        "kind": "human",
        "session": "s-2026-09-18-6e3sw2",
        "target": "x-0001",
        "type": "revision",
        "body": "A finding.",
    }
    return {**base, **over}


def test_a_well_formed_log_reports_nothing(tmp_path: Path) -> None:
    write(tmp_path, created())
    records, problems = replay(tmp_path)
    assert problems == []
    assert records[0].annotations[0].type == "revision"


def test_a_type_the_quilt_lacks_or_none_at_all_is_no_problem(tmp_path: Path) -> None:
    """A type is only a label: one the quilt no longer lists stands as written, and an annotation with none is untyped; both are drawn as `drawn` says."""
    write(tmp_path, created(type="catastrophe"), created(id="a-2026-09-18-612336", type=None))
    records, problems = replay(tmp_path)
    assert problems == []
    assert [a.type for a in records[0].annotations] == ["catastrophe", None]


def test_a_type_that_is_not_an_id_is_reported(tmp_path: Path) -> None:
    write(tmp_path, created(type=7))
    _records, problems = replay(tmp_path)
    assert any("its type is not a type's id" in p for p in problems)


def test_an_id_that_is_a_path_is_reported(tmp_path: Path) -> None:
    """An id becomes a DOM id and a URL fragment, and would become a filename the first time anything stored one."""
    write(tmp_path, created(id="../../escape"))
    _records, problems = replay(tmp_path)
    assert any("is not an annotation id" in p for p in problems)


def test_a_reply_to_nothing_is_reported(tmp_path: Path) -> None:
    """Otherwise it is in the record and on no page: not a finding, because it answers one, and under no finding."""
    write(tmp_path, created(), created(id="a-2026-09-18-612336", event="replied", reply_to="a-1999-01-01-k6a9h1"))
    _records, problems = replay(tmp_path)
    assert any("replies to unknown annotation" in p for p in problems)

    # and a reply whose parent IS there says nothing
    write(tmp_path, created(), created(id="a-2026-09-18-612336", event="replied", reply_to="a-2026-09-18-fy08sq"))
    _records, ok = replay(tmp_path)
    assert ok == []


def test_each_kind_of_foreign_line_is_reported_by_line_and_skipped(tmp_path: Path) -> None:
    """A line loom did not write is reported with its line number and why, and the lines around it still load."""
    (tmp_path / ".loom/annotations").mkdir(parents=True)
    lines = [
        json.dumps(created()),
        "{not json",
        json.dumps(["a", "list"]),
        json.dumps({"event": "liked", "id": "a-2026-09-18-fy08sq"}),
        json.dumps({k: v for k, v in created().items() if k != "id"}),
        json.dumps(created(id="a-2026-09-18-by4q46", session="")),
        json.dumps({"event": "resolved", "when": "x"}),
        json.dumps({"event": "edited", "id": "a-1999-01-01-ekn992", "body": "x"}),
        json.dumps(created(id="a-2026-09-18-612336", body="Still here.")),
    ]
    (tmp_path / ".loom/annotations" / "log.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    records, problems = replay(tmp_path)
    assert problems[0].startswith(".loom/annotations/log.jsonl:2: ")  # the JSON decoder's own words follow
    assert problems[1:] == [
        ".loom/annotations/log.jsonl:3: not a review event",
        ".loom/annotations/log.jsonl:4: not a review event",
        ".loom/annotations/log.jsonl:5: created without an id",
        ".loom/annotations/log.jsonl:6: created 'a-2026-09-18-by4q46' names no session",
        ".loom/annotations/log.jsonl:7: resolved without an id",
        ".loom/annotations/log.jsonl:8: edited names unknown annotation a-1999-01-01-ekn992",
    ]
    assert [a.id for r in records for a in r.annotations] == ["a-2026-09-18-fy08sq", "a-2026-09-18-612336"]


def test_a_whole_source_discard_and_its_undo_replay_by_the_source_they_name(tmp_path: Path) -> None:
    """A discard with no id names a whole record by `source`, which for a person's record carries the day it was written; its undo restores it."""
    other = created(id="a-2026-09-18-612336", session="s-2026-09-18-w22p58")
    discard: dict[str, object] = {"event": "discarded", "when": "x", "source": "s-2026-09-18-6e3sw2"}
    write(tmp_path, created(), other, discard)
    records, problems = replay(tmp_path)
    assert problems == [] and {r.rel: r.discarded for r in records} == {
        "s-2026-09-18-6e3sw2": True,
        "s-2026-09-18-w22p58": False,
    }
    write(tmp_path, created(), other, discard, {**discard, "undo": True})
    records, _ = replay(tmp_path)
    assert not any(r.discarded for r in records)
    # with no `source`, the event's own session names the record
    write(tmp_path, created(), other, {"event": "discarded", "when": "x", "session": "s-2026-09-18-w22p58"})
    records, _ = replay(tmp_path)
    assert {r.rel: r.discarded for r in records} == {"s-2026-09-18-6e3sw2": False, "s-2026-09-18-w22p58": True}


def test_an_edit_restates_the_fields_it_carries_and_repoints_against(tmp_path: Path) -> None:
    edited: dict[str, object] = {
        "event": "edited",
        "id": "a-2026-09-18-fy08sq",
        "when": "x",
        "body": "Restated.",
        "type": "question",
        "look": {"color": "green"},
        "drawn": {"color": "green", "style": "highlight", "weight": 2, "opacity": 60},
        "placement": {"page": 2},
        "against": "sha256:new",
    }
    write(tmp_path, created(against="sha256:old"), edited)
    records, problems = replay(tmp_path)
    a = records[0].annotations[0]
    assert problems == []
    assert (a.body, a.type, a.own_look, a.placement, a.target_hash) == (
        "Restated.",
        "question",
        {"color": "green"},
        {"page": 2},
        "sha256:new",
    )
    assert a.drawn["color"] == "green"
    # an edit that carries only a body leaves everything else as the last edit set it
    write(
        tmp_path,
        created(against="sha256:old"),
        edited,
        {"event": "edited", "id": a.id, "when": "y", "body": "Again."},
    )
    a = replay(tmp_path)[0][0].annotations[0]
    assert (a.body, a.type, a.own_look, a.target_hash) == ("Again.", "question", {"color": "green"}, "sha256:new")
    # a type of null takes the type off and leaves the look
    write(tmp_path, created(), {"event": "edited", "id": a.id, "when": "z", "type": None})
    a = replay(tmp_path)[0][0].annotations[0]
    assert a.type is None
