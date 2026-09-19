"""The fixture quilts are the generator's output (book 14.3): `scripts/gen_quilts.py --check` regenerates each and compares byte for byte.

Editing a quilt by hand, or an asset the generator draws on, fails here; that is the alarm this test exists for.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "gen_quilts.py"


# The showcase is TeX-tier only because `loom refs scan` reads the page text of the two PDFs it files, which
# needs the real poppler; the shim on the unit tier writes nothing and the check would fail on empty pages.
@pytest.mark.parametrize("which", ["demo", "synthetic", pytest.param("showcase", marks=pytest.mark.tex)])
def test_the_checked_in_quilt_is_what_the_generator_writes(which: str) -> None:
    if which == "showcase" and not shutil.which("pdftotext"):
        pytest.skip("the showcase files two PDFs into its store, and their page text comes from poppler")
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
