"""The quilt's annotation types: the defaults `loom init` writes, reading the file, and what a bad file costs."""

from __future__ import annotations

from pathlib import Path

from loom.agents import denied_by
from loom.paths import ANNOTATION_TYPES
from loom.records.types import COLORS, default_text, load_types, parse_types
from loom.scan.quilt import QuiltConfig
from tests.helpers import json_of, ok

FOUR = """
[[type]]
id = "hint"
name = "Hint"
color = "green"
style = "underline"
weight = 2
opacity = 80
open = true
instructions = "A question that leads the learner toward the fault without giving the answer."
"""


def test_the_defaults_are_four_types_with_their_looks() -> None:
    types, problems = parse_types(default_text())
    assert problems == []
    assert [(t.id, t.name, t.look.color, t.look.style, t.look.opacity, t.open, t.notes) for t in types] == [
        ("revision", "Revision", "red", "highlight", 65, True, False),
        ("suggestion", "Suggestion", "orange", "highlight", 60, True, False),
        ("question", "Question", "blue", "highlight", 60, True, False),
        ("note", "Note", "grey", "highlight", 60, False, True),
    ]
    assert all(t.instructions and t.look.color in COLORS for t in types)


def test_a_quilt_without_the_file_has_the_defaults_and_no_complaint(tmp_path: Path) -> None:
    got = load_types(tmp_path)
    assert [t.id for t in got.types] == ["revision", "suggestion", "question", "note"]
    assert got.source is None and got.problems == []


def test_a_file_that_is_not_toml_loads_the_defaults_and_says_so(tmp_path: Path) -> None:
    (tmp_path / ".loom").mkdir()
    (tmp_path / ANNOTATION_TYPES).write_text("[[type]\nid = ", encoding="utf-8")
    got = load_types(tmp_path)
    assert [t.id for t in got.types] == ["revision", "suggestion", "question", "note"]
    assert len(got.problems) == 1 and "the default types are used" in got.problems[0]


def test_a_type_that_cannot_be_read_costs_only_itself(tmp_path: Path) -> None:
    (tmp_path / ".loom").mkdir()
    bad = '\n[[type]]\nid = "loud"\nname = "Loud"\ncolor = "teal"\nstyle = "highlight"\nweight = 2\nopacity = 60\n'
    (tmp_path / ANNOTATION_TYPES).write_text(FOUR + bad, encoding="utf-8")
    got = load_types(tmp_path)
    assert [t.id for t in got.types] == ["hint"]
    assert got.types[0].look.style == "underline" and got.types[0].notes is False
    assert got.problems == [f"{ANNOTATION_TYPES}: type 'loud': color must be one of {', '.join(COLORS)}"]


def test_init_writes_the_defaults_listed_and_upgrade_keeps_an_edited_file(tmp_path: Path) -> None:
    q = tmp_path / "q"
    ok("init", str(q), "--prefix", "zz", "--ai", "none", "--yes")
    assert (q / ANNOTATION_TYPES).read_text(encoding="utf-8") == default_text()
    (q / ANNOTATION_TYPES).write_text(FOUR, encoding="utf-8")
    ok("upgrade", cwd=q)
    assert (q / ANNOTATION_TYPES).read_text(encoding="utf-8") == FOUR
    (q / ANNOTATION_TYPES).unlink()
    report = json_of("upgrade", "--json", cwd=q)
    assert ANNOTATION_TYPES in str(report)
    assert (q / ANNOTATION_TYPES).read_text(encoding="utf-8") == default_text()


def test_an_agent_may_edit_the_types_but_nothing_else_of_loom_s(tmp_path: Path) -> None:
    config = QuiltConfig()
    assert denied_by(config, ANNOTATION_TYPES) is None
    assert denied_by(config, ".loom/annotations/log.jsonl") == ".loom/"


def test_the_manifest_carries_the_types_and_a_bad_file_is_a_diagnostic(tmp_path: Path) -> None:
    q = tmp_path / "q"
    ok("init", str(q), "--prefix", "zz", "--ai", "none", "--yes")
    (q / ANNOTATION_TYPES).write_text(FOUR + '\n[[type]]\nid = "x"\n', encoding="utf-8")
    ok("build", cwd=q)
    import json

    manifest = json.loads((q / ".loom" / "build" / "manifest.json").read_text(encoding="utf-8"))
    assert [t["id"] for t in manifest["annotation_types"]] == ["hint"]
    assert manifest["annotation_types"][0]["look"] == {
        "color": "green",
        "style": "underline",
        "weight": 2,
        "opacity": 80,
    }
    codes = [d["code"] for d in manifest["diagnostics"]]
    assert "loom:annotation-types" in codes
