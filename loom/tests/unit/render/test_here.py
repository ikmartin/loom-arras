"""`loom here`: the place a viewer tab reported to a running `loom serve`, read back by the command and named against the quilt, held in memory only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.helpers import json_of, ok
from tests.unit._quilts import demo, open_session
from tests.unit.render._serve import get, post


def told(s: Any, place: dict[str, Any]) -> None:
    """Report `place` as a viewer tab does."""
    status, said = post(s.url + "_api/here", place)
    assert status == 200 and said == {"ok": True}, said


def test_with_nothing_serving_the_quilt_it_says_so(tmp_path: Path) -> None:
    q = demo(tmp_path)
    got = json_of("here", "--json", cwd=q)
    assert got["serving"] is False and got["verdict"].startswith("nothing serves this quilt")


def test_a_server_no_tab_has_reported_to_names_where_to_open_it(session) -> None:  # type: ignore[no-untyped-def]
    s, q = session
    got = json_of("here", "--json", cwd=q)
    assert got["serving"] is True and got["place"] is None and s.url in got["verdict"]


def test_a_document_a_block_and_the_words_selected_are_named_with_their_links(session) -> None:  # type: ignore[no-untyped-def]
    s, q = session
    sid = open_session(q)
    told(
        s,
        {
            "route": "reading",
            "item": {"kind": "document", "id": "drafting/main.tex"},
            "block": {"src": "nodes/dm-0003.tex:1:4", "key": "dm-0003"},
            "selection": {"key": "dm-0003", "text": "a finite set"},
            "beside": {"kind": "work", "id": "Calloway14", "place": {"page": 2}},
            "session": sid,
        },
    )
    got = json_of("here", "--json", cwd=q)["looking"]
    assert got["item"]["link"] == "quilt:drafting/main.tex"
    assert (got["block"]["key"], got["block"]["link"]) == ("dm-0003", "quilt:dm-0003")
    assert got["selection"]["text"] == "a finite set"
    assert got["beside"]["link"] == "cited:doi:10.4171/demo/14-1?page=2"
    assert got["session"]["link"] == f"quilt:{sid}"
    text = ok("here", cwd=q).stdout
    assert text.startswith("the person is looking at drafting/main.tex, at dm-0003 (")
    assert '"a finite set"' in text and "[](quilt:dm-0003)" in text and "annotations land here" in text
    assert "by the viewer tab touched last" in text


def test_a_region_of_a_page_review_and_a_key_gone_are_each_said(session) -> None:  # type: ignore[no-untyped-def]
    s, q = session
    told(
        s,
        {
            "route": "reading",
            "item": {"kind": "work", "id": "Calloway14"},
            "page": 3,
            "selection": {"page": 3, "rects": [[72, 100.5, 300, 140]]},
        },
    )
    text = ok("here", cwd=q).stdout
    assert "Calloway14" in text and "page 3" in text and "72,100.5,300,140" in text
    assert "[](cited:doi:10.4171/demo/14-1?page=3)" in text
    # the tab touched last wins: a second report replaces the first
    told(s, {"route": "review", "review": {"key": "dm-0003", "cause": "earlier-change"}})
    assert ok("here", cwd=q).stdout.startswith("the person is in Review, on dm-0003 (")
    told(s, {"route": "reading", "item": {"kind": "node", "id": "dm-9999"}})
    assert "(no longer in the quilt)" in ok("here", cwd=q).stdout
    told(s, {"route": "elsewhere", "path": "/graph"})
    assert ok("here", cwd=q).stdout.startswith("the person is on /graph in the viewer")


def test_the_place_is_held_in_memory_and_served_only_with_the_token(tmp_path: Path, serve) -> None:  # type: ignore[no-untyped-def]
    """Where a person reads and what they selected are theirs: never on disk, and never served without the token or to another origin."""
    q = demo(tmp_path)
    s = serve(q)
    before = {
        p.relative_to(q).as_posix(): p.read_bytes() for p in q.rglob("*") if p.is_file() and "build" not in p.parts
    }
    told(
        s,
        {
            "route": "reading",
            "item": {"kind": "node", "id": "dm-0003"},
            "selection": {"key": "dm-0003", "text": "private words"},
        },
    )
    after = {
        p.relative_to(q).as_posix(): p.read_bytes() for p in q.rglob("*") if p.is_file() and "build" not in p.parts
    }
    assert after == before and not any(b"private words" in b for b in after.values())
    assert not any(b"private words" in p.read_bytes() for p in (q / "build").rglob("*") if p.is_file())
    token = json.loads(get(s.url + "_api")[2])["token"]
    assert get(s.url + "_api/here")[0] == 403
    assert get(s.url + "_api/here", {"X-Loom-Token": token, "Origin": "http://evil.example"})[0] == 403
    status, _, raw = get(s.url + "_api/here", {"X-Loom-Token": token})
    assert status == 200 and json.loads(raw)["place"]["selection"]["text"] == "private words"
