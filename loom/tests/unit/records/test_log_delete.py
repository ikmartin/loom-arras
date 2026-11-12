"""Deleting from the annotation log: an annotation goes with every event and every reply below it, and `restore` puts back exactly what went."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loom.records.log import delete, log_path, replay, restore

FINDING = "a-2026-09-18-fy08sq"
REPLY = "a-2026-09-18-612336"
REPLY_TO_REPLY = "a-2026-09-18-by4q46"
OTHER = "a-2026-09-18-k6a9h1"


def event(kind: str, ann_id: str, **over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "event": kind,
        "id": ann_id,
        "when": "2026-09-18T00:00:00Z",
        "author": "A Reader",
        "kind": "human",
        "session": "s-2026-09-18-6e3sw2",
        "target": "x-0001",
        "type": "question",
        "body": f"{kind} {ann_id}",
    }
    return {**base, **over}


def log(root: Path) -> list[str]:
    p = log_path(root)
    return p.read_text(encoding="utf-8").splitlines() if p.is_file() else []


def state(root: Path) -> list[tuple[str, str, str]]:
    """Each annotation as replay has it: id, status and body."""
    records, problems = replay(root)
    assert problems == []
    return sorted((a.id, a.status, a.body) for r in records for a in r.annotations)


@pytest.fixture
def q(tmp_path: Path) -> Path:
    """A log holding a finding with a reply and a reply to that, both edited or resolved, and another finding beside them."""
    lines = [
        event("created", FINDING),
        event("created", OTHER),
        event("replied", REPLY, reply_to=FINDING),
        event("edited", FINDING, body="Restated."),
        event("replied", REPLY_TO_REPLY, reply_to=REPLY),
        event("resolved", FINDING, body="Done."),
        event("edited", OTHER, body="Other, restated."),
    ]
    p = log_path(tmp_path)
    p.parent.mkdir(parents=True)
    p.write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in lines), encoding="utf-8")
    return tmp_path


def test_a_deletion_takes_every_event_of_an_annotation_and_of_its_replies_all_the_way_down(q: Path) -> None:
    before = log(q)
    removed = delete(q, [FINDING])
    assert [(e["event"], e["id"]) for e in removed] == [
        ("created", FINDING),
        ("replied", REPLY),
        ("edited", FINDING),
        ("replied", REPLY_TO_REPLY),
        ("resolved", FINDING),
    ]  # in the log's order
    assert state(q) == [(OTHER, "open", "Other, restated.")]
    assert all(FINDING not in line and REPLY not in line for line in log(q))
    # the log as it was is kept in the build directory, in case the rewrite is cut short
    assert (q / ".loom/build" / "annotations-before-delete.jsonl").read_text(encoding="utf-8").splitlines() == before


def test_deleting_a_reply_leaves_what_it_answers(q: Path) -> None:
    removed = delete(q, [REPLY])
    assert {e["id"] for e in removed} == {REPLY, REPLY_TO_REPLY}
    assert [a for a, _, _ in state(q)] == sorted([FINDING, OTHER])


def test_deleting_what_is_not_there_writes_nothing(q: Path) -> None:
    before = log(q)
    assert delete(q, ["a-1999-01-01-ekn992"]) == []
    assert log(q) == before and not (q / ".loom/build").exists()


def test_a_restore_puts_back_what_a_deletion_took_and_refuses_a_second_time(q: Path) -> None:
    before = state(q)
    removed = delete(q, [FINDING])
    assert restore(q, removed) == [FINDING, REPLY, REPLY_TO_REPLY]
    assert state(q) == before  # resolved, restated and answered, as it stood
    with pytest.raises(ValueError, match="in the log already"):
        restore(q, removed)
    assert state(q) == before
