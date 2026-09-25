"""What a log says when it is wrong, and what a cycle does to a build (docs/reports/hostile-demo.md)."""

from __future__ import annotations

import json
from pathlib import Path

from loom.records.log import replay


def write(root: Path, *events: dict[str, object]) -> None:
    (root / "annotations").mkdir(parents=True, exist_ok=True)
    (root / "annotations" / "log.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def created(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "a-2026-09-18-0001",
        "event": "created",
        "when": "2026-09-18T00:00:00Z",
        "author": "A Reader",
        "kind": "human",
        "session": "s-2026-09-18-0001",
        "target": "x-0001",
        "annotation_kind": "objection",
        "body": "A finding.",
    }
    return {**base, **over}


def test_a_well_formed_log_reports_nothing(tmp_path: Path) -> None:
    write(tmp_path, created())
    records, problems = replay(tmp_path)
    assert problems == []
    assert records[0].annotations[0].kind == "objection"


def test_an_unknown_kind_is_reported_and_kept(tmp_path: Path) -> None:
    """`kind` is an open string a viewer must tolerate from any publisher, so the value stands; the silence was the fault."""
    write(tmp_path, created(annotation_kind="catastrophe"))
    records, problems = replay(tmp_path)
    assert any("catastrophe" in p for p in problems)
    assert records[0].annotations[0].kind == "catastrophe"  # published as written, not corrected to `objection`


def test_a_missing_kind_is_reported_rather_than_assumed(tmp_path: Path) -> None:
    """The column was spelled `annotation-kind` in an early draft; a log written that way lost its kind on every line and said nothing."""
    e = created()
    del e["annotation_kind"]
    write(tmp_path, {**e, "annotation-kind": "question"})
    _records, problems = replay(tmp_path)
    assert any("is not one of" in p for p in problems)


def test_an_id_that_is_a_path_is_reported(tmp_path: Path) -> None:
    """An id becomes a DOM id and a URL fragment, and would become a filename the first time anything stored one."""
    write(tmp_path, created(id="../../escape"))
    _records, problems = replay(tmp_path)
    assert any("is not an annotation id" in p for p in problems)


def test_a_reply_to_nothing_is_reported(tmp_path: Path) -> None:
    """Otherwise it is in the record and on no page: not a finding, because it answers one, and under no finding."""
    write(tmp_path, created(), created(id="a-2026-09-18-0002", event="replied", reply_to="a-1999-01-01-9999"))
    _records, problems = replay(tmp_path)
    assert any("replies to unknown annotation" in p for p in problems)

    # and a reply whose parent IS there says nothing
    write(tmp_path, created(), created(id="a-2026-09-18-0002", event="replied", reply_to="a-2026-09-18-0001"))
    _records, ok = replay(tmp_path)
    assert ok == []


def test_each_kind_of_foreign_line_is_reported_by_line_and_skipped(tmp_path: Path) -> None:
    """Book 7.4.1: a line loom did not write is reported with its line number and why, and the lines around it still load."""
    (tmp_path / "annotations").mkdir()
    lines = [
        json.dumps(created()),
        "{not json",
        json.dumps(["a", "list"]),
        json.dumps({"event": "liked", "id": "a-2026-09-18-0001"}),
        json.dumps({k: v for k, v in created().items() if k != "id"}),
        json.dumps(created(id="a-2026-09-18-0003", session="")),
        json.dumps({"event": "resolved", "when": "x"}),
        json.dumps({"event": "edited", "id": "a-1999-01-01-0001", "body": "x"}),
        json.dumps(created(id="a-2026-09-18-0002", body="Still here.")),
    ]
    (tmp_path / "annotations" / "log.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    records, problems = replay(tmp_path)
    assert problems[0].startswith("annotations/log.jsonl:2: ")  # the JSON decoder's own words follow
    assert problems[1:] == [
        "annotations/log.jsonl:3: not a review event",
        "annotations/log.jsonl:4: not a review event",
        "annotations/log.jsonl:5: created without an id",
        "annotations/log.jsonl:6: created 'a-2026-09-18-0003' names no session",
        "annotations/log.jsonl:7: resolved without an id",
        "annotations/log.jsonl:8: edited names unknown annotation a-1999-01-01-0001",
    ]
    assert [a.id for r in records for a in r.annotations] == ["a-2026-09-18-0001", "a-2026-09-18-0002"]


def test_a_whole_source_discard_and_its_undo_replay_by_the_source_they_name(tmp_path: Path) -> None:
    """A discard with no id names a whole record by `source`, which for a person's record carries the day it was written; its undo restores it."""
    other = created(id="a-2026-09-18-0002", session="s-2026-09-18-0002")
    discard: dict[str, object] = {"event": "discarded", "when": "x", "source": "s-2026-09-18-0001"}
    write(tmp_path, created(), other, discard)
    records, problems = replay(tmp_path)
    assert problems == [] and {r.rel: r.discarded for r in records} == {
        "s-2026-09-18-0001": True,
        "s-2026-09-18-0002": False,
    }
    write(tmp_path, created(), other, discard, {**discard, "undo": True})
    records, _ = replay(tmp_path)
    assert not any(r.discarded for r in records)
    # with no `source`, the event's own session names the record
    write(tmp_path, created(), other, {"event": "discarded", "when": "x", "session": "s-2026-09-18-0002"})
    records, _ = replay(tmp_path)
    assert {r.rel: r.discarded for r in records} == {"s-2026-09-18-0001": False, "s-2026-09-18-0002": True}


def test_an_edit_restates_the_fields_it_carries_and_repoints_against(tmp_path: Path) -> None:
    edited: dict[str, object] = {
        "event": "edited",
        "id": "a-2026-09-18-0001",
        "when": "x",
        "body": "Restated.",
        "severity": "major",
        "placement": {"page": 2},
        "against": "sha256:new",
    }
    write(tmp_path, created(against="sha256:old", severity="minor"), edited)
    records, problems = replay(tmp_path)
    a = records[0].annotations[0]
    assert problems == []
    assert (a.body, a.severity, a.placement, a.target_hash) == ("Restated.", "major", {"page": 2}, "sha256:new")
    # an edit that carries only a body leaves everything else as the last edit set it
    write(
        tmp_path,
        created(against="sha256:old", severity="minor"),
        edited,
        {"event": "edited", "id": a.id, "when": "y", "body": "Again."},
    )
    a = replay(tmp_path)[0][0].annotations[0]
    assert (a.body, a.severity, a.target_hash) == ("Again.", "major", "sha256:new")
