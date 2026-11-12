"""Annotations on a PDF: a project file by its path or a cited work, on a page with its place, drawn with a tool, edited, found again when the file changes or detached when they cannot be, and taken in from the file's own annotations; and on a cited work as a whole."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import exits, json_of, ok, refused
from tests.unit._pdfs import PROSE, STEP, lines_pdf
from tests.unit._quilts import demo, showcase

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
def test_a_re_saved_file_keeps_its_marks_and_a_lost_file_detaches_them(paper: Path) -> None:
    """The bytes change and the words do not: words and a drawn box are found again where they stood, and say so; the file gone, every mark on it is detached (A3)."""
    words = annotated(paper, *ON, "--quote", "Cycle spaces")["id"]
    box = annotated(paper, *ON, "--box", TITLE, "--mark", "box")["id"]
    assert not published(paper, words)["refound"] and not published(paper, box)["detached"]
    before = {a: published(paper, a)["rects"] for a in (words, box)}
    pdf = paper / "notes" / "paper.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"\n% another version\n")
    for a in (words, box):
        row = published(paper, a)
        assert (row["detached"], row["refound"], row["target"]["page"]) == (False, True, 1), a
        assert all(abs(x - y) < 0.01 for x, y in zip(row["rects"][0], before[a][0], strict=True)), a
    pdf.unlink()
    assert published(paper, words)["detached"] is True and published(paper, box)["detached"] is True


def write_on(q: Path, pages: list[list[str]], **kw: Any) -> Path:
    return lines_pdf(q / "notes" / "paper.pdf", pages, **kw)


@pytest.mark.poppler
def test_a_mark_records_the_words_around_it_and_a_drawing_its_gap(paper: Path) -> None:
    """Annotate, take in and a move each write the words under a mark and up to eight either side, across a page break; a drawing writes its gap from its pin word, and a mark on words none."""
    from loom.cli._quilt import open_scan
    from loom.records.marks import take_in

    write_on(paper, [["The first page ends with these words here."], PROSE])
    words = annotated(paper, "notes/paper.pdf", "--page", "2", "--quote", "order of a weighted digraph")
    assert words["anchor"] == {
        "exact": "order of a weighted digraph",
        "prefix": "page ends with these words here. The median",
        "suffix": "minimises the total weight of the arcs that",
    }
    assert "gap" not in words
    # a box round "Every vertex": its words, and its top left 2 pt left of and 2 pt above the first of them
    box = annotated(paper, "notes/paper.pdf", "--page", "2", "--box", "70,117,140,133", "--mark", "box")
    assert box["anchor"]["exact"] == "Every vertex" and box["anchor"]["prefix"].endswith("run backwards.")
    assert box["gap"] == [-2.0, pytest.approx(-2.38, abs=0.5)]
    # a pin in the margin: no words under it, so the next one pins it
    pin = annotated(paper, "notes/paper.pdf", "look", "--page", "2", "--box", "20,118,36,134", "--mark", "pin")
    assert pin["anchor"]["exact"] == "" and pin["anchor"]["suffix"].startswith("Every vertex")
    assert pin["gap"][0] == pytest.approx(-52.0)
    writer = ("person", "Tester")
    item = {
        "page": 2,
        "mark": "box",
        "rects": [[70, 117, 140, 133]],
        "body": "from the file",
        "origin": {"subtype": "Square"},
    }
    assert take_in(open_scan(str(paper)), "notes/paper.pdf", [item], writer)["taken"] == 1
    taken = log(paper)[-1]
    assert (taken["anchor"], taken["gap"]) == (box["anchor"], box["gap"])
    # moved: its words and its gap are taken again where it now stands, on the file as it is now
    ok("annotate", "--edit", box["id"], "--box", "70,145,140,161", "--as", "Tester", cwd=paper)
    moved = log(paper)[-1]
    assert moved["anchor"]["exact"] == "and the counting" and moved["gap"] and moved["artifact"] == box["artifact"]
    from loom.records.log import replay

    (got,) = [a for r in replay(paper)[0] for a in r.annotations if a.id == box["id"]]
    assert (got.selector.exact if got.selector else None, got.gap) == ("and the counting", moved["gap"])


@pytest.mark.poppler
def test_a_mark_is_found_again_a_line_down_and_on_the_next_page(paper: Path) -> None:
    """The file is written again with a line more above the marks, then with them on the next page: marks on words stand on their words, a box and ink move with the words they were drawn beside."""
    write_on(paper, [PROSE])
    on = ("notes/paper.pdf", "--page", "1")
    words = annotated(paper, *on, "--quote", "the median polytope is integral")["id"]
    box = annotated(paper, *on, "--box", "300,110,360,150", "--mark", "box")["id"]
    ink = annotated(paper, *on, "--mark", "ink", "--stroke", "100,140,200,145")["id"]
    at = {a: published(paper, a) for a in (words, box, ink)}
    write_on(paper, [["A line more at the top of the page.", *PROSE]])
    for a in (words, box, ink):
        row = published(paper, a)
        assert (row["detached"], row["refound"], row["target"]["page"]) == (False, True, 1), a
        assert row["rects"][0][1] == pytest.approx(at[a]["rects"][0][1] + STEP, abs=0.5), a
    assert published(paper, ink)["strokes"] == [
        [100, pytest.approx(140 + STEP, abs=0.5), 200, pytest.approx(145 + STEP, abs=0.5)]
    ]
    write_on(paper, [PROSE[:2], PROSE[2:]])
    for a in (words, box, ink):
        row = published(paper, a)
        assert (row["detached"], row["refound"], row["target"]["page"]) == (False, True, 2), a
    # nothing of its words left: detached, and the place it was written at kept
    write_on(paper, [["Nothing of what was marked is in this file."]])
    for a in (words, box, ink):
        row = published(paper, a)
        assert (row["detached"], row["refound"], row["target"]["page"]) == (True, False, 1), a


@pytest.mark.poppler
def test_an_older_drawing_with_no_gap_stays_detached_and_older_words_are_found(paper: Path) -> None:
    """A mark written before marks recorded their context: words are found again by their words alone, and a drawing, which records no gap, is detached on a changed file."""
    write_on(paper, [PROSE])
    on = ("notes/paper.pdf", "--page", "1")
    words = annotated(paper, *on, "--quote", "the median polytope is integral")
    box = annotated(paper, *on, "--box", "300,110,360,150", "--mark", "box")
    path = paper / ".loom/annotations" / "log.jsonl"
    lines = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    for e in lines:
        if e.get("id") == words["id"]:
            e["anchor"] = {"exact": "the median polytope is integral", "prefix": "", "suffix": ""}
        if e.get("id") == box["id"]:
            e.pop("gap", None)
            e.pop("anchor", None)
    path.write_text("".join(json.dumps(e) + "\n" for e in lines))
    write_on(paper, [["A line more at the top of the page.", *PROSE]])
    assert (published(paper, words["id"])["refound"], published(paper, box["id"])["detached"]) == (True, True)


@pytest.mark.poppler
def test_unchanged_bytes_read_nothing(paper: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A mark on the file it was written on stands where it was written: resolving it runs no pdftotext."""
    from loom.refs import pages

    write_on(paper, [PROSE])
    words = annotated(paper, "notes/paper.pdf", "--page", "1", "--quote", "the median polytope is integral")

    def refused_here(args: list[str]) -> str:
        raise AssertionError(f"pdftotext ran: {args}")

    monkeypatch.setattr(pages, "_pdftotext", refused_here)
    row = published(paper, words["id"])
    assert (row["detached"], row["refound"], row["rects"]) == (False, False, words["rects"])


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


