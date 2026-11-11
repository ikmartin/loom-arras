"""Annotations on a PDF: a project file by its path or a cited work, on a page with its place, drawn with a tool, edited, detached when the file changes, and taken in from the file's own annotations; and on a cited work as a whole."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import json_of, ok, refused
from tests.unit._quilts import demo

AGENT = "Reading Agent"
ARDEN = Path(__file__).resolve().parents[2] / "quilts" / "sources" / "showcase-works" / "arden-cycle-spaces.pdf"
#: "Cycle spaces" on page 1 of the Arden PDF, as `pdftotext -bbox-layout` places it, as x0,y0,x1,y1.
TITLE = "207,125,293,141"
ON = ("notes/paper.pdf", "--page", "1")


@pytest.fixture
def paper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The demo with a copy of a PDF among its shown files."""
    from loom.scan.quilt import save_author

    save_author("Tester")
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-10-01T09:00:00Z")
    q = demo(tmp_path)
    (q / "notes").mkdir()
    (q / "notes" / "paper.pdf").write_bytes(ARDEN.read_bytes())
    return q


def log(q: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in (q / ".loom/annotations" / "log.jsonl").read_text().splitlines() if x.strip()]


def annotated(q: Path, *args: str, who: str = "Tester") -> dict[str, Any]:
    """Run `loom annotate` and return the event it wrote."""
    ok("annotate", *args, "--as", who, cwd=q)
    return log(q)[-1]


def published(q: Path, ann_id: str) -> dict[str, Any]:
    """An annotation as the manifest carries it, resolved now."""
    from loom.cli._quilt import open_scan
    from loom.records.store import Records

    result = open_scan(str(q))
    manifest: dict[str, Any] = {"nodes": {}, "keys": {}, "diagnostics": []}
    Records(q, result.quilt.history_dir).apply(result, manifest)
    return manifest["annotations"][ann_id]  # type: ignore[no-any-return]


def test_an_annotation_on_a_cited_work_with_no_page_is_on_the_whole_work(paper: Path) -> None:
    """By citekey or by an identifier its entry states; it has no place, so nothing detaches it, and an agent reads it with `loom since`."""
    whole = annotated(paper, "Calloway14", "Read this paper through and write its overview.")
    assert (whole["target"], whole["anchor"], "page" in whole) == ("doi:10.4171/demo/14-1", None, False)
    again = annotated(paper, "doi:10.4171/demo/14-1", "and this one")
    assert again["target"] == whole["target"]
    row = published(paper, whole["id"])
    assert (row["target"]["work"], row["target"]["page"], row["detached"]) == ("Calloway14", None, False)
    got = json_of("since", "--as", AGENT, "--json", cwd=paper)
    assert {a["body"] for a in got["annotations"]} >= {"Read this paper through and write its overview."}
    assert "the whole work" in ok("status", "--reading", cwd=paper).stdout


def test_what_an_annotation_on_a_pdf_page_needs_is_refused_by_name(paper: Path) -> None:
    """It names its page; a pin says something; a box stands in one rectangle; ink has strokes of whole points; a tool draws only on a PDF."""
    base = ("annotate", "--as", "Tester")
    before = log(paper)
    refused(*base, "dm-0003", "x", "--mark", "pin", cwd=paper, code=2, match="draw on a page of a PDF")
    refused(*base, "notes/paper.pdf", "x", "--box", TITLE, cwd=paper, code=2, match="names its page")
    refused(*base, *ON, "--box", TITLE, "--mark", "pin", cwd=paper, code=2, match="says something")
    refused(*base, *ON, "--mark", "box", "--stroke", "1,2,3,4", cwd=paper, code=2, match="only ink and an arrow")
    refused(*base, *ON, "--box", TITLE, "--mark", "ink", cwd=paper, code=2, match="needs its strokes")
    refused(*base, *ON, "--mark", "ink", "--stroke", "1,2,3", cwd=paper, code=2, match="an x and a y")
    refused(*base, *ON, "--mark", "pin", "--box", "1,1,2,2;3,3,4,4", "x", cwd=paper, code=2, match="one rectangle")
    refused(*base, *ON, cwd=paper, code=2, match="its words, a rectangle or its strokes")
    assert log(paper) == before


def test_every_tool_is_written_and_stroked_ones_are_bounded(paper: Path) -> None:
    pin = annotated(paper, *ON, "look here", "--box", "50,50,66,66", "--mark", "pin")
    assert (pin["target"], pin["page"], pin["rects"], pin["mark"]) == ("notes/paper.pdf", 1, [[50, 50, 66, 66]], "pin")
    assert pin["artifact"] and "session" not in pin
    assert annotated(paper, *ON, "words on the page", "--box", "50,90,250,110", "--mark", "text")["mark"] == "text"
    assert annotated(paper, *ON, "--box", "50,120,150,170", "--mark", "oval")["mark"] == "oval"
    ink = annotated(paper, *ON, "--mark", "ink", "--stroke", "10,10,20,30,40,5", "--stroke", "50,50,60,60")
    assert ink["strokes"] == [[10, 10, 20, 30, 40, 5], [50, 50, 60, 60]] and ink["rects"] == [[10, 5, 60, 60]]
    assert annotated(paper, *ON, "--mark", "arrow", "--stroke", "1,2,30,40")["rects"] == [[1, 2, 30, 40]]
    # the look comes from the type and what is set on it, as any annotation's
    green = annotated(paper, *ON, "--box", "1,1,9,9", "--mark", "box", "--color", "green", "--type", "note")
    assert (green["look"], green["drawn"]["color"]) == ({"color": "green"}, "green")


