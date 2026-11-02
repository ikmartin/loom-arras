"""The viewer's Settings writing `config.toml`: one line at a time, the person's comments kept, and nothing written that is refused."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from loom.cli.quilt import CONFIG_TEMPLATE
from loom.config_edit import ConfigRefused, check, edit_text, save, set_values
from loom.reshape.importer import set_main, set_main_forced
from loom.scan.quilt import load_quilt

TEMPLATE = CONFIG_TEMPLATE.format(name="ring", prefix="r")


def _quilt(tmp_path: Path, text: str = TEMPLATE) -> Path:
    root = tmp_path / "q"
    root.mkdir()
    (root / "config.toml").write_text(text, encoding="utf-8")
    return root


def _config(root: Path) -> str:
    return (root / "config.toml").read_text(encoding="utf-8")


def test_a_value_changes_in_place_and_keeps_its_comment(tmp_path: Path) -> None:
    root = _quilt(tmp_path)
    set_values(load_quilt(root), {"quilt.prefix": "ring", "quilt.engine": "xelatex"})
    text = _config(root)
    assert 'prefix = "ring"               # default id prefix for loom new\n' in text
    assert 'engine = "xelatex"         # default engine; % !TEX program in a document overrides\n' in text
    # every other line is as the template wrote it
    assert text == TEMPLATE.replace('prefix = "r"', 'prefix = "ring"').replace('"pdflatex"', '"xelatex"')


def test_a_template_line_becomes_the_setting_with_its_comment(tmp_path: Path) -> None:
    root = _quilt(tmp_path)
    set_values(load_quilt(root), {"quilt.home": "notes/start.md"})
    text = _config(root)
    assert 'home = "notes/start.md"        # the file the viewer opens on' in text
    assert "# home =" not in text
    assert text.index("home =") < text.index("[library]")


def test_a_new_key_goes_after_its_table_s_last_key(tmp_path: Path) -> None:
    root = _quilt(tmp_path)
    set_values(load_quilt(root), {"library.contact": "me@example.org"})
    text = _config(root)
    assert "online = false" in text
    assert text.index("online = false") < text.index('contact = "me@example.org"') < text.index("[lint]")
    assert tomllib.loads(text)["library"]["contact"] == "me@example.org"


def test_a_missing_table_is_added_at_the_end(tmp_path: Path) -> None:
    root = _quilt(tmp_path, '[quilt]\nname = "ring"  # the project\n')
    set_values(load_quilt(root), {"agents.deny": ["paper/", "*.bib"]})
    assert _config(root) == '[quilt]\nname = "ring"  # the project\n\n[agents]\ndeny = ["paper/", "*.bib"]\n'


def test_none_removes_the_line_and_nothing_else(tmp_path: Path) -> None:
    root = _quilt(tmp_path, '[quilt]\nname = "ring"\nmain = "paper/main.tex"  # the paper\nprefix = "r"\n')
    set_values(load_quilt(root), {"quilt.main": None})
    assert _config(root) == '[quilt]\nname = "ring"\nprefix = "r"\n'


def test_a_multi_line_array_is_replaced_whole(tmp_path: Path) -> None:
    body = (
        '[quilt]\nname = "ring"\n\n[agents]\ndeny = [\n  "paper/",  # the paper\n  "notes/",\n]  # what agents leave\n'
    )
    root = _quilt(tmp_path, body)
    set_values(load_quilt(root), {"agents.deny": ["notes/"]})
    assert _config(root) == '[quilt]\nname = "ring"\n\n[agents]\ndeny = ["notes/"]  # what agents leave\n'


def test_each_value_type_round_trips(tmp_path: Path) -> None:
    root = _quilt(tmp_path)
    changes = {
        "quilt.name": 'Rings "and" modules — ∮',
        "library.online": True,
        "lint.disable": ["loom:main-unset", "loom:home-missing"],
    }
    config = set_values(load_quilt(root), changes)
    assert config.name == 'Rings "and" modules — ∮'
    assert config.online is True
    assert config.lint_disable == ["loom:main-unset", "loom:home-missing"]


def test_a_layout_it_cannot_edit_is_refused_and_left_alone(tmp_path: Path) -> None:
    body = 'quilt.name = "ring"\n'
    root = _quilt(tmp_path, body)
    with pytest.raises(ConfigRefused, match="cannot edit line by line"):
        set_values(load_quilt(root), {"quilt.prefix": "ring"})
    assert _config(root) == body


def test_a_change_that_would_add_a_warning_is_refused(tmp_path: Path) -> None:
    root = _quilt(tmp_path)
    with pytest.raises(ConfigRefused, match="negates"):
        set_values(load_quilt(root), {"agents.deny": ["!paper/"]})
    assert _config(root) == TEMPLATE


@pytest.mark.parametrize(
    ("key", "value", "why"),
    [
        ("quilt.name", "  ", "must not be empty"),
        ("quilt.name", "two\nlines", "one line"),
        ("quilt.prefix", "r-1", "letters and digits"),
        ("quilt.engine", "tectonic", "must be one of"),
        ("quilt.main", "notes/other.tex", "not one of your documents"),
        ("quilt.home", "build/x.html", "not a file the viewer shows"),
        ("library.online", "yes", "true or false"),
        ("lint.disable", ["loom:interface-version"], "can be silenced"),
        ("lint.disable", ["no-such-code"], "can be silenced"),
        ("agents.deny", ["!paper/"], "negates"),
        ("agents.deny", ["../elsewhere/"], "leaves the quilt"),
        ("quilt.history", "records", "read-only"),
        ("quilt.research_state", "state.md", "read-only"),
        ("basis.theorem", "proved", "not a setting"),
    ],
)
def test_check_refuses(key: str, value: object, why: str) -> None:
    with pytest.raises(ValueError, match=why):
        check(key, value, masters={"paper/main.tex"}, shown=lambda rel: rel == "README.md")


def test_check_normalises() -> None:
    assert check("quilt.main", "", masters={"paper/main.tex"}) is None
    assert check("quilt.home", "/README.md", shown=lambda rel: rel == "README.md") == "README.md"
    assert check("library.contact", "  ") is None
    assert check("agents.deny", [" paper/ ", "paper/", ""]) == ["paper/"]


def test_save_writes_nothing_when_any_key_is_refused(tmp_path: Path) -> None:
    root = _quilt(tmp_path)
    with pytest.raises(ConfigRefused) as caught:
        save(load_quilt(root), {"quilt.name": "Rings", "quilt.prefix": "r-1"})
    assert set(caught.value.refused) == {"quilt.prefix"}
    assert _config(root) == TEMPLATE


def test_set_main_replaces_the_template_line(tmp_path: Path) -> None:
    root = _quilt(tmp_path)
    (root / "paper").mkdir()
    (root / "paper" / "main.tex").write_text("\\documentclass{article}\n", encoding="utf-8")
    assert set_main(load_quilt(root), "paper/main.tex")
    text = _config(root)
    assert 'main = "paper/main.tex"   # the default LaTeX document' in text
    assert "# main =" not in text
    # main names an existing file now, so a second document does not take its place
    assert not set_main(load_quilt(root), "other/main.tex")
    assert set_main_forced(load_quilt(root), "other/main.tex")
    assert tomllib.loads(_config(root))["quilt"]["main"] == "other/main.tex"


def test_edit_text_leaves_a_text_it_does_not_change_alone() -> None:
    assert edit_text(TEMPLATE, {"quilt.main": None}) == TEMPLATE
