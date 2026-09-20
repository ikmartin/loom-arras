"""`--run` reaches the run the author named, and never creates a directory (the beta experiment's first finding)."""

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


def test_a_prefix_reaches_the_run_it_names(tmp_path: Path) -> None:
    """The failure this test exists for: a whole session's annotations filed under a run that does not exist, silently."""
    d = quilt(tmp_path)
    rel = started(d, "early structural results review")

    # a read command with a prefix, which used to mkdir ./early/ at the quilt root
    assert run("source", "dm-0003", "--run", "early", cwd=d).exit_code == 0
    assert not (d / "early").exists(), "an unmatched --run must never create a directory"
    assert (d / rel / "run.log").is_file(), "the prefix must reach the real run's log"

    # and a write command with the same prefix files against the same run
    assert run("comment", "dm-0003", "a finding", "--kind", "question", "--run", "early", cwd=d).exit_code == 0
    events = [json.loads(x) for x in (d / "annotations" / "log.jsonl").read_text().splitlines() if x.strip()]
    created = [e for e in events if e["event"] == "created"]
    assert created[-1]["run"] == rel, f"filed under {created[-1]['run']!r}, not the run that made it"

    # which is what makes the re-check contract work
    out = run("ai", "findings", "--run", "early structural results review", "--json", cwd=d)
    assert out.exit_code == 0
    assert len(json.loads(out.output)["findings"]) == 1


def test_an_unmatched_run_is_an_error_not_a_directory(tmp_path: Path) -> None:
    d = quilt(tmp_path)
    started(d, "a real run")
    before = sorted(p.name for p in d.iterdir())

    r = run("source", "dm-0003", "--run", "no-such-run-at-all", cwd=d)
    assert r.exit_code == 2, r.output
    assert "no run matches" in r.output
    assert sorted(p.name for p in d.iterdir()) == before, "nothing may be created at the quilt root"


def test_a_run_outside_the_runs_directory_is_refused(tmp_path: Path) -> None:
    """`--run build` used to drop a run.log into the author's own directories; `drafting`, `nodes` and `canon` were reachable identically."""
    d = quilt(tmp_path)
    started(d, "a real run")
    (d / "build").mkdir(exist_ok=True)

    r = run("source", "dm-0003", "--run", "build", cwd=d)
    assert r.exit_code == 2, r.output
    assert "not under ai/runs/" in r.output
    assert not (d / "build" / "run.log").exists()


def test_an_ambiguous_prefix_names_its_matches(tmp_path: Path) -> None:
    d = quilt(tmp_path)
    started(d, "early one")
    started(d, "early two")
    r = run("source", "dm-0003", "--run", "early", cwd=d)
    assert r.exit_code == 2
    assert "matches 2 runs" in r.output and "early one" in r.output
