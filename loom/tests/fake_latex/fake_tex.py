#!/usr/bin/env python3
"""Fake TeX toolchain for the unit tier: one script installed under the names latexmk, pdflatex, latex, lualatex, xelatex, dvisvgm, bibtex, biber, pdftotext, pdfinfo, kpsewhich.

It parses the input enough to find \\newtheorem declarations, sectioning, theorem-like environments, equations, and \\label commands through expanded inclusions; emits a plausible .aux with sequential numbering by section; writes a placeholder PDF carrying the document's plain text so the fake pdftotext returns it; emits a fixed SVG for dvisvgm. Every invocation is appended to $FAKE_TEX_LOG. FAKE_TEX_FAIL=1 makes the engines fail with a "! LaTeX Error" line and exit 12; FAKE_TEX_FAIL_MATCH=substring fails only inputs whose path contains it. Never install this on a real PATH.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ENGINES = {"latexmk", "pdflatex", "latex", "lualatex", "xelatex"}
SYSTEM_FILES = {
    "xy.tex",
    "amsmath.sty",
    "amsthm.sty",
    "amssymb.sty",
    "graphicx.sty",
    "hyperref.sty",
    "standalone.cls",
    "article.cls",
    "amsart.cls",
    "tikz.sty",
    "tikz-cd.sty",
    "loom.sty",
    "biblatex.sty",
    "cleveref.sty",
}
EQUATION_ENVS = {"equation", "align", "gather", "multline", "eqnarray", "alignat", "flalign"}
SECTIONING = ["part", "chapter", "section", "subsection", "subsubsection", "paragraph", "subparagraph"]
CHARS_PER_PAGE = 3000


def log_call(argv: list[str]) -> None:
    path = os.environ.get("FAKE_TEX_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(" ".join(argv) + "\n")


def strip_comments(text: str) -> str:
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def expand(path: Path, seen: set[Path] | None = None) -> str:
    seen = seen or set()
    if path in seen:
        return f"[cycle {path.name}]"
    seen = seen | {path}
    text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))

    def repl(m: re.Match[str]) -> str:
        name = m.group(2).strip()
        for cand in (Path(name), Path(name + ".tex")):
            if cand.is_file():
                inner = expand(cand, seen)
                return shift_sectioning(inner) if m.group(1) == "nest" else inner
        return f"[missing {name}]"

    return re.sub(r"\\(input|include|nest)\{([^}]*)\}", repl, text)


SHIFT = {
    "chapter": "section",
    "section": "subsection",
    "subsection": "subsubsection",
    "subsubsection": "paragraph",
    "paragraph": "subparagraph",
}


def shift_sectioning(text: str) -> str:
    """What loom.sty's \\nest does: every sectioning command one level down, composing across nested files."""
    return re.sub(
        r"\\(chapter|section|subsection|subsubsection|paragraph)(\*?)(?=[\[{])",
        lambda m: "\\" + SHIFT[m.group(1)] + m.group(2),
        text,
    )


def theorem_envs(text: str) -> tuple[set[str], set[str]]:
    numbered, unnumbered = set(), set()
    for m in re.finditer(r"\\newtheorem(\*?)\s*\{([^}]*)\}", text):
        (unnumbered if m.group(1) else numbered).add(m.group(2).strip())
    for m in re.finditer(r"\\declaretheorem(?:\[[^\]]*\])?\s*\{([^}]*)\}", text):
        numbered.add(m.group(1).strip())
    return numbered, unnumbered


