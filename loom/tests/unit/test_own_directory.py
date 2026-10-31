"""A document compiles from its own directory (plan 0.22.4): its names resolve there at every depth, `..` is refused, derived texts read their source's directory, loom writes node files beside the document, and the macros come from the block or a loom.sty kept beside it."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from loom.refs.scan import _named_bibs, bib_file
from loom.render.assets import resolve_graphic
from loom.reshape.linearize import with_macro_block
from loom.scan.expand import resolve_inclusion
from loom.scan.preamble import _local
from loom.scan.quilt import load_quilt, save_author
from loom.scan.scan import landmark_bases, scan
from loom.tex.aux import parse_aux
from tests.helpers import json_of, ok

PAPER = with_macro_block(
    "\\documentclass{article}\n\\usepackage{local}\n\\newtheorem{lemma}{Lemma}\n\\begin{document}\n"
    "\\section{Start}\\label{qq-0100}\n\\input{nodes/qq-0001}\n\\includegraphics{figures/fig.pdf}\n"
    "\\bibliography{refs}\n\\end{document}\n"
)[0]


def paper_quilt(tmp_path: Path) -> Path:
    """A quilt whose one document is `paper/main.tex`, with its node files, a style, a figure and a bibliography beside it."""
    q = tmp_path / "q"
    (q / "paper" / "nodes").mkdir(parents=True)
    (q / "paper" / "figures").mkdir()
    (q / "config.toml").write_text('[quilt]\nname = "q"\nprefix = "qq"\nmain = "paper/main.tex"\n', encoding="utf-8")
    (q / "paper" / "main.tex").write_text(PAPER, encoding="utf-8")
    (q / "paper" / "local.sty").write_text("\\newcommand{\\local}{x}\n\\newtheorem{remark}{Remark}\n", encoding="utf-8")
    (q / "paper" / "nodes" / "qq-0001.tex").write_text(
        "\\begin{lemma}\\label{qq-0001}A \\local{} lemma.\\end{lemma}\n", encoding="utf-8"
    )
    (q / "paper" / "figures" / "fig.pdf").write_bytes(b"%PDF-1.4\n%fake\n")
    (q / "paper" / "refs.bib").write_text("@misc{x, title={X}}\n", encoding="utf-8")
    return q


def test_a_document_reads_its_names_from_its_own_directory(tmp_path: Path) -> None:
    q = paper_quilt(tmp_path)
    result = scan(load_quilt(q))
    assert result.base_of("paper/main.tex") == "paper"
    assert "paper/nodes/qq-0001.tex" in result.expansions["paper/main.tex"].reached
    closure = result.closures["paper/main.tex"]
    assert "paper/local.sty" in closure.files and "remark" in closure.taxa
    assert not [d for d in result.diagnostics if d.code == "missing-include"]
    ok("compile", "paper/main.tex", cwd=q)
    # the fake TeX reads `\input` from its working directory, so the node's number shows the compile ran in paper/
    assert "qq-0001" in parse_aux((q / "build/paper/main/main.aux").read_text())


def test_dotdot_is_refused_by_every_resolver(tmp_path: Path) -> None:
    """Overleaf cannot follow `..`, so no document may reach above its directory."""
    q = paper_quilt(tmp_path)
    (q / "shared.tex").write_text("Shared.\n", encoding="utf-8")
    (q / "up.sty").write_text("% up\n", encoding="utf-8")
    (q / "up.pdf").write_bytes(b"%PDF-1.4\n")
    (q / "up.bib").write_text("@misc{y, title={Y}}\n", encoding="utf-8")
    assert resolve_inclusion(q, "../shared", base="paper") == (None, "missing")
    assert _local(q, "../up", (".sty",), "paper") is None
    assert resolve_graphic(q, "../up.pdf", "paper") is None
    assert _named_bibs(q, "\\bibliography{../up}", "paper") == ([], ["../up"])


def test_an_agent_copy_and_a_landmark_read_their_source_s_directory(tmp_path: Path) -> None:
    save_author("A. Author")
    q = paper_quilt(tmp_path)
    ok("draft", "paper/main.tex", "--ai", "aidoc.tex", cwd=q)
    result = scan(load_quilt(q))
    assert result.base_of("drafting-ai/aidoc.tex") == "paper"
    assert "paper/local.sty" in result.closures["drafting-ai/aidoc.tex"].files
    ok("compile", "drafting-ai/aidoc.tex", cwd=q)
    assert (q / "build/drafting-ai/aidoc/aidoc.pdf").is_file()
    ok("stamp", "paper/main.tex", "-m", "first", cwd=q)
    assert set(landmark_bases(load_quilt(q)).values()) == {"paper"}
    assert bib_file(load_quilt(q)) == "paper/refs.bib"


def test_loom_new_and_atomize_write_node_files_beside_the_document(tmp_path: Path) -> None:
    q = paper_quilt(tmp_path)
    made = json_of("new", "lemma", "--as", "A. Author", "--json", cwd=q)
    assert (made["file"], made["input"]) == (f"paper/nodes/{made['id']}.tex", f"\\input{{nodes/{made['id']}}}")
    main = q / "paper" / "main.tex"
    main.write_text(
        main.read_text().replace(
            "\\end{document}", "\\begin{lemma}\\label{qq-0003}\nInline.\n\\end{lemma}\n\\end{document}"
        )
    )
    ok("atomize", "paper/main.tex", "--to", "paper/spine.tex", cwd=q)
    assert (q / "paper" / "nodes" / "qq-0003.tex").is_file()
    assert "\\input{nodes/qq-0003}" in (q / "paper" / "spine.tex").read_text()


def test_the_macros_come_from_the_block_or_a_loom_sty_beside_the_document(tmp_path: Path) -> None:
    """The block and a kept loom.sty each load loom's macros, and neither shadows them; a document with neither is told."""
    q = paper_quilt(tmp_path)
    sty = resources.files("loom").joinpath("assets", "loom.sty").read_text(encoding="utf-8")
    (q / "paper" / "loom.sty").write_text(sty, encoding="utf-8")
    body = "\\begin{document}\nX\\uses{qq-0001}\n\\end{document}\n"
    (q / "paper" / "kept.tex").write_text("\\documentclass{article}\n\\usepackage{loom}\n" + body, encoding="utf-8")
    (q / "paper" / "neither.tex").write_text("\\documentclass{article}\n" + body, encoding="utf-8")
    (q / "paper" / "main.tex").write_text(PAPER.replace("\\end{document}", "\\uses{qq-0001}\n\\end{document}"))
    result = scan(load_quilt(q))
    assert "paper/loom.sty" in result.closures["paper/kept.tex"].files
    diags = json_of("lint", "--json", cwd=q, code=1)["diagnostics"]
    found = {
        (d["code"], d["locations"][0]["file"])
        for d in diags
        if d["code"] in ("loom:macros-unloaded", "loom:macro-shadowed")
    }
    assert found == {("loom:macros-unloaded", "paper/neither.tex")}


