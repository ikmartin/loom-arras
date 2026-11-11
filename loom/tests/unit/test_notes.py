"""Notes, a quote among them (plan 0.22.8): written on anything the viewer shows, read by an agent through `loom since`, kept, linked, and fading when neither."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import json_of, ok, refused
from tests.unit._quilts import demo, open_session

AGENT = "Reading Agent"


@pytest.fixture
def q(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from loom.scan.quilt import save_author

    save_author("Tester")
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-10-01T09:00:00Z")
    root = demo(tmp_path)
    (root / "notes").mkdir()
    (root / "notes" / "a.md").write_text("# A\n\nThe orbit is finite.\n", encoding="utf-8")
    (root / "notes" / "p.html").write_text("<p>A <b>gadget</b> has a handle.</p>", encoding="utf-8")
    (root / ".hidden.md").write_text("no", encoding="utf-8")
    return root


def noted(q: Path, *args: str, who: str = "Tester") -> dict:  # type: ignore[type-arg]
    return json_of("note", *args, "--as", who, "--json", cwd=q)["note"]


def test_a_note_is_written_on_each_thing_the_viewer_shows(q: Path) -> None:
    """A key, a file by its path, a cited work's page, a transcript message as SESSION#SEQ, and a session alone; a hidden file, a quote on a work with no page and a note saying nothing are refused."""
    from loom.mailbox import post

    sid = open_session(q)
    said = post(q, sid, "Look at the orbit lemma.", "Tester")
    on_key = noted(q, "--on", "dm-0003", "--quote", "finite")
    assert (
        on_key["target"] == {"key": "dm-0003"}
        and on_key["quote"] == "finite"
        and on_key["id"].startswith("n-2026-10-01-")
    )
    assert noted(q, "--on", "notes/a.md", "--quote", "The orbit is finite.")["target"] == {"file": "notes/a.md"}
    on_work = noted(q, "--on", "Calloway14", "--page", "2", "--box", "10,20,100,40")
    assert (
        on_work["target"]["citekey"] == "Calloway14"
        and on_work["page"] == 2
        and on_work["rects"] == [[10, 20, 110, 60]]
    )
    assert noted(q, "--on", f"{sid}#{said.seq}", "--quote", "orbit lemma")["target"] == {
        "message": {"session": sid, "seq": said.seq}
    }
    assert noted(q, "file this later", "--on", sid)["target"] == {"session": sid}
    refused(
        "note", "--on", ".hidden.md", "--quote", "no", "--as", "Tester", cwd=q, code=2, match="hidden from the viewer"
    )
    refused("note", "--on", "Calloway14", "--quote", "x", "--as", "Tester", cwd=q, code=2, match="names its page")
    refused("note", "x", "--on", "Calloway14", "--page", "0", "--as", "Tester", cwd=q, code=2, match="counted from 1")
    refused("note", "--on", "dm-0003", "--as", "Tester", cwd=q, code=2, match="quotes something or says something")
    refused("note", "--on", f"{sid}#999", "--quote", "x", "--as", "Tester", cwd=q, code=2, match="no message 999")


def test_a_note_on_a_cited_work_with_no_page_is_on_the_whole_work(q: Path) -> None:
    """By citekey or by an identifier its entry states, a work added by hand with none among them; it has no words to quote."""
    from loom.refs.added import add_entry
    from loom.scan.quilt import load_quilt

    whole = noted(q, "Read this paper through and write its overview.", "--on", "Calloway14")
    assert whole["target"] == {"work": "doi:10.4171/demo/14-1", "citekey": "Calloway14"} and "page" not in whole
    assert noted(q, "and this one", "--on", "doi:10.4171/demo/14-1")["target"]["citekey"] == "Calloway14"
    add_entry(
        load_quilt(q), {"author": "Fulton, William", "title": "Intersection theory", "year": "1998"}, "Ful98", "Tester"
    )
    assert noted(q, "worth reading", "--on", "Ful98")["target"]["citekey"] == "Ful98"
    assert "on Calloway14  Tester" in ok("since", "--as", AGENT, "--dry-run", cwd=q).stdout
    got = json_of("since", "--as", AGENT, "--json", cwd=q)
    assert {n["target"].get("citekey") for n in got["noted"]} >= {"Calloway14", "Ful98"}


