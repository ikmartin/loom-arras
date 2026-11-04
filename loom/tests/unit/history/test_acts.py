"""A version of a document at each of the author's acts, and a version put back: Keep, Undo, recording and restoring through the write API, on the synthetic quilt, whose main document is several files."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from loom.history.ledger import load_history
from loom.render.api import ApiError, handle
from loom.render.build import build
from loom.scan.quilt import load_quilt
from tests.unit._quilts import REPO

MAIN = "drafting/main.tex"
NODE = "drafting/nodes/sy-0002.tex"


@pytest.fixture
def q(tmp_path: Path) -> Path:
    from loom.scan.quilt import save_author

    save_author("The synthetic quilt")
    root = tmp_path / "q"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", root, ignore=shutil.ignore_patterns("build", ".git"))
    return root


def versions(q: Path) -> list:
    from loom.history.acts import versions_of
    from loom.scan.scan import scan

    return versions_of(load_history(load_quilt(q).history_dir), MAIN, scan(load_quilt(q)).masters)


def edit(q: Path, old: str, new: str, path: str = NODE) -> None:
    p = q / path
    p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


def test_keep_keeps_a_version_of_each_document_a_kept_file_is_part_of_once(q: Path) -> None:
    handle(q, "changes-keep", {})  # the first look keeps no version: nothing was edited
    first = len(versions(q))
    edit(q, "Every orbit", "Each orbit")
    said = handle(q, "changes-keep", {"path": NODE})["result"]
    assert "a version of main.tex" in said and "talk.tex" in said  # the node is part of both documents
    kept = versions(q)[-1]
    assert (kept.get("kept_for"), kept.message) == ("keep", "Kept an edit")
    assert set(kept.get("files")) >= {MAIN, NODE}
    assert len(versions(q)) == first + 1
    # kept again unchanged, no second version
    handle(q, "changes-keep", {})
    assert len(versions(q)) == first + 1
    # a file no document is made of keeps only a line
    (q / "README.md").write_text("changed\n", encoding="utf-8")
    assert handle(q, "changes-keep", {"path": "README.md"})["result"] == "kept README.md"
    line = load_history(load_quilt(q).history_dir).entries[-1]
    assert (line.action, line.get("path")) == ("keep", "README.md")


def test_undo_keeps_the_text_it_sets_aside_as_a_version_before_writing(q: Path) -> None:
    handle(q, "changes-keep", {})
    edit(q, "Every orbit", "Each orbit")
    handle(q, "changes-undo", {"path": NODE})
    history = load_history(load_quilt(q).history_dir)
    kept = versions(q)[-1]
    assert kept.get("kept_for") == "undo" and "Each orbit" in history.landmark_path(kept).read_text()
    assert [e.action for e in history.entries[-2:]] == ["stamp", "undo"]
    assert "Each orbit" not in (q / NODE).read_text()


def test_an_act_goes_ahead_when_no_version_can_be_kept_and_says_why(q: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    handle(q, "changes-keep", {})
    edit(q, "Every orbit", "Each orbit")

    def conflicted(*_: object) -> None:
        raise ValueError("drafting/main.tex reaches two definitions of sy-0002; a landmark needs one text per key")

    monkeypatch.setattr("loom.history.steps.plan_document_stamp", conflicted)
    said = handle(q, "changes-undo", {"path": NODE})["result"]
    assert "no version of main.tex was kept: drafting/main.tex reaches two definitions of sy-0002" in said
    assert "Each orbit" not in (q / NODE).read_text()


def test_a_version_of_several_files_is_put_back_file_by_file_and_the_restore_is_itself_a_version(q: Path) -> None:
    handle(q, "history-record", {"document": MAIN, "name": "First"})
    first = versions(q)[-1]
    edit(q, "Every orbit", "Each orbit")
    edit(q, "\\begin{document}", "\\begin{document}\nA new opening.\n", MAIN)
    root = load_quilt(q).root
    path = load_history(load_quilt(q).history_dir).landmark_path(first).relative_to(root).as_posix()
    said = handle(q, "history-restore", {"document": MAIN, "version": path})["result"]
    assert said == "put main.tex back as “First” holds it; its text before is the version “Before restoring “First””"
    assert "Every orbit" in (q / NODE).read_text() and "A new opening." not in (q / MAIN).read_text()
    restored = load_history(load_quilt(q).history_dir).entries[-1]
    assert restored.action == "restore" and set(restored.get("paths")) == {MAIN, NODE}
    # restoring the version kept first puts it forward again
    before = versions(q)[-1]
    assert before.get("kept_for") == "restore"
    again = load_history(load_quilt(q).history_dir).landmark_path(before).relative_to(root).as_posix()
    handle(q, "history-restore", {"document": MAIN, "version": again})
    assert "Each orbit" in (q / NODE).read_text() and "A new opening." in (q / MAIN).read_text()


def test_a_flat_version_of_a_document_now_of_several_files_is_not_put_back(q: Path) -> None:
    import json

    # a version stamped before stamps kept each file's text is one flat text
    ledger = load_quilt(q).history_dir / "ledger.jsonl"
    lines = [json.loads(line) for line in ledger.read_text().splitlines()]
    for line in lines:
        if line.get("landmark") == "widgets-v1.tex":
            line.pop("files", None)
    ledger.write_text("".join(json.dumps(line) + "\n" for line in lines))
    m = build(load_quilt(q)).manifest
    old = next(c for c in m["canon"] if c["stem"] == "widgets-v1")
    assert old["action"] == "stamp"
    assert old["cannot_restore"] == "This version was kept as one text, and the document is now several files."
    with pytest.raises(ApiError, match="kept as one text") as e:
        handle(q, "history-restore", {"document": MAIN, "version": old["path"]})
    assert e.value.code == "cannot-restore"
    with pytest.raises(ApiError, match="not a version of drafting/talk.tex"):
        handle(q, "history-restore", {"document": "drafting/talk.tex", "version": old["path"]})


def test_history_lists_every_act_with_what_it_was_done_to(q: Path) -> None:
    handle(q, "changes-keep", {})
    edit(q, "Every orbit", "Each orbit")
    handle(q, "changes-undo", {"path": NODE})
    acts = build(load_quilt(q)).manifest["history"]["acts"]
    undo = acts[-1]
    assert undo["action"] == "undo" and undo["path"] == NODE and undo["from"].startswith("sha256:")
    # the node is part of both documents, so a version of each was kept before the undo wrote
    stamps = [a for a in acts if a["action"] == "stamp" and a.get("kept_for") == "undo"]
    assert {a["in"] for a in stamps} == {MAIN, "drafting/talk.tex"}
    assert all(a["landmark"].startswith(".loom/history/") for a in stamps)
    assert [a["step"] for a in acts if "step" in a] == sorted(a["step"] for a in acts if "step" in a)