def test_a_drawn_annotation_moves_and_redraws_with_an_edit_and_one_on_words_does_not(paper: Path) -> None:
    pin = annotated(paper, *ON, "look here", "--box", "50,50,66,66", "--mark", "pin")["id"]
    ink = annotated(paper, *ON, "--mark", "ink", "--stroke", "10,10,20,30")["id"]
    box = annotated(paper, *ON, "--box", "100,100,200,200")["id"]
    ok("annotate", "--edit", pin, "--box", "70,70,86,86", "--as", "Tester", cwd=paper)
    ok("annotate", "--edit", ink, "--stroke", "1,1,5,5", "--stroke", "8,8,9,12", "--as", "Tester", cwd=paper)
    edits = {e["id"]: e for e in log(paper) if e["event"] == "edited"}
    assert edits[pin]["rects"] == [[70, 70, 86, 86]]
    assert edits[ink]["strokes"] == [[1, 1, 5, 5], [8, 8, 9, 12]] and edits[ink]["rects"] == [[1, 1, 9, 12]]
    assert published(paper, pin)["rects"] == [[70, 70, 86, 86]]
    refused("annotate", "--edit", box, "--box", "1,1,2,2", "--as", "Tester", cwd=paper, code=2, match="not a rectangle")
    refused("annotate", "--edit", pin, "--stroke", "1,1,2,2", "--as", "Tester", cwd=paper, code=2, match="only ink")
    refused("annotate", "--edit", pin, "", "--as", "Tester", cwd=paper, code=2, match="empty body")
    # an agent deletes only its own, on a PDF as anywhere
    refused("annotate", "--delete", pin, "--as", AGENT, cwd=paper, env={"AI_AGENT": "1"}, code=2, match="its own")


@pytest.mark.poppler
def test_an_annotation_on_words_of_a_project_pdf_is_placed_by_the_page(paper: Path) -> None:
    words = annotated(paper, *ON, "--quote", "Cycle spaces", "--style", "highlight")
    assert words["anchor"]["exact"] == "Cycle spaces" and "mark" not in words and len(words["rects"]) == 1
    assert 200 < words["rects"][0][0] < 215 and 120 < words["rects"][0][1] < 130
    row = published(paper, words["id"])
    assert (row["detached"], row["quote"], row["target"]["file"]) == (False, "Cycle spaces", "notes/paper.pdf")
    refused(
        "annotate",
        *ON,
        "--quote",
        "not in this paper at all",
        "--as",
        "Tester",
        cwd=paper,
        code=1,
        match="not on page 1",
    )


@pytest.mark.poppler
def test_a_changed_file_moves_words_and_detaches_the_rest(paper: Path) -> None:
    """The bytes change: words still on the page are drawn where they are now; a box with no words, or words that left, is detached (A3)."""
    words = annotated(paper, *ON, "--quote", "Cycle spaces")["id"]
    gone = annotated(paper, *ON, "--quote", "Elspeth Arden")["id"]
    box = annotated(paper, *ON, "--box", TITLE, "--mark", "box")["id"]
    assert not published(paper, words)["detached"] and not published(paper, box)["detached"]
    pdf = paper / "notes" / "paper.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"\n% another version\n")
    assert published(paper, words)["detached"] is False and published(paper, words)["rects"]
    assert published(paper, box)["detached"] is True
    pdf.unlink()
    assert published(paper, gone)["detached"] is True


@pytest.mark.poppler
def test_a_pdfs_own_annotations_are_taken_in_once(paper: Path) -> None:
    """Page, place and words say one is here already, so taking a PDF in twice adds nothing; the words under a highlight are read from the page, its colour is the nearest of the nine, a StrikeOut is struck, and what wrote it stays in its origin."""
    from loom.cli._quilt import open_scan
    from loom.records.marks import MarkRefused, take_in

    items = [
        {
            "page": 1,
            "mark": "highlight",
            "rects": [[206.9, 125.4, 293.4, 141.0]],
            "body": "from Preview",
            "origin": {"by": "Reader", "subtype": "Highlight", "color": [255, 255, 0], "ref": "19R"},
        },
        {"page": 1, "mark": "pin", "rects": [[50, 50, 66, 66]], "body": "a sticky note", "color": "teal"},
        {"page": 1, "mark": "ink", "strokes": [[10, 10, 20, 30]]},
        {"page": 1, "rects": [[300, 300, 340, 310]], "origin": {"subtype": "StrikeOut", "color": [1, 0, 0]}},
        {"page": 1, "mark": "pin", "rects": [[50, 50, 66, 66]]},
        {"page": "one", "mark": "pin", "rects": [[1, 1, 2, 2]], "body": "x"},
    ]
    writer = ("human", "Tester")
    assert take_in(open_scan(str(paper)), "notes/paper.pdf", items, writer) == {"taken": 4, "already": 0, "skipped": 2}
    made = [e for e in log(paper) if e["event"] == "created" and e["target"] == "notes/paper.pdf"]
    assert made[0]["anchor"]["exact"] == "Cycle spaces" and made[0]["origin"]["by"] == "Reader"
    assert made[0]["look"] == {"color": "yellow", "style": "highlight"} and "mark" not in made[0]
    assert made[1]["mark"] == "pin" and made[1]["look"] == {}
    assert made[3]["look"] == {"color": "red", "style": "strike"}
    # the file's own annotation it came from is still there, so the viewer hides that one
    assert published(paper, made[0]["id"])["hides"] == "19R"
    assert take_in(open_scan(str(paper)), "notes/paper.pdf", items, writer) == {"taken": 0, "already": 4, "skipped": 2}
    with pytest.raises(MarkRefused, match="not a PDF"):
        take_in(open_scan(str(paper)), "dm-0003", items, writer)