def test_an_agent_reads_a_persons_quotes_with_loom_since_and_never_its_own(q: Path) -> None:
    ok("since", "--as", AGENT, cwd=q)
    mine = noted(q, "--on", "notes/a.md", "--quote", "The orbit is finite.", who="Tester")
    noted(q, "an aside", "--on", "notes/a.md", who=AGENT)
    got = json_of("since", "--as", AGENT, "--json", cwd=q)
    assert [n["id"] for n in got["noted"]] == [mine["id"]]
    assert got["noted"][0]["quote"] == "The orbit is finite." and got["noted"][0]["link"] == f"[](quilt:{mine['id']})"
    text = ok("since", "--as", AGENT, "--dry-run", cwd=q).stdout
    assert "nothing" in text


def test_a_note_fades_after_two_weeks_unless_kept_or_linked(q: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fading is computed when the manifest is published (P3), never stored; a kept note and a linked note stay, and nothing is deleted."""
    old = noted(q, "--on", "notes/a.md", "--quote", "The orbit is finite.")
    kept = noted(q, "--on", "notes/a.md", "--quote", "orbit")
    linked = noted(q, "--on", "dm-0003", "--quote", "finite")
    ok("note", "--keep", kept["id"], "--as", "Tester", cwd=q)
    ok("annotate", "dm-0003", f"see [](quilt:{linked['id']})", "--type", "note", "--as", "Tester", cwd=q)
    monkeypatch.setenv("LOOM_FIXED_TIME", "2026-10-20T09:00:00Z")
    from tests.helpers import run

    run("build", cwd=q)
    notes = json.loads((q / ".loom/build/manifest.json").read_text())["notes"]
    assert notes[old["id"]]["faded"] is True
    assert notes[kept["id"]]["faded"] is False and notes[kept["id"]]["kept"]
    assert notes[linked["id"]]["faded"] is False
    assert len(notes) == 3


def test_a_note_whose_quote_is_gone_is_detached_and_one_on_a_page_reads_its_text(q: Path) -> None:
    from tests.helpers import run

    on_md = noted(q, "--on", "notes/a.md", "--quote", "The orbit is finite.")
    on_html = noted(q, "--on", "notes/p.html", "--quote", "A gadget has a handle.")
    (q / "notes/a.md").write_text("# A\n\nThe orbit is infinite after all.\n", encoding="utf-8")
    run("build", cwd=q)
    notes = json.loads((q / ".loom/build/manifest.json").read_text())["notes"]
    assert notes[on_md["id"]]["detached"] is True
    assert notes[on_html["id"]]["detached"] is False


def test_a_note_is_linked_by_its_id_and_opens_what_it_is_on(q: Path) -> None:
    from loom.cli._quilt import open_scan
    from loom.links import LinkError, resolve

    n = noted(q, "--on", "notes/a.md", "--quote", "The orbit is finite.")
    result = open_scan(str(q))
    assert resolve(result, q, f"quilt:{n['id']}").kind == "note"
    with pytest.raises(LinkError, match="no note"):
        resolve(result, q, "quilt:n-2026-01-01-c4yrbe")
    assert ok("link", n["id"], cwd=q).stdout.strip() == f"[](quilt:{n['id']})"


ARDEN = Path(__file__).resolve().parents[1] / "quilts" / "sources" / "showcase-works" / "arden-cycle-spaces.pdf"
#: "Cycle spaces" on page 1 of the Arden PDF, as `pdftotext -bbox-layout` places it.
TITLE = "207,125,86,16"


@pytest.fixture
def paper(q: Path) -> Path:
    """The quilt with a copy of a PDF among its shown files."""
    (q / "notes" / "paper.pdf").write_bytes(ARDEN.read_bytes())
    return q


def published_note(root: Path, nid: str) -> dict:  # type: ignore[type-arg]
    from loom.cli._quilt import open_scan
    from loom.notes import published

    return published(open_scan(str(root)))[nid]


@pytest.mark.poppler
def test_a_quote_on_a_pdf_is_not_looked_for_in_its_bytes(paper: Path) -> None:
    """The words are on the page though the file's bytes hide them, so the note stands; a quote is placed by the page's word boxes, so it can be drawn."""
    n = noted(paper, "--on", "notes/paper.pdf", "--page", "1", "--quote", "Cycle spaces of finite quivers")
    row = published_note(paper, n["id"])
    assert row["detached"] is False
    assert row["rects"] and row["artifact"] and "mark" not in row


@pytest.mark.poppler
def test_a_mark_is_placed_by_its_words_needs_no_session_and_never_fades(
    paper: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    n = noted(paper, "--on", "notes/paper.pdf", "--page", "1", "--quote", "Cycle spaces", "--mark", "highlight")
    assert n["mark"] == "highlight" and n["session"] == "" and len(n["rects"]) == 1
    assert 200 < n["rects"][0][0] < 215 and 120 < n["rects"][0][1] < 130
    monkeypatch.setenv("LOOM_FIXED_TIME", "2027-01-01T09:00:00Z")
    assert published_note(paper, n["id"])["faded"] is False
    refused(
        "note",
        "--on",
        "notes/paper.pdf",
        "--page",
        "1",
        "--quote",
        "not in this paper at all",
        "--mark",
        "underline",
        "--as",
        "Tester",
        cwd=paper,
        code=2,
        match="not on page 1",
    )


def test_what_a_mark_needs_is_refused_by_name(paper: Path) -> None:
    """A mark is on a PDF and names its page; a pin says something; a box has one rectangle; ink has strokes."""
    base = ("note", "--as", "Tester")
    refused(
        *base, "--on", "notes/a.md", "--quote", "orbit", "--mark", "highlight", cwd=paper, code=2, match="page of a PDF"
    )
    refused(
        *base,
        "--on",
        "notes/paper.pdf",
        "--quote",
        "Cycle",
        "--mark",
        "highlight",
        cwd=paper,
        code=2,
        match="names its page",
    )
    refused(
        *base,
        "--on",
        "notes/paper.pdf",
        "--page",
        "1",
        "--box",
        TITLE,
        "--mark",
        "pin",
        cwd=paper,
        code=2,
        match="says something",
    )
    refused(
        *base,
        "--on",
        "notes/paper.pdf",
        "--page",
        "1",
        "--mark",
        "box",
        "--stroke",
        "1,2,3,4",
        cwd=paper,
        code=2,
        match="one rectangle",
    )
    refused(
        *base,
        "--on",
        "notes/paper.pdf",
        "--page",
        "1",
        "--box",
        TITLE,
        "--mark",
        "ink",
        cwd=paper,
        code=2,
        match="needs its strokes",
    )
    refused(
        *base,
        "--on",
        "notes/paper.pdf",
        "--page",
        "1",
        "--mark",
        "ink",
        "--stroke",
        "1,2,3",
        cwd=paper,
        code=2,
        match="an x and a y",
    )


def test_every_mark_is_written_and_stroked_ones_are_bounded(paper: Path) -> None:
    on = ("--on", "notes/paper.pdf", "--page", "1")
    assert noted(paper, "look here", *on, "--box", "50,50,16,16", "--mark", "pin")["rects"] == [[50, 50, 66, 66]]
    assert (
        noted(paper, "words on the page", *on, "--box", "50,90,200,20", "--mark", "text")["body"] == "words on the page"
    )
    assert noted(paper, *on, "--box", "50,120,100,50", "--mark", "oval")["mark"] == "oval"
    ink = noted(paper, *on, "--mark", "ink", "--stroke", "10,10,20,30,40,5", "--stroke", "50,50,60,60")
    assert ink["strokes"] == [[10, 10, 20, 30, 40, 5], [50, 50, 60, 60]] and ink["rects"] == [[10, 5, 60, 60]]
    assert noted(paper, *on, "--mark", "arrow", "--stroke", "1,2,30,40")["rects"] == [[1, 2, 30, 40]]


@pytest.mark.poppler
def test_a_mark_takes_a_colour_keeps_it_through_a_comment_and_can_lose_it(paper: Path) -> None:
    from loom.notes import load

    on = ("--on", "notes/paper.pdf", "--page", "1")
    hl = noted(paper, *on, "--quote", "Cycle spaces", "--mark", "highlight", "--color", "green")["id"]
    assert load(paper)[hl].color == "green"
    assert "green highlight on notes/paper.pdf" in ok("since", "--as", AGENT, "--dry-run", cwd=paper).stdout
    noted(paper, "worth a comment", "--edit", hl)
    assert load(paper)[hl].color == "green"
    # a change of colour alone leaves what it says
    noted(paper, "--edit", hl, "--color", "pink")
    assert (load(paper)[hl].color, load(paper)[hl].body) == ("pink", "worth a comment")
    noted(paper, "--edit", hl, "--color", "none")
    assert load(paper)[hl].color is None and load(paper)[hl].body == "worth a comment"
    assert "color" not in noted(paper, *on, "--quote", "Cycle spaces", "--mark", "underline")


@pytest.mark.poppler
def test_a_colour_is_for_a_mark_and_is_one_of_the_five(paper: Path) -> None:
    from loom.cli._quilt import open_scan
    from loom.notes import NoteRefused, change, write

    base = ("note", "--as", "Tester", "--on", "notes/paper.pdf", "--page", "1", "--quote", "Cycle")
    refused(*base, "--color", "green", cwd=paper, code=2, match="only a mark")
    refused(*base, "--mark", "highlight", "--color", "teal", cwd=paper, code=2, match="teal")
    with pytest.raises(NoteRefused, match="one of yellow"):
        write(
            open_scan(str(paper)),
            "notes/paper.pdf",
            author="T",
            author_kind="person",
            session="",
            page=1,
            quote="Cycle",
            mark="highlight",
            color="teal",
        )
    plain = noted(
        paper, "--on", "notes/paper.pdf", "--page", "1", "--quote", "Cycle", "--session", open_session(paper)
    )["id"]
    with pytest.raises(NoteRefused, match="only a mark"):
        change(paper, plain, "T", "person", color="green")


@pytest.mark.poppler
def test_a_mark_is_changed_erased_and_restored_and_the_log_keeps_it(paper: Path) -> None:
    from loom.cli._quilt import open_scan
    from loom.notes import load, published
    from loom.paths import NOTE_LOG

    on = ("--on", "notes/paper.pdf", "--page", "1")
    hl = noted(paper, *on, "--quote", "Cycle spaces", "--mark", "highlight")["id"]
    noted(paper, "worth a comment", "--edit", hl)
    assert load(paper)[hl].body == "worth a comment"
    noted(paper, "--erase", hl)
    assert load(paper)[hl].erased
    assert hl not in published(open_scan(str(paper)))
    noted(paper, "--restore", hl)
    assert load(paper)[hl].erased is None and load(paper)[hl].body == "worth a comment"
    assert [json.loads(line)["event"] for line in (paper / NOTE_LOG).read_text().splitlines()] == [
        "noted",
        "changed",
        "erased",
        "restored",
    ]


@pytest.mark.poppler
def test_an_agent_changes_only_its_own_marks(paper: Path) -> None:
    on = ("--on", "notes/paper.pdf", "--page", "1")
    mine = noted(paper, *on, "--quote", "Cycle spaces", "--mark", "highlight")["id"]
    theirs = noted(paper, *on, "--quote", "finite quivers", "--mark", "underline", who=AGENT)["id"]
    refused("note", "--erase", mine, "--as", AGENT, cwd=paper, code=2, match="an agent changes only its own")
    refused("note", "no", "--edit", mine, "--as", AGENT, cwd=paper, code=2, match="an agent changes only its own")
    assert noted(paper, "--erase", theirs, who=AGENT)["erased"]
    assert "erased" not in noted(paper, "--restore", theirs, who=AGENT)


@pytest.mark.poppler
def test_a_changed_file_moves_a_mark_with_words_and_detaches_the_rest(paper: Path) -> None:
    """The bytes change: words still on the page are drawn where they are now; a mark with no words, or whose words left, is detached (A3)."""
    on = ("--on", "notes/paper.pdf", "--page", "1")
    words = noted(paper, *on, "--quote", "Cycle spaces", "--mark", "highlight")["id"]
    gone = noted(paper, *on, "--quote", "Elspeth Arden", "--mark", "highlight")["id"]
    box = noted(paper, *on, "--box", TITLE, "--mark", "box")["id"]
    assert not published_note(paper, words)["detached"] and not published_note(paper, box)["detached"]
    pdf = paper / "notes" / "paper.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"\n% another version\n")
    assert published_note(paper, words)["detached"] is False and published_note(paper, words)["rects"]
    assert published_note(paper, box)["detached"] is True
    pdf.unlink()
    assert published_note(paper, gone)["detached"] is True


def test_a_note_written_during_a_take_in_draws_an_id_of_its_own(paper: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A take-in counts once and numbers its whole run from that, so a note written while it runs waits for the log rather than drawing the number the run is about to use."""
    import loom.notes as notes
    from loom.cli._quilt import open_scan

    result = open_scan(str(paper))
    counted = threading.Event()
    placed = notes._placed

    def slowly(*args: Any, **kwargs: Any) -> Any:
        if not counted.is_set():
            counted.set()
            time.sleep(0.3)
        return placed(*args, **kwargs)

    monkeypatch.setattr(notes, "_placed", slowly)
    items = [{"page": 1, "mark": "pin", "rects": [[50, 50, 66, 66]], "body": "from the file"}]
    taker = threading.Thread(
        target=notes.take_in,
        args=(result, "notes/paper.pdf", items),
        kwargs={"author": "Tester", "author_kind": "person"},
    )
    taker.start()
    assert counted.wait(5)
    notes.write(
        result,
        "notes/paper.pdf",
        author="Tester",
        author_kind="person",
        session="",
        body="beside",
        page=1,
        mark="pin",
        rects=[[9, 9, 25, 25]],
    )
    taker.join()
    ids = [e["id"] for e in map(json.loads, notes._path(paper).read_text().splitlines()) if e["event"] == "noted"]
    assert len(ids) == len(set(ids)) == 2


@pytest.mark.poppler
def test_a_pdfs_own_annotations_are_taken_in_once(paper: Path) -> None:
    """Page, place and words say an annotation is already here, an erased one included, so taking a PDF in twice adds nothing; what wrote each stays in its origin and the words under a highlight are read from the page."""
    from loom.cli._quilt import open_scan
    from loom.notes import erase, load, published, take_in

    result = open_scan(str(paper))
    items = [
        {
            "page": 1,
            "mark": "highlight",
            "rects": [[206.9, 125.4, 293.4, 141.0]],
            "body": "from Preview",
            "color": "yellow",
            "origin": {"by": "Reader", "subtype": "Highlight", "color": [255, 255, 0], "ref": "19R", "sha": "abc"},
        },
        {"page": 1, "mark": "pin", "rects": [[50, 50, 66, 66]], "body": "a sticky note", "color": "teal"},
        {"page": 1, "mark": "ink", "strokes": [[10, 10, 20, 30]]},
        {"page": 1, "mark": "pin", "rects": [[50, 50, 66, 66]]},
        {"page": "one", "mark": "pin", "rects": [[1, 1, 2, 2]], "body": "x"},
    ]
    kw = {"author": "Tester", "author_kind": "person"}
    assert take_in(result, "notes/paper.pdf", items, **kw) == {"taken": 3, "already": 0, "skipped": 2}
    notes = list(load(paper).values())
    assert notes[0].quote == "Cycle spaces" and notes[0].origin["by"] == "Reader" and notes[0].session == ""  # type: ignore[index]
    assert notes[0].color == "yellow" and notes[1].color is None
    assert take_in(result, "notes/paper.pdf", items, **kw) == {"taken": 0, "already": 3, "skipped": 2}
    erase(paper, notes[1].id, "Tester", "person")
    assert take_in(result, "notes/paper.pdf", items, **kw)["taken"] == 0
    # erased and from the file: the manifest goes on saying so, so the viewer goes on hiding the annotation in the file
    erase(paper, notes[0].id, "Tester", "person")
    assert published_note(paper, notes[0].id)["erased"]
    assert notes[1].id not in published(result)
