"""`loom since`: what people did since an agent last looked, against its own marker, reported once and only once."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from loom.since import marker_path
from tests.helpers import json_of, ok
from tests.unit._quilts import demo, new_session

WHO = "A. Author"
AGENT = "Referee Agent"


def look(q: Path, *more: str, who: str = AGENT, env: dict[str, str] | None = None) -> dict[str, Any]:
    """One `loom since --json` as `who`; the report."""
    return json_of("since", "--as", who, "--json", *more, cwd=q, env=env)  # type: ignore[no-any-return]


def last_id(q: Path) -> str:
    return str(json.loads((q / "annotations" / "log.jsonl").read_text().splitlines()[-1])["id"])


@pytest.fixture
def q(tmp_path: Path) -> Path:
    """The demo with a fresh session, which is where a first look starts."""
    q = demo(tmp_path)
    new_session(q, "a sitting", WHO)
    return q


def test_a_first_look_reports_a_persons_annotations_whole_and_the_next_reports_nothing(q: Path) -> None:
    ok("annotate", "dm-0003", "Is this sharp?", "--kind", "question", "--quote", "finite set", "--as", WHO, cwd=q)
    ok("annotate", "dm-0004", "A gap here.", "--as", AGENT, cwd=q)
    mine = last_id(q)
    ok("annotate", "--reply", mine, "It is not; see dm-0004.", "--as", WHO, cwd=q)
    got = look(q)
    assert got["first"] is True and got["verdict"].startswith(f"your first look as {AGENT}, since the session opened")
    asked, answered = got["annotations"]
    assert (asked["target"], asked["kind"], asked["quote"], asked["body"]) == (
        "dm-0003",
        "question",
        "finite set",
        "Is this sharp?",
    )
    assert answered["act"] == "replied" and answered["yours"] is True and answered["to"] == AGENT
    assert all(a["by"] == WHO for a in got["annotations"]), "an agent's own annotation is no news to it"
    again = look(q)
    assert again["first"] is False and again["annotations"] == [] and again["verdict"].endswith(": nothing")


def test_a_record_of_the_markers_own_second_is_reported_once(q: Path) -> None:
    """Under one fixed clock every record carries the marker's second, so only what the marker carries tells old from new; the clock is set after the session's opening, which the real one stamped."""
    fixed = {"LOOM_FIXED_TIME": "2099-01-01T00:00:00Z"}
    ok("annotate", "dm-0002", "First.", "--as", WHO, cwd=q, env=fixed)
    assert [a["body"] for a in look(q, env=fixed)["annotations"]] == ["First."]
    ok("annotate", "dm-0003", "Second, in the same second.", "--as", WHO, cwd=q, env=fixed)
    assert [a["body"] for a in look(q, env=fixed)["annotations"]] == ["Second, in the same second."]
    assert look(q, env=fixed)["annotations"] == []


def test_what_a_person_settled_is_reported_with_whose_it_was(q: Path) -> None:
    ok("annotate", "dm-0003", "A gap here.", "--as", AGENT, cwd=q)
    gap = last_id(q)
    ok("annotate", "dm-0004", "And here.", "--as", AGENT, cwd=q)
    other = last_id(q)
    look(q)
    ok("annotate", "--resolve", gap, "Fixed in the source.", "--as", WHO, cwd=q)
    ok("annotate", "--discard", other, "Not a gap.", "--as", WHO, cwd=q)
    acts = {a["id"]: a for a in look(q)["acts"]}
    assert (acts[gap]["act"], acts[gap]["yours"], acts[gap]["body"]) == ("resolved", True, "Fixed in the source.")
    assert (acts[other]["act"], acts[other]["body"]) == ("discarded", "Not a gap.")
    # what a person wrote and withdrew in one window is no news at all
    ok("annotate", "dm-0002", "Never mind.", "--as", WHO, cwd=q)
    ok("annotate", "--discard", last_id(q), "--as", WHO, cwd=q)
    later = look(q)
    assert later["annotations"] == [] and later["acts"] == []


def test_an_acceptance_and_a_key_gone_stale_are_each_reported_once(q: Path) -> None:
    look(q)
    # staleness is the local reviewer's, as `loom status` shows it, so the acceptance is theirs
    config = Path(os.environ["XDG_CONFIG_HOME"]) / "loom" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f'[author]\nname = "{WHO}"\n')
    ok("accept", "dm-0002", cwd=q)
    got = look(q)
    assert [r["key"] for r in got["accepted"]] == ["dm-0002"] and got["stale"] == []
    node = next(p for p in (q / "nodes").glob("*.tex") if "\\label{dm-0002}" in p.read_text())
    text = node.read_text()
    node.write_text(text.replace("\\label{dm-0002}", "\\label{dm-0002} An added clause.", 1))
    stale = look(q)["stale"]
    assert [r["key"] for r in stale] == ["dm-0002"] and stale[0]["why"] == ["edited"]
    assert look(q)["stale"] == []


def test_the_research_state_reports_a_persons_writes_and_edits_by_hand_as_diffs(q: Path) -> None:
    ok("write", "state", "Goals: the parity theorem.\n", "--as", AGENT, cwd=q)
    look(q)
    page = q / "research-state.md"
    page.write_text(page.read_text() + "Open: the balanced case.\n")
    [edited] = look(q)["state"]
    assert edited["act"] == "edited" and edited["by"] is None and "+Open: the balanced case." in edited["diff"]
    from loom.pages import text_hash

    ok(
        "write",
        "state",
        "Goals: the parity theorem, both cases.\n",
        "--base",
        text_hash(page.read_text()),
        "--as",
        WHO,
        cwd=q,
    )
    [written] = look(q)["state"]
    assert (written["act"], written["by"]) == ("written", WHO) and "+Goals: the parity theorem, both cases." in written[
        "diff"
    ]
    ok("write", "state", "Goals: settled.\n", "--base", text_hash(page.read_text()), "--as", AGENT, cwd=q)
    assert look(q)["state"] == [], "the agent's own write is no news to it"


def test_what_a_person_said_is_reported_and_an_agents_words_are_not(q: Path) -> None:
    look(q)
    ok("session", "say", "Have a look at dm-0003.", "--as", WHO, cwd=q)
    ok("session", "say", "Looked; one gap.", "--as", AGENT, cwd=q)
    [said] = look(q)["said"]
    assert (said["by"], said["body"]) == (WHO, "Have a look at dm-0003.")


def test_each_name_has_its_own_marker_and_a_dry_run_leaves_it(q: Path) -> None:
    ok("annotate", "dm-0002", "Is this sharp?", "--as", WHO, cwd=q)
    look(q)
    assert marker_path(q, AGENT).is_file()
    assert len(look(q, who="Tutor Agent")["annotations"]) == 1, "another agent has not looked yet"
    ok("annotate", "dm-0003", "And this?", "--as", WHO, cwd=q)
    before = marker_path(q, AGENT).read_text()
    assert len(look(q, "--dry-run")["annotations"]) == 1
    assert marker_path(q, AGENT).read_text() == before
    text = ok("since", "--as", AGENT, cwd=q).stdout
    assert text.startswith("since you last looked") and "annotations and replies (1)" in text and "And this?" in text


def test_the_marker_is_neither_committed_nor_watched(q: Path) -> None:
    from loom.gitignore import MANAGED
    from loom.render.watch import snapshot

    look(q)
    assert ".loom/since/" in MANAGED
    assert ".loom/since/" in (q / ".gitignore").read_text()
    assert marker_path(q, AGENT) not in snapshot(q), "a look would rebuild the site"
