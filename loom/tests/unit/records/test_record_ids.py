"""Two clones of a quilt merge their logs: a record's id says which record it means, or `loom lint` says it cannot."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from loom.paths import ANNOTATION_LOG, LINKS, NOTE_LOG
from loom.records.ids import repeated
from loom.sessions import INDEX
from tests.helpers import json_of
from tests.unit._quilts import demo


def _last(q: Path, rel: str, event: str) -> dict[str, object]:
    """The log's last line that gives a record its id."""
    lines = [json.loads(ln) for ln in (q / rel).read_text(encoding="utf-8").splitlines()]
    return next(e for e in reversed(lines) if e.get("event") == event)


def _append(q: Path, rel: str, line: dict[str, object]) -> None:
    path = q / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, sort_keys=True) + "\n")


def _second_annotation(q: Path) -> str:
    made = _last(q, ANNOTATION_LOG, "created")
    _append(q, ANNOTATION_LOG, {**made, "author": "Someone Else", "body": "written in another clone"})
    return str(made["id"])


def _second_note(q: Path) -> str:
    note = {
        "event": "noted",
        "id": "n-2026-11-05-0001",
        "author": "A",
        "kind": "person",
        "session": "s",
        "target": {"key": "dm-0002"},
        "when": "2026-11-05T00:00:00Z",
    }
    _append(q, NOTE_LOG, note)
    _append(q, NOTE_LOG, {**note, "author": "B"})
    return "n-2026-11-05-0001"


def _second_session(q: Path) -> str:
    made = _last(q, INDEX, "created")
    _append(q, INDEX, {**made, "title": "another clone's sitting"})
    return str(made["id"])


def _second_link(q: Path) -> str:
    link = {"id": "link-0001", "from": "a", "to": "b", "kind": "depends-on", "why": "w"}
    _append(q, LINKS, link)
    _append(q, LINKS, {**link, "to": "c"})
    return "link-0001"


@pytest.mark.parametrize(
    ("rel", "provoke"),
    [(ANNOTATION_LOG, _second_annotation), (NOTE_LOG, _second_note), (INDEX, _second_session), (LINKS, _second_link)],
    ids=["annotation", "note", "session", "link"],
)
def test_lint_reports_two_records_under_one_id(tmp_path: Path, rel: str, provoke: Callable[[Path], str]) -> None:
    """Keeping both sides of a merge conflict leaves two records under one id, which a reply or a link cannot tell apart; nothing said so."""
    q = demo(tmp_path)
    ident = provoke(q)
    found = [d for d in json_of("lint", "--json", cwd=q)["diagnostics"] if d["code"] == "loom:repeated-id"]
    assert len(found) == 1, found
    assert rel in found[0]["message"] and ident in found[0]["message"]
    assert "change the id on one of them" in found[0]["message"]


def test_a_line_kept_twice_is_reported_as_a_line_to_delete(tmp_path: Path) -> None:
    q = demo(tmp_path)
    made = _last(q, ANNOTATION_LOG, "created")
    _append(q, ANNOTATION_LOG, made)
    total = len((q / ANNOTATION_LOG).read_text(encoding="utf-8").splitlines())
    [(line, said)] = repeated(q, ANNOTATION_LOG, ("created", "replied"))
    assert line == total and f"delete line {total}" in said


def test_a_later_event_about_a_record_is_no_second_record(tmp_path: Path) -> None:
    """An edit or a resolution names the id it is about, as it must; only the event that gives a record its id can repeat one."""
    q = demo(tmp_path)
    made = _last(q, ANNOTATION_LOG, "created")
    _append(q, ANNOTATION_LOG, {"event": "edited", "id": made["id"], "body": "restated", "when": made["when"]})
    assert repeated(q, ANNOTATION_LOG, ("created", "replied")) == []


def test_the_shipped_demo_repeats_no_id(tmp_path: Path) -> None:
    q = demo(tmp_path)
    assert not [d for d in json_of("lint", "--json", cwd=q)["diagnostics"] if d["code"] == "loom:repeated-id"]
