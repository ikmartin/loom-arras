"""Digests (book 8): postnote matching, provenance checks, extraction from a reference paper's source on the fake toolchain, porting with --as, and the fetch gate."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from loom.refs.pages import storage_root
from loom.scan.postnote import normalize, parts
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from loom.tex.bundle import build_bundle
from tests.helpers import edit, exits, ok, refused
from tests.unit._quilts import work_home

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


def demo(tmp_path: Path) -> Path:
    ok("init", str(tmp_path / "q"), "--demo", cwd=tmp_path)
    q = tmp_path / "q"
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write("\n@misc{Ref20, title={Widgets}, author={Ref, A.}, year={2020}, eprint={2001.00001v2}}\n")
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "ref.tex").write_text(REF)
    # extraction is gated on loom holding the document, so the source is filed before it is read (plan 0.13 §4)
    ok("refs", "add", "Ref20", str(tmp_path / "paper" / "ref.tex"), cwd=q)
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
    lint = ok("lint", cwd=q).output
    assert "unmatched-postnote" not in lint
    node.write_text(node.read_text().replace("% see", "See"))
    r = scan(load_quilt(q))
    post = [(e.src, e.to) for e in r.edges.edges if e.via == "postnote"]
    assert ("dm-0002", "Calloway14-prop-3.2") in post
    assert ("dm-0002", "Calloway14-sec-3") in post  # a postnote naming a section resolves to the section node
    lint = ok("lint", cwd=q).output
    assert "loom:unmatched-postnote" in lint and "Lemma 99" in lint
    digest = q / "digests" / "Calloway14.tex"
    digest.write_text(
        digest.read_text().replace(
            "\\label{Calloway14-prop-3.2}", "\\label{Calloway14-prop-3.2}\\label{Calloway14-lem-99}", 1
        )
    )
    assert "unmatched-postnote" not in ok("lint", cwd=q).output  # an alias id names the result under another numbering
    assert (
        lint.count("unmatched-postnote") == 1
    )  # \cite{Calloway14} without a postnote is neither an edge nor a diagnostic


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
    lint = ok("lint", cwd=q).output
    assert "loom:version-mismatch" in lint and "v2" in lint and "v3" in lint
    assert "loom:missing-package" in lint and "tikz-cd" in lint
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text().rstrip("\n") + "\nSee \\cite[Theorem 1]{Ref20}.\n")
    assert ok("status", "--undigested", cwd=q).output.split() == ["Ref20"]


def test_extract_from_source_drops_proofs_keeps_uses_and_refuses_existing(tmp_path: Path) -> None:
    q = demo(tmp_path)
    r = ok("digest", "extract", "Ref20", cwd=q)
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
    # the digest requires xy and the demo's master does not load it, which the extraction's own lint says
    assert "Lint on the digest:\n" in r.output and "loom:missing-package" in r.output
    assert "digest Ref20 requires xy, which the preamble of drafting/main.tex does not load" in r.output
    refused("digest", "extract", "Ref20", code=2, match="digests/Ref20.tex exists", cwd=q)
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(
        node.read_text().replace(
            "\\end{lemma}", "By \\cite[Theorem 3.1]{Ref20} and \\cite[Thm.~3.2, p.~1]{Ref20}.\n\\end{lemma}", 1
        )
    )
    deps = ok("deps", "dm-0002", cwd=q).output
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
    r = ok("digest", "extract", "Ref20", cwd=q, env={"FAKE_TEX_FAIL": "1"})
    text = (q / "digests" / "Ref20.tex").read_text()
    assert "% !LOOM numbering: emulated" in text and "Numbering: emulated" in r.output
    for local in ("def-2.1", "lem-2.2", "thm-3.1", "thm-3.2", "sec-2", "sec-3"):
        assert f"\\label{{Ref20-{local}}}" in text, local


def test_import_digest_as_rewrites_prefix(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ok("digest", "extract", "Ref20", cwd=q)
    src = q / "digests" / "Ref20.tex"
    ok("init", str(tmp_path / "lib"), "--demo", cwd=tmp_path)
    lib = tmp_path / "lib"
    r = ok("digest", "import", str(src), "--as", "Other20", cwd=lib)
    text = (lib / "digests" / "Other20.tex").read_text()
    assert text.startswith("% !LOOM digest: Other20\n")
    assert "Ref20" not in text
    assert "\\label{Other20-thm-3.1}" in text and "\\uses{Other20-lem-2.2, Other20-def-2.1}" in text
    assert "\\cite[Theorem 3.1 (Main), p.~1]{Other20}" in text and "\\eqref{Other20-eq:key}" in text
    assert "digest-without-bib" in r.output  # Other20 is not in lib's bibliography
    refused(
        "digest", "import", str(src), "--as", "Other20", code=2, match="digest import never overwrites", cwd=lib
    )  # never overwrites


def test_fetch_refused_without_config(tmp_path: Path) -> None:
    q = demo(tmp_path)
    before = sorted(p.relative_to(q) for p in storage_root(q).rglob("*"))
    refused("refs", "fetch", "Ref20", code=1, match="fetch = true", cwd=q)
    assert sorted(p.relative_to(q) for p in storage_root(q).rglob("*")) == before, "a refused fetch writes nothing"


def test_build_runs_with_the_network_off_and_says_how_to_turn_each_step_on(tmp_path: Path) -> None:
    """`loom refs build` is usable in a quilt that has opted into nothing: it says so, still does the local steps, and names the two things a machine cannot do. Both switches are false in a new quilt's config, so a build that could fetch or look up says which line to change and which flag does it for one run (DR-193)."""
    q = demo(tmp_path)
    r = ok("refs", "build", cwd=q)
    assert "(lookup off)" in r.output and "(fetching off)" in r.output
    assert "needs you" in r.output and "needs an agent" in r.output
    assert "could be looked up: set resolve = true under [refs] in config.toml, or pass --resolve" in r.output
    assert "could be fetched: set fetch = true under [refs] in config.toml, or pass --fetch" in r.output


