"""The transcript (plan 0.14 phase 1): `inbox.jsonl` is the one record of a session's conversation, read by index, paged by the build, and written by the two parties only."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tests.helpers import ok, refused, the
from tests.unit._fakes import FakeHandler
from tests.unit._quilts import demo, new_session


def quilt(tmp_path: Path) -> tuple[Path, str]:
    q = demo(tmp_path)
    return q, new_session(q)


def test_the_index_reads_from_where_new_events_start(tmp_path: Path) -> None:
    """A poll reads what is new: bytes already indexed are never scanned again, so a corrupted old line goes unnoticed by a reader past it."""
    from loom.mailbox import Transcript, inbox_path, post

    q, sid = quilt(tmp_path)
    post(q, sid, "one", "A. Author")
    post(q, sid, "two", "A. Author")
    t = Transcript(inbox_path(q, sid))
    assert [e.body for e in t.since(0)] == ["one", "two"] and t.seq == 2
    # scribble over the first line in place, then append: a rescan would lose seq 1 from the index
    p = inbox_path(q, sid)
    raw = p.read_bytes()
    first = raw.index(b"\n")
    p.write_bytes(b"x" * first + raw[first:])
    post(q, sid, "three", "A. Author")
    assert [e.body for e in t.since(2)] == ["three"]
    assert t.seqs == [1, 2, 3]
    # a rewritten, shorter file starts the index again
    p.write_text(json.dumps({"seq": 1, "kind": "message", "who": "A", "when": "", "body": "only"}) + "\n")
    assert [e.body for e in t.since(0)] == ["only"] and t.seq == 1


def test_a_line_still_being_written_waits_for_its_newline(tmp_path: Path) -> None:
    from loom.mailbox import Transcript, inbox_path, post

    q, sid = quilt(tmp_path)
    post(q, sid, "whole", "A. Author")
    with inbox_path(q, sid).open("a") as fh:
        fh.write('{"seq": 2, "kind": "message", "who": "A", "body": "half')
    t = Transcript(inbox_path(q, sid))
    assert [e.body for e in t.since(0)] == ["whole"]


def test_the_last_seq_is_read_from_the_tail(tmp_path: Path) -> None:
    from loom.mailbox import inbox_path, last_seq, post

    q, sid = quilt(tmp_path)
    assert last_seq(q, sid) == 0
    for i in range(300):  # past one 4 KiB step
        post(q, sid, f"message {i} " + "x" * 40, "A. Author")
    assert last_seq(q, sid) == 300
    with inbox_path(q, sid).open("a") as fh:
        fh.write("not json\n")
    assert last_seq(q, sid) == 300


def test_two_writers_never_draw_the_same_number(tmp_path: Path) -> None:
    """The person through the viewer and an agent through `say` post at once; the lock is what keeps the sequence a sequence."""
    from loom.mailbox import read_events

    q, sid = quilt(tmp_path)
    code = "import sys; from pathlib import Path; from loom.mailbox import post\nfor i in range(50): post(Path(sys.argv[1]), sys.argv[2], f'{sys.argv[3]} {i}', sys.argv[3])"
    procs = [subprocess.Popen([sys.executable, "-c", code, str(q), sid, who]) for who in ("A", "B")]
    assert all(p.wait(timeout=120) == 0 for p in procs)
    seqs = [e.seq for e in read_events(q, sid)]
    assert sorted(seqs) == list(range(1, 101))


def test_a_post_needs_words_or_something_attached(tmp_path: Path) -> None:
    import pytest

    from loom.mailbox import post, read_events

    q, sid = quilt(tmp_path)
    with pytest.raises(ValueError):
        post(q, sid, "  ", "A. Author")
    post(q, sid, "", "A. Author", changed=[{"id": "a-2026-09-16-0001", "kind": "note"}])
    assert read_events(q, sid)[0].changed[0]["id"] == "a-2026-09-16-0001"


def test_say_is_one_post_for_an_agent_and_a_person(tmp_path: Path) -> None:
    from loom.mailbox import post, read_events

    q, sid = quilt(tmp_path)
    agent = {"AI_AGENT": "1"}
    # an agent that has not said who it is
    refused("session", "say", "hello", "--session", sid, cwd=q, env=agent, code=2, match="Name yourself with --as")
    said = ok("session", "say", "Read it; one objection.", "--session", sid, "--as", "Referee Agent", cwd=q, env=agent)
    assert said.stdout.strip() == f"said in {sid}"
    [e] = read_events(q, sid)
    assert (e.who, e.body, e.changed) == ("Referee Agent", "Read it; one objection.", [])
    # from stdin
    post(q, sid, "And the second proof?", "A. Author")
    ok("session", "say", "-", "--session", sid, "--as", "Referee Agent", cwd=q, env=agent, stdin="Long answer.\n")
    assert read_events(q, sid)[-1].body == "Long answer."
    refused(
        "session",
        "say",
        "  ",
        "--session",
        sid,
        "--as",
        "Referee Agent",
        cwd=q,
        env=agent,
        code=2,
        match="nothing to say",
    )
    # a person says things the same way, into the same inbox
    ok("session", "say", "Good; carry on.", "--session", sid, "--as", "A. Author", cwd=q)
    assert (read_events(q, sid)[-1].who, read_events(q, sid)[-1].body) == ("A. Author", "Good; carry on.")


def test_the_build_pages_the_transcript_beside_the_manifest(tmp_path: Path) -> None:
    from loom.mailbox import PAGE, pages, post

    q, sid = quilt(tmp_path)
    for i in range(PAGE + 50):
        post(q, sid, f"message **{i}**", "A. Author")
    got = pages(q, sid)
    assert sorted(got) == [1, 2]
    assert [e["seq"] for e in got[2]["events"]] == list(range(PAGE + 1, PAGE + 51))
    assert got[1]["events"][0]["body_html"] == "<p>message <strong>0</strong></p>"
    ok("build", cwd=q)
    page: dict[str, Any] = json.loads((q / "build" / "transcripts" / sid / "2.json").read_text())
    assert page["session"] == sid and page["page"] == 2 and len(page["events"]) == 50
    manifest = json.loads((q / "build" / "manifest.json").read_text())
    assert "messages" not in manifest["threads"][sid]
    assert the(manifest["sessions"], lambda s: s["id"] == sid, f"session {sid} in the manifest")["seq"] == PAGE + 50
    # a deleted session's pages go with it
    ok("session", "delete", sid, "--as", "A. Author", "--yes", cwd=q)
    ok("build", cwd=q)
    assert not list((q / "build" / "transcripts").glob(f"{sid}/*.json"))


def test_the_events_endpoint_reads_by_index_and_holds_the_id_to_its_shape(tmp_path: Path) -> None:
    from loom.mailbox import post
    from loom.render.serve import LoomHandler

    q, sid = quilt(tmp_path)
    post(q, sid, "Look at *this*.", "A. Author")

    good = FakeHandler(q, f"/_api/events?session={sid}&since=0")
    LoomHandler._events(good)  # type: ignore[arg-type]
    assert good.answer is not None and good.answer[0] == 200
    body = good.answer[1]
    assert body["seq"] == 1 and body["events"][0]["body_html"] == "<p>Look at <em>this</em>.</p>"
    assert "attached" not in body
    bad = FakeHandler(q, "/_api/events?session=../../etc&since=0")
    LoomHandler._events(bad)  # type: ignore[arg-type]
    assert bad.answer is not None and bad.answer[0] == 400


def test_no_agent_document_asks_for_a_journal() -> None:
    """The chat is the transcript; a template still asking for `thread.md` would have the agent keep a second record nobody reads."""
    assets = Path(__file__).resolve().parents[2] / "src" / "loom" / "assets"
    for base in (assets / "ai", assets / "demo" / "ai"):
        for p in base.rglob("*.md"):
            assert "thread.md" not in p.read_text(encoding="utf-8"), p


def test_a_purpose_set_later_is_replayed(tmp_path: Path) -> None:
    from loom.sessions import purpose, sessions

    q, sid = quilt(tmp_path)
    purpose(q, sid, "the second proof", "A. Author")
    assert sessions(q)[sid].purpose == "the second proof"


def test_serve_answers_a_transcript_page_from_the_inbox(tmp_path: Path) -> None:
    """`loom serve` answers a transcript page from the inbox itself, since a message rebuilds nothing (0.14 study F14)."""
    from loom.mailbox import PAGE, post
    from loom.render.serve import LoomHandler

    q, sid = quilt(tmp_path)
    for i in range(PAGE + 3):
        post(q, sid, f"m{i}", "Seed Agent")
    ask = FakeHandler(q, f"/build/transcripts/{sid}/2.json")
    assert LoomHandler._page(ask) is True  # type: ignore[arg-type]
    assert ask.answer is not None and [e["seq"] for e in ask.answer[1]["events"]] == [PAGE + 1, PAGE + 2, PAGE + 3]
    assert LoomHandler._page(FakeHandler(q, "/build/manifest.json")) is False  # type: ignore[arg-type]


def test_a_reports_blocks_are_marked_for_the_viewer_and_a_plain_message_is_not() -> None:
    """A mode's report is one message (plan 0.21.2): each bracketed block becomes a `<section data-block>` headed by its name, so the viewer can fold it, and the brackets, which only classify it, never show."""
    from loom.mailbox import render_body
    from loom.records.store import render_markdown

    report = "Mode: referee, on dm-0003.\n\n## [summary]\nOne objection, $x$.\n\n## [referee-review] Major and minor issues\n- A gap.\n\n## [decision]\n"
    html = render_body(report)
    assert html.startswith('<p>Mode: referee, on dm-0003.</p><section data-block="summary"><h2>summary</h2>')
    assert '<section data-block="referee-review"><h2>Major and minor issues</h2><ul>' in html
    assert html.endswith('<section data-block="decision"><h2>decision</h2></section>')
    assert "[summary]" not in html and '<span class="math inline">\\(x\\)</span>' in html
    plain = "Done; see $x$.\n\n## A heading of my own\nText."
    assert render_body(plain) == render_markdown(plain)
