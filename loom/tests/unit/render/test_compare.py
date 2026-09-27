"""Compare's texts (`render/compare.py`, book 15.2.6): the differing pairs of two items, their directions, and the renderings cached by content."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from loom.render.build import build
from loom.render.compare import CompareError, _changed, compare
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan

SYNTHETIC = Path(__file__).resolve().parents[2] / "quilts" / "synthetic"


@pytest.fixture
def quilt(tmp_path: Path) -> Path:
    root = tmp_path / "synthetic"
    shutil.copytree(SYNTHETIC, root, ignore=shutil.ignore_patterns("build", ".git"))
    return root


def pairs(root: Path, left: str, right: str) -> dict[str, dict]:  # type: ignore[type-arg]
    return {p["pair"]: p for p in compare(scan(load_quilt(root)), left, right)["pairs"]}


def test_an_agent_copy_against_its_source_gives_each_change_its_direction(quilt: Path) -> None:
    """The fixture's copy: `sy-0002` changed by the agent (the source holds the base), `sy-0001` changed on both sides since the copy; the unchanged, moved, new and deleted nodes are no pair."""
    got = pairs(quilt, "drafting/main.tex", "drafting-ai/aidoc.tex")
    assert sorted(got) == ["sy-0001", "sy-0002"]
    assert got["sy-0002"]["base"] == "left" and got["sy-0001"]["base"] == "both"
    assert got["sy-0002"]["left"]["key"] == "sy-0002" and got["sy-0002"]["right"]["key"] == "sy-0002-ai"
    # the direction belongs to the documents, not the panes
    assert pairs(quilt, "drafting-ai/aidoc.tex", "drafting/main.tex")["sy-0002"]["base"] == "right"


def test_landmarks_are_ordered_in_time(quilt: Path) -> None:
    today = pairs(quilt, "widgets-v1", "drafting/main.tex")
    assert today and {p["base"] for p in today.values()} == {"left"}
    assert {p["base"] for p in pairs(quilt, "widgets-v3", "widgets-v1").values()} <= {"right"}
    # a landmark by its name, its step, or DOC@STEP
    assert pairs(quilt, "1", "drafting/main.tex").keys() == today.keys()
    assert pairs(quilt, "main@1", "drafting/main.tex").keys() == today.keys()


def test_a_display_name_changed_alone_is_no_difference(quilt: Path) -> None:
    node = quilt / "nodes" / "sy-0003.tex"
    if not node.is_file():
        pytest.skip("sy-0003 is inline in this fixture")
    node.write_text("% !LOOM name: Renamed\n" + node.read_text(encoding="utf-8"), encoding="utf-8")
    assert "sy-0003" not in pairs(quilt, "widgets-v3", "drafting/main.tex")


def test_the_hashes_are_the_fragments_and_a_rendering_is_made_once(quilt: Path) -> None:
    """A pair's hashes are the `data-hash` the build wrote on the same nodes, so a viewer with nothing serving marks what loom would; a second request renders nothing."""
    build(load_quilt(quilt))
    master = (quilt / "build" / "fragments" / "masters" / "aidoc.html").read_text(encoding="utf-8")
    written = dict(re.findall(r'data-pair="([^"]*)" data-hash="([^"]*)"', master))
    got = pairs(quilt, "drafting/main.tex", "drafting-ai/aidoc.tex")
    assert got["sy-0002"]["right"]["hash"] == written["sy-0002"]
    rendered = sorted((quilt / "build" / "compare").iterdir())
    times = [p.stat().st_mtime_ns for p in rendered]
    assert b"review-changed" in rendered[0].read_bytes()
    pairs(quilt, "drafting/main.tex", "drafting-ai/aidoc.tex")
    assert sorted((quilt / "build" / "compare").iterdir()) == rendered
    assert [p.stat().st_mtime_ns for p in rendered] == times


def test_a_landmark_fragment_carries_pairs_and_no_live_wiring(quilt: Path) -> None:
    build(load_quilt(quilt))
    landmark = (quilt / "build" / "fragments" / "canon" / "widgets-v1.html").read_text(encoding="utf-8")
    assert 'data-pair="sy-0002"' in landmark and 'data-pair="sy-0002/proof"' in landmark
    nodes = re.findall(r'<(?:div|details) class="env[^>]*>', landmark)
    assert nodes and not [n for n in nodes if "data-key=" in n or "data-id=" in n]


def test_a_derived_label_is_the_same_word_as_its_plain_one() -> None:
    assert _changed(r"see \ref{sy-0001} and (\ref{eq:x})", r"see \ref{sy-0001-ai} and (\ref{eq:x-ai})") == ([], [])
    assert _changed(r"see \ref{sy-0001}", r"see \ref{sy-0003-ai}") == ([[4, 17]], [[4, 20]])


def test_an_item_that_is_neither_is_refused(quilt: Path) -> None:
    with pytest.raises(CompareError, match="nowhere-v9"):
        compare(scan(load_quilt(quilt)), "drafting/main.tex", "nowhere-v9")


def test_a_landmark_by_its_path_and_a_node_by_its_key(quilt: Path) -> None:
    """What a viewer holds for an item: a landmark's path, and a node's key, which compares with its agent copy."""
    assert (
        pairs(quilt, ".loom/history/0001-widgets-v1/widgets-v1.tex", "drafting/main.tex").keys()
        == pairs(quilt, "widgets-v1", "drafting/main.tex").keys()
    )
    got = pairs(quilt, "sy-0002", "sy-0002-ai")
    assert list(got) == ["sy-0002"] and got["sy-0002"]["base"] == "left"
