"""Notes, a quote among them (plan 0.22.8): written on anything the viewer shows, read by an agent through `loom since`, kept, linked, and fading when neither."""

from __future__ import annotations

import json
from pathlib import Path

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
        and on_work["rects"] == [[10, 20, 100, 40]]
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
    ok("annotate", "dm-0003", f"see [](quilt:{linked['id']})", "--kind", "note", "--as", "Tester", cwd=q)
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
        resolve(result, q, "quilt:n-2026-01-01-0099")
    assert ok("link", n["id"], cwd=q).stdout.strip() == f"[](quilt:{n['id']})"