def test_a_digest_is_called_thin_by_the_results_it_has_after_extraction(tmp_path: Path) -> None:
    """A digest with far fewer results than its paper has pages is reported for an agent rather than counted as done. Results are counted after this run's extraction has written them: counted before, every fresh digest had none and all sixteen of a real run were called "too thin to trust"."""
    q = demo(tmp_path)
    sections = work_home(q, "Ref20") / "sections.json"
    sections.write_text(json.dumps({"sha256": "0" * 64, "pages": 12, "chars": 1, "sections": []}))
    fresh = ok("refs", "build", "--only", "extract", cwd=q)
    assert "entered the digest  1: Ref20" in fresh.output and "too thin to trust" not in fresh.output, fresh.output
    assert "needs an agent 0" in fresh.output, fresh.output
    # the same five results against a paper of forty pages are too few to trust
    sections.write_text(json.dumps({"sha256": "0" * 64, "pages": 40, "chars": 1, "sections": []}))
    thin = ok("refs", "build", "--only", "extract", cwd=q)
    assert "1 too thin to trust: Ref20 (5 results, 40 pages)" in thin.output, thin.output
    assert "needs an agent 1" in thin.output, thin.output


def test_build_refuses_an_unknown_step(tmp_path: Path) -> None:
    refused("refs", "build", "--only", "polish", code=2, match="unknown step", cwd=demo(tmp_path))


@pytest.mark.network
def test_fetch_writes_gitignored_dirs(tmp_path: Path) -> None:
    """A fetch files the source and the PDF in the store under the work's identifier, both of which the quilt's `.gitignore` keeps out of the repository."""
    if not os.environ.get("LOOM_NETWORK"):
        pytest.skip("set LOOM_NETWORK=1 to fetch from arXiv")
    q = demo(tmp_path)
    edit(q / "config.toml", "fetch = false", "fetch = true")
    ok("refs", "fetch", "Man12", cwd=q)  # the demo's own entry: eprint 0805.2065v2, whose title the arrival check reads
    home = work_home(q, "Man12")
    assert home == storage_root(q) / "arxiv" / "0805.2065v2"
    assert any((home / "src").iterdir()) and (home / "paper.pdf").is_file()
    ignored = (q / ".gitignore").read_text().splitlines()
    assert "digests/storage/**/paper.pdf" in ignored and "digests/storage/**/src/" in ignored