def number_labels(text: str) -> tuple[list[tuple[str, str, int]], int]:
    """Return [(label, number, page)] in document order and the page count."""
    numbered, _ = theorem_envs(text)
    counters = {s: 0 for s in SECTIONING}
    thm = eq = 0
    current = ""
    labels: list[tuple[str, str, int]] = []
    token = re.compile(
        r"\\(" + "|".join(SECTIONING) + r")(\*?)\s*(?:\[[^\]]*\])?\{|\\begin\{([^}]*)\}|\\label\{([^}]*)\}"
    )
    body_start = text.find(r"\begin{document}")
    for m in token.finditer(text, max(body_start, 0)):
        if m.group(1):
            level = m.group(1)
            if m.group(2):
                current = ""
                continue
            counters[level] += 1
            for lower in SECTIONING[SECTIONING.index(level) + 1 :]:
                counters[lower] = 0
            if level == "section":
                thm = eq = 0
            parts = [str(counters[s]) for s in SECTIONING[: SECTIONING.index(level) + 1] if counters[s] or s == level]
            current = ".".join(parts)
        elif m.group(3):
            env = m.group(3).strip("*") if m.group(3) != m.group(3).rstrip("*") else m.group(3)
            if m.group(3) in numbered:
                thm += 1
                current = f"{counters['section']}.{thm}" if counters["section"] else str(thm)
            elif env in EQUATION_ENVS and not m.group(3).endswith("*"):
                eq += 1
                current = f"{counters['section']}.{eq}" if counters["section"] else str(eq)
        elif m.group(4):
            page = 1 + m.start() // CHARS_PER_PAGE
            labels.append((m.group(4).strip(), current, page))
    pages = max(1, 1 + len(text) // CHARS_PER_PAGE)
    return labels, pages


def plain_text(text: str) -> str:
    body = text.split(r"\begin{document}", 1)[-1].split(r"\end{document}", 1)[0]
    body = re.sub(r"\\(begin|end)\{[^}]*\}", " ", body)
    body = re.sub(r"\\(label|ref|eqref|cite|uses|incomplete)\{[^}]*\}", " ", body)
    for _ in range(3):
        body = re.sub(r"\\[A-Za-z@]+\*?\s*(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", body)
    body = re.sub(r"\\[A-Za-z@]+\*?", " ", body)
    body = body.replace("{", " ").replace("}", " ").replace("$", " ")
    return re.sub(r"\s+", " ", body).strip()


def out_dir(args: list[str]) -> Path:
    for i, a in enumerate(args):
        for flag in ("-outdir=", "-output-directory=", "--output-directory="):
            if a.startswith(flag):
                return Path(a[len(flag) :])
        if a in ("-outdir", "-output-directory") and i + 1 < len(args):
            return Path(args[i + 1])
    return Path(".")


def input_file(args: list[str]) -> Path | None:
    positional = [a for a in args if not a.startswith("-")]
    skip_after = {"-outdir", "-output-directory", "-jobname", "-e"}
    cleaned = []
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a in skip_after:
            skip = True
            continue
        if not a.startswith("-"):
            cleaned.append(a)
    positional = cleaned
    if not positional:
        return None
    p = Path(positional[-1])
    return p if p.suffix else p.with_suffix(".tex")


def run_engine(tool: str, args: list[str]) -> int:
    src = input_file(args)
    if src is None or not src.is_file():
        sys.stderr.write(f"fake {tool}: no input file\n")
        return 1
    outdir = out_dir(args)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = src.stem
    match = os.environ.get("FAKE_TEX_FAIL_MATCH")  # fail only when the input path contains this (e.g. "bundles/")
    if os.environ.get("FAKE_TEX_FAIL") or (match and match in str(src)):
        (outdir / f"{stem}.log").write_text(
            "! LaTeX Error: fake failure requested by FAKE_TEX_FAIL.\n", encoding="utf-8"
        )
        sys.stdout.write("! LaTeX Error: fake failure requested by FAKE_TEX_FAIL.\n")
        return 12
    text = expand(src)
    labels, pages = number_labels(text)
    aux = ["\\relax"] + [f"\\newlabel{{{lab}}}{{{{{num}}}{{{page}}}}}" for lab, num, page in labels]
    (outdir / f"{stem}.aux").write_text("\n".join(aux) + "\n", encoding="utf-8")
    body = plain_text(text)
    pdf = f"%PDF-1.4\n%FAKE-LOOM\n%%Pages: {pages}\n{body}\n"
    (outdir / f"{stem}.pdf").write_text(pdf, encoding="utf-8")
    if tool == "latex":
        (outdir / f"{stem}.dvi").write_text(pdf, encoding="utf-8")
    (outdir / f"{stem}.log").write_text(
        f"This is fake {tool}\nOutput written on {stem}.pdf ({pages} pages, {len(pdf)} bytes).\n", encoding="utf-8"
    )
    return 0


def run_dvisvgm(args: list[str]) -> int:
    out = None
    for i, a in enumerate(args):
        if a.startswith("--output="):
            out = Path(a[len("--output=") :])
        elif a in ("-o", "--output") and i + 1 < len(args):
            out = Path(args[i + 1])
    if out is None:
        inputs = [a for a in args if not a.startswith("-")]
        out = Path(inputs[-1]).with_suffix(".svg") if inputs else Path("out.svg")
    out.write_text(
        "<?xml version='1.0'?>\n<svg xmlns='http://www.w3.org/2000/svg' width='100pt' height='40pt' "
        "viewBox='0 0 100 40'><g id='page1'><text id='text1' x='2' y='20'>fake</text></g></svg>\n",
        encoding="utf-8",
    )
    return 0


def run_bib(args: list[str]) -> int:
    inputs = [a for a in args if not a.startswith("-")]
    if inputs:
        stem = Path(inputs[-1])
        stem = stem.with_suffix("") if stem.suffix in (".aux", ".bcf") else stem
        Path(f"{stem}.bbl").write_text("\\begin{thebibliography}{1}\n\\end{thebibliography}\n", encoding="utf-8")
    return 0


def read_fake_pdf(path: Path) -> tuple[str, int]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    pages = 1
    body: list[str] = []
    for line in lines:
        if line.startswith("%%Pages:"):
            pages = int(line.split(":", 1)[1].strip() or 1)
        elif line.startswith("%"):
            continue
        else:
            body.append(line)
    return "\n".join(body), pages


def run_pdftotext(args: list[str]) -> int:
    positional = [a for a in args if not a.startswith("-") or a == "-"]
    if not positional:
        return 1
    text, _ = read_fake_pdf(Path(positional[0]))
    target = positional[1] if len(positional) > 1 else str(Path(positional[0]).with_suffix(".txt"))
    if target == "-":
        sys.stdout.write(text + "\n")
    else:
        Path(target).write_text(text + "\n", encoding="utf-8")
    return 0


def run_pdfinfo(args: list[str]) -> int:
    positional = [a for a in args if not a.startswith("-")]
    if not positional:
        return 1
    _, pages = read_fake_pdf(Path(positional[0]))
    sys.stdout.write(f"Pages:          {pages}\n")
    return 0


def run_kpsewhich(args: list[str]) -> int:
    if "-var-value" in args:
        sys.stdout.write("\n")
        return 0
    found = False
    for name in (a for a in args if not a.startswith("-")):
        if Path(name).is_file():
            sys.stdout.write(f"{Path(name).resolve()}\n")
            found = True
        elif name in SYSTEM_FILES:
            sys.stdout.write(f"/fake/texmf/{name}\n")
            found = True
    return 0 if found else 1


def main() -> int:
    tool = Path(sys.argv[0]).name
    args = sys.argv[1:]
    log_call([tool, *args])
    if any(a in ("--version", "-v", "-version") for a in args):
        sys.stdout.write(f"{tool} (fake loom toolchain) 0.0\n")
        return 0
    if tool in ENGINES:
        return run_engine(tool, args)
    if tool in ("dvisvgm", "pdftocairo"):
        return run_dvisvgm(args)
    if tool in ("bibtex", "biber"):
        return run_bib(args)
    if tool == "pdftotext":
        return run_pdftotext(args)
    if tool == "pdfinfo":
        return run_pdfinfo(args)
    if tool == "kpsewhich":
        return run_kpsewhich(args)
    sys.stderr.write(f"fake toolchain: unknown tool {tool}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
