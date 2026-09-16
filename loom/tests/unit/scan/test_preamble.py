from pathlib import Path

from loom.scan.directives import parse_directives
from loom.scan.preamble import build_closure, taxa_conflicts, taxa_union
from loom.scan.source import read_source


def _quilt(tmp_path: Path, files: dict[str, str]):
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    srcs = {rel: read_source(tmp_path, rel) for rel in files if rel.endswith(".tex")}
    return srcs


def test_taxa_newtheorem_forms(tmp_path: Path) -> None:
    srcs = _quilt(
        tmp_path,
        {
            "drafts/main.tex": r"""
\documentclass{amsart}
\usepackage{amsthm}
\theoremstyle{plain}
\newtheorem{thm}{Theorem}[section]
\newtheorem{lem}[thm]{Lemma}
\newtheorem*{mainthm}{Main Theorem}
\theoremstyle{definition}
\newtheorem{defn}[thm]{Definition}
\newtheorem{constr}[thm]{Construction}
\theoremstyle{remark}
\newtheorem{rmk}[thm]{Remark}
\begin{document}
\newtheorem{ignored}{Ignored}
\end{document}
"""
        },
    )
    m = srcs["drafts/main.tex"]
    c = build_closure(m, tmp_path, dict(srcs), parse_directives(m))
    t = c.taxa
    assert (t["thm"].name, t["thm"].style, t["thm"].numbered, t["thm"].within) == ("Theorem", "plain", True, "section")
    assert (t["lem"].name, t["lem"].counter) == ("Lemma", "thm")
    assert (t["mainthm"].name, t["mainthm"].numbered) == ("Main Theorem", False)
    assert t["defn"].style == "definition" and t["constr"].style == "definition"
    assert t["rmk"].style == "remark"
    assert "ignored" not in t
    assert not c.loads_loom


def test_taxa_declaretheorem_and_directive(tmp_path: Path) -> None:
    srcs = _quilt(
        tmp_path,
        {
            "drafts/main.tex": r"""
\documentclass{article}
\usepackage{thmtools}
\usepackage{loom}
\declaretheorem[name=Proposition, style=definition]{prop}
\declaretheorem{corollary}
% !LOOM environment: claim = Claim, plain
% !TEX program = lualatex
\begin{document}
\end{document}
"""
        },
    )
    m = srcs["drafts/main.tex"]
    c = build_closure(m, tmp_path, dict(srcs), parse_directives(m))
    assert (c.taxa["prop"].name, c.taxa["prop"].style) == ("Proposition", "definition")
    assert c.taxa["corollary"].name == "Corollary"
    assert (c.taxa["claim"].name, c.taxa["claim"].style) == ("Claim", "plain")
    assert c.loads_loom and c.engine == "lualatex"


def test_taxa_transitive_sty_chain(tmp_path: Path) -> None:
    srcs = _quilt(
        tmp_path,
        {
            "drafts/main.tex": "\\documentclass{amsart}\n\\input{preamble.tex}\n\\begin{document}\n\\end{document}\n",
            "preamble.tex": "\\usepackage{base-macros,math-env,\n  quiver}\n",
            "base-macros.sty": "\\usepackage{math-env}\n\\newcommand{\\Res}{\\mathrm{Res}}\n",
            "math-env.sty": "\\theoremstyle{theorem}\n\\newtheorem{thm}{Theorem}[section]\n\\newtheorem{math-example}[thm]{Example}\n\\newtheorem*{thm*}{Theorem}\n\\newtheorem*{predefn}{Preliminary-Definition}\n",
        },
    )
    m = srcs["drafts/main.tex"]
    c = build_closure(m, tmp_path, dict(srcs), parse_directives(m))
    assert c.files == ["drafts/main.tex", "preamble.tex", "base-macros.sty", "math-env.sty"]
    assert set(c.taxa) == {"thm", "math-example", "thm*", "predefn"}
    assert c.taxa["thm"].style == "plain"
    assert c.taxa["predefn"].name == "Preliminary-Definition"
    assert c.macros["Res"].body == "\\mathrm{Res}"
    codes = [d.code for d in c.diagnostics]
    assert codes.count("loom:unknown-theoremstyle") == 1


def test_taxa_display_name_macro(tmp_path: Path) -> None:
    srcs = _quilt(
        tmp_path,
        {
            "drafts/main.tex": r"""
\documentclass{amsart}
\newtheorem*{namedtheorem}{\theoremname}
\newcommand{\theoremname}{testing}
\newcommand{\lemname}{Lemma}
\newtheorem{lem}{\lemname}
\newenvironment{named}[1]{\renewcommand\theoremname{#1}\begin{namedtheorem}}{\end{namedtheorem}}
\begin{document}
\end{document}
"""
        },
    )
    m = srcs["drafts/main.tex"]
    c = build_closure(m, tmp_path, dict(srcs), parse_directives(m))
    assert c.taxa["lem"].name == "Lemma"
    assert c.taxa["namedtheorem"].name == "Namedtheorem"
    assert [d.code for d in c.diagnostics] == ["loom:taxon-name-macro"]


def test_taxa_conflict_between_masters(tmp_path: Path) -> None:
    srcs = _quilt(
        tmp_path,
        {
            "drafts/main.tex": "\\documentclass{amsart}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\\end{document}\n",
            "drafts/talk.tex": "\\documentclass{beamer}\n\\theoremstyle{definition}\\newtheorem{thm}{Theorem}\n\\begin{document}\\end{document}\n",
        },
    )
    cs = [build_closure(srcs[p], tmp_path, dict(srcs), []) for p in ("drafts/main.tex", "drafts/talk.tex")]
    assert taxa_union(cs)["thm"].style == "plain"
    assert [env for env, _ in taxa_conflicts(cs)] == ["thm"]
