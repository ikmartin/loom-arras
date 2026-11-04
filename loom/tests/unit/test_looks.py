"""A person's look at the open files (plan 0.22.8): what Review's Your Changes counts from, and keep and undo, the author's verbs on a change."""

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
    """P7: the text undone is kept in the history first, and the ledger names both; a file gone since the look comes back, and one new since is removed."""
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
    # a file new since the look is removed, its text kept first
    ok("changes", "--undo", "notes/b.md", cwd=q)
    assert not (q / "notes/b.md").exists()
    assert changes(q) == {}
    refused("changes", "--undo", "notes/zzz.md", cwd=q, code=2, match="has not changed since your look")
    quilt = load_quilt(q)
    undone = [e for e in load_history(quilt.history_dir).entries if e.action == "undo"]
    assert [e.data["path"] for e in undone] == ["notes/a.md", "README.md", "notes/b.md"]
    assert read_raw(q, undone[0].data["from"], quilt.history_dir) == "# A\n\nan agent's edit\n"
    assert undone[2].data["to"] is None and read_raw(q, undone[2].data["from"], quilt.history_dir) == "new\n"


def test_keeping_and_undoing_are_the_authors(q: Path) -> None:
    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text("changed\n", encoding="utf-8")
    for args in (("--keep-all",), ("--undo", "notes/a.md")):
        refused("changes", *args, cwd=q, code=2, match="author's", env={"AI_AGENT": "1"})
    assert (q / "notes/a.md").read_text() == "changed\n"


def test_keeping_one_file_leaves_the_time_of_the_look(q: Path) -> None:
    """The look's time is the person's last look at everything, so the changes still listed are still since it."""
    from loom.looks import read_look

    ok("changes", "--keep-all", cwd=q)
    when = read_look(q, "Tester").when  # type: ignore[union-attr]
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    (q / "notes/b.md").write_text("new\n", encoding="utf-8")
    ok("changes", "--keep", "notes/a.md", cwd=q)
    assert read_look(q, "Tester").when == when  # type: ignore[union-attr]
    assert changes(q) == {"notes/b.md": "new"}


TWO = "".join(f"line {i}\n" for i in range(1, 21))


def two_edits(q: Path) -> None:
    """Two changes to one file, far enough apart to be two hunks: line 2 and line 18."""
    (q / "notes/a.md").write_text(TWO, encoding="utf-8")
    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text(
        TWO.replace("line 2\n", "line two\n").replace("line 18\n", "line eighteen\n"), encoding="utf-8"
    )


def test_one_change_of_a_file_is_kept_or_undone_alone(q: Path) -> None:
    """A hunk is one of the diff's `@@` groups, numbered as the list shows them; keeping one leaves the other a change, undoing one puts only it back."""
    from loom.looks import changes as changed
    from loom.scan.quilt import load_quilt

    two_edits(q)
    got = json_of("changes", "--json", cwd=q)["changes"]
    assert [(c["path"], c["hunks"]) for c in got] == [("notes/a.md", 2)]
    ok("changes", "--keep", "notes/a.md", "--hunk", "0", cwd=q)
    left = changed(load_quilt(q), "Tester")
    assert len(left) == 1 and left[0].hunks == 1 and "+line eighteen" in left[0].diff and "line two" not in left[0].diff
    ok("changes", "--undo", "notes/a.md", "--hunk", "0", cwd=q)
    assert (q / "notes/a.md").read_text() == TWO.replace("line 2\n", "line two\n")
    assert changes(q) == {}
    two_edits(q)
    refused("changes", "--keep", "notes/a.md", "--hunk", "5", cwd=q, code=2, match="no change number 5")
    refused("changes", "--hunk", "0", cwd=q, code=2, match="--hunk names a change")


def test_several_changes_of_a_file_are_one_act(q: Path) -> None:
    """`--hunk` may repeat, and the ledger names them all."""
    from loom.history.ledger import load_history
    from loom.scan.quilt import load_quilt

    (q / "notes/a.md").write_text(TWO, encoding="utf-8")
    ok("changes", "--keep-all", cwd=q)
    (q / "notes/a.md").write_text(
        TWO.replace("line 2\n", "line two\n").replace("line 18\n", "line eighteen\n"), encoding="utf-8"
    )
    said = ok("changes", "--keep", "notes/a.md", "--hunk", "1", "--hunk", "0", cwd=q).stdout
    assert "kept changes 1, 0 of notes/a.md" in said
    assert changes(q) == {}
    line = load_history(load_quilt(q).history_dir).entries[-1]
    assert line.action == "keep" and line.get("hunks") == [1, 0]


