"""A Markdown file's boxes (plan 0.27): what is a task, the line each names, and the tick, which changes one character, keeps the old text and is not listed back to the person who made it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loom.files import render_file_markdown
from loom.looks import changes
from loom.records.snapshots import read_raw
from loom.records.store import render_markdown
from loom.scan.hashing import sha256
from loom.scan.quilt import load_quilt, save_author
from loom.tasks import Task, TickRefused, items, tick
from tests.unit._quilts import demo

WHO = "Tester"


def lines_of(text: str) -> list[int]:
    return [t.line for t in items(text)]


def test_only_a_list_item_opening_with_a_box_is_a_task() -> None:
    text = (
        "- [ ] open\n- [x] done\n- [X] done too\n- plain\n- [ ]\n- [y] no\n- [ ](http://a.example) a link\n\n"
        "1. [ ] ordered\n   - [x] nested\n\n> - [ ] quoted\n\n```\n- [ ] fenced\n```\n\n[ ] in no list\n"
    )
    found = items(text)
    written = text.split("\n")
    assert [written[t.line] for t in found] == [
        "- [ ] open",
        "- [x] done",
        "- [X] done too",
        "1. [ ] ordered",
        "   - [x] nested",
        "> - [ ] quoted",
    ]
    assert [t.done for t in found] == [False, True, True, False, True, False]


def test_a_box_names_its_true_line_after_mathematics_over_several_lines() -> None:
    """The renderer lifts mathematics and takes its line breaks with it, which moved every later line up by as many."""
    text = "Intro\n\n$$\na = b\n+ c\n$$\n\n- [ ] after $x$\n\nand `$` in code\n\n$$d\ne$$\n\n- [x] later\n"
    written = text.split("\n")
    assert [written[n] for n in lines_of(text)] == ["- [ ] after $x$", "- [x] later"]


def test_lines_count_as_markdown_counts_them() -> None:
    assert lines_of("a\r\n\r\n$$\r\nb\r\n$$\r\n\r\n- [ ] crlf\r\n") == [6]
    assert lines_of("a\n\n- [ ] form feed\x0cinside\n- [ ] next\n") == [2, 3]


def test_a_files_box_is_marked_and_a_cells_is_only_drawn() -> None:
    body = render_file_markdown("- [ ] one $x$\n- [x] two\n", "a.md", {}, tasks=[])
    assert '<li class="task" data-done="false" data-task="1:' in body
    assert '<li class="task" data-done="true" data-task="2:' in body
    assert "[ ]" not in body and "[x]" not in body and 'class="math inline"' in body
    cell = render_file_markdown("- [x] two\n", "n.ipynb", {})
    assert cell == '<ul>\n<li class="task" data-done="true">two</li>\n</ul>'


def test_a_message_keeps_its_brackets() -> None:
    assert render_markdown("- [ ] a message\n") == "<ul>\n<li>[ ] a message</li>\n</ul>"


@pytest.fixture
def q(tmp_path: Path) -> Path:
    save_author(WHO)
    root = demo(tmp_path)
    (root / "notes").mkdir()
    (root / "notes" / "a.md").write_text("# A\n\n- [ ] one\n- [ ] two\n\nend\n", encoding="utf-8")
    (root / "notes" / "b.txt").write_text("- [ ] plain text\n", encoding="utf-8")
    (root / ".hidden.md").write_text("- [ ] hidden\n", encoding="utf-8")
    return root


def box(q: Path, n: int = 0, path: str = "notes/a.md") -> Task:
    return items((q / path).read_bytes().decode("utf-8"))[n]


def set_box(q: Path, task: str, done: bool, *, who: str = WHO, path: str = "notes/a.md") -> bool:
    return tick(load_quilt(q), who, path, task, done)


def ledger(q: Path) -> list[dict]:  # type: ignore[type-arg]
    lines = (q / ".loom" / "history" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
    return [row for row in map(json.loads, lines) if row["action"] == "tick"]


def test_a_tick_changes_one_character_and_keeps_the_text_it_replaced(q: Path) -> None:
    from tests.helpers import ok

    ok("changes", "--keep-all", cwd=q)
    before = (q / "notes/a.md").read_text(encoding="utf-8")
    assert set_box(q, box(q, 1).id, True) is True
    assert (q / "notes/a.md").read_text(encoding="utf-8") == before.replace("- [ ] two", "- [x] two")
    [row] = ledger(q)
    assert (row["actor"], row["path"], row["line"], row["done"], row["words"]) == (WHO, "notes/a.md", 4, True, "two")
    assert read_raw(q, row["from"], q / ".loom" / "history") == before
    assert set_box(q, box(q, 1).id, False) is True
    assert (q / "notes/a.md").read_text(encoding="utf-8") == before


def test_every_other_byte_of_the_file_stands_crlf_and_all(q: Path) -> None:
    raw = b"# A\r\n\r\n- [ ] one  \r\n- [X] two\r\n\r\nno end of line"
    (q / "notes/a.md").write_bytes(raw)
    set_box(q, box(q, 0).id, True)
    assert (q / "notes/a.md").read_bytes() == raw.replace(b"- [ ] one", b"- [x] one")
    set_box(q, box(q, 1).id, False)
    assert (q / "notes/a.md").read_bytes() == raw.replace(b"- [ ] one", b"- [x] one").replace(b"[X]", b"[ ]")


def test_a_box_already_in_that_state_writes_nothing(q: Path) -> None:
    held = box(q).id
    assert set_box(q, held, False) is False
    assert ledger(q) == []


def test_two_ticks_on_one_drawn_page_both_land(q: Path) -> None:
    """A page is not drawn again between ticks, so each box's id has to outlive the other's tick and its own."""
    first, second = box(q, 0).id, box(q, 1).id
    set_box(q, first, True)
    set_box(q, second, True)
    assert (q / "notes/a.md").read_text(encoding="utf-8").count("[x]") == 2
    set_box(q, first, False)
    assert (q / "notes/a.md").read_text(encoding="utf-8").count("[x]") == 1


@pytest.mark.parametrize(
    "edit",
    [
        lambda s: s.replace("# A\n", "# A\n\nA new line.\n"),  # the box's line has moved
        lambda s: s.replace("- [ ] one", "- [ ] uno"),  # its words have changed
        lambda s: s.replace("- [ ] one", "- not a task"),  # it is no longer a box
    ],
)
def test_a_line_that_no_longer_reads_as_the_page_drew_it_is_refused(q: Path, edit) -> None:  # type: ignore[no-untyped-def]
    drawn = box(q).id
    p = q / "notes/a.md"
    edited = edit(p.read_text(encoding="utf-8"))
    p.write_text(edited, encoding="utf-8")
    with pytest.raises(TickRefused) as refused:
        set_box(q, drawn, True)
    assert refused.value.code == "stale"
    assert p.read_text(encoding="utf-8") == edited


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("notes/b.txt", "not-a-task"),
        (".hidden.md", "no-such-file"),
        ("notes/none.md", "no-such-file"),
        ("../outside.md", "no-such-file"),
    ],
)
def test_only_a_shown_markdown_file_has_boxes_to_tick(q: Path, tmp_path: Path, path: str, code: str) -> None:
    (tmp_path / "outside.md").write_text("- [ ] out\n", encoding="utf-8")
    with pytest.raises(TickRefused) as refused:
        set_box(q, "1:00000000", True, path=path)
    assert refused.value.code == code
    assert (tmp_path / "outside.md").read_text(encoding="utf-8") == "- [ ] out\n"


def test_a_link_out_of_the_quilt_is_left_alone_and_a_link_inside_it_stays_a_link(q: Path, tmp_path: Path) -> None:
    (tmp_path / "out.md").write_text("- [ ] out\n", encoding="utf-8")
    (q / "notes/away.md").symlink_to(tmp_path / "out.md")
    with pytest.raises(TickRefused):
        set_box(q, "1:00000000", True, path="notes/away.md")
    (q / "notes/here.md").symlink_to(q / "notes/a.md")
    set_box(q, box(q, 0).id, True, path="notes/here.md")
    assert (q / "notes/here.md").is_symlink()
    assert "- [x] one" in (q / "notes/a.md").read_text(encoding="utf-8")


def listed(q: Path) -> dict[str, int]:
    return {c.path: c.hunks for c in changes(load_quilt(q), WHO)}


def test_a_tick_is_not_listed_back_to_the_person_who_made_it(q: Path) -> None:
    from tests.helpers import ok

    ok("changes", "--keep-all", cwd=q)
    set_box(q, box(q).id, True)
    assert "notes/a.md" not in listed(q)


def test_another_edit_to_the_file_stays_listed_beside_a_tick(q: Path) -> None:
    from tests.helpers import ok

    ok("changes", "--keep-all", cwd=q)
    p = q / "notes/a.md"
    p.write_text(
        "# A edited\n\n" + "\n".join(f"line {n}" for n in range(9)) + "\n\n- [ ] one\n- [ ] two\n", encoding="utf-8"
    )
    before = {c.path: c.diff for c in changes(load_quilt(q), WHO)}["notes/a.md"]
    set_box(q, box(q, 1).id, True)
    after = {c.path: c.diff for c in changes(load_quilt(q), WHO)}["notes/a.md"]
    assert "# A edited" in after and "- [x] two" in p.read_text(encoding="utf-8")
    assert "+- [x] two" not in after and "-- [ ] two" not in after, "the tick is in the look, so it is only context"
    assert before == after.replace("- [x] two", "- [ ] two")


def test_a_tick_inside_an_edit_already_listed_stays_part_of_it(q: Path) -> None:
    from tests.helpers import ok

    ok("changes", "--keep-all", cwd=q)
    p = q / "notes/a.md"
    p.write_text(p.read_text(encoding="utf-8").replace("- [ ] two", "- [ ] two, reworded"), encoding="utf-8")
    set_box(q, box(q, 1).id, True)
    [diff] = [c.diff for c in changes(load_quilt(q), WHO) if c.path == "notes/a.md"]
    assert "+- [x] two, reworded" in diff and "-- [ ] two\n" in diff


def test_with_no_name_or_look_the_tick_still_lands_and_the_file_is_listed_as_ever(q: Path) -> None:
    set_box(q, box(q).id, True, who="")
    assert "- [x] one" in (q / "notes/a.md").read_text(encoding="utf-8")
    assert ledger(q)[0]["actor"] is None


def test_a_tick_keeps_its_old_text_by_content(q: Path) -> None:
    text = (q / "notes/a.md").read_text(encoding="utf-8")
    set_box(q, box(q).id, True)
    assert ledger(q)[0]["from"] == sha256(text)
