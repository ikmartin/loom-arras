"""`recorded`: whether loom can still produce the text a note was written against (WQ-48). Every writer and the check hash the same text, every version written against is frozen at once, and a note whose version is gone is not pinned to the text that replaced it."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import ok, the

WHO = ("--author", "A. Author")


@pytest.fixture
def q(tmp_path: Path) -> Path:
    ok("init", str(tmp_path / "q"), "--demo", cwd=tmp_path)
    return tmp_path / "q"


def comment(q: Path, *args: str) -> str:
    r = ok("comment", *args, "--kind", "note", *WHO, cwd=q)
    return r.output.split()[0]


def resolved(q: Path) -> dict[str, object]:
    from loom.cli._quilt import open_scan
    from loom.records.store import Records

    result = open_scan(str(q))
    return {r.annotation.id: r for r in Records(q, result.quilt.history_dir).resolved(result)}


def rewrite(q: Path, rel: str, old: str, new: str) -> None:
    p = q / rel
    text = p.read_text()
    assert old in text
    p.write_text(text.replace(old, new, 1))


def test_a_note_on_any_kind_of_key_is_recorded(q: Path) -> None:
    """A section's and a document's text holds its children's places; the version a note records and the version it is checked against are the same text."""
    ids = {
        "section": comment(q, "dm-0010", "On the section."),
        "document": comment(q, "drafting/main.tex", "On the paper."),
        "result": comment(q, "dm-0002", "On the lemma."),
        "proof": comment(q, "dm-0002/proof", "On the proof."),
        "equation": comment(q, "dm-0001#eq:fix", "On the equation."),
    }
    got = resolved(q)
    assert {kind: got[a].recorded for kind, a in ids.items()} == dict.fromkeys(ids, True)  # type: ignore[attr-defined]


def test_a_version_written_against_survives_edits_before_any_build(q: Path) -> None:
    rewrite(q, "nodes/dm-0002.tex", "one or two points", "one or two elements")
    ann = comment(q, "dm-0002", "Which elements?", "--quote", "one or two elements")
    rewrite(q, "nodes/dm-0002.tex", "Every orbit", "Each orbit")  # moved again, and nothing was built in between
    assert resolved(q)[ann].recorded  # type: ignore[attr-defined]


def test_an_edit_restates_the_finding_against_the_text_as_it_is_now(q: Path) -> None:
    from loom.cli._quilt import open_scan
    from loom.render.manifest import key_hash

    ann = comment(q, "dm-0002", "Say which orbits.")
    rewrite(q, "nodes/dm-0002.tex", "Every orbit", "Each orbit")
    ok("comment", "--edit", ann, "Still: say which orbits.", *WHO, cwd=q)
    a = resolved(q)[ann].annotation  # type: ignore[attr-defined]
    assert a.body == "Still: say which orbits." and a.target_hash == key_hash(open_scan(str(q)), "dm-0002")


def test_a_reply_records_the_text_it_was_written_against(q: Path) -> None:
    from loom.cli._quilt import open_scan
    from loom.render.manifest import key_hash

    parent = comment(q, "dm-0002", "Say which orbits.")
    before = key_hash(open_scan(str(q)), "dm-0002")
    rewrite(q, "nodes/dm-0002.tex", "Every orbit", "Each orbit")
    ok("comment", "--reply", parent, "Done.", *WHO, cwd=q)
    got = resolved(q)
    reply = the(got.values(), lambda x: x.annotation.in_reply_to == parent, f"reply to {parent}")  # type: ignore[attr-defined]
    now = key_hash(open_scan(str(q)), "dm-0002")
    assert got[parent].annotation.target_hash == before  # type: ignore[attr-defined]
    assert reply.annotation.target_hash == now != before  # type: ignore[attr-defined]


def test_a_note_whose_version_is_gone_is_not_pinned_to_the_new_text(q: Path) -> None:
    from loom.cli._quilt import open_scan
    from loom.records.log import append
    from loom.records.store import Records
    from loom.render.build import _marks_by_node

    kept = comment(q, "dm-0002", "Which points?", "--quote", "one or two points")
    # a note naming a version loom never kept, whose quote still reads in today's text
    lost = {
        "event": "created",
        "id": "a-2026-01-01-0001",
        "when": "2026-01-01T00:00:00Z",
        "author": "A. Author",
        "kind": "human",
        "session": "s-2026-01-01-0001",
        "target": "dm-0002",
        "against": "sha256:" + "0" * 64,
        "anchor": {"exact": "one or two points", "prefix": "", "suffix": ""},
        "annotation_kind": "note",
        "body": "About a version nobody kept.",
    }
    append(q, lost)
    got = resolved(q)
    assert got[kept].recorded and not got[lost["id"]].recorded  # type: ignore[attr-defined]
    assert got[lost["id"]].span is not None  # its words still read, which is the danger  # type: ignore[attr-defined]
    result = open_scan(str(q))
    marked = {m.ann_id for ms in _marks_by_node(result, Records(q, result.quilt.history_dir)).values() for m in ms}
    assert kept in marked and lost["id"] not in marked


def test_an_edit_from_the_viewer_changes_the_body(q: Path) -> None:
    """The viewer names the new text `message`, as every endpoint does; the log's field is `body`, and replay read only that."""
    from loom.render.api import handle

    ann = comment(q, "dm-0002", "Say which orbits.")
    sid = ok("session", "list", cwd=q).output.split()[0]
    handle(
        q, "edit", {"annotation": ann, "message": "Say which orbits, please.", "session": sid, "author": "A. Author"}
    )
    assert resolved(q)[ann].annotation.body == "Say which orbits, please."  # type: ignore[attr-defined]
