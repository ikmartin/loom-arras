"""A note on a page of a cited work (plan 0.13 items 2 and 4): its shape in the annotation log, and how it resolves against the store rather than against a key."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loom.cli._quilt import open_scan
from loom.records.annotations import load_records
from loom.records.log import append
from loom.records.store import Records
from tests.helpers import json_of, ok, the
from tests.unit._quilts import demo


def _note_on_page(q: Path, session: str, **fields: Any) -> None:
    """Append one `created` event for a note on a page of `Calloway14`, whose demo store is `doi/10.4171_demo_14-1`."""
    ann_id = fields.pop("id")
    anchor = {"kind": "pdf", "sha256": fields.pop("sha256"), "page": fields.pop("page", 2), **fields.pop("anchor", {})}
    append(
        q,
        {
            "when": "2026-09-21T10:00:00Z",
            "author": "A. Author",
            "kind": "human",
            "session": session,
            "event": "created",
            "id": ann_id,
            "target": "doi:10.4171/demo/14-1",
            "against": "sha256:" + anchor["sha256"],
            "anchor": anchor,
            "annotation_kind": fields.pop("kind", "question"),
            "body": fields.pop("body", "Is this the balanced case?"),
            **fields,
        },
    )
    Records(q)  # replays: a malformed event would be reported here, and the assertion below is on the shape


def test_a_note_on_a_page_round_trips_through_the_log(tmp_path: Path) -> None:
    """The log's `anchor` is two shapes under one name: the text triple every annotation carries, and, on a note against a page, the page anchor beside it, told apart by `kind`. Reading one must keep the page fields, not drop them into the selector."""
    q = demo(tmp_path)
    sid = ok("session", "new", "reading", cwd=q).stdout.split()[0]
    text_anchor = {
        "basis": "text", "start": 12, "end": 36, "exact": "balanced at every vertex", "prefix": "locus is ", "suffix": " of the",
    }  # fmt: skip
    _note_on_page(q, sid, id="a-2026-09-21-0001", sha256="feed" * 16, anchor=text_anchor)
    box_anchor = {"basis": "box", "quads": [[82.8, 278.1, 529.2, 315.7]], "exact": "", "prefix": "", "suffix": ""}
    _note_on_page(q, sid, id="a-2026-09-21-0002", sha256="feed" * 16, kind="note", anchor=box_anchor)
    ok("annotate", "dm-0003", "on a key, as ever", "--kind", "note", "--session", sid, "--author", "A. Author", cwd=q)

    records, problems = load_records(q)
    assert problems == []
    by_id = {a.id: a for r in records for a in r.annotations}
    text = by_id["a-2026-09-21-0001"]
    assert text.anchor is not None and (text.anchor.kind, text.anchor.page, text.anchor.basis) == ("pdf", 2, "text")
    assert (text.anchor.start, text.anchor.end) == (12, 36) and text.anchor.quads is None
    assert text.selector is not None and text.selector.exact == "balanced at every vertex"
    assert text.target_key == "doi:10.4171/demo/14-1"
    box = by_id["a-2026-09-21-0002"]
    assert box.anchor is not None and box.anchor.basis == "box" and box.anchor.quads == [[82.8, 278.1, 529.2, 315.7]]
    # and a note on a key is exactly what it was: a selector and no page anchor
    plain = the(
        by_id.values(), lambda a: a.target_key == "dm-0003" and a.body == "on a key, as ever", "the note on dm-0003"
    )
    assert plain.anchor is None
    # the shape survives the dict form the manifest and the API hand around
    assert text.to_dict()["anchor"]["basis"] == "text" and "quads" not in text.to_dict()["anchor"]
    assert box.to_dict()["anchor"]["quads"] == [[82.8, 278.1, 529.2, 315.7]]


def test_a_note_on_a_page_resolves_against_the_store_and_not_against_a_key(tmp_path: Path) -> None:
    """`recorded` is whether the artifact the anchor names is the one in the store; `detached` is a quotation that no longer locates in the page's committed text; a box is never detached. The target is the work's identifier and the citekey is found through the bibliography, so a renamed citekey changes nothing. None of it touches a key's own text."""
    q = demo(tmp_path)
    home = q / "digests" / "storage" / "doi" / "10.4171_demo_14-1"
    sha = "feed" * 16
    (home / "sections.json").write_text(json.dumps({"sha256": sha, "pages": 2, "chars": 60, "sections": []}))
    (home / "pages").mkdir(exist_ok=True)
    (home / "pages" / "0002.txt").write_text("the fixed locus is balanced at every vertex of the widget\n")
    sid = ok("session", "new", "reading", cwd=q).stdout.split()[0]
    found_anchor = {
        "basis": "text",
        "start": 19,
        "end": 43,
        "exact": "balanced at every vertex",
        "prefix": "",
        "suffix": "",
    }
    _note_on_page(q, sid, id="a-2026-09-21-0001", sha256=sha, anchor=found_anchor)
    lost_anchor = {"basis": "text", "start": 0, "end": 5, "exact": "nowhere on this page", "prefix": "", "suffix": ""}
    _note_on_page(q, sid, id="a-2026-09-21-0002", sha256=sha, anchor=lost_anchor)
    box_anchor = {"basis": "box", "quads": [[1, 2, 3, 4]], "exact": "", "prefix": "", "suffix": ""}
    _note_on_page(q, sid, id="a-2026-09-21-0003", sha256="dead" * 16, kind="note", anchor=box_anchor)

    by_id = {r.annotation.id: r for r in Records(q).resolved(open_scan(str(q)))}
    found = by_id["a-2026-09-21-0001"]
    assert found.work == "Calloway14" and found.recorded and not found.detached and found.span == (19, 43)
    lost = by_id["a-2026-09-21-0002"]
    assert lost.work == "Calloway14" and lost.recorded and lost.detached
    box = by_id["a-2026-09-21-0003"]
    # a stale artifact, but the rectangles are the record
    assert (box.work, box.recorded, box.detached) == ("Calloway14", False, False)

    # status: no row, no count, listed by work on request (design §4)
    j = json_of("status", "--json", cwd=q)
    carrying = [k for k, e in j["keys"].items() if "a-2026-09-21" in json.dumps(e)]
    assert carrying == [], f"a note on a page shows in the rows of {carrying}"
    assert [r["id"] for r in j["reading"]] == ["a-2026-09-21-0001", "a-2026-09-21-0002", "a-2026-09-21-0003"]
    assert j["reading"][0]["work"] == "Calloway14" and j["reading"][0]["page"] == 2
    listed = ok("status", "--reading", cwd=q).output
    for said in ("Calloway14", "a-2026-09-21-0002", "detached", "p.2 (box)"):
        assert said in listed, f"{said!r} not in status --reading:\n{listed}"
    assert "a-2026-09-21" not in ok("status", cwd=q).output
    # and the agent's own list carries the citekey and the page, which is what it can act on
    mine = json_of("ai", "annotations", "--session", sid, "--json", cwd=q)["annotations"]
    assert {(f["work"], f["page"]) for f in mine} == {("Calloway14", 2)}