@pytest.mark.poppler
def test_a_pdf_marked_in_preview_is_taken_in_in_the_nearest_of_the_nine(paper: Path) -> None:
    """Preview's own colours, as the viewer reads its annotations (`portable.ts`): each comes to the nearest of the nine by hue, whether the viewer named it or only the PDF's colour came, and a strike-out is struck."""
    from loom.cli._quilt import open_scan
    from loom.records.marks import take_in

    write_on(paper, [PROSE])

    def item(line: int, subtype: str, rgb: list[int], **kw: Any) -> dict[str, Any]:
        top = 100 + line * STEP - 9
        return {
            "page": 1,
            "rects": [[72, top, 300, top + 11]],
            "body": "",
            "origin": {"by": "Reader", "subtype": subtype, "color": rgb},
            **kw,
        }

    preview = [
        item(0, "Highlight", [255, 222, 89], style="highlight", color="yellow"),
        item(1, "Highlight", [122, 229, 130], style="highlight"),
        item(2, "Underline", [255, 38, 0], style="underline"),
        item(3, "StrikeOut", [255, 38, 0], style="strike", color="red"),
        item(4, "Highlight", [110, 191, 255], style="highlight"),
        item(5, "Highlight", [255, 127, 191], style="highlight"),
        item(6, "Highlight", [193, 124, 255], style="highlight"),
    ]
    assert take_in(open_scan(str(paper)), "notes/paper.pdf", preview, ("person", "Tester"))["taken"] == 7
    made = [e for e in log(paper) if e["event"] == "created"][-7:]
    assert [e["look"] for e in made] == [
        {"color": "yellow", "style": "highlight"},
        {"color": "green", "style": "highlight"},
        {"color": "red", "style": "underline"},
        {"color": "red", "style": "strike"},
        {"color": "blue", "style": "highlight"},
        {"color": "pink", "style": "highlight"},
        {"color": "purple", "style": "highlight"},
    ]
    assert made[3]["anchor"]["exact"].startswith("because the incidence")


