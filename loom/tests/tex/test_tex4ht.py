"""TeX tier: a document's HTML made by TeX4ht (plan 0.29.2): it runs nothing a quilt carries, numbers every row of a display as amsmath does, stamps where each node begins and which label each reference prints, keeps the last good page when a run makes none, and nothing a document writes with `\\HCode` survives the normaliser."""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import pytest

from loom.render.normalise import normalise
from loom.tex.runner import compile_document
from loom.tex.tex4ht import compile_html

DOC = r"""\documentclass{article}
\usepackage{amsmath,amsthm}
\numberwithin{equation}{section}
\newtheorem{lemma}[equation]{Lemma}
\begin{document}
\section{One}
\begin{lemma}\label{l1}First.\end{lemma}
\begin{align}
a&=b\label{r1}\\
c&=d\nonumber\\
e&=f\label{r3}
\end{align}
\begin{lemma}\label{l2}Second.\end{lemma}
\input{part}
See \ref{l1}, \ref{l2}, \eqref{r1} and \eqref{r3}.%s
\end{document}
"""
PART = "Text of the part.\n\\begin{lemma}\\label{l3}Third.\\end{lemma}\n"


def _quilt(q: Path, extra: str = "") -> Path:
    q.mkdir(parents=True, exist_ok=True)
    (q / "main.tex").write_text(DOC % extra, encoding="utf-8")
    (q / "part.tex").write_text(PART, encoding="utf-8")
    return q


def _html(q: Path, **kw):  # type: ignore[no-untyped-def]
    pdf = compile_document(q, "", "main.tex", q / ".loom/build/main")
    assert pdf.pdf is not None, pdf.first_error
    return compile_html(
        q, "", "main.tex", q / ".loom/build/main/html", envs=["lemma", "proof"], seed=q / ".loom/build/main", **kw
    )


@pytest.mark.tex
def test_every_row_and_every_reference_numbers_as_the_pdf_does_and_each_node_is_stamped(tmp_path: Path) -> None:
    q = _quilt(tmp_path / "q")
    res = _html(q)
    assert res.html is not None and res.passes == 1, res.first_error
    n = normalise(res.html.read_text(encoding="utf-8"))
    heads = re.findall(r"Lemma (\d+\.\d+)", n.html)
    assert heads == ["1.1", "1.4", "1.5"], heads  # two numbered rows between the first two
    refs = dict(re.findall(r'<a class="ref" data-label="([^"]+)" data-made="">\(?([\d.]+)\)?</a>', n.html))
    assert refs == {"l1": "1.1", "l2": "1.4", "r1": "1.2", "r3": "1.3"}, refs
    nodes = re.findall(r'<div class="node" data-env="lemma" data-file="([^"]*)" data-line="(\d+)">', n.html)
    assert nodes == [("", "7"), ("", "13"), ("part.tex", "2")], nodes


@pytest.mark.tex
def test_nothing_a_quilt_carries_for_tex4ht_runs(tmp_path: Path) -> None:
    """A `.mk4` build file and a `.make4ht` configuration are Lua programs, and `tex4ht.env` names commands; the run removes all three from its copy."""
    marker = tmp_path / "ran"
    q = _quilt(tmp_path / "q")
    lua = f'os.execute("touch {marker}")\n'
    (q / "main.mk4").write_text(lua, encoding="utf-8")
    (q / ".make4ht").write_text(lua, encoding="utf-8")
    (q / "tex4ht.env").write_text(f"G.svg\nGtouch {marker}\n", encoding="utf-8")
    res = _html(q)
    assert res.html is not None, res.first_error
    assert not marker.exists()


@pytest.mark.tex
def test_html_a_document_writes_for_itself_is_neutralised(tmp_path: Path) -> None:
    # guarded as a document that writes HTML for itself is, since `\HCode` exists only under TeX4ht
    hostile = r"\ifdefined\HCode\HCode{<script>window.loomHostile=1</script><img src=x onerror=alert(2)><a href=javascript:alert(3)>go</a>}\fi"
    q = _quilt(tmp_path / "q", hostile)
    res = _html(q)
    assert res.html is not None, res.first_error
    raw = res.html.read_text(encoding="utf-8")
    assert "<script>window.loomHostile" in raw  # TeX4ht writes what it is told
    n = normalise(raw)
    assert "script" in n.dropped
    for gone in ("<script", "loomHostile", "onerror", "javascript:"):
        assert gone not in n.html


@pytest.mark.tex
def test_a_run_that_makes_no_page_leaves_the_last_good_one(tmp_path: Path) -> None:
    q = _quilt(tmp_path / "q")
    good = _html(q)
    assert good.html is not None
    page = good.html.read_text(encoding="utf-8")
    (q / "main.tex").write_text("\\documentclass{article}\\begin{document}\\input{nowhere}\n", encoding="utf-8")
    bad = compile_html(q, "", "main.tex", q / ".loom/build/main/html", envs=["lemma"], timeout=120)
    assert bad.html is None and not bad.ok
    assert (q / ".loom/build/main/html/main.html").read_text(encoding="utf-8") == page


