"""Build a quilt on disk from a dict of files and scan it."""

from __future__ import annotations

from pathlib import Path

from loom.scan.quilt import load_quilt
from loom.scan.scan import ScanResult, scan

DEFAULT_CONFIG = '[quilt]\nmain = "drafts/main.tex"\ndrafts = "drafts"\nprefix = "ab"\nengine = "pdflatex"\n'

PREAMBLE = r"""\documentclass{amsart}
\usepackage{amsthm}
\usepackage{loom}
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}[theorem]{Lemma}
\newtheorem{proposition}[theorem]{Proposition}
\theoremstyle{definition}
\newtheorem{definition}[theorem]{Definition}
\newtheorem{example}[theorem]{Example}
\theoremstyle{remark}
\newtheorem{remark}[theorem]{Remark}
"""


def make_quilt(tmp_path: Path, files: dict[str, str], config: str = DEFAULT_CONFIG) -> ScanResult:
    root = tmp_path / "quilt"
    root.mkdir(exist_ok=True)
    (root / "config.toml").write_text(config, encoding="utf-8")
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return scan(load_quilt(root))


SINGLE_FILE = (
    PREAMBLE
    + r"""\begin{document}

\section{Setup}\label{ab-0010}

\begin{definition}[Widget]\label{ab-0001}
A \emph{widget} is a pair $(X, \sigma)$ with $\sigma^2 = \mathrm{id}$.
\end{definition}

\section{Results}\label{ab-0011}

\begin{lemma}\label{ab-0002}\label{lem:involution-fixed}
Every widget has a $\sigma$-fixed point.
\end{lemma}
\begin{proof}
Take the orbit decomposition; since $\sigma^2 = \mathrm{id}$, every orbit has one or two points, and ...
\end{proof}

\begin{theorem}[Main]\label{ab-0003}
The fixed locus of a widget is nonempty and closed.
\end{theorem}

Closedness is \cite[Theorem 4.1]{Man12} applied to the involution.

\begin{proof}[Proof of Theorem~\ref{ab-0003}]
\uses{ab-0001}
By Lemma~\ref{lem:involution-fixed} the locus is nonempty; ...
\end{proof}

\end{document}
"""
)