@pytest.mark.poppler
def test_a_note_on_a_works_page_is_found_again_on_a_changed_copy_of_the_work(tmp_path: Path) -> None:
    """A work filed again: a text anchor's words are looked for on every page's committed text, its own first, and a box anchor, which records its words and gap like any drawing, is found by them."""
    q = showcase(tmp_path)
    words = annotated(q, "Bellamy19", "Why?", "--page", "2", "--quote", "totally unimodular")["id"]
    box = annotated(q, "Bellamy19", "This one.", "--page", "2", "--box", "82,85,157,97")
    assert box["anchor"]["basis"] == "box" and box["anchor"]["exact"] == "Theorem 2.3." and box["gap"]
    home = q / ".loom/digests/storage/doi/10.4171_showcase_19-2"
    # the copy is filed again: its bytes differ, so its map names another hash, and its words moved to page 3
    pdf = home / "paper.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"\n% filed again\n")
    from loom.refs.pages import sha256_of

    sections = json.loads((home / "sections.json").read_text())
    (home / "sections.json").write_text(json.dumps({**sections, "sha256": sha256_of(pdf)}))
    page2 = (home / "pages" / "0002.txt").read_text()
    (home / "pages" / "0002.txt").write_text(page2.replace("totally unimodular", "unimodular"))
    (home / "pages" / "0003.txt").write_text((home / "pages" / "0003.txt").read_text() + "\ntotally unimodular\n")
    row = published(q, words)
    assert (row["target"]["page"], row["refound"], row["detached"]) == (3, True, False)
    row = published(q, box["id"])
    assert (row["target"]["page"], row["refound"], row["detached"]) == (2, True, False)
    assert row["rects"][0] == pytest.approx([82, 85, 157, 97], abs=0.5)


@pytest.mark.poppler
def test_a_note_on_a_work_filed_by_its_hash_is_read_on_the_copy_it_was_written_on(tmp_path: Path) -> None:
    """Arden24A's copy is filed by its file's hash, `file/<sha16>/`, as `library add` files a PDF that states no identifier of its own; the directory its identifier names holds another document. A note on its page is read on its own copy (`work_dir`), as the viewer's artifacts and the sidecar are: it keeps its page and is recorded, anchored, not found again elsewhere and not detached."""
    from loom.refs.pages import sha256_of

    q = showcase(tmp_path)
    store = q / ".loom/digests/storage"
    assert (store / "file/e43d5afaac8f10f0/paper.pdf").is_file()
    quote = "a saturated sublattice of the lattice of weightings"
    note = annotated(q, "Arden24A", "Why saturated?", "--page", "2", "--quote", quote, who="A. Author")
    assert note["anchor"]["page"] == 2 and note["anchor"]["basis"] == "text"
    # another document under the identifier's own directory, its words on page 3: read there, the note would look written on a changed file and move
    decoy = store / "arxiv" / "2504.01234v2"
    (decoy / "pages").mkdir(parents=True)
    (decoy / "paper.pdf").write_bytes((store / "doi/10.4171_showcase_19-2/paper.pdf").read_bytes())
    sha = sha256_of(decoy / "paper.pdf")
    (decoy / "sections.json").write_text(json.dumps({"sha256": sha, "pages": 3, "chars": 0, "sections": []}))
    for n, text in ((1, "Nothing here."), (2, "Nor here."), (3, f"Here: {quote}.")):
        (decoy / "pages" / f"{n:04d}.txt").write_text(text + "\n")
    exits(1, "build", cwd=q)
    row = json.loads((q / ".loom/build" / "manifest.json").read_text())["annotations"][note["id"]]
    assert (row["target"]["work"], row["target"]["page"]) == ("Arden24A", 2)
    assert (row["recorded"], row["anchored"], row["refound"], row["detached"]) == (True, True, False, False)
