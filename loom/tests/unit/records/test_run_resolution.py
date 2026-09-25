"""`--session` reaches the session the author named, and never creates anything (the beta experiment's first finding)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers import json_of, ok, refused


def quilt(tmp_path: Path) -> Path:
    d = tmp_path / "q"
    ok("init", str(d), "--demo", cwd=tmp_path)  # --demo ships the ai layer
    return d


def started(d: Path, name: str) -> str:
    r = ok("ai", "start", name, cwd=d)
    return r.output.strip().splitlines()[-1].strip()


def test_a_title_reaches_the_session_it_names(tmp_path: Path) -> None:
    """The failure this test exists for: a whole sitting's annotations filed under a run that does not exist, silently."""
    d = quilt(tmp_path)
    sid = started(d, "early structural results review")

    # a read command naming the session by its title, which used to mkdir ./early/ at the quilt root
    ok("source", "dm-0003", "--session", "early structural results review", cwd=d)
    assert not (d / "early").exists(), "an unmatched --session must never create a directory"
    assert (d / ".loom" / "sessions" / sid / "run.log").is_file(), "the title must reach the real session's log"

    # and a write command files against the same session
    ok("comment", "dm-0003", "a finding", "--kind", "question", "--author", "A. Author", cwd=d)
    events = [json.loads(x) for x in (d / "annotations" / "log.jsonl").read_text().splitlines() if x.strip()]
    created = [e for e in events if e["event"] == "created"]
    assert created[-1]["session"] == sid, f"filed under {created[-1]['session']!r}, not the session that made it"

    # which is what makes the re-check contract work
    out = json_of("ai", "findings", "--session", "early structural results review", "--json", cwd=d)
    assert len(out["findings"]) == 1


@pytest.mark.parametrize("name", ["no-such-session-at-all", "build"])
def test_an_unmatched_session_is_an_error_and_never_a_path(tmp_path: Path, name: str) -> None:
    """A session is an id, so there is no path to abuse: an unmatched `--session`, even one naming a directory of the author's, is refused and creates nothing, at the quilt root or inside that directory."""
    d = quilt(tmp_path)
    started(d, "a real sitting")
    (d / "build").mkdir(exist_ok=True)
    before = sorted(p.name for p in d.iterdir())

    refused("source", "dm-0003", "--session", name, cwd=d, code=2, match="no session matches")
    assert sorted(p.name for p in d.iterdir()) == before, "nothing may be created at the quilt root"
    assert not (d / "build" / "run.log").exists()


def test_an_ambiguous_title_names_its_matches(tmp_path: Path) -> None:
    """Titles are the author's and may repeat; the id never does, which is why the id is the address."""
    d = quilt(tmp_path)
    started(d, "morning pass")
    started(d, "morning pass")
    r = refused("source", "dm-0003", "--session", "morning pass", cwd=d, code=2, match="matches 2 sessions")
    assert "morning pass" in r.output