def test_an_act_on_a_page_drawn_before_the_file_moved_is_refused(q: Path) -> None:
    """`seen` is the file's hash as the page showed it, so a hunk's number never names a change the person did not see."""
    from loom.looks import LookRefused, keep, undo
    from loom.looks import changes as changed
    from loom.scan.quilt import load_quilt

    two_edits(q)
    quilt = load_quilt(q)
    seen = changed(quilt, "Tester")[0].after
    (q / "notes/a.md").write_text("moved on\n", encoding="utf-8")
    for act in (keep, undo):
        with pytest.raises(LookRefused) as exc:
            act(quilt, "Tester", "notes/a.md", hunks=[0], seen=seen)
        assert exc.value.code == "stale"
    assert (q / "notes/a.md").read_text() == "moved on\n"


def test_the_build_publishes_each_changes_hash_and_hunks(q: Path) -> None:
    two_edits(q)
    run("build", cwd=q)
    m = json.loads((q / ".loom/build/manifest.json").read_text())
    entry = next(c for c in m["changes"] if c["path"] == "notes/a.md")
    from loom.scan.hashing import sha256

    assert entry["hunks"] == 2 and entry["hash"] == sha256((q / "notes/a.md").read_text())


NODE = "drafting/nodes/dm-0001.tex"


def _block_key(q: Path) -> str:
    """The first statement in the demo's first node file, by its manifest key."""
    run("build", cwd=q)
    m = json.loads((q / ".loom/build/manifest.json").read_text())
    return next(k for k, v in m["keys"].items() if v["file"] == NODE and v["kind"] == "statement")


def _entry(q: Path, path: str) -> dict[str, object]:
    run("build", cwd=q)
    m = json.loads((q / ".loom/build/manifest.json").read_text())
    return next(c for c in m["changes"] if c["path"] == path)


def test_the_build_says_which_blocks_each_change_touches_and_which_documents_read_the_file(q: Path) -> None:
    key = _block_key(q)
    ok("changes", "--keep-all", cwd=q)
    node = q / NODE
    text = node.read_text()
    # the last line inside the statement
    inside = text[: text.index("\\end{")].rstrip().rsplit("\n", 1)[-1]
    assert inside.strip(), "the statement has a last line to change"
    node.write_text(text.replace(inside, inside + " Indeed.", 1), encoding="utf-8")
    entry = _entry(q, NODE)
    assert entry["blocks"] == [[key]]
    assert entry["documents"] == ["drafting/main.tex", "drafting/outline.tex"]


def test_text_outside_any_block_touches_none_and_a_file_in_no_document_is_in_none(q: Path) -> None:
    ok("changes", "--keep-all", cwd=q)
    main = q / "drafting/main.tex"
    main.write_text(
        main.read_text().replace(r"\begin{document}", r"\begin{document}" + "\nA new sentence of prose.\n", 1)
    )
    assert _entry(q, "drafting/main.tex")["blocks"] == [[]]
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    note = _entry(q, "notes/a.md")
    assert note["blocks"] == [[]] and note["documents"] == []


def test_accepting_keeps_only_the_changes_that_touch_nothing_else(q: Path) -> None:
    """What the viewer's Accept keeps: a change wholly inside the blocks accepted; one touching another block too stays."""
    from loom.looks import blocks_of, keep_accepted
    from loom.looks import changes as changed
    from loom.scan.quilt import load_quilt
    from loom.scan.scan import scan

    key = _block_key(q)
    ok("changes", "--keep-all", cwd=q)
    node = q / NODE
    text = node.read_text()
    inside = text[: text.index("\\end{")].rstrip().rsplit("\n", 1)[-1]
    node.write_text(text.replace(inside, inside + " Indeed.", 1), encoding="utf-8")
    (q / "notes/a.md").write_text("# A\n\nsecond\n", encoding="utf-8")
    result = scan(load_quilt(q))
    assert keep_accepted(result, "Tester", ["some-other-key"]) == []
    assert changes(q) == {NODE: "changed", "notes/a.md": "changed"}
    assert keep_accepted(result, "Tester", [key]) == [NODE]
    assert changes(q) == {"notes/a.md": "changed"}
    assert [blocks_of(result, c) for c in changed(load_quilt(q), "Tester")] == [[[]]]
