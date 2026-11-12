"""Run TeX4ht on a document, into HTML that loom normalises (plan 0.29.2): TeX decides what the document says.

The run is `make4ht`'s draft mode with loom's own configuration (`configuration`), on a copy of the document's directory outside the quilt from which every TeX4ht file a quilt could carry is removed, with a home of its own: a `.mk4` build file and a `.make4ht` configuration are Lua programs, and `tex4ht.env` names the commands `t4ht` runs, so each would be a quilt's command run unasked. It is seeded with the last `pdflatex` compile's aux and bibliography, so every reference prints the number the PDF prints and one pass is enough; a document with no compile behind it gets a second pass when the first changed its aux. A run that makes no HTML leaves the last good one in place.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from loom.clock import tex_date
from loom.scan.preamble import PreambleClosure
from loom.tex.runner import stage_document, stop_run

#: What a quilt could carry that TeX4ht or make4ht would run or obey: build files, make4ht's own configuration, and the commands `t4ht` reads.
CARRIED = re.compile(r"(?:\.mk4|\.make4ht|^tex4ht\.env|^\.tex4ht)$")
#: Engine flags for make4ht; `latex` (DVI) stands for pdflatex, as TeX4ht has no PDF mode.
ENGINE = {"pdflatex": [], "latex": [], "lualatex": ["-l"], "xelatex": ["-x"]}
#: Figures TeX4ht's DVI route reads bounding boxes of from `.xbb` files, which `extractbb` writes beside them.
FIGURES = (".pdf", ".png", ".jpg", ".jpeg")
#: Beside a page, the displays it holds as placeholders, each `Repaired` as JSON, in the order of their numbers.
REPAIRED = "repaired.json"
#: Beside a page, the hash of every source file the run read, by quilt-relative path.
SOURCES = "sources.json"
#: Beside a page, the text of every `.tex` file the run read, by quilt-relative path: what an edit since is measured against.
TEXTS = "texts.json"
#: The files a run's sources are, whose change makes its page stale; build products and pictures are not among them.
SOURCE_SUFFIXES = frozenset((".tex", ".sty", ".cls", ".clo", ".def", ".cfg", ".bib", ".bst", ".bbx", ".cbx", ".ltx"))


def source_hashes(root: Path) -> dict[str, str]:
    """The sha256 of every source file under `root`, by its path relative to `root`."""
    return {
        f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in sorted(root.rglob("*"))
        if f.is_file() and f.suffix.lower() in SOURCE_SUFFIXES
    }


#: What a run's output directory keeps: the page, its stylesheet and the pictures TeX4ht made.
KEPT = (".html", ".css", ".svg", ".png", ".jpg", ".jpeg")

#: Count every numbered row of a multi-row display, as amsmath does: TeX4ht's MathJax mode passes the display through verbatim and steps `equation` once, labelling only the first row, so every later number sharing the counter drifts and later labels print `??`.
ROWS = r"""\ExplSyntaxOn
\int_new:N \l__loom_depth_int
\bool_new:N \l__loom_numbered_bool
\bool_new:N \l__loom_blank_bool
\tl_new:N \l__loom_label_tl
\tl_new:N \l__loom_prev_tl
\cs_new_protected:Npn \__loom_row:
  {
    \bool_if:NT \l__loom_numbered_bool
      {
        \refstepcounter { equation }
        \tl_if_empty:NF \l__loom_label_tl { \exp_args:NV \label \l__loom_label_tl }
      }
    \bool_set_true:N \l__loom_numbered_bool
    \bool_set_true:N \l__loom_blank_bool
    \tl_clear:N \l__loom_label_tl
  }