def test_requires_missing_package_named_first_on_bundle_failure(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ok("digest", "extract", "Ref20", cwd=q)
    node = q / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text().replace("\\end{lemma}", "By \\cite[Theorem 3.1]{Ref20}.\n\\end{lemma}", 1))
    r = exits(1, "compile", "dm-0002", cwd=q, env={"FAKE_TEX_FAIL": "1"})
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
    r = ok("lint", "--json", cwd=q)
    assert "loom:unverified-locators" not in r.output  # a preprint alone says nothing is wrong

    d.write_text(
        "% !LOOM digest: Split\n% !LOOM prefix: Split\n% !LOOM extracted-from: arXiv:2001.00002v1\n"
        "% !LOOM published-as: doi:10.1090/S1\n% !LOOM method: extract\n" + body,
        encoding="utf-8",
    )
    r = ok("lint", "--json", cwd=q)
    assert "loom:unverified-locators" in r.output and "a reader will open" in r.output

    # and a digest that does not say where its statements came from cannot be checked at all
    d.write_text(head + body, encoding="utf-8")
    r = ok("lint", "--json", cwd=q)
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
    ok("refs", "add", key, str(paper), cwd=q)
    ok("digest", "extract", key, "--no-compile", cwd=q)
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
    # the counter is `subsection`, so LaTeX prints 1.1 and 1.2 and emulation must say the same (DR-180)
    theorem = text.split("\\label{Ro22-thm-1.1}", 1)[1].split("\\end{theorem}", 1)[0]
    lemma = text.split("\\label{Ro22-lem-1.2}", 1)[1].split("\\end{lemma}", 1)[0]
    assert "The fixed stack is algebraic." in theorem and "A lemma." in lemma, text


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


NUMBERING = r"""\documentclass{article}
\usepackage{amsthm}
\newtheorem{thm}{Theorem}[section]
\newtheorem{lem}[thm]{Lemma}
\newtheorem{othm}{Theorem}[section]
\newtheorem*{mainthm}{Main Theorem}
\begin{document}
\section{Conventions}
CONVENTIONS

\section{Results}
\begin{mainthm}
Unnumbered first.
\end{mainthm}
\begin{thm}\label{a}
Numbered one.
\end{thm}
\begin{othm}
A second Theorem 2.1 on a counter of its own.
\end{othm}
\appendix
\section{Extra}
\begin{lem}\label{b}
An appendix lemma.
\end{lem}
\begin{mainthm}
Unnumbered second.
\end{mainthm}
\end{document}
"""


def _cited(q: Path, key: str) -> None:
    with (q / "digests" / "bibliography.bib").open("a") as fh:
        fh.write(f"\n@misc{{{key}, title={{X}}, author={{Y, Z.}}, year={{2000}}}}\n")


