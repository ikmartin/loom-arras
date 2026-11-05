"""Two clones of a quilt merge their logs: each record keeps an id of its own, and `loom lint` says so when one does not."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from loom.links import ANNOTATION as ANNOTATION_LINK
from loom.links import SESSION as SESSION_LINK
from loom.notes import ID as NOTE_ID
from loom.notes import LINK as NOTE_LINK
from loom.notes import MESSAGE, load
from loom.paths import ANNOTATION_LOG, LINKS, NOTE_LOG
from loom.records.ids import draw, repeated
from loom.records.log import ID as ANNOTATION_ID
from loom.records.log import replay
from loom.refs.links import add_link, read_links, remove_link
from loom.sessions import ID as SESSION_ID
from loom.sessions import INDEX, sessions
from tests.helpers import copy, json_of, ok
from tests.unit._quilts import demo

AS = ("--as", "Same Agent")


def _clones(tmp_path: Path) -> tuple[Path, Path]:
    """Two clones of one quilt, as coauthors hold them."""
    q = demo(tmp_path)
    return copy(q, tmp_path / "one"), copy(q, tmp_path / "two")


def _merge(ours: Path, theirs: Path, rel: str, count: int) -> None:
    """Keep both sides of git's conflict on one log: their last `count` lines after ours."""
    added = (theirs / rel).read_text(encoding="utf-8").splitlines(keepends=True)[-count:]
    with (ours / rel).open("a", encoding="utf-8") as fh:
        fh.writelines(added)


def _no_report(q: Path) -> None:
    assert not [d for d in json_of("lint", "--json", cwd=q)["diagnostics"] if d["code"] == "loom:repeated-id"]


def test_two_clones_merge_into_records_each_with_an_id_of_its_own(tmp_path: Path) -> None:
    """Each clone's first annotation of the day was `0001`; merged, a reply to it could not say which it meant, and nothing reported it."""
    one, two = _clones(tmp_path)
    args = ("annotate", "dm-0002", "the same words in both clones", "--kind", "question", *AS)
    mine, theirs = (ok(*args, cwd=q).stdout.split()[0] for q in (one, two))
    assert mine != theirs
    _merge(one, two, ANNOTATION_LOG, 1)

    records, problems = replay(one)
    assert problems == []
    assert {mine, theirs} <= {a.id for r in records for a in r.annotations}
    _no_report(one)
    # each id says which annotation it means: a resolution of one leaves the other open
    ok("annotate", "--resolve", mine, "answered", *AS, cwd=one)
    status = {a.id: a.status for r in replay(one)[0] for a in r.annotations}
    assert status[mine] == "resolved" and status[theirs] == "open"


def test_two_clones_merge_into_notes_each_with_an_id_of_its_own(tmp_path: Path) -> None:
    """A note's replay keeps the last under an id, so the earlier of two left every view."""
    one, two = _clones(tmp_path)
    mine, theirs = (ok("note", "the same words", "--on", "dm-0002", *AS, cwd=q).stdout.split()[1] for q in (one, two))
    assert mine != theirs
    _merge(one, two, NOTE_LOG, 1)
    assert {mine, theirs} <= set(load(one))
    _no_report(one)


def test_two_clones_merge_into_sessions_each_with_an_id_of_its_own(tmp_path: Path) -> None:
    """A session's replay keeps the last `created` under an id, so the earlier session left `session list`, and both clones' files shared one directory."""
    one, two = _clones(tmp_path)
    args = ("session", "new", "--name", "a sitting", "--no-use", *AS)
    mine, theirs = (ok(*args, cwd=q).stdout.split()[0] for q in (one, two))
    assert mine != theirs
    _merge(one, two, INDEX, 1)
    assert {mine, theirs} <= set(sessions(one))
    _no_report(one)


def test_two_clones_merge_into_links_each_with_an_id_of_its_own(tmp_path: Path) -> None:
    """A link's count held no day, so it was shared on any day, and undoing either removed both."""
    one, two = _clones(tmp_path)
    mine = add_link(one, "a", "b", "depends-on", "why", "A").id
    theirs = add_link(two, "a", "c", "depends-on", "why", "B").id
    assert mine != theirs
    _merge(one, two, LINKS, 1)
    _no_report(one)
    remove_link(one, mine)
    assert [x.id for x in read_links(one)] == [theirs]


@pytest.mark.parametrize(
    "pattern",
    [ANNOTATION_ID, ANNOTATION_LINK, NOTE_ID, SESSION_ID, SESSION_LINK],
    ids=["annotation", "annotation-link", "note", "session", "session-link"],
)
def test_every_pattern_reads_what_is_drawn_and_what_was_counted(pattern: re.Pattern[str]) -> None:
    """A pattern that still wanted digits would refuse every new id, and an id written under a counter is still an id."""
    head = pattern.pattern.strip("^").split("\\d", 1)[0]
    assert pattern.match(draw(f"{head}2026-11-05-", ()))
    assert pattern.match(f"{head}2026-11-05-0001")


def test_a_link_or_a_message_target_reads_a_drawn_id() -> None:
    note, session = draw("n-2026-11-05-", ()), draw("s-2026-11-05-", ())
    assert NOTE_LINK.search(f"[](quilt:{note})")
    found = MESSAGE.match(f"{session}#3")
    assert found is not None and found.group(1) == session


def test_a_draw_is_six_characters_a_url_and_a_filename_can_hold() -> None:
    assert re.fullmatch(r"link-[0-9a-hjkmnp-tv-z]{6}", draw("link-", ()))


def test_a_draw_skips_what_is_taken_and_a_fixed_clock_repeats_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fixtures are compared byte for byte, so under a fixed clock each draw is the next of one sequence."""
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-09-16T00:00:00Z")
    first = draw("a-2026-09-16-", ())
    assert draw("a-2026-09-16-", ()) == first
    second = draw("a-2026-09-16-", {first})
    assert second != first and draw("a-2026-09-16-", {first}) == second


def test_session_list_takes_its_order_from_when_never_from_the_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Listing by id was oldest first while ids counted up; a token sorts anywhere."""
    q = demo(tmp_path)
    tokens = iter(["zzzzzz", "000000"])
    monkeypatch.setattr("loom.records.ids._token", lambda _prefix, _attempt: next(tokens))
    for title, when in (("older", "2030-01-01T00:00:00Z"), ("newer", "2030-01-01T00:00:01Z")):
        monkeypatch.setenv("LOOM_FIXED_TIME", when)
        ok("session", "new", "--name", title, "--no-use", *AS, cwd=q)
    titles = [s["title"] for s in json_of("session", "list", "--json", cwd=q)["sessions"]]
    assert titles[-2:] == ["older", "newer"]


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
        "id": "n-2026-11-05-a5v44a",
        "author": "A",
        "kind": "person",
        "session": "s",
        "target": {"key": "dm-0002"},
        "when": "2026-11-05T00:00:00Z",
    }
    _append(q, NOTE_LOG, note)
    _append(q, NOTE_LOG, {**note, "author": "B"})
    return "n-2026-11-05-a5v44a"


def _second_session(q: Path) -> str:
    made = _last(q, INDEX, "created")
    _append(q, INDEX, {**made, "title": "another clone's sitting"})
    return str(made["id"])


def _second_link(q: Path) -> str:
    link = {"id": "link-zhxqxj", "from": "a", "to": "b", "kind": "depends-on", "why": "w"}
    _append(q, LINKS, link)
    _append(q, LINKS, {**link, "to": "c"})
    return "link-zhxqxj"


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