\cs_new_protected:Npn \loom_rows:nN #1 #2
  {
    \int_zero:N \l__loom_depth_int
    \bool_set_true:N \l__loom_numbered_bool
    \bool_set_true:N \l__loom_blank_bool
    \tl_clear:N \l__loom_label_tl
    \tl_clear:N \l__loom_prev_tl
    \tl_map_inline:nn {#1}
      {
        \tl_if_eq:NnTF \l__loom_prev_tl { \begin } { \int_incr:N \l__loom_depth_int }
          {
            \tl_if_eq:NnTF \l__loom_prev_tl { \end } { \int_decr:N \l__loom_depth_int }
              {
                \int_compare:nNnT \l__loom_depth_int = 0
                  { \tl_if_eq:NnT \l__loom_prev_tl { \label } { \tl_set:Nn \l__loom_label_tl {##1} } }
              }
          }
        \tl_set:Nn \l__loom_prev_tl {##1}
        \int_compare:nNnTF \l__loom_depth_int = 0
          {
            \tl_if_eq:nnTF {##1} { \\ } { \__loom_row: }
              {
                \bool_set_false:N \l__loom_blank_bool
                \tl_if_eq:nnT {##1} { \notag } { \bool_set_false:N \l__loom_numbered_bool }
                \tl_if_eq:nnT {##1} { \nonumber } { \bool_set_false:N \l__loom_numbered_bool }
                \tl_if_eq:nnT {##1} { \tag } { \bool_set_false:N \l__loom_numbered_bool }
              }
          }
          { \bool_set_false:N \l__loom_blank_bool }
      }
    \bool_if:NTF \l__loom_blank_bool { \bool_if:NT #2 { \__loom_row: } } { \__loom_row: }
  }
\cs_new_protected:Npn \loom_rows:nn #1 #2
  {
    \cs_if_exist:cT {#1}
      {
        \RenewDocumentEnvironment{#1}{+!b}
          {
            \NoFonts\expandafter\VerbMathToks\expandafter{\detokenize{##1}}{#1}\EndNoFonts
            \loom_rows:nN {##1} #2
          }{}
      }
  }
\clist_map_inline:nn { align, gather, alignat, flalign, xalignat, xxalignat } { \loom_rows:nn {#1} \c_false_bool }
\loom_rows:nn { eqnarray } \c_true_bool
\ExplSyntaxOff
"""

#: Where each node begins and in which file, where the reader is when an included file starts and ends, and which label each reference prints, wrapped round the kernel's and hyperref's `\@setref` once every package has defined its own.
STAMPS = r"""\def\loomfile{\ifx\CurrentFilePath\empty\else\CurrentFilePath/\fi\CurrentFile}
\def\loomnode#1{\ConfigureEnv{#1}{\ifvmode\IgnorePar\fi\EndP\HCode{<div class="loom-node" data-env="#1" data-file="\loomfile" data-line="\the\inputlineno">}}{\ifvmode\IgnorePar\fi\EndP\HCode{</div>}}{}{}}
\AddToHook{file/before}{\HCode{<!--loom-file \loomfile-->}}
\AddToHook{file/after}{\HCode{<!--loom-file-end-->}}
\def\loomdisplay#1{\HCode{<div class="mathjax-env" data-loom-display="#1"></div>}}
\makeatletter
\AddToHook{begindocument/end}{%
\let\loom@setref\@setref
\def\@setref#1#2#3{\HCode{<span class="loom-ref" data-label="\detokenize{#3}">}\loom@setref{#1}{#2}{#3}\HCode{</span>}}}
\makeatother
"""

_ENV = re.compile(r"^[A-Za-z@*]+$")

#: Displays TeX4ht's MathJax mode reads whole as one argument, which no TeX macro can do when their braces do not balance, though pdflatex, which never reads them so, may set them.
DISPLAYS = (
    "equation equation* align align* gather gather* multline multline* flalign flalign* alignat alignat* "
    "eqnarray eqnarray* xalignat xxalignat displaymath"
).split()
_NUMBERED = frozenset("equation align gather multline flalign alignat eqnarray xalignat xxalignat".split())
_DISPLAY = re.compile(
    r"(?<!\\)\\begin\s*\{(" + "|".join(re.escape(d) for d in DISPLAYS) + r")\}|(?<!\\)\\\[|(?<!\\)\$\$"
)
_ROW = re.compile(r"\\begin\s*\{|\\end\s*\{|\\\\")


@dataclass
class Repaired:
    """A display read as its author wrote it, because its braces do not balance: the file, quilt-relative, the line it begins on, and its TeX."""

    file: str
    line: int
    tex: str


def _blank_comments(text: str) -> str:
    """`text` with every comment blanked to the end of its line, offsets kept."""
    out = list(text)
    i = 0
    while i < len(out):
        if out[i] == "\\":
            i += 2
            continue
        if out[i] == "%":
            while i < len(out) and out[i] != "\n":
                out[i] = " "
                i += 1
        i += 1
    return "".join(out)


def _balanced(body: str) -> bool:
    depth = 0
    i = 0
    while i < len(body):
        c = body[i]
        if c == "\\":
            i += 2
            continue
        depth += (c == "{") - (c == "}")
        if depth < 0:
            return False
        i += 1
    return depth == 0


def _steps(env: str, body: str) -> str:
    """What a numbered display would have done to `equation` and its labels, row by row, for one loom reads as written."""
    if env not in _NUMBERED:
        return ""
    rows: list[str] = []
    if env in ("equation", "multline"):
        rows = [body]
    else:
        depth, start = 0, 0
        for m in _ROW.finditer(body):
            if m.group(0).startswith("\\begin"):
                depth += 1
            elif m.group(0).startswith("\\end"):
                depth -= 1
            elif depth == 0:
                rows.append(body[start : m.start()])
                start = m.end()
        rows.append(body[start:])
        if not rows[-1].strip() and env != "eqnarray" and len(rows) > 1:
            rows.pop()
    out = []
    for row in rows:
        if re.search(r"\\(?:notag|nonumber|tag)(?![A-Za-z])", row):
            continue
        label = re.search(r"\\label\s*\{([^{}]*)\}", row)
        out.append("\\refstepcounter{equation}" + (f"\\label{{{label.group(1)}}}" if label else ""))
    return "".join(out)


def repair_displays(text: str, first: int = 0) -> tuple[str, list[tuple[int, str]]]:
    """`text` with each display whose braces do not balance replaced by `\\loomdisplay{N}`, numbered from `first`, and stepping `equation` as it would; with each one's line and TeX.

    The replacement keeps the display's line breaks, so every later line keeps its number.
    """
    clean = _blank_comments(text)
    out: list[str] = []
    found: list[tuple[int, str]] = []
    at = pos = 0
    while (m := _DISPLAY.search(clean, pos)) is not None:
        env = m.group(1)
        closing = f"\\end{{{env}}}" if env else ("\\]" if m.group(0) == "\\[" else "$$")
        close = clean.find(closing, m.end())
        if close < 0:
            break
        end = close + len(closing)
        if not _balanced(clean[m.end() : close]):
            span = text[m.start() : end]
            found.append((clean.count("\n", 0, m.start()) + 1, span))
            out.append(text[at : m.start()])
            steps = _steps(env, clean[m.end() : close]) if env else ""
            out.append(f"\\loomdisplay{{{first + len(found) - 1}}}{steps}" + "\n" * span.count("\n"))
            at = end
        pos = end
    out.append(text[at:])
    return "".join(out), found


#: xr's package, and the external document it reads labels from, with xr's prefix in group 1 and its path in group 2.
_XR = re.compile(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{\s*xr(?:-hyper)?\s*\}")
_EXTERNAL = re.compile(r"\\externaldocument\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}")
_NEWLABEL = re.compile(r"^\\newlabel\{([^}]*)\}(.*)$", re.M)


def external_labels(text: str, here: Path) -> tuple[str, list[str]]:
    """`text` with xr's package and each `\\externaldocument` blanked, and the labels each external document's aux defines, prefixed as xr prefixes them, as aux lines to read in their place.

    TeX4ht cannot read an external aux written by pdflatex (`xr`'s and `xr-hyper`'s links break on it), while the run's own aux, read as the document's, takes the same lines without complaint. A relative path is read from `here`, the document's directory. Blanking keeps every line and offset where it was.
    """
    lines: list[str] = []
    for m in _EXTERNAL.finditer(_blank_comments(text)):
        name = m.group(2).strip()
        aux = Path(name if name.endswith(".aux") else name + ".aux")
        aux = aux if aux.is_absolute() else here / aux
        if not aux.is_file():
            continue
        prefix = (m.group(1) or "").strip()
        lines += [
            f"\\newlabel{{{prefix}{n.group(1)}}}{n.group(2)}"
            for n in _NEWLABEL.finditer(aux.read_text(encoding="utf-8", errors="replace"))
        ]
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))  # noqa: E731
    return _EXTERNAL.sub(blank, _XR.sub(blank, text)), lines


def _read_externals(here: Path, files: list[Path], aux: Path) -> None:
    """Blank xr in each of `files` and add the labels it would have read to `aux`, the run's own (`external_labels`); `here` is the document's directory in the quilt, which a relative path is read from, since the stage carries no aux."""
    lines: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        if "externaldocument" not in text and "{xr" not in text:
            continue
        fixed, found = external_labels(text, here)
        if fixed != text:
            f.write_text(fixed, encoding="utf-8")
        lines += found
    if lines:
        before = aux.read_text(encoding="utf-8", errors="replace") if aux.is_file() else "\\relax\n"
        aux.write_text(before.rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8")


#: Where one text of a run of texts begins, between blocks; TeX4ht mangles a hyphen in a comment, so the name has none.
SNIPPET = "\\def\\loomsnippet#1{\\par\\ifvmode\\IgnorePar\\fi\\EndP\\HCode{<!--loomsnippet #1-->}}\n"


def configuration(envs: Sequence[str], *, snippets: bool = False, math: str = "mathjax") -> str:
    """The `.cfg` for a document whose nodes are the environments `envs`: MathJax mode, the row counting, the stamps, and with `snippets` the mark each text of a run begins with.

    With `math` 'svg' TeX sets every formula itself and TeX4ht draws each display as a picture: the mode a diagram is drawn in, with the marks and nothing else.
    """
    marks = SNIPPET if snippets else ""
    if math == "svg":
        return "\\Preamble{xhtml,svg}\n\\begin{document}\n" + marks + "\n\\EndPreamble\n"
    nodes = "".join(f"\\loomnode{{{e}}}" for e in sorted(set(envs)) if _ENV.match(e))
    return "\\Preamble{xhtml,mathjax}\n\\begin{document}\n" + ROWS + STAMPS + marks + nodes + "\n\\EndPreamble\n"


@dataclass
class HtmlResult:
    """How a TeX4ht run went: `html` is the page this run made, None when it made none, though the last good one stays in `outdir`."""

    ok: bool
    outdir: Path
    returncode: int
    html: Path | None = None
    log: str = ""
    errors: list[str] = field(default_factory=list)
    passes: int = 0
    seconds: float = 0.0
    repaired: list[Repaired] = field(default_factory=list)

    @property
    def first_error(self) -> str:
        return self.errors[0] if self.errors else (f"make4ht exited {self.returncode}" if self.returncode else "")


def compile_html(
    root: Path,
    base: str,
    tex: str,
    outdir: Path,
    *,
    envs: list[str],
    engine: str = "pdflatex",
    seed: Path | None = None,
    timeout: int = 600,
    started: Callable[[subprocess.Popen[str]], None] | None = None,
) -> HtmlResult:
    """Make the HTML of the document `tex` into `outdir`, from `base`, its quilt-relative directory (P12).

    Parameters
    ----------
    root : Path
        The quilt root.
    base : str
        The document's directory, `ScanResult.base_of`; '' at the root.
    tex : str
        The document, quilt-relative.
    outdir : Path
        Where the page and its pictures go; replaced only by a run that made a page.
    envs : list of str
        The environments loom reads as nodes, each stamped where it begins (`configuration`).
    engine : str, default 'pdflatex'
    seed : Path, optional
        The directory of the document's last `pdflatex` compile, whose aux and bibliography the run starts from.
    timeout : int, default 600
        Seconds for each pass; the pass is killed with everything it started.
    started : callable, optional
        Handed each pass's process, for a caller that may end it with `stop_run`.

    Returns
    -------
    HtmlResult
    """
    exe = shutil.which("make4ht")
    if exe is None:
        return HtmlResult(False, outdir, 127, errors=["make4ht is not installed"])
    began = time.monotonic()
    stem = Path(tex).stem
    with tempfile.TemporaryDirectory(prefix="loom-html-") as tmp:
        stage = stage_document(root, base, [tex], Path(tmp) / "src")
        cwd = stage / base
        read = source_hashes(stage)
        texts = {
            f.relative_to(stage).as_posix(): f.read_text(encoding="utf-8", errors="replace")
            for f in sorted(stage.rglob("*.tex"))
            if f.is_file()
        }
        repaired: list[Repaired] = []
        for f in sorted(stage.rglob("*.tex")):
            text = f.read_text(encoding="utf-8", errors="replace")
            fixed, found = repair_displays(text, len(repaired))
            if found:
                f.write_text(fixed, encoding="utf-8")
                repaired += [Repaired(f.relative_to(stage).as_posix(), line, tex) for line, tex in found]
        _prepare(stage, cwd, envs)
        name = os.path.relpath(stage / tex, cwd)
        if seed is not None:
            for suffix in (".aux", ".bbl", ".toc", ".out"):
                if (seed / f"{stem}{suffix}").is_file():
                    shutil.copy2(seed / f"{stem}{suffix}", cwd / f"{stem}{suffix}")
        _read_externals(root / base, sorted(stage.rglob("*.tex")), cwd / f"{stem}.aux")
        home = Path(tmp) / "home"
        out = Path(tmp) / "out"
        aux = cwd / f"{stem}.aux"
        passes, code, said = 0, 0, ""
        while True:
            before = aux.read_bytes() if aux.is_file() else None
            code, said = _pass(exe, cwd, name, out, home, engine, timeout, started)
            if code == 124:
                return HtmlResult(
                    False,
                    outdir,
                    124,
                    errors=[f"make4ht timed out after {timeout}s"],
                    passes=passes + 1,
                    seconds=time.monotonic() - began,
                )
            passes += 1
            after = aux.read_bytes() if aux.is_file() else None
            if seed is not None or after == before or passes >= 3 or not (out / f"{stem}.html").is_file():
                break
        log = cwd / f"{stem}.log"
        text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else said
        errors = re.findall(r"^! .*$", text, re.M)
        page = out / f"{stem}.html"
        if page.is_file():
            outdir.parent.mkdir(parents=True, exist_ok=True)
            fresh = Path(tempfile.mkdtemp(prefix=f".{outdir.name}.run-", dir=outdir.parent))
            for f in out.iterdir():
                if f.is_file() and f.suffix.lower() in KEPT:
                    shutil.copy2(f, fresh / f.name)
            # the displays the page holds as placeholders, which the normaliser fills with their TeX as written
            (fresh / REPAIRED).write_text(json.dumps([vars(r) for r in repaired], ensure_ascii=False), encoding="utf-8")
            # what the page was made from, so a publication can tell whether it still says what the sources do
            (fresh / SOURCES).write_text(json.dumps(read, sort_keys=True), encoding="utf-8")
            (fresh / TEXTS).write_text(json.dumps(texts, sort_keys=True, ensure_ascii=False), encoding="utf-8")
            old = outdir.with_name(f".{outdir.name}.old")
            shutil.rmtree(old, ignore_errors=True)
            if outdir.exists():
                outdir.rename(old)
            fresh.rename(outdir)
            shutil.rmtree(old, ignore_errors=True)
        made = outdir / f"{stem}.html" if page.is_file() else None
        return HtmlResult(
            made is not None and code == 0, outdir, code, made, text, errors, passes, time.monotonic() - began, repaired
        )


def _prepare(stage: Path, cwd: Path, envs: Sequence[str], *, snippets: bool = False, math: str = "mathjax") -> None:
    """Make a staged copy ready for a run: what a quilt carries for TeX4ht removed, bounding boxes beside its figures, and loom's configuration and build file in `cwd`."""
    for f in sorted(stage.rglob("*")):
        if f.is_file() and CARRIED.search(f.name):
            f.unlink()
    if shutil.which("extractbb"):
        for f in sorted(cwd.rglob("*")):
            if f.is_file() and f.suffix.lower() in FIGURES:
                subprocess.run(["extractbb", f.name], cwd=f.parent, capture_output=True, timeout=60, check=False)
    (cwd / "loom-html.cfg").write_text(configuration(envs, snippets=snippets, math=math), encoding="utf-8")
    (cwd / "loom-html.mk4").write_text("-- loom's build file: make4ht's defaults and nothing else\n", encoding="utf-8")


def _pass(
    exe: str,
    cwd: Path,
    name: str,
    out: Path,
    home: Path,
    engine: str,
    timeout: int,
    started: Callable[[subprocess.Popen[str]], None] | None = None,
    math: str = "mathjax",
) -> tuple[int, str]:
    """One make4ht pass over `name` in `cwd`, writing into `out`, with `home` its own, formulas in `math` mode: its exit code and what it said; 124 when it ran past `timeout` and was killed with everything it started."""
    home.mkdir(exist_ok=True)
    env = {**os.environ, **tex_date(), "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config")}
    if "TEXMFHOME" not in os.environ:
        env["TEXMFHOME"] = _texmfhome()
    cmd = [exe, *ENGINE.get(engine, []), "-m", "draft", "-u", "-c", "loom-html.cfg", "-e", "loom-html.mk4"]
    proc = subprocess.Popen(
        [*cmd, "-d", str(out), name, math],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        env=env,
        start_new_session=True,
    )
    if started is not None:
        started(proc)
    try:
        said, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_run(proc)
        proc.communicate()
        return 124, ""
    return proc.returncode, said


def make_html(
    root: Path,
    base: str,
    name: str,
    text: str,
    *,
    envs: Sequence[str] = (),
    engine: str = "pdflatex",
    aux: Path | None = None,
    timeout: int = 600,
    pictures: tuple[Path, str] | None = None,
    math: str = "mathjax",
) -> tuple[str | None, str]:
    """One TeX4ht pass over `text`, a document loom wrote, as `name.tex` in a copy of the document directory `base` outside the quilt.

    Parameters
    ----------
    root : Path
        The quilt root.
    base : str
        The directory the text's local files resolve in, quilt-relative.
    name : str
        The document's name, without `.tex`.
    text : str
        The whole document, preamble and body.
    envs : sequence of str, default ()
        The environments stamped as nodes; the configuration also defines `\\loomsnippet`.
    engine : str, default 'pdflatex'
    aux : Path, optional
        An aux the run starts from, so references and citations print what that document prints.
    timeout : int, default 600
    pictures : (Path, str), optional
        A directory each picture the page draws is kept in, under its content's hash, and the path the page names that directory by.
    math : str, default 'mathjax'
        'mathjax' leaves formulas as TeX for the viewer; 'svg' has TeX4ht draw each display as a picture (`configuration`).

    Returns
    -------
    (str or None, str)
        The page, None when the run made none, and TeX's log.
    """
    exe = shutil.which("make4ht")
    if exe is None:
        return None, "make4ht is not installed"
    with tempfile.TemporaryDirectory(prefix="loom-html-") as tmp:
        stage = stage_document(root, base, [], Path(tmp) / "src")
        cwd = stage / base
        cwd.mkdir(parents=True, exist_ok=True)
        _prepare(stage, cwd, envs, snippets=True, math=math)
        (cwd / f"{name}.tex").write_text(text, encoding="utf-8")
        if aux is not None and aux.is_file():
            shutil.copy2(aux, cwd / f"{name}.aux")
        _read_externals(root / base, [cwd / f"{name}.tex"], cwd / f"{name}.aux")
        out = Path(tmp) / "out"
        code, said = _pass(exe, cwd, f"{name}.tex", out, Path(tmp) / "home", engine, timeout, math=math)
        log = cwd / f"{name}.log"
        told = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else said
        if code == 124:
            told += f"\n! make4ht timed out after {timeout}s\n"
        page = out / f"{name}.html"
        if not page.is_file():
            return None, told
        html = page.read_text(encoding="utf-8", errors="replace")
        if pictures is not None:
            where, named = pictures
            for f in sorted(out.iterdir()):
                if f.is_file() and f.suffix.lower() in KEPT and f.suffix.lower() not in (".html", ".css"):
                    kept = where / f"{hashlib.sha256(f.read_bytes()).hexdigest()[:20]}{f.suffix.lower()}"
                    if not kept.is_file():
                        where.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(f, kept)
                    html = re.sub(
                        rf"""(\bsrc=['"]){re.escape(f.name)}(['"])""", rf"\g<1>{named}/{kept.name}\g<2>", html
                    )
        return html, told


@dataclass
class Placed:
    """How a normalised fragment's blocks stand in the source: placed as an unbroken run of words, placed nearly, or not at all, with up to ten of the last for a report. A block of fewer than two words is too short to say and counts in none; one read from a `.bbl`, which BibTeX made, has no source and counts as `made`."""

    blocks: int = 0
    exact: int = 0
    near: int = 0
    unplaced: list[tuple[str, int, str]] = field(default_factory=list)
    missed: int = 0
    made: int = 0


def placed(
    fragment: str,
    clean: Callable[[str], str | None],
    master: str,
    base: str,
    macros: dict[str, str] | None = None,
    heads: frozenset[str] = frozenset(),
    environments: dict[str, str] | None = None,
) -> Placed:
    """Place each block of `fragment` in the source it came from.

    `clean(path)` is a quilt-relative file's text with comments blanked, as the scan holds it, or None; a block's file is the master's when TeX4ht named none, and is read against the document's directory `base` otherwise (P12). `macros` and `environments` are the document's own (`definitions`), each read as the words its code prints, and `heads` its theorems' names, folded, which a block may begin with though the source never says them.
    """
    import posixpath

    from loom.render.normalise import blocks
    from loom.tex.align import Source, rendered_words

    out = Placed()
    sources: dict[str, tuple[Source, list[int]] | None] = {}
    for b in blocks(fragment):
        words = rendered_words(b.text)
        if len(words) < 2:
            continue
        rel = master if not b.file else posixpath.normpath(posixpath.join(base, b.file))
        if rel.endswith(".bbl"):
            out.made += 1
            continue
        if rel not in sources:
            text = clean(rel)
            sources[rel] = (
                (Source(text, macros, environments), [0] + [m.end() for m in re.finditer("\n", text)])
                if text is not None
                else None
            )
        out.blocks += 1
        got = None
        if (known := sources[rel]) is not None:
            src, lines = known
            got = src.place(words, lines[min(max(b.line - 1, 0), len(lines) - 1)], heads=heads)
        if got is None:
            out.missed += 1
            if len(out.unplaced) < 10:
                out.unplaced.append((rel, b.line, " ".join(words)[:80]))
        elif got.exact:
            out.exact += 1
        else:
            out.near += 1
    return out


_ENVIRONMENT = re.compile(r"\\(?:re)?newenvironment\s*\*?\s*\{([^{}]+)\}")


def definitions(closure: PreambleClosure | None) -> tuple[dict[str, str], dict[str, str]]:
    """A document's own macros, each by its definition, and its own environments, each by the code it opens with, from its preamble closure: what alignment reads them as printing."""
    from loom.scan.tokenize import read_args

    if closure is None:
        return {}, {}
    macros = {m.name: m.body for m in closure.macros.values()}
    environments: dict[str, str] = {}
    text = closure.clean_text()
    for m in _ENVIRONMENT.finditer(text):
        (_args, _default, opening, _closing), _, _ = read_args(text, m.end(), "oomm")
        if opening:
            environments[m.group(1).strip()] = opening
    return macros, environments


_TEXMFHOME: str | None = None


def _texmfhome() -> str:
    """The person's own TeX tree, as their home names it: a run's home is empty, and their packages must still be found."""
    global _TEXMFHOME
    if _TEXMFHOME is None:
        try:
            _TEXMFHOME = subprocess.run(
                ["kpsewhich", "-var-value=TEXMFHOME"], capture_output=True, text=True, timeout=30, check=False
            ).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            _TEXMFHOME = ""
    return _TEXMFHOME
