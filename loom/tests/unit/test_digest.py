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
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write("\n@misc{Ref20, title={Widgets}, author={Ref, A.}, year={2020}, eprint={2001.00001v2}}\n")
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "ref.tex").write_text(REF)
    # extraction is gated on loom holding the document, so the source is filed before it is read (plan 0.13 §4)
    assert run("refs", "add", "Ref20", str(tmp_path / "paper" / "ref.tex"), cwd=q).exit_code == 0
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
            "% see \\cite[Prop.~3.2]{Calloway14}, \\cite[Section 3]{Calloway14}, \\cite[Lemma 99]{Calloway14}, and \\cite{Calloway14}.\n\\end{lemma}",
            1,
        )
    )
    r = scan(load_quilt(q))
    post = [(e.src, e.to) for e in r.edges.edges if e.via == "postnote"]
    assert ("dm-0003/proof", "Calloway14-prop-3.2") in post  # the demo's own citation
    assert ("dm-0002", "Calloway14-prop-3.2") not in post  # inside a comment: comments are blanked before every stage
    lint = run("lint", cwd=q).output
    assert "unmatched-postnote" not in lint
    node.write_text(node.read_text().replace("% see", "See"))
    r = scan(load_quilt(q))
    post = [(e.src, e.to) for e in r.edges.edges if e.via == "postnote"]
    assert ("dm-0002", "Calloway14-prop-3.2") in post
    assert ("dm-0002", "Calloway14-sec-3") in post  # a postnote naming a section resolves to the section node
    lint = run("lint", cwd=q).output
    assert "loom:unmatched-postnote" in lint and "Lemma 99" in lint
    digest = q / "digests" / "Calloway14.tex"
    digest.write_text(
        digest.read_text().replace("\\label{Calloway14-prop-3.2}", "\\label{Calloway14-prop-3.2}\\label{Calloway14-lem-99}", 1)
    )
    assert "unmatched-postnote" not in run("lint", cwd=q).output  # an alias id names the result under another numbering
    assert lint.count("unmatched-postnote") == 1  # \cite{Calloway14} without a postnote is neither an edge nor a diagnostic


def test_version_mismatch_and_missing_package_and_undigested(tmp_path: Path) -> None:
    q = demo(tmp_path)
    # A digest whose source is a preprint, against a bibliography that now cites a later one: the demo's own cited work
    # is filed under a DOI, which carries no version, so the mismatch is made here rather than borrowed.
    (q / "digests" / "Man12.tex").write_text(
        "% !LOOM digest: Man12\n% !LOOM extracted-from: arXiv:0805.2065v2\n% !LOOM method: extract\n\n"
        "\\begin{theorem}[{\\cite[Theorem 1]{Man12}}]\\label{Man12-thm-1}\nA.\n\\end{theorem}\n",
        encoding="utf-8",
    )
    bib = q / "digests" / "bibliography.bib"
    bib.write_text(bib.read_text().replace("eprint  = {0805.2065v2}", "eprint  = {0805.2065v3}", 1))
    assert "0805.2065v3" in bib.read_text()
    digest = q / "digests" / "Calloway14.tex"
    digest.write_text(digest.read_text().replace("% !LOOM method:", "% !LOOM requires: tikz-cd\n% !LOOM method:", 1))
    lint = run("lint", cwd=q).output
    assert "loom:version-mismatch" in lint and "v2" in lint and "v3" in lint
    assert "loom:missing-package" in lint and "tikz-cd" in lint
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text().rstrip("\n") + "\nSee \\cite[Theorem 1]{Ref20}.\n")
    assert run("status", "--undigested", cwd=q).output.split() == ["Ref20"]


