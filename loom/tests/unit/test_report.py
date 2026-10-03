"""The report layer itself (plan 0.18.3): what a report prints, its JSON envelope, and progress on a fake clock."""

from __future__ import annotations

import io
import json

import pytest

from loom.cli.report import Group, Item, Progress, Report, table, wrap


def test_the_verdict_comes_first_and_a_long_group_says_what_it_left_out() -> None:
    r = Report(
        "2 works need you",
        ok=False,
        groups=[
            Group(
                "no PDF",
                [Item(f"work {n}", key=f"Ck{n:02d}") for n in range(15)],
                limit=12,
                next="loom refs coverage",
                problem=True,
            )
        ],
    )
    lines = r.render().split("\n")
    assert lines[0] == "2 works need you"
    assert lines[2] == "no PDF (15)"
    assert lines[3] == "  work 0  Ck00"
    assert lines[-1] == "  … and 3 more; loom refs coverage"


def test_an_identifier_is_never_cut_to_fit() -> None:
    key = "romagnyGroupActionsStacks2005-def-2.3"
    out = wrap("  " + "word " * 18 + key, width=60)
    assert all(len(line) <= 60 for line in out[:-1]) and out[-1].endswith(key)
    assert all(key not in line or line.strip().endswith(key) for line in out)
    assert wrap("x" * 120, width=100) == ["x" * 120]  # a word longer than the width stands alone, whole


def test_the_json_is_the_same_report_with_its_data_beside_it() -> None:
    r = Report(
        "1 error",
        ok=False,
        exit=1,
        groups=[
            Group(
                "error dangling-link", [Item("main.tex:3  no such label", key="sy-0001", fixes=["loom lint"])], limit=0
            )
        ],
        notes=["see the log"],
        data={"diagnostics": [{"code": "dangling-link"}]},
    )
    doc = r.to_json()
    assert doc["verdict"] == "1 error" and doc["ok"] is False and doc["exit"] == 1
    assert doc["groups"][0]["items"][0] == {
        "text": "main.tex:3  no such label",
        "key": "sy-0001",
        "fixes": ["loom lint"],
    }
    assert doc["diagnostics"] == [{"code": "dangling-link"}] and doc["notes"] == ["see the log"]
    json.dumps(doc)
    with pytest.raises(ValueError, match="envelope"):
        Report("x", data={"verdict": "y"})


def test_a_dry_run_says_so_and_fixes_read_as_fixes() -> None:
    r = Report(
        "would add 3 entries",
        dry_run=True,
        groups=[Group("needs you", [Item("no PDF", key="Ck", fixes=["loom refs add Ck FILE"])], problem=True)],
    )
    text = r.render()
    assert text.startswith("dry run: would add 3 entries")
    assert "    fix: loom refs add Ck FILE" in text
    assert r.to_json()["dry_run"] is True


def test_a_table_aligns_its_columns_and_leaves_the_last_unpadded() -> None:
    assert table([("ok", "doctor", "x"), ("warn", "tex", "yy")]) == ["ok    doctor  x", "warn  tex     yy"]


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_progress_is_silent_at_first_then_one_line_at_a_time_off_a_terminal() -> None:
    clock, out = Clock(), io.StringIO()
    with Progress("rendering", total=3, stream=out, tty=False, clock=clock, ticking=False) as p:
        p.item("main.tex")
        assert out.getvalue() == "", "a fast command prints nothing"
        clock.now = 2.5
        p.item("talk.tex")
        clock.now = 3.0
        p.tick()  # within `every` of the last line: nothing new
        clock.now = 20.0
        p.tick()
    lines = out.getvalue().splitlines()
    assert lines[0] == "rendering  2/3  talk.tex  0:02"
    assert lines[1] == "rendering  2/3  talk.tex  0:20  still working, 17 s"


def test_progress_on_a_terminal_rewrites_one_line() -> None:
    clock, out = Clock(), io.StringIO()
    with Progress("extract", total=2, stream=out, tty=True, clock=clock, ticking=False, quiet=0) as p:
        p.item("a")
        p.item("b")
    text = out.getvalue()
    assert text.count("\r\x1b[2K") == 2 and text.endswith("\n") and "\n" not in text[:-1]


def test_progress_follows_a_builds_stages_and_counts() -> None:
    """`build` and `refs build` report `(stage, item, n, total)`; the line names the stage, the item and its place in the count."""
    clock, out = Clock(), io.StringIO()
    with Progress("scanning", stream=out, tty=False, clock=clock, ticking=False, quiet=0, every=0) as p:
        p.told("scanning", "", 0, None)
        p.told("rendering", "", 0, 3)
        clock.now = 5.0
        p.told("rendering", "dm-0002", 2, 3)
        p.told("publishing", "", 0, None)
    lines = out.getvalue().splitlines()
    assert "rendering  2/3  dm-0002  0:05" in lines
    assert lines[-1] == "publishing  0:05"
