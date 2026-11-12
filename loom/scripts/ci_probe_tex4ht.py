"""Print what TeX4ht writes for the TeX tier's texts, raw, with the TeX it ran on: a probe of a TeX Live loom has not run, to compare with the one it has. Temporary, for the CI branch that brings the TeX tier to TeX Live 2026."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from loom.tex.tex4ht import make_html

PREAMBLE = r"""\documentclass{amsart}
\usepackage{amsmath,amsthm,tikz-cd}
\newtheorem{lemma}{Lemma}
\newcommand{\R}{\mathbb{R}}
\newcommand{\widget}{gadget}"""

GOOD = [
    "\\begin{lemma}[Named]\\label{q1}\nEvery \\widget\\ on $\\R^n$ is \\emph{fine}.\n\\end{lemma}",
    "A paragraph with \\textbf{bold} words.\n\nAnd a second paragraph.",
    "\\begin{proof}\nBy \\ref{q1}.\n\\end{proof}",
    "A diagram:\n\\[\\begin{tikzcd} A \\arrow[r] & B \\end{tikzcd}\\]",
]

DISPLAYS = r"""Inline $a+b$ and \(c\). A display \[x^2\] and
\begin{equation}\label{e1} y = 1 \end{equation}
\begin{equation*} z \end{equation*}
\begin{align} a &= b \\ c &= d \label{e2} \end{align}
\begin{gather} p \\ q \end{gather}
\begin{multline} m \\ n \end{multline}
A square commutes: \begin{equation}\label{eq:sq} \begin{tikzcd} A \arrow[r] \arrow[d] & B \arrow[d] \\ C \arrow[r] & D \end{tikzcd} \end{equation}
\begin{lemma}\label{l1} A lemma. \end{lemma}
\begin{proof} A proof. \end{proof}"""


def run(label: str, text: str, math: str = "mathjax") -> None:
    with tempfile.TemporaryDirectory() as tmp:
        page, log = make_html(Path(tmp), "", "probe", text, envs=["lemma", "proof"], math=math)
    print(f"\n===== {label} ({math}) =====")
    print("----- page -----")
    print(page if page is not None else "NO PAGE")
    print("----- log, errors and the last lines -----")
    lines = log.split("\n")
    for n, ln in enumerate(lines):
        if ln.startswith("!"):
            print("\n".join(lines[n : n + 4]))
    print("\n".join(lines[-12:]))


def main() -> None:
    for cmd in (
        ["make4ht", "--version"],
        ["pdflatex", "--version"],
        ["kpsewhich", "mathjax-latex-4ht.sty"],
        ["kpsewhich", "tex4ht.sty"],
    ):
        if shutil.which(cmd[0]):
            print(
                " ".join(cmd), "->", subprocess.run(cmd, capture_output=True, text=True).stdout.strip().split("\n")[0]
            )
    if shutil.which("tlmgr"):
        print(
            subprocess.run(
                ["tlmgr", "info", "--only-installed", "tex4ht", "make4ht", "luaxml"], capture_output=True, text=True
            ).stdout
        )
    print(sys.version)
    snippet = PREAMBLE.split("\n") + ["\\begin{document}"]
    for i, t in enumerate(GOOD):
        snippet += [f"\\loomsnippet{{{i}}}", "\\begingroup", *t.split("\n"), "\\par\\endgroup"]
    snippet += ["\\loomsnippet{end}", "\\end{document}", ""]
    run("snippet run of the TeX tier's good texts", "\n".join(snippet))
    doc = PREAMBLE + "\n\\begin{document}\n" + DISPLAYS + "\n\\end{document}\n"
    run("displays, a diagram, a lemma and a proof", doc)
    run("the same, every display a picture", doc, math="svg")


def quilt() -> None:
    """The synthetic quilt as the fixture test builds it, with every raw page a build's snippet runs make, and the raw page of `main.tex` round its equation references."""
    import os
    import re

    import loom.render.snippets as snippets
    from loom.cli import main as cli

    repo = Path(__file__).resolve().parents[1]
    tmp = Path(tempfile.mkdtemp())
    q = tmp / "synthetic"
    shutil.copytree(repo / "tests" / "quilts" / "synthetic", q)
    os.environ.update(
        {
            "LOOM_FIXED_TIME": "2026-09-16T00:00:00Z",
            "HOME": str(tmp / "home"),
            "XDG_CONFIG_HOME": str(tmp / "home/.config"),
            "LOOM_PROGRESS": "off",
        }
    )
    for doc in ("drafting/main.tex", "drafting/talk.tex", ".loom/copies/aidoc.tex"):
        subprocess.run(
            [sys.executable, "-m", "loom", "compile", doc, "--html"], cwd=q, check=False, capture_output=True
        )
    page = q / ".loom/build/drafting/main/html/main.html"
    print("\n===== main.tex's page round each equation reference =====")
    text = page.read_text(errors="replace") if page.is_file() else "NO PAGE"
    at = text.find("References")
    print("\n===== main.tex's page round its references =====")
    print(text[max(0, at - 200) : at + 1600])
    for m in re.finditer(r"loom-ref|eq:prose|eq:fix|eq:step", text):
        print("...", text[max(0, m.start() - 200) : m.start() + 300].replace("\n", " "), "...")
    original = snippets.make_html

    def logged(*a, **k):  # type: ignore[no-untyped-def]
        made, log = original(*a, **k)
        print("\n===== a snippet run's raw page =====")
        print(made if made is not None else "NO PAGE\n" + log[-2000:])
        return made, log

    snippets.make_html = logged  # type: ignore[assignment]
    os.chdir(q)
    try:
        cli(["build"], standalone_mode=False)
    except SystemExit:
        pass


if __name__ == "__main__":
    main()
    quilt()
