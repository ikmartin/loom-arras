"""The checked-in CLI reference equals what the command tree generates (book 13.4)."""

from __future__ import annotations

import runpy
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_cli_reference_matches_checked_in() -> None:
    mod = runpy.run_path(str(REPO / "scripts" / "gen_cli_reference.py"), run_name="not_main")
    generated = mod["generate"]()
    assert (REPO / "docs" / "cli-reference.md").read_text(encoding="utf-8") == generated, (
        "run scripts/gen_cli_reference.py"
    )
    assert "## `loom ai`" in generated and "`loom digest extract`" in generated and "`loom upgrade`" in generated


def test_the_books_reference_is_the_generated_one() -> None:
    """Book 12.2 is the generated reference with every heading one level down; it drifts from the code as silently as the checked-in file would."""
    mod = runpy.run_path(str(REPO / "scripts" / "gen_cli_reference.py"), run_name="not_main")
    book = mod["BOOK"].read_text(encoding="utf-8")
    assert book == mod["spliced"](book, mod["generate"]()), "run scripts/gen_cli_reference.py"
