"""A node's own text reads an inclusion of a child as the child itself, so moving a node into nodes/ leaves every hash where it was (book 5.13)."""

from __future__ import annotations

import shutil
from pathlib import Path

from loom.render.manifest import key_hash, own_text
from loom.reshape.atomize import _directive_start, _line_bounds
from loom.scan.hashing import child_marker
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

QUILTS = Path(__file__).resolve().parents[3] / "tests" / "quilts"


def _scan(root: Path):  # type: ignore[no-untyped-def]
    return scan(load_quilt(root))


def _move_out(root: Path, result, key: str) -> None:  # type: ignore[no-untyped-def]
    """Do what a single-node atomize plan does: the node's lines become nodes/<id>.tex, an \\input line stands in its place."""
    n = result.assembly.nodes[key]
    text = result.files[n.file].text
    ls, le = _line_bounds(text, _directive_start(result, n, n.start), n.end)
    (root / "nodes").mkdir(exist_ok=True)
    (root / "nodes" / f"{n.id}.tex").write_text(text[ls:le].rstrip("\n") + "\n", encoding="utf-8")
    (root / n.file).write_text(text[:ls] + f"\\input{{nodes/{n.id}}}" + text[le:], encoding="utf-8")


def test_moving_a_node_out_of_a_draft_changes_no_hash(tmp_path: Path) -> None:
    root = tmp_path / "synthetic"
    shutil.copytree(QUILTS / "synthetic", root)
    before_result = _scan(root)
    key = "sy-0001"  # a definition inside a labelled section of drafting/main.tex
    section = before_result.assembly.nodes[key]
    assert section.file == "drafting/main.tex"
    before = {k: key_hash(before_result, k) for k, n in before_result.assembly.nodes.items() if n.kind != "file"}

    _move_out(root, before_result, key)

    after_result = _scan(root)
    after = {k: key_hash(after_result, k) for k, n in after_result.assembly.nodes.items() if n.kind != "file"}
    assert before[key] == after[key], "the moved node's own text is unchanged"
    changed = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    assert changed == [], "no other node's hash may move either"


def test_an_inclusion_of_a_child_reads_as_that_child(tmp_path: Path) -> None:
    root = tmp_path / "synthetic"
    shutil.copytree(QUILTS / "synthetic", root)
    result = _scan(root)
    main = result.assembly.nodes["sy-0100"]  # the section that inputs nodes/sy-0002
    text = own_text(result, main)
    assert child_marker("sy-0002") in text
    assert "\\input{nodes/sy-0002}" not in text
