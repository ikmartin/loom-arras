"""Digests (book 8): postnote matching, provenance checks, extraction from a reference paper's source on the fake toolchain, porting with --as, and the fetch gate."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.scan.postnote import normalize, parts
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from loom.tex.bundle import build_bundle

REF = r"""\documentclass{article}
\usepackage{amsmath,amsthm}
\usepackage{xy}
\newcommand{\Hom}{\operatorname{Hom}}
\newcommand{\pair}[2]{\langle #1, #2\rangle}
\DeclareMathOperator{\Tr}{Tr}
\def\weird#1.{[#1]}
\newtheorem{thm}{Theorem}[section]
\newtheorem{lem}[thm]{Lemma}
\theoremstyle{definition}
\newtheorem{defn}[thm]{Definition}
\begin{document}
\section{Introduction}
We study widgets. This paper proves Theorem~\ref{main}.

Second paragraph of the introduction.
\section{Setup}
\begin{defn}\label{d:widget}
A widget is $\pair{x}{y}$ with $\Hom(x,y)$ and $\Tr$.
\end{defn}
\begin{lem}\label{l:one}
Every widget has $\weird a.$ parts, see \eqref{eq:key}.
\begin{equation}\label{eq:key} x = y \end{equation}
\end{lem}
\begin{proof}
By Definition~\ref{d:widget} and \eqref{eq:key}.
\end{proof}
\section{Results}
\begin{thm}[Main]\label{main}
Widgets are gadgets.
\end{thm}
\begin{proof}
Combine Lemma~\ref{l:one} and Definition~\ref{d:widget}.
\end{proof}
\begin{thm}
Unlabelled theorem.
\end{thm}
\end{document}
"""


def run(*args: str, cwd: Path, env: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args), env=env)
    finally:
        os.chdir(old)


def demo(tmp_path: Path) -> Path:
    assert run("init", str(tmp_path / "q"), "--demo", cwd=tmp_path).exit_code == 0
    q = tmp_path / "q"
    with (q / "refs.bib").open("a") as fh:
        fh.write("\n@misc{Ref20, title={Widgets}, author={Ref, A.}, year={2020}, eprint={2001.00001v2}}\n")
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "ref.tex").write_text(REF)
    return q


def test_postnote_normalization_table() -> None:
    assert normalize("Theorem 4.1") == "theorem 4.1"
    assert normalize("Thm.~4.1, p.~12") == "theorem 4.1"
    assert normalize("Section 4") == "section 4" == normalize("\\S 4") == normalize("§4") == normalize("Sec. IV")
    assert normalize("see Prop. 3.11") == "proposition 3.11" == normalize("Proposition 3.11 (2)")
    assert normalize("\\href{https://stacks.math.columbia.edu/tag/04Y5}{Tag 04Y5}") == "tag 04y5"
    assert normalize("Cor. A.31") == "corollary a.31" and normalize("Rmk A.19") == "remark a.19"
    assert normalize("pp.~12--14") == ""
    assert parts("Theorems 4.1 and 4.3") == ["theorem 4.1", "theorem 4.3"]
    assert parts("Thm. A.20, Rmk A.19") == ["theorem a.20", "remark a.19"]
    assert parts("Theorem 4.1, p.~12") == ["theorem 4.1"]
    assert parts("Standing assumptions, Section 1") == [
        "standing assumption",
        "section 1",
    ]  # plurals fold on both sides


def test_postnote_match_edge_unmatched_and_no_postnote(tmp_path: Path) -> None:
    q = demo(tmp_path)
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(
        node.read_text().replace(
            "\\end{lemma}",
            "% see \\cite[Prop.~3.2]{Man12}, \\cite[Section 2]{Man12}, \\cite[Lemma 99]{Man12}, and \\cite{Man12}.\n\\end{lemma}",
            1,
        )
    )
    r = scan(load_quilt(q))
    post = [(e.src, e.to) for e in r.edges.edges if e.via == "postnote"]
    assert ("dm-0003/proof", "Man12-prop-3.2") in post  # the demo's own citation
    assert ("dm-0002", "Man12-prop-3.2") not in post  # inside a comment: comments are blanked before every stage
    lint = run("lint", cwd=q).output
    assert "unmatched-postnote" not in lint
    node.write_text(node.read_text().replace("% see", "See"))
    r = scan(load_quilt(q))
    post = [(e.src, e.to) for e in r.edges.edges if e.via == "postnote"]
    assert ("dm-0002", "Man12-prop-3.2") in post
    assert ("dm-0002", "Man12-setup") in post and ("dm-0002", "Man12-sec-2") in post  # Section 2 names both
    lint = run("lint", cwd=q).output
    assert "loom:unmatched-postnote" in lint and "Lemma 99" in lint
    digest = q / "digests" / "Man12.tex"
    digest.write_text(
        digest.read_text().replace("\\label{Man12-prop-3.2}", "\\label{Man12-prop-3.2}\\label{Man12-lem-99}", 1)
    )
    assert "unmatched-postnote" not in run("lint", cwd=q).output  # an alias id names the result under another numbering
    assert lint.count("unmatched-postnote") == 1  # \cite{Man12} without a postnote is neither an edge nor a diagnostic


def test_version_mismatch_and_missing_package_and_undigested(tmp_path: Path) -> None:
    q = demo(tmp_path)
    bib = q / "refs.bib"
    bib.write_text(bib.read_text().replace("eprint  = {0805.2065v2}", "eprint  = {0805.2065v3}", 1))
    assert "0805.2065v3" in bib.read_text()
    digest = q / "digests" / "Man12.tex"
    digest.write_text(
        digest.read_text().replace("% !LOOM requires: amsmath, amsthm", "% !LOOM requires: amsmath, amsthm, tikz-cd")
    )
    lint = run("lint", cwd=q).output
    assert "loom:version-mismatch" in lint and "v2" in lint and "v3" in lint
    assert "loom:missing-package" in lint and "tikz-cd" in lint
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text().rstrip("\n") + "\nSee \\cite[Theorem 1]{Ref20}.\n")
    assert run("status", "--undigested", cwd=q).output.split() == ["Ref20"]


def test_extract_from_source_drops_proofs_keeps_uses_and_refuses_existing(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("digest", "extract", "Ref20", str(tmp_path / "paper" / "ref.tex"), cwd=q)
    assert r.exit_code == 0, r.output
    text = (q / "digests" / "Ref20.tex").read_text()
    head = text.splitlines()[:5]
    assert head[0] == "% !LOOM digest: Ref20" and head[1] == "% !LOOM source: arXiv:2001.00001v2"
    assert head[2] == "% !LOOM method: extract" and head[3].startswith("% !LOOM created: ")
    assert "% !LOOM requires: xy" in text and "numbering: emulated" not in text
    assert "\\begin{proof}" not in text
    assert (
        "\\begin{definition}[{\\cite[Definition 2.1, p.~1]{Ref20}}]\\label{Ref20-def-2.1}" in text
    )  # the quilt's environment names
    assert "\\begin{lemma}[{\\cite[Lemma 2.2, p.~1]{Ref20}}]\\label{Ref20-lem-2.2}\n\\uses{Ref20-def-2.1}\n" in text
    assert (
        "\\begin{theorem}[{\\cite[Theorem 3.1 (Main), p.~1]{Ref20}}]\\label{Ref20-thm-3.1}\n\\uses{Ref20-lem-2.2, Ref20-def-2.1}\n"
        in text
    )
    assert (
        "\\label{Ref20-thm-3.2}" in text
    )  # the unlabelled theorem, numbered by emulation after the .aux resynchronised 3.1
    assert "$\\langle x, y\\rangle$ with $\\operatorname{Hom}(x,y)$ and $\\operatorname{Tr}$" in text  # macros expanded
    assert "\\label{Ref20-eq:key}" in text and "\\eqref{Ref20-eq:key}" in text
    assert "% !LOOM begin macros\n\\let\\weird\\undefined\n\\def\\weird#1.{[#1]}\n% !LOOM end macros" in text
    assert "\\section{Setup}\\label{Ref20-sec-2}" in text and "\\section{Results}\\label{Ref20-sec-3}" in text
    assert "\\section*{Overview}\nWe study widgets. This paper proves Theorem~\\ref{Ref20-thm-3.1}." in text
    assert "\\label{Ref20-setup}" in text and "\\incomplete{Standing assumptions not extracted" in text
    assert "Extracted 4 results (2 Theorem, 1 Definition, 1 Lemma); 2 sections" in r.output
    assert "\\uses recorded: 3" in r.output and "Numbering: from the paper's .aux" in r.output
    assert "Lint on the digest: clean" in r.output or "loom:missing-package" in r.output
    again = run("digest", "extract", "Ref20", str(tmp_path / "paper" / "ref.tex"), cwd=q)
    assert again.exit_code != 0 and "exists" in again.output
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(
        node.read_text().replace(
            "\\end{lemma}", "By \\cite[Theorem 3.1]{Ref20} and \\cite[Thm.~3.2, p.~1]{Ref20}.\n\\end{lemma}", 1
        )
    )
    deps = run("deps", "dm-0002", cwd=q).output
    assert "Ref20-thm-3.1" in deps and "Ref20-thm-3.2" in deps
    res = scan(load_quilt(q))
    bundle = build_bundle(res, "dm-0002").text
    assert (
        bundle.count("\\begingroup\n\\let\\weird\\undefined") == 4
    )  # one scoped group per digest statement in the closure (8.3.2)
    lem_bundle = build_bundle(res, "Ref20-lem-2.2").text
    assert (
        "\\begingroup\n\\let\\weird\\undefined\n\\def\\weird#1.{[#1]}\n\\begin{lemma}" in lem_bundle
        and "\\endgroup" in lem_bundle
    )


def test_extract_counter_emulation_when_compile_fails(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("digest", "extract", "Ref20", str(tmp_path / "paper" / "ref.tex"), cwd=q, env={"FAKE_TEX_FAIL": "1"})
    assert r.exit_code == 0, r.output
    text = (q / "digests" / "Ref20.tex").read_text()
    assert "% !LOOM numbering: emulated" in text and "Numbering: emulated" in r.output
    for local in ("def-2.1", "lem-2.2", "thm-3.1", "thm-3.2", "sec-2", "sec-3"):
        assert f"\\label{{Ref20-{local}}}" in text, local


def test_import_digest_as_rewrites_prefix(tmp_path: Path) -> None:
    q = demo(tmp_path)
    assert run("digest", "extract", "Ref20", str(tmp_path / "paper" / "ref.tex"), cwd=q).exit_code == 0
    src = q / "digests" / "Ref20.tex"
    assert run("init", str(tmp_path / "lib"), "--demo", cwd=tmp_path).exit_code == 0
    lib = tmp_path / "lib"
    r = run("digest", "import", str(src), "--as", "Other20", cwd=lib)
    assert r.exit_code == 0, r.output
    text = (lib / "digests" / "Other20.tex").read_text()
    assert text.startswith("% !LOOM digest: Other20\n")
    assert "Ref20" not in text
    assert "\\label{Other20-thm-3.1}" in text and "\\uses{Other20-lem-2.2, Other20-def-2.1}" in text
    assert "\\cite[Theorem 3.1 (Main), p.~1]{Other20}" in text and "\\eqref{Other20-eq:key}" in text
    assert "digest-without-bib" in r.output  # Other20 is not in lib's bibliography
    assert run("digest", "import", str(src), "--as", "Other20", cwd=lib).exit_code != 0  # never overwrites


def test_fetch_refused_without_config(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("digest", "fetch", "Ref20", cwd=q)
    assert r.exit_code == 2 and "fetch = true" in r.output
    assert not (q / "refs").exists() or not any((q / "refs").rglob("*.tex"))


@pytest.mark.network
def test_fetch_writes_gitignored_dirs(tmp_path: Path) -> None:
    if not os.environ.get("LOOM_NETWORK"):
        pytest.skip("set LOOM_NETWORK=1 to fetch from arXiv")
    q = demo(tmp_path)
    cfg = q / "config.toml"
    cfg.write_text(cfg.read_text() + "\n[refs]\nfetch = true\n")
    bib = q / "refs.bib"
    bib.write_text(bib.read_text().replace("eprint={2001.00001v2}", "eprint={0805.2065v2}"))
    r = run("digest", "fetch", "Ref20", "--pdf", cwd=q)
    assert r.exit_code == 0, r.output
    home = q / "digests" / "arxiv" / "0805.2065v2"
    assert any((home / "src").iterdir()) and (home / "paper.pdf").exists()


def test_requires_missing_package_named_first_on_bundle_failure(tmp_path: Path) -> None:
    q = demo(tmp_path)
    assert run("digest", "extract", "Ref20", str(tmp_path / "paper" / "ref.tex"), cwd=q).exit_code == 0
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text().replace("\\end{lemma}", "By \\cite[Theorem 3.1]{Ref20}.\n\\end{lemma}", 1))
    r = run("compile", "dm-0002", cwd=q, env={"FAKE_TEX_FAIL": "1"})
    assert r.exit_code == 1
    lines = [ln for ln in r.output.splitlines() if ln.strip()]
    assert lines[0].startswith("loom:missing-package: digest Ref20 requires xy") and lines[-1].startswith(
        "FAILED bundle dm-0002"
    )
