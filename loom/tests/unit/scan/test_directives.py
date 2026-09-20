from pathlib import Path

from loom.scan.directives import file_level, list_value, parse_directives
from loom.scan.source import read_source


def _src(tmp_path: Path, text: str):
    (tmp_path / "f.tex").write_text(text, encoding="utf-8")
    return read_source(tmp_path, "f.tex")


def test_directive_three_forms(tmp_path: Path) -> None:
    src = _src(
        tmp_path,
        "% !LOOM ignore\n% !LOOM tags: a, b-c, d.e\n% !LOOM begin macros\n\\newcommand{\\x}{y}\n%!LOOM end macros\n% !TEX program = lualatex\n% !TEX root = ../main.tex\n% !LOOM bogus-key: 1\n",
    )
    ds = parse_directives(src)
    forms = [(d.key, d.form, d.value) for d in ds]
    assert forms[0] == ("ignore", "bare", "")
    assert forms[1] == ("tags", "kv", "a, b-c, d.e") and list_value(forms[1][2]) == ["a", "b-c", "d.e"]
    assert forms[2] == ("macros", "begin", "") and forms[3] == ("macros", "end", "")
    assert forms[4] == ("program", "tex", "lualatex") and forms[5] == ("root", "tex", "../main.tex")
    assert forms[6] == ("bogus-key", "kv", "1")
    assert src.ignored


def test_directive_scope_file_level(tmp_path: Path) -> None:
    lines = (
        ["% !LOOM author: A"]
        + ["x"] * 25
        + ["% !LOOM tags: late", "\\begin{lemma}", "% !LOOM tags: inner", "\\end{lemma}"]
    )
    src = _src(tmp_path, "\n".join(lines))
    ds = parse_directives(src)
    first_node = src.text.index("\\begin{lemma}")
    assert [d.key for d in file_level(ds, first_node)] == ["author"]
