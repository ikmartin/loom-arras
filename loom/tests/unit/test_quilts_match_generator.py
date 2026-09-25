"""The fixture quilts are the generator's output (book 14.3): `scripts/gen_quilts.py --check` regenerates each and compares byte for byte.

Editing a quilt by hand, or an asset the generator draws on, fails here; that is the alarm this test exists for.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "gen_quilts.py"


# The demo and the showcase need the real poppler: `loom refs scan` reads the page text of the PDFs they file, and the shim on the unit tier writes nothing, so the work would be filed under a content hash rather than the identifier its first page prints.
@pytest.mark.parametrize(
    "which",
    [pytest.param("demo", marks=pytest.mark.poppler), "synthetic", pytest.param("showcase", marks=pytest.mark.poppler)],
)
def test_the_checked_in_quilt_is_what_the_generator_writes(which: str) -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), which, "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_synthetic_quilt_carries_the_intended_errors() -> None:
    """Four errors on purpose, one per fault a source contract can carry: a reference to nothing, an inclusion of nothing, a file included twice, and an id defined twice."""
    lines = (REPO / "tests" / "quilts" / "synthetic" / "EXPECTED-LINT.txt").read_text(encoding="utf-8").splitlines()
    errors = sorted(line.split()[1] for line in lines if line.startswith("error"))
    assert errors == ["dangling-link", "dangling-link", "double-inclusion", "duplicate-id", "missing-include"]


def test_the_showcase_carries_the_faults_it_is_meant_to_show() -> None:
    """One error on purpose -- a sketch made live again over the node file its own atomize wrote -- and the four facts about a lived-in quilt that the viewer has something to say about."""
    lines = (REPO / "tests" / "quilts" / "showcase" / "EXPECTED-LINT.txt").read_text(encoding="utf-8").splitlines()
    codes = sorted(line.split()[1] for line in lines)
    assert [line.split()[1] for line in lines if line.startswith("error")] == ["duplicate-id"]
    for code in ("loom:detached-annotation", "loom:missing-proof", "loom:unmatched-postnote", "unreachable"):
        assert code in codes, code


def test_the_showcase_referee_findings_are_the_agents() -> None:
    """The showcase's referee findings are recorded as the agent's, so none goes back to the agent in the author's packet."""
    log = REPO / "tests" / "quilts" / "showcase" / "annotations" / "log.jsonl"
    events = [json.loads(line) for line in log.read_text().splitlines()]
    first = {f"a-2026-09-16-000{i}" for i in range(1, 6)}
    got = {e["id"]: (e["author"], e["kind"]) for e in events if e.get("event") == "created" and e.get("id") in first}
    assert got == {i: ("Referee (Agent)", "agent") for i in first}
