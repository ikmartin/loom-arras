"""The write API over a running `loom serve` (specs/write-api.md): discovery, the CSRF gate, comments and their answers, refusals as JSON, citation suggestions, and who a browser write is from."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from loom.render.serve import ServeSession
from tests.helpers import the
from tests.unit._fakes import configure, sleeper
from tests.unit._quilts import REPO, demo, mapped, new_session, open_session, propose, showcase
from tests.unit.render._serve import get, log, post


def test_the_write_api_binds_to_loopback_only(session) -> None:  # type: ignore[no-untyped-def]
    """specs/write-api.md §3 has no authentication and says so, resting entirely on the socket never leaving this machine. That was an assumption until this test."""
    s, _ = session
    assert s.httpd is not None
    assert s.httpd.server_address[0] == "127.0.0.1"


def test_discovery_lists_what_this_publisher_serves(session) -> None:  # type: ignore[no-untyped-def]
    s, _ = session
    status, _, raw = get(s.url + "_api")
    assert status == 200
    body = json.loads(raw)
    from loom.render.api import CAPABILITIES

    assert body["write_api"] == 1
    assert body["capabilities"] == CAPABILITIES


def test_a_comment_written_over_http_is_the_same_comment(session) -> None:  # type: ignore[no-untyped-def]
    """One implementation of what an annotation is: the endpoint calls the function the CLI calls, so the two cannot drift."""
    s, d = session
    sid = open_session(d)
    status, body = post(
        s.url + "_api/annotate",
        {
            "session": sid,
            "target": "dm-0003",
            "message": "Written from the viewer.",
            "kind": "objection",
            "severity": "minor",
            "author": "A Reader",
        },
    )
    assert status == 200, body
    mine = [e for e in log(d) if e.get("body") == "Written from the viewer."]
    assert len(mine) == 1
    assert mine[0]["kind"] == "human" and mine[0]["author"] == "A Reader"
    assert mine[0]["severity"] == "minor"

    # and it can be answered, restated and withdrawn over the same surface
    ann = mine[0]["id"]
    for endpoint, extra in (
        ("reply", {"message": "Noted."}),
        ("edit", {"message": "Restated."}),
        ("discard", {"reason": "mine"}),
    ):
        status, body = post(
            s.url + f"_api/{endpoint}", {"session": sid, "annotation": ann, "author": "A Reader", **extra}
        )
        assert status == 200, (endpoint, body)
    assert {e["event"] for e in log(d) if e.get("id") == ann} >= {"created", "edited", "discarded"}


def test_the_manifest_is_current_when_a_write_answers(session) -> None:  # type: ignore[no-untyped-def]
    """A write rebuilds before it answers, so the `refresh()` a viewer runs on the answer never races the watcher. Asserted as the property -- the manifest carries the write when the POST resolves -- rather than as a duration, which would be a flake on a loaded machine."""
    s, d = session
    sid = open_session(d)
    status, body = post(s.url + "_api/session-rename", {"session": sid, "title": "renamed in place"})
    assert status == 200, body
    # no sleep, no poll: the very next read must already have it
    _, _, raw = get(s.url + "build/manifest.json")
    rows = {x["id"]: x for x in json.loads(raw)["sessions"]}
    assert rows[sid]["title"] == "renamed in place", rows[sid]


def test_a_refused_write_answers_rather_than_dying(session) -> None:  # type: ignore[no-untyped-def]
    s, d = session
    sid = open_session(d)
    status, body = post(s.url + "_api/annotate", {"session": sid, "message": "no target"})
    assert status == 400 and body["error"]["code"] == "missing-field", body
    status, body = post(s.url + "_api/annotate", {"session": sid, "target": "nope-9999", "message": "x", "author": "R"})
    assert status == 404 and body["error"] == {"code": "no-such-node", "message": "no such key: nope-9999"}, body
    status, body = post(s.url + "_api/discard", {"session": sid, "annotation": "a-1999-01-01-0001", "author": "R"})
    assert status == 404 and body["error"] == {
        "code": "no-such-annotation",
        "message": "no annotation a-1999-01-01-0001",
    }, body
    # a write that names no session at all is malformed, not something to file against whatever was last active
    status, body = post(s.url + "_api/annotate", {"target": "dm-0003", "message": "orphan"})
    assert status == 400 and body["error"]["code"] == "no-session", body
    status, body = post(s.url + "_api/annotate", {"run": sid, "target": "dm-0003", "message": "orphan"})
    assert status == 400 and body["error"]["code"] == "no-session", body  # a session is named `session`, nothing else
    # nobody to sign it: the quilt names no author and the browser gave none
    status, body = post(s.url + "_api/annotate", {"session": sid, "target": "dm-0003", "message": "unsigned"})
    assert status == 400 and body["error"]["code"] == "refused" and "no author name" in body["error"]["message"], body


@pytest.mark.parametrize("decision", ["accept", "reject", "sideways"])
def test_a_citation_suggestion_is_accepted_or_rejected_over_the_api(session, decision: str) -> None:  # type: ignore[no-untyped-def]
    """Accepting files a breadcrumb for the work and closes the finding; rejecting closes it with the reason on the resolve event and files nothing; any other decision is refused and changes nothing."""
    s, d = session
    sid = open_session(d)
    status, made = post(
        s.url + "_api/annotate",
        {
            "session": sid,
            "target": "dm-0003",
            "message": "Cite Manolache, Prop 3.2.",
            "kind": "citation",
            "author": "R",
        },
    )
    assert status == 200, made
    ann = [e for e in log(d) if e.get("body") == "Cite Manolache, Prop 3.2."][0]["id"]
    notes = d / "reference-notes.jsonl"
    before = notes.read_text() if notes.exists() else ""

    status, body = post(
        s.url + "_api/refs-cite",
        {"session": sid, "annotation": ann, "decision": decision, "reason": "already cited", "author": "R"},
    )
    after = notes.read_text() if notes.exists() else ""
    resolved = [e for e in log(d) if e.get("id") == ann and e["event"] == "resolved"]
    if decision == "sideways":
        assert status == 400 and body["error"]["code"] == "bad-field", body
        assert after == before and resolved == []
        return
    assert status == 200, body
    assert len(resolved) == 1, resolved  # the same suggestion is not answered twice
    if decision == "accept":
        added = [json.loads(x) for x in after[len(before) :].splitlines() if x.strip()]
        assert len(added) == 1
        assert added[0]["for"] == ["dm-0003"]
        assert added[0]["identifier"] == {"verified": False}  # a breadcrumb, never a second source of identity truth
    else:
        assert after == before  # nothing is filed for a work nobody wanted
        assert "already cited" in json.dumps(resolved[0])


def test_a_write_without_the_token_is_refused_over_the_wire(session) -> None:  # type: ignore[no-untyped-def]
    """A browser blocks a cross-origin response and never the request, so any page the author happens to be reading could otherwise POST into their quilt (plan 0.13 §8)."""
    s, d = session
    body = {"session": open_session(d), "target": "dm-0003", "message": "from somewhere else", "author": "Nobody"}
    status, said = post(s.url + "_api/annotate", body, token="")
    assert status == 403 and "X-Loom-Token" in said["error"]["message"], said
    assert not [e for e in log(d) if e.get("body") == "from somewhere else"]

    # the token is served where the viewer reads it, and the same well-formed write carrying it is written
    _, _, discovery = get(s.url + "_api")
    assert json.loads(discovery)["token"]
    status, said = post(s.url + "_api/annotate", body)
    assert status == 200, said
    assert len([e for e in log(d) if e.get("body") == "from somewhere else"]) == 1


def test_the_write_api_refuses_a_post_from_another_page() -> None:
    """The gate each branch of it: an Origin that is not this server, a content type a cross-site form can send, and a missing token are each refused by name."""
    from loom.render.serve import LoomHandler

    checks = LoomHandler._csrf

    class Fake:
        token = "right"
        server = type("S", (), {"server_address": ("127.0.0.1", 8791)})()

        def __init__(self, headers: dict[str, str]) -> None:
            self.headers = headers

    good = {"Content-Type": "application/json", "X-Loom-Token": "right", "Origin": "http://127.0.0.1:8791"}
    assert checks(Fake(good)) == ""  # type: ignore[arg-type]
    assert "not this server" in checks(Fake({**good, "Origin": "https://example.org"}))  # type: ignore[arg-type]
    # a cross-site form post can set neither a custom header nor a JSON content type
    assert "application/json" in checks(Fake({**good, "Content-Type": "application/x-www-form-urlencoded"}))  # type: ignore[arg-type]
    assert "X-Loom-Token" in checks(Fake({"Content-Type": "application/json"}))  # type: ignore[arg-type]


def test_a_browser_write_is_the_person_at_the_browser_not_the_servers_shell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With `loom serve` started in an agent's terminal, a note written in the author's own browser is the configured author's, never `agent`; an agent posting to the same endpoint names itself and is believed by its name."""
    from loom.render.api import handle

    q = demo(tmp_path)
    (q / "config.toml").write_text(
        (q / "config.toml").read_text() + '\n[author]\nname = "Wren Halloway"\n', encoding="utf-8"
    )
    monkeypatch.setenv("AI_AGENT", "1")
    said = handle(
        q, "annotate", {"session": open_session(q), "target": "dm-0003", "message": "from the browser", "kind": "note"}
    )
    assert said["ok"], said
    written = log(q)[-1]
    assert written["author"] == "Wren Halloway" and written["kind"] == "human", written
    handle(
        q,
        "annotate",
        {
            "session": open_session(q),
            "target": "dm-0003",
            "message": "from an agent",
            "kind": "note",
            "author": "Referee (Agent)",
        },
    )
    robot = log(q)[-1]
    assert robot["author"] == "Referee (Agent)" and robot["kind"] == "agent", robot


