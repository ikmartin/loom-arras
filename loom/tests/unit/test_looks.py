"""A person's look at the open files (plan 0.22.8): what the changes waiting on them are counted from, and keep and discard, the author's verbs on a change (`pending.py`)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers import json_of, ok, refused, run
from tests.unit._quilts import demo, track_edits


@pytest.fixture
def q(tmp_path: Path) -> Path:
    from loom.scan.quilt import save_author

    save_author("Tester")
    root = track_edits(demo(tmp_path))
    (root / "notes").mkdir()
    (root / "notes" / "a.md").write_text("# A\n\nfirst\n", encoding="utf-8")
    (root / "notes" / "fig.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    return root


def changes(q: Path) -> dict[str, str]:
    """Each in-place change's path and new words: the demo's suggested edit aside."""
    return {c["path"]: c["new"] for c in json_of("changes", "--json", cwd=q)["changes"] if c["kind"] == "edit"}


def test_a_look_holds_every_open_text_file_and_nothing_else(q: Path) -> None:
    """Shown text files only, LaTeX included; an image, a hidden file and loom's own records are left out, and each text is kept by its hash."""
    from loom.looks import read_look
    from loom.records.snapshots import read_raw
    from loom.scan.quilt import load_quilt

    (q / ".hidden.md").write_text("no", encoding="utf-8")
    assert json_of("changes", "--json", cwd=q)["look"] is None
    assert ok("changes", "--keep-all", cwd=q).stdout.startswith("took your first look")
    look = read_look(q, "Tester")
    assert look is not None and look.who == "Tester"
    assert "notes/a.md" in look.files and "drafting/main.tex" in look.files
    assert not [p for p in look.files if p.startswith(".") or p.endswith(".png")]
    assert read_raw(q, look.files["notes/a.md"], load_quilt(q).history_dir) == "# A\n\nfirst\n"
    assert (q / ".loom/looked/tester.json").is_file()
    assert changes(q) == {}


def test_changes_since_the_look_are_in_changed_new_and_gone_files_each_with_its_patch(q: Path) -> None:
    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    (q / "notes/b.md").write_text("new\n", encoding="utf-8")
    (q / "README.md").unlink()
    assert changes(q) == {"notes/a.md": "second", "notes/b.md": "new", "README.md": ""}
    run("build", cwd=q)
    m = json.loads((q / ".loom/build/manifest.json").read_text())
    assert m["changes_since"]["who"] == "Tester"
    row = next(c for c in m["changes"] if c["path"] == "notes/a.md")
    assert (row["old"], row["new"], row["documents"]) == ("first", "second", [])
    patch = (q / ".loom/build" / row["diff"]).read_text()
    assert patch.startswith("--- a/notes/a.md") and "-first" in patch and "+second" in patch


def test_keep_takes_a_change_into_the_look_and_discard_puts_its_old_words_back(q: Path) -> None:
    """P7: what a discard sets aside is kept in the history first, and the ledger names the change; a file gone since the look comes back, and one new since is removed."""
    from loom.history.ledger import load_history
    from loom.records.snapshots import read_raw
    from loom.scan.quilt import load_quilt

    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text("# A\n\nan agent's edit\n", encoding="utf-8")
    (q / "README.md").unlink()
    (q / "notes/b.md").write_text("new\n", encoding="utf-8")
    ok("changes", "--discard", "notes/a.md", cwd=q)
    assert (q / "notes/a.md").read_text() == "# A\n\nfirst\n"
    ok("changes", "--discard", "README.md", cwd=q)
    assert (q / "README.md").is_file()
    ok("changes", "--discard", "notes/b.md", cwd=q)
    assert not (q / "notes/b.md").exists() and changes(q) == {}
    quilt = load_quilt(q)
    undone = [e for e in load_history(quilt.history_dir).entries if e.action == "undo"]
    assert [e.data["path"] for e in undone] == ["notes/a.md", "README.md", "notes/b.md"]
    assert read_raw(q, undone[0].data["from"], quilt.history_dir) == "# A\n\nan agent's edit\n"
    assert undone[2].data["to"] is None and read_raw(q, undone[2].data["from"], quilt.history_dir) == "new\n"
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    ok("changes", "--keep", "notes/a.md", cwd=q)
    assert changes(q) == {} and (q / "notes/a.md").read_text() == "# A\n\nsecond\n"


def test_keeping_and_discarding_are_the_authors(q: Path) -> None:
    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text("changed\n", encoding="utf-8")
    for args in (("--keep-all",), ("--discard", "notes/a.md")):
        refused("changes", *args, cwd=q, code=2, match="author's", env={"AI_AGENT": "1"})
    assert (q / "notes/a.md").read_text() == "changed\n"


