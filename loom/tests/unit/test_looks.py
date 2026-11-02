"""A person's look at the open files (plan 0.22.8): what Review's Changes counts from, and keep and undo, the author's verbs on a change."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers import json_of, ok, refused, run
from tests.unit._quilts import demo


@pytest.fixture
def q(tmp_path: Path) -> Path:
    from loom.scan.quilt import save_author

    save_author("Tester")
    root = demo(tmp_path)
    (root / "notes").mkdir()
    (root / "notes" / "a.md").write_text("# A\n\nfirst\n", encoding="utf-8")
    (root / "notes" / "fig.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    return root


def changes(q: Path) -> dict[str, str]:
    return {c["path"]: c["kind"] for c in json_of("changes", "--json", cwd=q)["changes"]}


def test_a_look_holds_every_open_text_file_and_nothing_else(q: Path) -> None:
    """Shown text files only, LaTeX included; an image, a hidden file and loom's own records are left out, and each text is kept by its hash."""
    from loom.looks import read_look
    from loom.records.snapshots import read_raw
    from loom.scan.quilt import load_quilt

    (q / ".hidden.md").write_text("no", encoding="utf-8")
    assert json_of("changes", "--json", cwd=q)["look"] is None
    ok("changes", "--keep-all", cwd=q)
    look = read_look(q, "Tester")
    assert look is not None and look.who == "Tester"
    assert "notes/a.md" in look.files and "drafting/main.tex" in look.files
    assert not [p for p in look.files if p.startswith(".") or p.endswith(".png")]
    quilt = load_quilt(q)
    assert read_raw(q, look.files["notes/a.md"], quilt.history_dir) == "# A\n\nfirst\n"
    assert (q / ".loom/looked/tester.json").is_file()
    assert changes(q) == {}


def test_changes_since_the_look_are_changed_new_and_gone_each_with_its_diff(q: Path) -> None:
    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    (q / "notes/b.md").write_text("new\n", encoding="utf-8")
    (q / "README.md").unlink()
    got = json_of("changes", "--json", cwd=q)["changes"]
    assert {c["path"]: c["kind"] for c in got} == {"notes/a.md": "changed", "notes/b.md": "new", "README.md": "gone"}
    diff = next(c["diff"] for c in got if c["path"] == "notes/a.md")
    assert "-first" in diff and "+second" in diff and diff.startswith("--- a/notes/a.md")
    # the build publishes them, each diff beside the manifest
    run("build", cwd=q)
    m = json.loads((q / ".loom/build/manifest.json").read_text())
    assert {c["path"]: c["kind"] for c in m["changes"]} == {
        "notes/a.md": "changed",
        "notes/b.md": "new",
        "README.md": "gone",
    }
    assert m["changes_since"]["who"] == "Tester"
    body = next(c for c in m["changes"] if c["path"] == "notes/a.md")["diff"]
    assert "+second" in (q / ".loom/build" / body).read_text()


def test_keep_takes_one_file_or_all_into_the_look(q: Path) -> None:
    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    (q / "notes/b.md").write_text("new\n", encoding="utf-8")
    ok("changes", "--keep", "notes/a.md", cwd=q)
    assert changes(q) == {"notes/b.md": "new"}
    refused("changes", "--keep", "notes/zzz.md", cwd=q, code=2, match="has not changed since your look")
    ok("changes", "--keep-all", cwd=q)
    assert changes(q) == {}


def test_undo_puts_the_text_back_and_keeps_what_it_replaced(q: Path) -> None:
    """P7: the text undone is kept in the history first, and the ledger names both; a file gone since the look comes back, and one new since has nothing to go back to."""
    from loom.history.ledger import load_history
    from loom.records.snapshots import read_raw
    from loom.scan.quilt import load_quilt

    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text("# A\n\nan agent's edit\n", encoding="utf-8")
    (q / "README.md").unlink()
    (q / "notes/b.md").write_text("new\n", encoding="utf-8")
    ok("changes", "--undo", "notes/a.md", cwd=q)
    assert (q / "notes/a.md").read_text() == "# A\n\nfirst\n"
    ok("changes", "--undo", "README.md", cwd=q)
    assert (q / "README.md").is_file()
    refused("changes", "--undo", "notes/b.md", cwd=q, code=2, match="delete it yourself, or keep it")
    assert changes(q) == {"notes/b.md": "new"}
    quilt = load_quilt(q)
    undone = [e for e in load_history(quilt.history_dir).entries if e.action == "undo"]
    assert [e.data["path"] for e in undone] == ["notes/a.md", "README.md"]
    assert read_raw(q, undone[0].data["from"], quilt.history_dir) == "# A\n\nan agent's edit\n"


def test_keeping_and_undoing_are_the_authors(q: Path) -> None:
    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text("changed\n", encoding="utf-8")
    for args in (("--keep-all",), ("--undo", "notes/a.md")):
        refused("changes", *args, cwd=q, code=2, match="author's", env={"AI_AGENT": "1"})
    assert (q / "notes/a.md").read_text() == "changed\n"
