"""The transcript (plan 0.14 phase 1): `inbox.jsonl` is the one record of a session's conversation, read by index, paged by the build, and written by the two parties only."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from click.testing import CliRunner

from loom.cli import main


def run(*args: str, cwd: Path, env: dict[str, str] | None = None, stdin: str | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), env=env, input=stdin)
    finally:
        os.chdir(old)


def quilt(tmp_path: Path) -> tuple[Path, str]:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    sid = run("session", "new", "a sitting", "--author", "A. Author", cwd=q).output.split()[0]
    return q, sid


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


def test_a_heartbeat_is_not_rewritten_every_wake(tmp_path: Path) -> None:
    """`loom serve` rebuilds when `attached.json` changes; a rewrite per wake rebuilt it four times a second while an agent was parked."""
    from loom.mailbox import ATTACHED, attach, session_dir

    q, sid = quilt(tmp_path)
    attach(q, sid, "Referee Agent", "agent")
    p = session_dir(q, sid) / ATTACHED
    rows = json.loads(p.read_text())
    rows[0]["since"] = "marker"
    p.write_text(json.dumps(rows))
    attach(q, sid, "Referee Agent", "agent")
    assert json.loads(p.read_text())[0]["since"] == "marker"  # untouched
    # a new reader is written at once, and an old beat is renewed
    attach(q, sid, "Tutor Agent", "agent")
    assert {r["who"] for r in json.loads(p.read_text())} == {"Referee Agent", "Tutor Agent"}
    rows = json.loads(p.read_text())
    for r in rows:
        r["beat"] = "2020-01-01T00:00:00Z"
    p.write_text(json.dumps(rows))
    attach(q, sid, "Referee Agent", "agent")
    beat = next(r["beat"] for r in json.loads(p.read_text()) if r["who"] == "Referee Agent")
    assert beat != "2020-01-01T00:00:00Z"


def test_say_is_the_agents_half_of_the_transcript(tmp_path: Path) -> None:
    from loom.mailbox import cursor, post, read_events

    q, sid = quilt(tmp_path)
    agent = {"AI_AGENT": "1"}
    refused = run("session", "say", "hello", "--session", sid, cwd=q, env=agent)
    assert refused.exit_code != 0 and "--as" in refused.output  # an agent that has not said who it is
    person = run("session", "say", "hello", "--session", sid, "--as", "A. Author", cwd=q)
    assert person.exit_code != 0 and "loom session send" in person.output
    said = run("session", "say", "Read it; one objection.", "--session", sid, "--as", "Referee Agent", cwd=q, env=agent)
    assert said.exit_code == 0 and said.output.strip() == f"said in {sid}"
    [e] = read_events(q, sid)
    assert (e.who, e.body, e.changed) == ("Referee Agent", "Read it; one objection.", [])
    assert cursor(q, sid, "Referee Agent") == 1  # it had read everything before, so its own words are not news
    # from stdin, and never past a message the agent has not read
    post(q, sid, "And the second proof?", "A. Author")
    piped = run(
        "session", "say", "-", "--session", sid, "--as", "Referee Agent", cwd=q, env=agent, stdin="Long answer.\n"
    )
    assert piped.exit_code == 0
    assert read_events(q, sid)[-1].body == "Long answer."
    assert cursor(q, sid, "Referee Agent") == 1
    empty = run("session", "say", "  ", "--session", sid, "--as", "Referee Agent", cwd=q, env=agent)
    assert empty.exit_code != 0


def test_a_packet_carries_the_whole_annotation(tmp_path: Path) -> None:
    """What was sent is recorded as sent: a body cut at 200 characters was not what the agent was asked about."""
    from loom.mailbox import pending
    from loom.sessions import sessions

    q, sid = quilt(tmp_path)
    long = "word " * 80
    r = run("comment", "dm-0003", long, "--kind", "note", "--session", sid, "--author", "A. Author", cwd=q)
    assert r.exit_code == 0, r.output
    [c] = pending(q, sessions(q)[sid], "A. Author")
    assert c["body"] == long.strip() or c["body"] == long


def test_the_build_pages_the_transcript_beside_the_manifest(tmp_path: Path) -> None:
    from loom.mailbox import PAGE, pages, post

    q, sid = quilt(tmp_path)
    for i in range(PAGE + 50):
        post(q, sid, f"message **{i}**", "A. Author")
    got = pages(q, sid)
    assert sorted(got) == [1, 2]
    assert [e["seq"] for e in got[2]["events"]] == list(range(PAGE + 1, PAGE + 51))
    assert got[1]["events"][0]["body_html"] == "<p>message <strong>0</strong></p>"
    assert run("build", cwd=q).exit_code in (0, 1)
    page: dict[str, Any] = json.loads((q / "build" / "transcripts" / sid / "2.json").read_text())
    assert page["session"] == sid and page["page"] == 2 and len(page["events"]) == 50
    manifest = json.loads((q / "build" / "manifest.json").read_text())
    assert "messages" not in manifest["threads"][sid]
    assert next(s for s in manifest["sessions"] if s["id"] == sid)["seq"] == PAGE + 50
    # a deleted session's pages go with it
    assert run("session", "delete", sid, "--author", "A. Author", "--yes", cwd=q).exit_code == 0
    assert run("build", cwd=q).exit_code in (0, 1)
    assert not list((q / "build" / "transcripts").glob(f"{sid}/*.json"))


def test_the_events_endpoint_reads_by_index_and_holds_the_id_to_its_shape(tmp_path: Path) -> None:
    from loom.mailbox import attach, post
    from loom.render.serve import LoomHandler

    q, sid = quilt(tmp_path)
    post(q, sid, "Look at *this*.", "A. Author")
    attach(q, sid, "Referee Agent", "agent")

    class Fake:
        quilt_root = q

        def __init__(self, path: str) -> None:
            self.path = path
            self.answer: tuple[int, Any] | None = None

        def _json(self, status: int, body: Any) -> None:
            self.answer = (int(status), body)

        def send_error(self, status: int) -> None:
            self.answer = (int(status), None)

    ok = Fake(f"/_api/events?session={sid}&since=0")
    LoomHandler._events(ok)  # type: ignore[arg-type]
    assert ok.answer is not None and ok.answer[0] == 200
    body = ok.answer[1]
    assert body["seq"] == 1 and body["events"][0]["body_html"] == "<p>Look at <em>this</em>.</p>"
    assert body["attached"] == [{"who": "Referee Agent", "kind": "agent"}]
    bad = Fake("/_api/events?session=../../etc&since=0")
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