def test_extract_from_source_drops_proofs_keeps_uses_and_refuses_existing(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = run("digest", "extract", "Ref20", cwd=q)
    assert r.exit_code == 0, r.output
    text = (q / "digests" / "Ref20.tex").read_text()
    head = text.splitlines()[:5]
    assert head[0] == "% !LOOM digest: Ref20" and head[1] == "% !LOOM prefix: Ref20"
    assert head[2] == "% !LOOM extracted-from: arXiv:2001.00001v2"  # the artifact parsed, not the work cited (DR-109)
    assert head[3] == "% !LOOM method: extract" and head[4].startswith("% !LOOM created: ")
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
    again = run("digest", "extract", "Ref20", cwd=q)
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
    r = run("digest", "extract", "Ref20", cwd=q, env={"FAKE_TEX_FAIL": "1"})
    assert r.exit_code == 0, r.output
    text = (q / "digests" / "Ref20.tex").read_text()
    assert "% !LOOM numbering: emulated" in text and "Numbering: emulated" in r.output
    for local in ("def-2.1", "lem-2.2", "thm-3.1", "thm-3.2", "sec-2", "sec-3"):
        assert f"\\label{{Ref20-{local}}}" in text, local


def test_import_digest_as_rewrites_prefix(tmp_path: Path) -> None:
    q = demo(tmp_path)
    assert run("digest", "extract", "Ref20", cwd=q).exit_code == 0
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
    r = run("refs", "fetch", "Ref20", cwd=q)
    assert r.exit_code == 1 and "fetch = true" in r.output
    assert not (q / "refs").exists() or not any((q / "refs").rglob("*.tex"))


def test_build_runs_with_the_network_off(tmp_path: Path) -> None:
    """`loom refs build` is usable in a quilt that has opted into nothing: it says so and still does the local steps."""
    q = demo(tmp_path)
    r = run("refs", "build", cwd=q)
    assert r.exit_code == 0, r.output
    assert "(lookup off)" in r.output and "(fetching off)" in r.output
    assert "needs you" in r.output and "needs an agent" in r.output


def test_build_refuses_an_unknown_step(tmp_path: Path) -> None:
    r = run("refs", "build", "--only", "polish", cwd=demo(tmp_path))
    assert r.exit_code == 2 and "unknown step" in r.output


@pytest.mark.network
def test_fetch_writes_gitignored_dirs(tmp_path: Path) -> None:
    if not os.environ.get("LOOM_NETWORK"):
        pytest.skip("set LOOM_NETWORK=1 to fetch from arXiv")
    q = demo(tmp_path)
    cfg = q / "config.toml"
    cfg.write_text(cfg.read_text().replace("fetch = false", "fetch = true"))
    bib = q / "digests" / "bibliography.bib"
    bib.write_text(bib.read_text().replace("eprint={2001.00001v2}", "eprint={0805.2065v2}"))
    r = run("refs", "fetch", "Ref20", cwd=q)
    assert r.exit_code == 0, r.output
    home = q / "digests" / "arxiv" / "0805.2065v2"
    assert any((home / "src").iterdir()) and (home / "paper.pdf").exists()


def test_requires_missing_package_named_first_on_bundle_failure(tmp_path: Path) -> None:
    q = demo(tmp_path)
    assert run("digest", "extract", "Ref20", cwd=q).exit_code == 0
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text().replace("\\end{lemma}", "By \\cite[Theorem 3.1]{Ref20}.\n\\end{lemma}", 1))
    r = run("compile", "dm-0002", cwd=q, env={"FAKE_TEX_FAIL": "1"})
    assert r.exit_code == 1
    lines = [ln for ln in r.output.splitlines() if ln.strip()]
    assert lines[0].startswith("loom:missing-package: digest Ref20 requires xy") and lines[-1].startswith(
        "FAILED bundle dm-0002"
    )


def test_unverified_locators_when_the_artifact_and_the_cited_work_differ(tmp_path: Path) -> None:
    """A digest extracted from a preprint while the bibliography cites the published article carries numbers and pages from the wrong document. It is the fault that was sitting in demos/relloc: `\\cite[Definition 2.1, p.~4]` against an article beginning at page 201 (DR-109)."""
    q = demo(tmp_path)
    d = q / "digests" / "Split.tex"
    d.parent.mkdir(parents=True, exist_ok=True)
    (q / "digests" / "bibliography.bib").write_text(
        (q / "digests" / "bibliography.bib").read_text()
        + "\n@article{Split, title={S}, doi={10.1090/S1}, eprint={2001.00002v1}}\n",
        encoding="utf-8",
    )
    head = "% !LOOM digest: Split\n% !LOOM prefix: Split\n% !LOOM method: extract\n"
    body = "\\section*{Overview}\nO.\n\\begin{theorem}[{\\cite[Theorem 1]{Split}}]\\label{Split-thm-1}\nS.\n\\end{theorem}\n"

    d.write_text(
        head.replace("method", "extracted-from: arXiv:2001.00002v1\n% !LOOM method", 1) + body, encoding="utf-8"
    )
    r = run("lint", "--json", cwd=q)
    assert "loom:unverified-locators" not in r.output  # a preprint alone says nothing is wrong

    d.write_text(
        "% !LOOM digest: Split\n% !LOOM prefix: Split\n% !LOOM extracted-from: arXiv:2001.00002v1\n"
        "% !LOOM published-as: doi:10.1090/S1\n% !LOOM method: extract\n" + body,
        encoding="utf-8",
    )
    r = run("lint", "--json", cwd=q)
    assert "loom:unverified-locators" in r.output and "a reader will open" in r.output

    # and a digest that does not say where its statements came from cannot be checked at all
    d.write_text(head + body, encoding="utf-8")
    r = run("lint", "--json", cwd=q)
    assert "loom:unverified-locators" in r.output and "does not say what it was extracted from" in r.output


