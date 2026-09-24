"""Packets (plan 0.14 phase 4): what the person marked since the last message goes out with the next one, whole, in the words the agent reads -- and the viewer previews exactly those words."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from loom.cli import main


def run(*args: str, cwd: Path, env: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), env=env)
    finally:
        os.chdir(old)


@pytest.fixture
def q(tmp_path: Path) -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    return tmp_path / "q"


def comment(q: Path, sid: str, *args: str, who: str = "A. Author", agent: bool = False) -> str:
    r = run("comment", *args, "--session", sid, "--author", who, cwd=q, env={"AI_AGENT": "1"} if agent else None)
    assert r.exit_code == 0, r.output
    return r.output.split()[0]


def sitting(q: Path) -> tuple[str, Any]:
    from loom.sessions import sessions

    sid = run("session", "new", "reading", "--author", "A. Author", cwd=q).output.split()[0]
    return sid, lambda: sessions(q)[sid]


def test_the_packet_is_what_the_person_marked_and_nothing_else(q: Path) -> None:
    from loom.mailbox import pending, post

    sid, session = sitting(q)
    mine = comment(q, sid, "dm-0003", "Which orbit?", "--quote", "finite set", "--kind", "question")
    theirs = comment(q, sid, "dm-0002", "An agent's own note.", "--kind", "note", who="Referee Agent", agent=True)
    reply = run("comment", "--reply", theirs, "Not here.", "--session", sid, "--author", "A. Author", cwd=q)
    assert reply.exit_code == 0, reply.output
    withdrawn = comment(q, sid, "dm-0002", "Never mind.", "--kind", "note")
    assert run("comment", "--discard", withdrawn, "--session", sid, "--author", "A. Author", cwd=q).exit_code == 0
    rows = pending(q, session(), "A. Author")
    assert [r["id"] for r in rows][0] == mine
    assert theirs not in [r["id"] for r in rows] and withdrawn not in [r["id"] for r in rows]
    assert [r["act"] for r in rows] == ["created", "replied"]
    # once a message has carried them, they are not carried again
    post(q, sid, "", "A. Author", changed=rows)
    assert pending(q, session(), "A. Author") == []


def test_a_message_carries_only_its_senders_notes(q: Path) -> None:
    """The 0.14 study (F3): the author's first message carried a second reader's notes too."""
    from loom.mailbox import pending, read_events

    sid, session = sitting(q)
    mine = comment(q, sid, "dm-0003", "Which orbit?", "--kind", "question")
    wrens = comment(q, sid, "dm-0002", "Split this.", "--kind", "suggestion", who="Wren Halloway")
    assert [r["id"] for r in pending(q, session(), "A. Author")] == [mine]
    assert run("session", "send", "--session", sid, "--as", "A. Author", cwd=q).exit_code == 0
    [sent] = read_events(q, sid)
    assert [c["id"] for c in sent.changed] == [mine]
    # Wren's note waits for Wren's own message
    assert [r["id"] for r in pending(q, session(), "Wren Halloway")] == [wrens]
    assert pending(q, session(), "A. Author") == []


def test_a_carried_annotation_is_whole(q: Path) -> None:
    from loom.mailbox import pending

    sid, session = sitting(q)
    long = "word " * 80
    comment(
        q,
        sid,
        "dm-0003",
        long,
        "--quote",
        "finite set",
        "--kind",
        "suggestion",
        "--payload",
        "a finite set $X$",
        "--placement",
        "replace",
        "--severity",
        "minor",
    )
    [row] = pending(q, session(), "A. Author")
    assert row["body"] == long.strip() or row["body"] == long
    assert (row["quote"], row["payload"], row["placement"], row["severity"]) == (
        "finite set",
        "a finite set $X$",
        "replace",
        "minor",
    )


def test_the_preview_is_the_text_the_agent_reads(q: Path) -> None:
    from loom.mailbox import pending, read_events, render, render_changes

    sid, session = sitting(q)
    comment(
        q,
        sid,
        "dm-0003",
        "Say which.",
        "--quote",
        "finite set",
        "--kind",
        "suggestion",
        "--payload",
        "a finite set",
        "--placement",
        "after",
    )
    preview = render_changes(pending(q, session(), "A. Author"))
    assert 'on "finite set"' in preview and '"Say which."' in preview and "proposes (after): a finite set" in preview
    assert run("session", "send", "--session", sid, "--as", "A. Author", cwd=q).exit_code == 0
    said = render(read_events(q, sid))
    assert said.endswith(preview)


def test_send_with_no_words_sends_the_packet_and_refuses_when_there_is_none(q: Path) -> None:
    from loom.mailbox import read_events

    sid, _ = sitting(q)
    empty = run("session", "send", "--session", sid, "--as", "A. Author", cwd=q)
    assert empty.exit_code != 0 and "nothing to send" in empty.output
    comment(q, sid, "dm-0003", "Which orbit?", "--kind", "question")
    assert run("session", "send", "--session", sid, "--as", "A. Author", cwd=q).exit_code == 0
    [e] = read_events(q, sid)
    assert e.body == "" and [c["kind"] for c in e.changed] == ["question"]


def test_the_message_endpoint_takes_a_packet_alone(q: Path) -> None:
    from loom.render.api import ApiError, handle

    sid, _ = sitting(q)
    with pytest.raises(ApiError, match="nothing to send"):
        handle(q, "message", {"session": sid, "text": "", "author": "A. Author"})
    comment(q, sid, "dm-0003", "Which orbit?", "--kind", "question")
    said = handle(q, "message", {"session": sid, "author": "A. Author"})
    assert said["ok"] and said["seq"] == 1


def test_the_packet_endpoint_previews_rows_and_text(q: Path) -> None:
    from loom.render.serve import LoomHandler

    sid, _ = sitting(q)
    ann = comment(q, sid, "dm-0003", "Which orbit?", "--kind", "question")

    class Fake:
        quilt_root = q

        def __init__(self, path: str) -> None:
            self.path = path
            self.answer: tuple[int, Any] | None = None

        def _json(self, status: int, body: Any) -> None:
            self.answer = (int(status), body)

        def send_error(self, status: int) -> None:
            self.answer = (int(status), None)

    ok = Fake(f"/_api/packet?session={sid}&author=A.%20Author")
    LoomHandler._packet(ok)  # type: ignore[arg-type]
    assert ok.answer is not None and ok.answer[0] == 200
    body = ok.answer[1]
    assert [(r["id"], r["kind"], r["target"]) for r in body["rows"]] == [(ann, "question", "dm-0003")]
    assert f"  {ann}  question · dm-0003 · created by A. Author" in body["text"]
    for path, status in ((f"/_api/packet?session=../{sid}", 400), ("/_api/packet?session=s-2026-01-01-0099", 404)):
        bad = Fake(path)
        LoomHandler._packet(bad)  # type: ignore[arg-type]
        assert bad.answer is not None and bad.answer[0] == status


def test_the_agent_is_handed_the_packet_whole(q: Path) -> None:
    sid, _ = sitting(q)
    comment(q, sid, "dm-0003", "Which orbit?", "--quote", "finite set", "--kind", "question")
    assert run("session", "send", "Have a look.", "--session", sid, "--as", "A. Author", cwd=q).exit_code == 0
    got = run(
        "session",
        "next",
        "--wait",
        "0",
        "--json",
        "--session",
        sid,
        "--as",
        "Referee Agent",
        cwd=q,
        env={"AI_AGENT": "1"},
    )
    assert got.exit_code == 0, got.output
    [c] = json.loads(got.output)["events"][0]["changed"]
    assert (c["body"], c["quote"], c["kind"]) == ("Which orbit?", "finite set", "question")


def test_a_message_from_the_viewer_is_the_persons_whatever_shell_serve_runs_in(
    q: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F17 of the 0.14 study: with `loom serve` started in an agent's terminal, the person's messages were recorded as `agent`, so a launched agent took them for another agent's and never started."""
    from loom.mailbox import read_events
    from loom.render.api import handle

    sid, _ = sitting(q)
    monkeypatch.setenv("AI_AGENT", "1")
    handle(q, "message", {"session": sid, "text": "From the browser."})
    from loom.cli._common import is_agent

    [e] = read_events(q, sid)
    assert not is_agent(e.who)  # the quilt's author, or nobody named -- never the shell's agent
