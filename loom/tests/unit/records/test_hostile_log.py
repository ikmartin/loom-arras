"""What a log says when it is wrong, and what a cycle does to a build (records/hostile-demo.md)."""

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