WRAPPED = r"""\documentclass{article}
\usepackage{amsmath,amsthm}
\newtheorem{prop}{Proposition}[section]
\newtheorem{lem}[prop]{Lemma}
\newtheorem{defnp}[prop]{Definition}
\newenvironment{defn}{\begin{defnp}\rm}{\end{defnp}}
\begin{document}
\section{Cones}
\begin{prop}\label{a}
First.
\end{prop}
\begin{defn}\label{b}
A cone is a thing.
\end{defn}
\begin{lem}\label{c}
Third.
\end{lem}
\end{document}
"""

BODY_DECLARED = r"""\documentclass{article}
\usepackage{amsmath,amsthm}
\begin{document}
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\section{Main}
\begin{theorem}\label{main}
The resolution property holds.
\end{theorem}
\begin{lemma}\label{aux}
An auxiliary fact.
\end{lemma}
\end{document}
"""

EMPTY_COUNTER = r"""\documentclass{article}
\newtheorem{counter}[subsection]{$\!\!$}
\newenvironment{theorem}{\begin{counter} {\bf Theorem.}}{\end{counter}}
\newenvironment{lemma}{\begin{counter} {\bf Lemma.}}{\end{counter}}
\begin{document}
\section{Fixed points}
\begin{theorem}\label{t}
The fixed stack is algebraic.
\end{theorem}
\begin{lemma}\label{l}
A lemma.
\end{lemma}
\end{document}
"""


def _extract(tmp_path: Path, src: str, key: str) -> str:
    q = demo(tmp_path)
    paper = tmp_path / f"{key}.tex"
    paper.write_text(src)
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write(f"\n@misc{{{key}, title={{X}}, author={{Y, Z.}}, year={{2000}}}}\n")
    assert run("refs", "add", key, str(paper), cwd=q).exit_code == 0
    r = run("digest", "extract", key, "--no-compile", cwd=q)
    assert r.exit_code == 0, r.output
    return (q / "digests" / f"{key}.tex").read_text()


def test_a_wrapper_around_a_theorem_environment_is_one_and_shares_its_counter(tmp_path: Path) -> None:
    """Behrend-Fantechi's digest read `lem-3.6` for the paper's Lemma 3.8: every definition was a wrapper the extractor did not recognise, on the counter the lemmas share."""
    text = _extract(tmp_path, WRAPPED, "Bf97")
    assert "Bf97-def-1.2" in text, "the definition is a result, and it is numbered"
    assert "Bf97-lem-1.3" in text and "Bf97-lem-1.2" not in text, "the lemma after it keeps the paper's number"


def test_a_theorem_declared_after_begin_document_is_still_a_theorem(tmp_path: Path) -> None:
    """Totaro 2004 declares its environments on the four lines after \\begin{document}, and extracted nothing."""
    text = _extract(tmp_path, BODY_DECLARED, "To04")
    assert "To04-thm-1.1" in text and "To04-lem-1.2" in text


def test_a_wrapper_takes_its_name_from_what_it_prints_when_the_counter_has_none(tmp_path: Path) -> None:
    """Romagny 2022 builds every environment around one counter named `$\\!\\!$`, and extracted one result of twenty-seven."""
    text = _extract(tmp_path, EMPTY_COUNTER, "Ro22")
    assert "\\begin{theorem}" in text or "Ro22-thm" in text
    assert "Ro22-lem" in text


def test_a_parameter_glued_to_a_control_word_stays_separate() -> None:
    """Behrend-Fantechi's exact-sequence macro is `0\\longrightarrow#1...`, and `E` substituted in gave `\\longrightarrowE`: an undefined command, rendered as an error in every sequence."""
    from loom.scan.macros import Macro, expand

    assert (
        expand(Macro("seq", 1, r"0\longrightarrow#1\longrightarrow 0"), ["E"]) == r"0\longrightarrow E\longrightarrow 0"
    )
    assert expand(Macro("seq", 1, r"0\longrightarrow#1"), [r"\alpha"]) == r"0\longrightarrow\alpha", (
        "a backslash ends a control word itself"
    )


