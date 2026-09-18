"""The fixture quilts are the generator's output (book 14.3): `scripts/gen_quilts.py --check` regenerates both and compares byte for byte.

Editing a quilt by hand, or an asset the generator draws on, fails here; that is the alarm this test exists for.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "gen_quilts.py"


@pytest.mark.parametrize("which", ["demo", "synthetic"])
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