def test_a_compile_leaves_the_document_s_directory_as_it_found_it(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """latexmk reads a `.bcf`, `.aux` or `.toc` it finds where it runs, and runs biber there, so a document compiles in a clean copy of its directory: an editor's leftovers are neither read nor overwritten."""
    import loom.tex.runner as runner

    q = paper_quilt(tmp_path)
    leftovers = {name: f"% the editor's {name}\n" for name in ("main.aux", "main.bbl", "main.bcf", "main.toc")}
    for name, text in leftovers.items():
        (q / "paper" / name).write_text(text, encoding="utf-8")
    before = sorted(p.name for p in (q / "paper").iterdir())
    ran_in: list[Path] = []
    real = runner.compile_tex

    def watched(cwd: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        ran_in.append(cwd)
        assert not any((cwd / name).exists() for name in leftovers), "a leftover was staged"
        return real(cwd, *args, **kwargs)

    monkeypatch.setattr(runner, "compile_tex", watched)
    ok("compile", "paper/main.tex", cwd=q)
    assert ran_in and not ran_in[0].is_relative_to(q)  # a copy, not the author's directory
    assert sorted(p.name for p in (q / "paper").iterdir()) == before
    assert {name: (q / "paper" / name).read_text() for name in leftovers} == leftovers
    assert "qq-0001" in parse_aux((q / "build/paper/main/main.aux").read_text())