def test_keeping_one_change_leaves_the_time_of_the_look(q: Path) -> None:
    """The look's time is the person's last look at everything, so the changes still listed are still since it."""
    from loom.looks import read_look

    ok("changes", "--keep-all", cwd=q)
    when = read_look(q, "Tester").when  # type: ignore[union-attr]
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    (q / "notes/b.md").write_text("new\n", encoding="utf-8")
    ok("changes", "--keep", "notes/a.md", cwd=q)
    assert read_look(q, "Tester").when == when  # type: ignore[union-attr]
    assert changes(q) == {"notes/b.md": "new"}


NODE = "drafting/nodes/dm-0001.tex"


def test_accepting_keeps_only_the_changes_that_touch_nothing_else(q: Path) -> None:
    """What the viewer's Accept keeps: a change wholly inside the blocks accepted; one in no block stays."""
    from loom.pending import keep_accepted
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    ok("changes", "--keep-all", cwd=q)
    node = q / NODE
    text = node.read_text()
    inside = text[: text.index("\\end{")].rstrip().rsplit("\n", 1)[-1]
    node.write_text(text.replace(inside, inside + " Indeed.", 1), encoding="utf-8")
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    result = scan(load_quilt(q))
    key = next(c["key"] for c in json_of("changes", "--json", cwd=q)["changes"] if c["path"] == NODE)
    assert keep_accepted(result, "Tester", ["some-other-key"]) == []
    assert keep_accepted(result, "Tester", [key]) == [NODE]
    assert changes(q) == {"notes/a.md": "second"}


def test_without_tracking_no_edit_in_place_waits_and_no_look_is_taken(q: Path) -> None:
    """Off, the default: Keep all takes no look, an edit in place is no change, and the manifest says nothing of a look; a suggested edit still waits."""
    from loom.looks import read_look

    track_edits(q, on=False)
    ok("changes", "--keep-all", cwd=q)
    assert read_look(q, "Tester") is None
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    listed = json_of("changes", "--json", cwd=q)
    assert changes(q) == {} and listed["look"] is None
    assert "not tracked" in ok("changes", cwd=q).stdout
    run("build", cwd=q)
    m = json.loads((q / ".loom/build/manifest.json").read_text())
    assert "changes_since" not in m and m["config"]["review"] == {"track_edits": False}
    assert not [c for c in m["changes"] if c["kind"] == "edit"]


def test_serve_takes_a_first_look_only_where_edits_are_tracked(q: Path) -> None:
    from loom.looks import read_look
    from loom.render.serve import ServeSession
    from loom.scan.quilt import load_quilt

    track_edits(q, on=False)
    ServeSession(load_quilt(q), q, port=0, compile_masters=False).first_look()
    assert read_look(q, "Tester") is None
    track_edits(q)
    ServeSession(load_quilt(q), q, port=0, compile_masters=False).first_look()
    assert read_look(q, "Tester") is not None


def test_latexs_auxiliary_files_are_in_no_look_and_an_old_look_holding_one_reports_nothing(q: Path) -> None:
    """What a compile writes beside its document, as an editor compiling in place leaves it, is neither in the look nor a change; a look taken before they were left out does not report one as gone."""
    from loom.looks import _write, read_look

    for name in ("main.aux", "main.log", "main.fls", "main.fdb_latexmk"):
        (q / "drafting" / name).write_text("written by a compile\n", encoding="utf-8")
    ok("changes", "--keep-all", cwd=q)
    look = read_look(q, "Tester")
    assert look is not None and not [
        p for p in look.files if p.startswith("drafting/main.") and p != "drafting/main.tex"
    ]
    (q / "drafting/main.log").write_text("written again\n", encoding="utf-8")
    look.files["drafting/main.aux"] = look.files["notes/a.md"]
    _write(q, look)
    (q / "drafting/main.aux").unlink()
    assert changes(q) == {}


def test_turning_tracking_on_in_settings_takes_the_look_then(q: Path) -> None:
    from loom.looks import read_look
    from loom.render.api import handle

    track_edits(q, on=False)
    said = handle(q, "settings-save", {"changes": {"review.track_edits": True}, "author": "Tester"})["result"]
    assert "took your look" in said and read_look(q, "Tester") is not None
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    assert changes(q) == {"notes/a.md": "second"}
    # saved again while on, the look stands, and the edit with it
    handle(q, "settings-save", {"changes": {"review.track_edits": True}, "author": "Tester"})
    assert changes(q) == {"notes/a.md": "second"}


def test_a_track_edits_that_is_not_a_boolean_is_off_and_warned_of() -> None:
    from loom.scan.quilt import QuiltConfig

    cfg = QuiltConfig.from_dict({"quilt": {"name": "x"}, "review": {"track_edits": "yes"}})
    assert cfg.track_edits is False and any("review.track_edits" in w for w in cfg.warnings)
    assert QuiltConfig.from_dict({"quilt": {"name": "x"}, "review": {"track_edits": True}}).track_edits is True
