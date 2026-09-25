"""Packets (plan 0.14 phase 4): what the person marked since the last message goes out with the next one, whole, in the words the agent reads -- and the viewer previews exactly those words."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.helpers import json_of, ok, refused
from tests.unit._fakes import FakeHandler
from tests.unit._quilts import demo, new_session


@pytest.fixture
def q(tmp_path: Path) -> Path:
    return demo(tmp_path)


def comment(q: Path, sid: str, *args: str, who: str = "A. Author", agent: bool = False) -> str:
    r = ok("annotate", *args, "--session", sid, "--author", who, cwd=q, env={"AI_AGENT": "1"} if agent else None)
    return r.stdout.split()[0]


def sitting(q: Path) -> tuple[str, Any]:
    """A fresh session's id, and a callable reading its record anew."""
    from loom.sessions import sessions

    sid = new_session(q, "reading")
    return sid, lambda: sessions(q)[sid]


def test_the_packet_is_what_the_person_marked_and_nothing_else(q: Path) -> None:
    from loom.mailbox import pending, post

    sid, session = sitting(q)
    mine = comment(q, sid, "dm-0003", "Which orbit?", "--quote", "finite set", "--kind", "question")
    theirs = comment(q, sid, "dm-0002", "An agent's own note.", "--kind", "note", who="Referee Agent", agent=True)
    ok("annotate", "--reply", theirs, "Not here.", "--session", sid, "--author", "A. Author", cwd=q)
    withdrawn = comment(q, sid, "dm-0002", "Never mind.", "--kind", "note")
    ok("annotate", "--discard", withdrawn, "--session", sid, "--author", "A. Author", cwd=q)
    rows = pending(q, session(), "A. Author")
    assert [r["id"] for r in rows][0] == mine
    assert theirs not in [r["id"] for r in rows] and withdrawn not in [r["id"] for r in rows]
    assert [r["act"] for r in rows] == ["created", "replied"]
    # once a message has carried them, they are not carried again
    post(q, sid, "", "A. Author", changed=rows)
    assert pending(q, session(), "A. Author") == []


def test_a_message_carries_only_its_senders_notes(q: Path) -> None:
    """A message carries its sender's notes and no one else's; another reader's wait for their own message (0.14 study F3)."""
    from loom.mailbox import pending, read_events

    sid, session = sitting(q)
    mine = comment(q, sid, "dm-0003", "Which orbit?", "--kind", "question")
    wrens = comment(q, sid, "dm-0002", "Split this.", "--kind", "suggestion", who="Wren Halloway")
    assert [r["id"] for r in pending(q, session(), "A. Author")] == [mine]
    ok("session", "send", "--session", sid, "--as", "A. Author", cwd=q)
    [sent] = read_events(q, sid)
    assert [c["id"] for c in sent.changed] == [mine]
    # Wren's note waits for Wren's own message
    assert [r["id"] for r in pending(q, session(), "Wren Halloway")] == [wrens]
    assert pending(q, session(), "A. Author") == []


def test_a_carried_annotation_is_whole(q: Path) -> None:
    """What was sent is recorded as sent: the body as typed, never cut short, with every field the agent is asked about."""
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
    assert row["body"] == long
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
    ok("session", "send", "--session", sid, "--as", "A. Author", cwd=q)
    said = render(read_events(q, sid))
    assert said.endswith(preview)


def test_send_with_no_words_sends_the_packet_and_refuses_when_there_is_none(q: Path) -> None:
    from loom.mailbox import read_events

    sid, _ = sitting(q)
    refused("session", "send", "--session", sid, "--as", "A. Author", cwd=q, code=2, match="nothing to send")
    comment(q, sid, "dm-0003", "Which orbit?", "--kind", "question")
    ok("session", "send", "--session", sid, "--as", "A. Author", cwd=q)
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

    good = FakeHandler(q, f"/_api/packet?session={sid}&author=A.%20Author")
    LoomHandler._packet(good)  # type: ignore[arg-type]
    assert good.answer is not None and good.answer[0] == 200
    body = good.answer[1]
    assert [(r["id"], r["kind"], r["target"]) for r in body["rows"]] == [(ann, "question", "dm-0003")]
    assert f"  {ann}  question · dm-0003 · created by A. Author" in body["text"]
    for path, status in ((f"/_api/packet?session=../{sid}", 400), ("/_api/packet?session=s-2026-01-01-0099", 404)):
        bad = FakeHandler(q, path)
        LoomHandler._packet(bad)  # type: ignore[arg-type]
        assert bad.answer is not None and bad.answer[0] == status


def test_the_agent_is_handed_the_packet_whole(q: Path) -> None:
    sid, _ = sitting(q)
    comment(q, sid, "dm-0003", "Which orbit?", "--quote", "finite set", "--kind", "question")
    ok("session", "send", "Have a look.", "--session", sid, "--as", "A. Author", cwd=q)
    got = json_of(
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
    [c] = got["events"][0]["changed"]
    assert (c["body"], c["quote"], c["kind"]) == ("Which orbit?", "finite set", "question")


def test_a_message_from_the_viewer_is_the_persons_whatever_shell_serve_runs_in(
    q: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A message through the viewer is the person's even when `loom serve` runs in an agent's shell; recorded as an agent's, a launched agent would take it for another agent's and never start (0.14 study F17)."""
    from loom.mailbox import read_events
    from loom.render.api import handle

    sid, _ = sitting(q)
    monkeypatch.setenv("AI_AGENT", "1")
    handle(q, "message", {"session": sid, "text": "From the browser."})
    from loom.cli._common import is_agent

    [e] = read_events(q, sid)
    assert not is_agent(e.who)  # the quilt's author, or nobody named -- never the shell's agent