def test_emulated_numbering_follows_the_starred_appendix_duplicate_and_cap_rules(tmp_path: Path) -> None:
    """Book 8.5 on `--no-compile`: `\\newtheorem*` is `-star-<n>` titled `(unnumbered)`, `\\appendix` letters the section, a second result under a used number is skipped and reported, `--to` writes elsewhere, and the setup node is capped at 1,500 characters."""
    q = demo(tmp_path)
    paragraph = "Throughout, every widget is a gadget of finite type over a field, and we say so at length. " * 8
    paper = tmp_path / "nu.tex"
    paper.write_text(NUMBERING.replace("CONVENTIONS", "\n\n".join([paragraph] * 3)))
    _cited(q, "Nu01")
    ok("refs", "add", "Nu01", paper, cwd=q)
    r = ok("digest", "extract", "Nu01", "--no-compile", "--to", "elsewhere.tex", cwd=q)
    assert not (q / "digests" / "Nu01.tex").exists()
    text = (q / "elsewhere.tex").read_text()
    labels = re.findall(r"\\label\{(Nu01-[^}]*)\}", text)
    aliases = ("Nu01-a", "Nu01-b")  # the paper's own labels ride along, prefixed
    assert [x for x in labels if "-sec-" not in x and x not in ("Nu01-setup", *aliases)] == [
        "Nu01-mainthm-star-1",
        "Nu01-thm-2.1",
        "Nu01-lem-A.1",
        "Nu01-mainthm-star-2",
    ], labels
    assert "\\cite[Main Theorem (unnumbered)]{Nu01}" in text
    assert "A second Theorem 2.1" not in text
    assert re.search(r"Skipped: Theorem 2\.1 at \S+:\d+: duplicate number 2\.1", r.output), r.output
    assert "% !LOOM numbering: emulated" in text.splitlines()[:8]
    setup = text.split("\\label{Nu01-setup}", 1)[1].split("\\end{theorem}", 1)[0]
    more = "\n\\emph{The paper's conventions continue beyond this; see the paper.}"
    assert more in setup and len(setup.replace(more, "").strip()) <= 1500


def test_a_compiled_paper_with_an_unlabelled_result_says_numbering_mixed(tmp_path: Path) -> None:
    """DR-180, contract §2.9: a compile that succeeded does not make every number the .aux's; an unlabelled result counted by emulation marks the header `mixed`, and a fully labelled paper claims nothing."""
    q = demo(tmp_path)
    r = ok("digest", "extract", "Ref20", cwd=q)  # REF's last theorem is unlabelled
    text = (q / "digests" / "Ref20.tex").read_text()
    assert "% !LOOM numbering: mixed" in text and "numbering: emulated" not in text
    assert "Numbering: from the paper's .aux, except 1 unlabelled result(s) counted by emulation" in r.output
    labelled = tmp_path / "paper" / "ref.tex"
    edit(labelled, "\\begin{thm}\nUnlabelled theorem.", "\\begin{thm}\\label{last}\nLabelled now.")
    ok("refs", "add", "Ref20", labelled, "--force", cwd=q)
    r = ok("digest", "extract", "Ref20", "--to", "again.tex", cwd=q)
    assert "% !LOOM numbering" not in (q / "again.tex").read_text()
    assert "Numbering: from the paper's .aux\n" in r.output


def test_a_paper_with_no_sections_gets_an_incomplete_overview(tmp_path: Path) -> None:
    text = _extract(
        tmp_path,
        "\\documentclass{article}\n\\newtheorem{thm}{Theorem}\n\\begin{document}\n\\begin{thm}\nOnly.\n\\end{thm}\n\\end{document}\n",
        "Ns01",
    )
    assert "\\section*{Overview}\n\\incomplete{Overview not extracted; the paper has no introduction.}" in text
    assert "\\label{Ns01-thm-1}" in text


def test_a_result_on_a_sectioning_counter_steps_it_and_an_aux_number_resynchronises_it() -> None:
    """`\\newtheorem{x}[subsection]{…}` numbers results as subsections; an .aux number for one moves the section counters, so the next heading and result follow it."""
    from loom.digest.counters import Numbering
    from loom.scan.model import Taxon

    t = Taxon("counter", "Theorem", "plain", True, "p.tex", 0, counter="subsection")
    n = Numbering({"counter": t})
    n.heading("section")
    assert [n.theorem(t), n.theorem(t)] == ["1.1", "1.2"]
    n.heading("subsection")
    assert n.theorem(t) == "1.4"  # a subsection heading and a result share the one counter
    n.resync(t, "3.7")
    assert n.theorem(t) == "3.8"
    n.heading("section")
    assert n.theorem(t) == "4.1"
