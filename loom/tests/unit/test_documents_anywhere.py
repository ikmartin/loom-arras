"""Documents anywhere, named by path (plan 0.22.3): a file loom reads with `\\documentclass` is a document wherever it sits, and its path without `.tex` names it in the build output, its fragment, the viewer's address and every lookup by word."""

from __future__ import annotations

import json
from pathlib import Path

from loom.scan.quilt import load_quilt, save_author
from loom.scan.scan import scan
from tests.helpers import json_of, ok, refused
from tests.unit._quilts import demo

PAPER = "\\documentclass{article}\n\\begin{document}\nA paper of its own.\n\\end{document}\n"


def unset_main(q: Path) -> None:
    config = q / "config.toml"
    config.write_text("".join(ln for ln in config.read_text().splitlines(keepends=True) if not ln.startswith("main ")))


def test_two_documents_of_one_stem_are_two_documents(tmp_path: Path) -> None:
    """`paper/main.tex` beside `drafting/main.tex` compiles, renders and is addressed apart from it."""
    q = demo(tmp_path)
    (q / "paper").mkdir()
    (q / "paper" / "main.tex").write_text(PAPER, encoding="utf-8")
    result = scan(load_quilt(q))
    assert {"drafting/main.tex", "paper/main.tex"} <= set(result.masters)
    assert result.default_master == "drafting/main.tex" and result.document_role("paper/main.tex") == "person"
    ok("compile", "paper/main.tex", cwd=q)
    ok("compile", "drafting/main.tex", cwd=q)
    assert (q / ".loom/build/paper/main/main.pdf").is_file() and (q / ".loom/build/drafting/main/main.pdf").is_file()
    ok("build", cwd=q)
    masters = {x["path"]: x for x in json.loads((q / ".loom/build/manifest.json").read_text())["masters"]}
    assert (masters["paper/main.tex"]["fragment"], masters["paper/main.tex"]["pdf"]) == (
        "fragments/masters/paper/main.html",
        "paper/main/main.pdf",
    )
    assert masters["drafting/main.tex"]["fragment"] == "fragments/masters/drafting/main.html"
    assert (q / ".loom/build/fragments/masters/paper/main.html").is_file()
    urls = {e["key"]: e["url"] for e in json_of("search", "paper", "--json", cwd=q)["matches"] if e["kind"] == "master"}
    assert urls.get("paper/main.tex") == "/master/paper/main", urls


def test_a_stem_two_documents_share_names_neither(tmp_path: Path) -> None:
    """A stem is a name only while one document has it; a lookup by a shared stem is refused, naming both."""
    save_author("A. Author")  # adopt is the author's
    q = demo(tmp_path)
    (q / "paper").mkdir()
    (q / "paper" / "main.tex").write_text(PAPER, encoding="utf-8")
    for args in (
        ("deloom", "main", "--to", ".loom/build/flat.tex"),
        ("search", "1.1", "--in", "main"),
        ("adopt", "main"),
    ):
        r = refused(*args, cwd=q, code=2, match="names 2 documents")
        assert "drafting/main.tex" in r.output and "paper/main.tex" in r.output, r.output
    ok("search", "1.1", "--in", "paper/main", cwd=q)  # its name, the path without .tex


def test_the_only_document_is_the_default_wherever_it_sits(tmp_path: Path) -> None:
    q = tmp_path / "q"
    (q / "paper").mkdir(parents=True)
    (q / "config.toml").write_text('[quilt]\nname = "q"\nprefix = "qq"\n', encoding="utf-8")
    (q / "paper" / "main.tex").write_text(PAPER, encoding="utf-8")
    result = scan(load_quilt(q))
    assert result.masters == ["paper/main.tex"] and result.default_master == "paper/main.tex"
    assert not [d for d in result.diagnostics if d.code in ("loom:main-unset", "loom:main-not-found")]


def test_several_documents_and_no_main_make_none_the_default(tmp_path: Path) -> None:
    """Choosing one of several by its path would be arbitrary, so the quilt says to set `[quilt] main`."""
    q = demo(tmp_path)
    unset_main(q)
    result = scan(load_quilt(q))
    assert result.default_master is None
    assert [d.code for d in result.diagnostics if d.code.startswith("loom:main")] == ["loom:main-unset"]
