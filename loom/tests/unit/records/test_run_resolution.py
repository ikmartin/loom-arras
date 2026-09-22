"""`--session` reaches the session the author named, and never creates anything (the beta experiment's first finding)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from click.testing import CliRunner

from loom.cli import main


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def quilt(tmp_path: Path) -> Path:
    d = tmp_path / "q"
    assert run("init", str(d), "--demo", cwd=tmp_path).exit_code == 0  # --demo ships the ai layer
    return d


def started(d: Path, name: str) -> str:
    r = run("ai", "start", name, cwd=d)
    assert r.exit_code == 0, r.output
    return r.output.strip().splitlines()[-1].strip()


def test_a_title_reaches_the_session_it_names(tmp_path: Path) -> None:
    """The failure this test exists for: a whole sitting's annotations filed under a run that does not exist, silently."""
    d = quilt(tmp_path)
    sid = started(d, "early structural results review")

    # a read command naming the session by its title, which used to mkdir ./early/ at the quilt root
    assert run("source", "dm-0003", "--session", "early structural results review", cwd=d).exit_code == 0
    assert not (d / "early").exists(), "an unmatched --session must never create a directory"
    assert (d / ".loom" / "sessions" / sid / "run.log").is_file(), "the title must reach the real session's log"

    # and a write command files against the same session
    said = run("comment", "dm-0003", "a finding", "--kind", "question", "--author", "A. Author", cwd=d)
    assert said.exit_code == 0, said.output
    events = [json.loads(x) for x in (d / "annotations" / "log.jsonl").read_text().splitlines() if x.strip()]
    created = [e for e in events if e["event"] == "created"]
    assert created[-1]["session"] == sid, f"filed under {created[-1]['session']!r}, not the session that made it"

    # which is what makes the re-check contract work
    out = run("ai", "findings", "--session", "early structural results review", "--json", cwd=d)
    assert out.exit_code == 0
    assert len(json.loads(out.output)["findings"]) == 1


def test_an_unmatched_session_is_an_error_not_a_directory(tmp_path: Path) -> None:
    d = quilt(tmp_path)
    started(d, "a real sitting")
    before = sorted(p.name for p in d.iterdir())

    r = run("source", "dm-0003", "--session", "no-such-session-at-all", cwd=d)
    assert r.exit_code == 2, r.output
    assert "no session matches" in r.output
    assert sorted(p.name for p in d.iterdir()) == before, "nothing may be created at the quilt root"


def test_a_session_is_never_a_path(tmp_path: Path) -> None:
    """`--run build` used to drop a run.log into the author's own directories; a session is an id, so there is no path to abuse."""
    d = quilt(tmp_path)
    started(d, "a real sitting")
    (d / "build").mkdir(exist_ok=True)

    r = run("source", "dm-0003", "--session", "build", cwd=d)
    assert r.exit_code == 2, r.output
    assert "no session matches" in r.output
    assert not (d / "build" / "run.log").exists()


def test_an_ambiguous_title_names_its_matches(tmp_path: Path) -> None:
    """Titles are the author's and may repeat; the id never does, which is why the id is the address."""
    d = quilt(tmp_path)
    started(d, "morning pass")
    started(d, "morning pass")
    r = run("source", "dm-0003", "--session", "morning pass", cwd=d)
    assert r.exit_code == 2
    assert "matches 2 sessions" in r.output and "morning pass" in r.output