def test_a_macro_that_is_a_program_is_kept_not_expanded() -> None:
    """`\\Bbb` unrolled, eight passes deep, into its own error-message trap in the middle of two statements."""
    from loom.digest.extract import expand_macros, is_simple
    from loom.scan.macros import Macro

    trap = Macro("Bbb", 0, r"\relaxnext@\ifmmode\let\next\Bbb@\else\def\next{\errmessage{only in math}}\fi\next")
    assert not is_simple(trap)
    assert is_simple(Macro("Hom", 0, r"\operatorname{Hom}"))
    assert not is_simple(Macro("loop", 0, r"\loop x"))  # refers to itself
    text, used = expand_macros(r"$\Bbb Z$ and $\Hom$", {"Bbb": trap, "Hom": Macro("Hom", 0, r"\operatorname{Hom}")})
    assert "errmessage" not in text and r"\Bbb" in text and r"\operatorname{Hom}" in text
    assert used == {"Hom"}


CONVENTIONS = r"""\documentclass{amsart}
\newtheorem{theorem}{Theorem}[section]
\begin{document}
\section{Introduction}
We study widgets.

\paragraph{Notation and conventions.}\label{conv} We work over a fixed ground field $k$. An algebraic stack is quasi-separated.

\section{Results}
\begin{theorem}\label{t}
Every widget is a gadget.
\end{theorem}
\end{document}
"""

THROUGHOUT = r"""\documentclass{amsart}
\newtheorem{theorem}{Theorem}[section]
\begin{document}
\section{Introduction}
We study widgets.

Throughout this paper, all schemes are noetherian and separated.

\section{Results}
\begin{theorem}\label{t}
Every widget is a gadget.
\end{theorem}
\end{document}
"""


def test_the_setup_node_carries_the_papers_own_conventions(tmp_path: Path) -> None:
    """Four sightings over three study iterations: every answer about hypotheses named the empty -setup stub as its limit, while Manolache's digest printed "Notation and conventions" two lines above it."""
    for name, src, want in (
        ("Co01", CONVENTIONS, "We work over a fixed ground field $k$."),
        ("Th01", THROUGHOUT, "Throughout this paper, all schemes are noetherian and separated."),
    ):
        (tmp_path / name).mkdir()
        text = _extract(tmp_path / name, src, name)
        setup = text.split(f"\\label{{{name}-setup}}", 1)[1].split("\\end{", 1)[0]
        assert want in setup and "\\incomplete" not in setup and "\\label" not in setup, setup
    (tmp_path / "none").mkdir()
    text = _extract(tmp_path / "none", WRAPPED, "No01")
    assert "\\incomplete{Standing assumptions not extracted" in text, "a paper with no conventions paragraph says so"


SENTENCES = r"""\documentclass{amsart}
\newtheorem{theorem}{Theorem}[section]
\begin{document}
\section{Review}
In this section we review the theory. All schemes are assumed to be of finite type
defined over a field of arbitrary characteristic.

\section{Localization}
In this section we prove the main theorem. For the remainder of the paper, all tori are assumed
to be split, and the coefficients of all Chow groups are rational.
\begin{theorem}\label{t}
Every widget is a gadget.
\end{theorem}
\begin{proof}
Throughout this argument we may assume all widgets are assumed small.
\end{proof}
In this section, we work over an algebraically closed field.
\end{document}
"""


def test_standing_assumptions_stated_as_sentences_are_found(tmp_path: Path) -> None:
    """Edidin and Graham state that every Chow group in their paper has rational coefficients in one sentence of an ordinary paragraph -- the hypothesis the study's agent went to the Overview for."""
    text = _extract(tmp_path, SENTENCES, "Eg98")
    setup = text.split("\\label{Eg98-setup}", 1)[1].split("\\end{", 1)[0]
    assert "All schemes are assumed to be of finite type defined over a field of arbitrary characteristic." in setup
    assert "the coefficients of all Chow groups are rational." in setup
    assert "algebraically closed" not in setup, "a sentence scoped to a section is not a standing assumption"
    assert "widgets are assumed small" not in setup, "nor is one inside a proof"
    assert "check each one's scope" in setup, "gathered sentences say they were gathered"


def test_a_step_that_is_off_with_work_waiting_says_how_to_turn_it_on(tmp_path: Path) -> None:
    """Both switches are false in a new quilt's config, so a build that could fetch or look up says which line to change and which flag does it for one run (DR-193)."""
    q = demo(tmp_path)
    r = run("refs", "build", cwd=q)
    assert r.exit_code == 0, r.output
    assert "could be looked up: set resolve = true under [refs] in config.toml, or pass --resolve" in r.output
    assert "could be fetched: set fetch = true under [refs] in config.toml, or pass --fetch" in r.output