# --- Every capability over the wire ---------------------------------------------------------------------------------
#
# One case per endpoint in CAPABILITIES, each run against a real `loom serve`: one write that succeeds, with what the server wrote read back from the quilt, and one refusal, with its status, code and message. `test_every_capability_has_a_case` fails when an endpoint is served that has no case here.

Serve = Callable[[Path], ServeSession]
Case = Callable[[Serve, Path, pytest.MonkeyPatch], None]
CASES: dict[str, Case] = {}
WHO = "A Reader"


def case(endpoint: str) -> Callable[[Case], Case]:
    def register(fn: Case) -> Case:
        CASES[endpoint] = fn
        return fn

    return register


def succeeds(s: ServeSession, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST and assert 200 with `ok`; the answer."""
    status, said = post(s.url + f"_api/{endpoint}", body)
    assert status == 200 and said.get("ok") is True, (endpoint, status, said)
    return said  # type: ignore[no-any-return]


def refuses(s: ServeSession, endpoint: str, body: dict[str, Any], status: int, code: str, match: str) -> None:
    """POST and assert the refusal: its status, its code, and `match` in its message."""
    got, said = post(s.url + f"_api/{endpoint}", body)
    assert got == status and said.get("error", {}).get("code") == code, (endpoint, got, said)
    assert match in said["error"]["message"], (endpoint, said)


def events(q: Path, ann: str) -> list[dict[str, Any]]:
    """The log's events that name one annotation, in order."""
    return [e for e in log(q) if e.get("id") == ann]


def index(q: Path, sid: str) -> list[dict[str, Any]]:
    """The session index's events for one session, in order."""
    lines = (q / ".loom" / "sessions" / "index.jsonl").read_text(encoding="utf-8").splitlines()
    return [e for e in map(json.loads, filter(None, lines)) if e.get("id") == sid]


def noted(s: ServeSession, q: Path, sid: str, body: str = "A note to act on.") -> str:
    """Write one note on dm-0003 over the wire; its id."""
    succeeds(s, "annotate", {"session": sid, "target": "dm-0003", "message": body, "author": WHO})
    return the(log(q), lambda e: e.get("body") == body and e["event"] == "created", body)["id"]  # type: ignore[no-any-return]


def on_demo(serve: Serve, tmp_path: Path) -> tuple[ServeSession, Path, str]:
    q = demo(tmp_path)
    return serve(q), q, new_session(q)


@case("annotate")
def _annotate(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s, q, sid = on_demo(serve, tmp_path)
    ann = noted(s, q, sid)
    assert the(events(q, ann), lambda e: True, "event")["session"] == sid
    refuses(
        s,
        "annotate",
        {"session": sid, "target": "nope-9999", "message": "x", "author": WHO},
        404,
        "no-such-node",
        "no such key",
    )


@case("reply")
def _reply(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s, q, sid = on_demo(serve, tmp_path)
    ann = noted(s, q, sid)
    succeeds(s, "reply", {"session": sid, "annotation": ann, "message": "Answered.", "author": WHO})
    reply = the(log(q), lambda e: e["event"] == "replied", "reply")
    assert (reply["reply_to"], reply["body"], reply["session"]) == (ann, "Answered.", sid), reply
    refuses(s, "reply", {"session": sid, "message": "to nothing"}, 400, "missing-field", "annotation is required")


@case("resolve")
def _resolve(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s, q, sid = on_demo(serve, tmp_path)
    ann = noted(s, q, sid)
    said = succeeds(s, "resolve", {"session": sid, "annotation": ann, "message": "Fixed.", "author": WHO})
    assert said["result"] == f"resolved {ann}"
    # the undo is another event, and puts it back
    said = succeeds(s, "resolve", {"session": sid, "annotation": ann, "undo": True, "author": WHO})
    assert said["result"] == f"reopened {ann}"
    assert [(e["event"], e.get("body"), e.get("undo")) for e in events(q, ann)[1:]] == [
        ("resolved", "Fixed.", None),
        ("resolved", "", True),
    ]
    missing = "a-1999-01-01-0001"
    refuses(
        s,
        "resolve",
        {"session": sid, "annotation": missing, "author": WHO},
        404,
        "no-such-annotation",
        f"no annotation {missing}",
    )


@case("edit")
def _edit(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s, q, sid = on_demo(serve, tmp_path)
    ann = noted(s, q, sid)
    succeeds(s, "edit", {"session": sid, "annotation": ann, "message": "Restated.", "severity": "minor", "author": WHO})
    edited = events(q, ann)[-1]
    assert (edited["event"], edited["body"], edited["severity"]) == ("edited", "Restated.", "minor"), edited
    missing = "a-1999-01-01-0001"
    refuses(
        s,
        "edit",
        {"session": sid, "annotation": missing, "message": "x", "author": WHO},
        404,
        "no-such-annotation",
        missing,
    )


@case("discard")
def _discard(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s, q, sid = on_demo(serve, tmp_path)
    ann = noted(s, q, sid)
    assert (
        succeeds(s, "discard", {"session": sid, "annotation": ann, "reason": "mine", "author": WHO})["result"]
        == f"discarded {ann}"
    )
    assert (
        succeeds(s, "discard", {"session": sid, "annotation": ann, "undo": True, "author": WHO})["result"]
        == f"reopened {ann}"
    )
    assert [(e["event"], e.get("body"), e.get("undo")) for e in events(q, ann)[1:]] == [
        ("discarded", "mine", None),
        ("discarded", "", True),
    ]
    refuses(s, "discard", {"annotation": ann, "author": WHO}, 400, "no-session", "must name the session")


@case("refs-cite")
def _refs_cite(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s, q, sid = on_demo(serve, tmp_path)
    ann = noted(s, q, sid, "Cite Manolache.")
    said = succeeds(s, "refs-cite", {"session": sid, "annotation": ann, "decision": "accept", "author": WHO})
    assert said["result"].startswith(f"accepted {ann}")
    crumb = json.loads((q / "reference-notes.jsonl").read_text().splitlines()[-1])
    assert (crumb["work"], crumb["for"]) == ("Cite Manolache.", ["dm-0003"]), crumb
    assert crumb["from"] == {"session": sid, "annotation": ann}, crumb
    missing = "a-1999-01-01-0001"
    refuses(
        s,
        "refs-cite",
        {"session": sid, "annotation": missing, "decision": "reject"},
        404,
        "no-such-annotation",
        missing,
    )


def proposed(serve: Serve, tmp_path: Path) -> tuple[ServeSession, Path, str]:
    """The demo with a work whose page text is on disk and one proposed result, `<ck>-thm-1.1`, served."""
    q, ck = mapped(tmp_path)
    propose(q, ck, "thm-1.1", 1, "Let $f$ be a DM-type morphism", "S")
    return serve(q), q, f"{ck}-thm-1.1"


def result_state(q: Path, node: str) -> str:
    ck = node.split("-", 1)[0]
    recs = json.loads((q / "digests" / f"{ck}.results.json").read_text())["results"]
    return str(the(recs, lambda r: r["id"] == node, node)["state"])


@case("digest-verify")
def _digest_verify(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s, q, node = proposed(serve, tmp_path)
    # an agent proposes and never vouches for its own reading, whatever surface it posts through
    refuses(s, "digest-verify", {"node": node, "author": "Referee Agent"}, 403, "author-only", "is an agent")
    assert result_state(q, node) == "proposed"
    succeeds(s, "digest-verify", {"node": node, "author": WHO})
    assert result_state(q, node) == "verified"


@case("digest-discard")
def _digest_discard(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s, q, node = proposed(serve, tmp_path)
    refuses(s, "digest-discard", {"node": node, "author": WHO}, 400, "missing-field", "reason is required")
    refuses(s, "digest-discard", {"node": node + ".9", "reason": "x", "author": WHO}, 404, "no-such-node", node + ".9")
    assert result_state(q, node) == "proposed"
    succeeds(s, "digest-discard", {"node": node, "reason": "not the paper's", "author": WHO})
    assert result_state(q, node) == "discarded"


@case("locate")
def _locate(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s = serve(showcase(tmp_path))
    text = "The median orders of a weighted digraph are in bijection with the vertices"
    said = succeeds(s, "locate", {"citekey": "Bellamy19", "page": 2, "text": text})
    assert said["anchor"]["basis"] == "text" and said["anchor"]["page"] == 2 and said["text"] == text, said
    refuses(s, "locate", {"citekey": "Nope", "page": 1, "text": "x"}, 404, "no-such-work", "Nope")


@case("session-use")
def _session_use(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    from loom.sessions import active, close, delete, sessions

    s, q, sid = on_demo(serve, tmp_path)
    close(q, sid, WHO)
    # a closed session is resumed by being chosen, and becomes the one writing lands in
    succeeds(s, "session-use", {"session": sid, "author": WHO})
    assert active(q) == sid and sessions(q)[sid].state == "open" and index(q, sid)[-1]["event"] == "resumed"
    gone = new_session(q, "a gone sitting")
    delete(q, gone, WHO)
    was = active(q)
    refuses(s, "session-use", {"session": gone}, 400, "refused", "was deleted")
    assert active(q) == was and sessions(q, deleted=True)[gone].state == "deleted"


@case("session-rename")
def _session_rename(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    from loom.sessions import sessions

    s, q, sid = on_demo(serve, tmp_path)
    succeeds(s, "session-rename", {"session": sid, "title": "second pass", "author": WHO})
    assert sessions(q)[sid].title == "second pass" and index(q, sid)[-1]["who"] == WHO
    refuses(s, "session-rename", {"session": sid}, 400, "missing-field", "title is required")


@case("session-delete")
def _session_delete(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    from loom.sessions import active, sessions

    s, q, sid = on_demo(serve, tmp_path)
    ann = noted(s, q, sid)
    succeeds(s, "session-delete", {"session": sid, "reason": "a false start", "author": WHO})
    assert index(q, sid)[-1] == {**index(q, sid)[-1], "event": "deleted", "why": "a false start"}
    assert sid not in sessions(q) and active(q) != sid
    assert events(q, ann), "a tombstone keeps what was written in the session"
    refuses(s, "session-delete", {"session": "s-1999-01-01-0001"}, 404, "no-such-session", "s-1999-01-01-0001")


@case("session-new")
def _session_new(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    from loom.sessions import active, sessions

    q = demo(tmp_path)
    s = serve(q)
    said = succeeds(s, "session-new", {"title": "from the page", "purpose": "check the orbits", "author": WHO})
    sid = said["result"].split()[0]
    assert active(q) == sid
    assert (sessions(q)[sid].title, sessions(q)[sid].purpose) == ("from the page", "check the orbits")
    refuses(s, "session-new", {"purpose": "untitled"}, 400, "missing-field", "title is required")


@case("session-close")
def _session_close(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    from loom.sessions import active, sessions

    s, q, sid = on_demo(serve, tmp_path)
    assert active(q) == sid
    succeeds(s, "session-close", {"session": sid, "author": WHO})
    assert sessions(q)[sid].state == "closed" and active(q) is None
    refuses(s, "session-close", {"session": sid}, 400, "refused", "is closed")


@case("session-reopen")
def _session_reopen(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    from loom.sessions import active, close, sessions

    s, q, sid = on_demo(serve, tmp_path)
    refuses(s, "session-reopen", {"session": sid}, 400, "refused", "already open")
    close(q, sid, WHO)
    was = active(q)
    assert succeeds(s, "session-reopen", {"session": sid, "author": WHO})["result"] == f"reopened {sid}"
    # reopening starts a new round and leaves which session is active alone
    assert sessions(q)[sid].state == "open" and len(sessions(q)[sid].rounds) == 2
    assert index(q, sid)[-1]["event"] == "resumed" and active(q) == was


@case("session-purpose")
def _session_purpose(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    from loom.sessions import sessions

    s, q, sid = on_demo(serve, tmp_path)
    assert (
        succeeds(s, "session-purpose", {"session": sid, "purpose": "the orbit lemma"})["result"]
        == f"{sid} is for the orbit lemma"
    )
    assert sessions(q)[sid].purpose == "the orbit lemma" and index(q, sid)[-1]["event"] == "purposed"
    # an empty purpose clears it
    succeeds(s, "session-purpose", {"session": sid})
    assert sessions(q)[sid].purpose == ""
    refuses(s, "session-purpose", {"session": "s-1999-01-01-0001", "purpose": "x"}, 404, "no-such-session", "s-1999")


@case("message")
def _message(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    from loom.mailbox import read_events

    s, q, sid = on_demo(serve, tmp_path)
    refuses(s, "message", {"session": sid, "author": WHO}, 400, "nothing-to-send", "nothing marked")
    said = succeeds(s, "message", {"session": sid, "text": "Look at dm-0003.", "author": WHO})
    assert (said["session"], said["attached"]) == (sid, [])
    got = read_events(q, sid)[-1]
    assert (got.seq, got.body, got.who) == (said["seq"], "Look at dm-0003.", WHO)
    refuses(s, "message", {"session": "no such sitting", "text": "x"}, 404, "no-such-session", "no such sitting")


def running(q: Path, sid: str, ready: Path, timeout: float = 20) -> int:
    """Wait for the turn loom started in `sid` to be running and to have written `ready`; its pid."""
    from loom.agent import state

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if state(q, sid).get("state") == "running" and ready.exists() and ready.read_text():
            return int(ready.read_text())
        time.sleep(0.05)
    raise AssertionError(f"no turn started in {sid} within {timeout}s: {state(q, sid)}")


def gone(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


@case("agent-stop")
def _agent_stop(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    from loom.agent import state

    q = demo(tmp_path)
    ready = tmp_path / "turn.pid"
    configure(q, start=sleeper(ready), resume=[], launch=False)
    s = serve(q)
    sid = new_session(q)
    refuses(s, "agent-stop", {"session": sid}, 409, "not-launching", "not launched")
    configure(q, start=sleeper(ready), resume=[])
    succeeds(s, "message", {"session": sid, "text": "Take your time.", "author": WHO})
    pid = running(q, sid, ready)
    assert succeeds(s, "agent-stop", {"session": sid}) == {"ok": True, "result": "stopped", "session": sid}
    assert gone(pid) and state(q, sid)["state"] == "stopped"
    assert succeeds(s, "agent-stop", {"session": sid})["result"] == "nothing was running"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def pulled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A quilt synced with a local bare remote, a collaborator's edit to `main.tex` fetched and awaiting incorporation."""
    import loom.sync as sync
    from loom.scan.quilt import load_quilt

    root = tmp_path / "quilt"
    (root / "drafting").mkdir(parents=True)
    git(root, "init", "-q", "-b", "quilt")
    for r in (root,):
        git(r, "config", "user.name", "Tester")
        git(r, "config", "user.email", "tester@example.org")
    (root / "config.toml").write_text(
        '[quilt]\nname = "test"\nmain = "drafting/main.tex"\ndrafting = "drafting"\ncanon = "canon"\nprefix = "zk"\nengine = "pdflatex"\n',
        encoding="utf-8",
    )
    (root / ".gitignore").write_text("build/\n.loom/serve.json\n", encoding="utf-8")
    source = (
        "\\documentclass{article}\n\\usepackage{loom}\n\\newtheorem{lemma}{Lemma}\n"
        "\\begin{document}\n\\begin{lemma}\\label{zk-0001}A\\end{lemma}\n\\end{document}\n"
    )
    (root / "drafting" / "main.tex").write_text(source, encoding="utf-8")
    (root / "loom.sty").write_text("% local support\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "private quilt")
    bare = tmp_path / "overleaf.git"
    subprocess.check_call(["git", "init", "-q", "--bare", str(bare)])
    git(root, "remote", "add", "origin", str(bare))
    git(root, "push", "-q", "origin", "HEAD:main")
    git(root, "fetch", "-q", "origin", "main")
    quilt = load_quilt(root)
    state = sync.configure(quilt, "origin", "main", "main.tex")
    monkeypatch.setattr(sync, "compile_tex", lambda *_a, **_k: SimpleNamespace(ok=True))
    sync.publish(quilt, state, push=True)
    other = tmp_path / "collaborator"
    subprocess.check_call(["git", "clone", "-q", "-b", "main", str(bare), str(other)])
    git(other, "config", "user.name", "Colleague")
    git(other, "config", "user.email", "colleague@example.org")
    (other / "main.tex").write_text(source.replace("zk-0001}A", "zk-0001}B"), encoding="utf-8")
    git(other, "commit", "-q", "-am", "edit statement")
    git(other, "push", "-q", "origin", "main")
    sync.fetch(quilt, state)
    return root


@case("sync-incorporate")
def _sync_incorporate(serve: Serve, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from loom.sync import SyncState

    (tmp_path / "unsynced").mkdir()
    s = serve(demo(tmp_path / "unsynced"))
    refuses(s, "sync-incorporate", {"incoming": "0" * 40, "base": "0" * 40}, 409, "sync-refused", "not configured")
    root = pulled(tmp_path, monkeypatch)
    s = serve(root)
    state = SyncState.read(root)
    before = (root / "drafting" / "main.tex").read_bytes()
    # pinned to the revision the page displayed: a different one changes nothing
    refuses(
        s,
        "sync-incorporate",
        {"incoming": "0" * 40, "base": state.integrated},
        400,
        "revision-changed",
        "reload Incoming",
    )
    assert (root / "drafting" / "main.tex").read_bytes() == before
    said = succeeds(s, "sync-incorporate", {"incoming": state.incoming, "base": state.integrated})
    assert said["result"]["integrated"] == state.incoming
    assert b"zk-0001}B" in (root / "drafting" / "main.tex").read_bytes()
    assert git(root, "show", "--format=", "--name-only", "HEAD").splitlines() == [".loom/source-sync.json"]
    assert git(root, "show", "--format=", "--name-only", "HEAD^").splitlines() == ["drafting/main.tex"]


def synthetic(serve: Serve, tmp_path: Path) -> tuple[ServeSession, Path]:
    """A copy of loom's synthetic quilt, served (which builds it)."""
    root = tmp_path / "synthetic"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", root, ignore=shutil.ignore_patterns("build", ".git"))
    return serve(root), root


@case("review-decision")
def _review_decision(serve: Serve, tmp_path: Path, _: pytest.MonkeyPatch) -> None:
    s, root = synthetic(serve, tmp_path)
    assert succeeds(s, "review-decision", {"key": "sy-0002", "status": "ok"})["result"] == "sy-0002: ok"
    raw = get(s.url + "build/manifest.json")[2]
    row = the(json.loads(raw)["unresolved"], lambda r: r["key"] == "sy-0002", "sy-0002's review row")
    assert row["status"] == "ok"
    refuses(s, "review-decision", {"key": "sy-9999", "status": "ok"}, 409, "not-unresolved", "sy-9999")


@case("review-finish")
def _review_finish(serve: Serve, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from loom.records.store import Records
    from loom.scan.quilt import load_quilt

    s, root = synthetic(serve, tmp_path)
    refuses(s, "review-finish", {}, 409, "nothing-pending", "no pending OK decisions")
    succeeds(s, "review-decision", {"key": "sy-0001", "status": "ok"})
    monkeypatch.setattr("loom.cli.review._master_compiles", lambda _result: (True, ""))
    monkeypatch.setattr("loom.cli.review._author", lambda _explicit, _root: "Test author")
    # the fixture's acceptance of sy-0001 is stale; finishing records a fresh one beside it
    stale = Records(root, load_quilt(root).history_dir).latest["sy-0001"]
    assert succeeds(s, "review-finish", {})["result"] == "accepted 1 keys"
    fresh = Records(root, load_quilt(root).history_dir).latest["sy-0001"]
    assert fresh != stale and fresh.author == "Test author", fresh
    raw = get(s.url + "build/manifest.json")[2]
    assert not [r for r in json.loads(raw)["unresolved"] if r["key"] == "sy-0001"]


@pytest.mark.parametrize(
    "endpoint",
    [pytest.param(e, marks=pytest.mark.poppler) if e == "locate" else e for e in sorted(CASES)],
)
def test_each_endpoint_writes_and_refuses_over_the_wire(
    endpoint: str, serve: Serve, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One success, with what the server wrote read back from the quilt, and one refusal with its status, code and message; `locate` needs the real pdftotext for its page's word boxes."""
    CASES[endpoint](serve, tmp_path, monkeypatch)


def test_every_capability_has_a_case_and_a_row_in_the_spec() -> None:
    """A capability served without a case above fails here, as does a case for one no longer served, and one specs/write-api.md does not list."""
    import re

    from loom.render.api import CAPABILITIES

    assert sorted(CASES) == sorted(CAPABILITIES)
    spec = (REPO.parent / "docs" / "specs" / "write-api.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"^\| `POST` \| `/_api/([\w-]+)`", spec, re.M))
    assert sorted(set(CAPABILITIES) - listed) == [], "served but not in specs/write-api.md's tables"
    assert sorted(listed - set(CAPABILITIES)) == [], "in specs/write-api.md's tables but not served"


def test_an_endpoint_not_served_is_a_404_naming_it(session) -> None:  # type: ignore[no-untyped-def]
    """An endpoint outside the list is a 404, which is what lets a viewer hide the affordance."""
    s, _ = session
    status, said = post(s.url + "_api/accept", {"keys": ["dm-0003"]})
    assert status == 404 and said == {"error": {"code": "unknown-endpoint", "message": "no endpoint accept"}}, said


def test_events_needs_a_session_and_reads_a_bad_since_as_the_start(session) -> None:  # type: ignore[no-untyped-def]
    from loom.mailbox import post as say

    s, d = session
    status, _, raw = get(s.url + "_api/events")
    assert status == 400
    sid = new_session(d)
    say(d, sid, "First.", WHO)
    status, _, raw = get(s.url + f"_api/events?session={sid}&since=abc")
    body = json.loads(raw)
    assert status == 200 and body["from"] == 0 and [e["body"] for e in body["events"]] == ["First."], body


def test_agent_stop_passes_the_csrf_gate_like_every_write(session) -> None:  # type: ignore[no-untyped-def]
    s, d = session
    status, said = post(s.url + "_api/agent-stop", {"session": new_session(d)}, token="")
    assert status == 403 and "X-Loom-Token" in said["error"]["message"], said