#: A footnote sits at the foot of the PDF's page and at its mark on the page; the PDF's end-of-proof box has no text.
FOOTNOTE = "inner note"


def _plain(fragment: str) -> str:
    """A fragment's text as a reader reads it, each display set apart as one mark: MathJax typesets it, so its words are not compared."""
    t = re.sub(r'<div class="math display"[^>]*>.*?</div>', "⟦DISPLAY⟧", fragment, flags=re.S)
    t = re.sub(r"<(?:/p|/li|/dd|/dt|/div|/h\d|br|/tr|/td|/figcaption)[^>]*>", " ", t)
    return html.unescape(re.sub(r"<[^>]+>", "", t))


def _features(text: str) -> dict[str, str]:
    return {
        m.group(1): part[m.end() :]
        for part in re.split(r"(?=\bF\d\db?\b)", text)
        if (m := re.match(r"(F\d\db?)\b", part))
    }


def _squash(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for a, b in {
        "“": "''",
        "”": "''",
        "‘": "'",
        "’": "'",
        "``": "''",
        "–": "-",
        "—": "-",
        "--": "-",
        "\\(": "",
        "\\)": "",
        "$": "",
        "□": "",
    }.items():
        s = s.replace(a, b)
    return re.sub(r"\s+", "", re.sub(r"\.\s*\.\s*\.", "…", s))


def census_score(pdf_text: str, fragment: str) -> tuple[set[str], set[str]]:
    """The census's features whose words the fragment shows as the PDF prints them (`pdftotext -layout`), and the rest.

    A display is judged by what follows it; two neighbours holding the same characters between them are both right, since a table set beside a feature's tag comes out of `pdftotext` in the order of its lines.
    """
    lines = [ln for ln in pdf_text.split("\n") if not re.fullmatch(r"\s*\d+\s*", ln) and FOOTNOTE not in ln]
    pdf = "\n".join(lines).replace("TEX", "TeX").replace("LATEX", "LaTeX").replace("LATeX", "LaTeX")
    expect, got = _features(pdf), _features(_plain(fragment.replace(FOOTNOTE, "")))
    said: dict[str, tuple[str, str]] = {}
    for k in sorted(expect):
        e, g = _squash(expect[k]), _squash(got.get(k, "∅"))
        if "⟦DISPLAY⟧" in g:
            after = g.rsplit("⟦DISPLAY⟧", 1)[1]
            e, g = (e[len(e) - len(after) :] if after else ""), after
        said[k] = (e, g)
    right = {k for k, (e, g) in said.items() if e == g}
    keys = sorted(said)
    for a, b in zip(keys, keys[1:], strict=False):
        if not {a, b} <= right and sorted(said[a][0] + said[b][0]) == sorted(said[a][1] + said[b][1]):
            right |= {a, b}
    return right, set(said) - right


@pytest.mark.tex
def test_the_census_reads_on_the_page_as_the_pdf_prints_it(tmp_path: Path) -> None:
    """Forty-two features a translator of LaTeX gets wrong (macros, counters, conditionals, lists, references, floats, tables, footnotes), each read in the fragment against the compiled PDF's words: at most two may differ, and today those are a footnote shown at its mark with its number twice, and a custom item label TeX4ht drops."""
    if shutil.which("pdftotext") is None:
        pytest.skip("no pdftotext to read the PDF with")
    q = tmp_path / "q"
    q.mkdir()
    shutil.copy(Path(__file__).with_name("census.tex"), q / "census.tex")
    pdf = compile_document(q, "", "census.tex", q / ".loom/build/census")
    assert pdf.pdf is not None, pdf.first_error
    res = compile_html(
        q,
        "",
        "census.tex",
        q / ".loom/build/census/html",
        envs=["theorem", "defn", "proof"],
        seed=q / ".loom/build/census",
    )
    assert res.html is not None, res.first_error
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf.pdf), "-"], capture_output=True, text=True, check=True
    ).stdout
    right, wrong = census_score(text, normalise(res.html.read_text(encoding="utf-8")).html)
    assert len(right) + len(wrong) >= 42 and len(wrong) <= 2, sorted(wrong)


@pytest.mark.tex
def test_loom_compile_html_says_how_much_of_the_page_it_places(tmp_path: Path) -> None:
    """`loom compile --html` writes the page and the fragment rebuilt from it beside the PDF, and counts the nodes stamped against the scan's and the blocks placed in their files, the part's among them."""
    from tests.helpers import json_of

    q = _quilt(tmp_path / "q")
    (q / "config.toml").write_text('[quilt]\nname = "q"\nprefix = "qq"\nmain = "main.tex"\n', encoding="utf-8")
    data = json_of("compile", "main.tex", "--html", "--json", cwd=q)
    made = data["html"]
    assert made["made"] and made["outdir"] == ".loom/build/main/html/", made
    assert (q / ".loom/build/main/html/main.html").is_file() and (q / ".loom/build/main/html/fragment.html").is_file()
    assert made["nodes"] == made["nodes_in_document"] == 3, made
    # the part's paragraph, and the master's after the part ends; a block of one word is too short to count
    assert made["blocks"] == made["exact"] == 2 and not made["unplaced"], made
