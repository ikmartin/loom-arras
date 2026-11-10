"""Run latexmk from a document's own directory into a build subdirectory.

The engine is the master's `% !TEX program` if present, else `[quilt] engine`. Nothing is set in the environment: a document's local styles, inputs and figures sit in its directory and below, as LaTeX and Overleaf expect, which is what makes it compile on Overleaf too (P12). Tests isolate HOME and the TeX trees through the environment they run in.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import signal
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

ENGINE_FLAGS = {
    "pdflatex": ["-pdf"],
    "lualatex": ["-lualatex"],
    "xelatex": ["-xelatex"],
    "latex": ["-dvi"],
}


@dataclass
class CompileResult:
    ok: bool
    engine: str
    outdir: Path
    returncode: int
    stdout: str = ""
    errors: list[str] = field(default_factory=list)
    pdf: Path | None = None
    aux: Path | None = None
    log: Path | None = None
    warnings: list[str] = field(default_factory=list)
    cwd: Path | None = None  # where latexmk ran, which the log's relative paths are relative to

    @property
    def first_error(self) -> str:
        """The first `! ` line of the log, which is what LaTeX calls an error; latexmk's closing advice is not one."""
        if self.errors:
            return self.errors[0]
        summary = latexmk_summary(self.stdout)
        if summary:
            return f"latexmk exited {self.returncode}: {summary[0]}"
        if self.log is not None:
            return f"latexmk exited {self.returncode} with no error line in {self.log.name}"
        return (self.stdout.strip().splitlines() or ["latexmk failed"])[-1]

    @property
    def usable(self) -> str:
        """`ok`, `warnings` when a PDF was produced and the log holds no error, or `failed`.

        latexmk exits nonzero on an undefined reference, which produces a perfectly readable PDF. Reporting that as a failure is the difference between a check a reader can act on and one they must ignore, so the middle case is named rather than collapsed into either end.
        """
        if self.ok:
            return "ok"
        return "warnings" if self.pdf is not None and not self.errors else "failed"


def latexmk_summary(stdout: str) -> list[str]:
    """The lines under latexmk's "Collected error summary", which name a failing tool (biber, bibtex, makeindex) that leaves no `! ` line in the log."""
    lines = stdout.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Collected error summary"):
            out = []
            for ln in lines[i + 1 :]:
                if not ln[:1].isspace() or not ln.strip():
                    break
                out.append(ln.strip())
            return out
    return []


BUILD_PRODUCTS = (
    ".aux",
    ".bbl",
    ".bcf",
    ".blg",
    ".dvi",
    ".fdb_latexmk",
    ".fls",
    ".idx",
    ".ilg",
    ".ind",
    ".lof",
    ".log",
    ".lot",
    ".nav",
    ".out",
    ".run.xml",
    ".snm",
    ".synctex.gz",
    ".toc",
    ".xdv",
)


def stage_sources(paper_dir: Path, dest: Path, outside: list[str] | tuple[str, ...] = ()) -> Path:
    """Copy a paper directory into `dest` without its build products; returns the copy of `paper_dir`, the root to compile.

    latexmk reads and rewrites a .bbl or .fdb_latexmk in its working directory even under -outdir, so compiling the author's directory in place both depends on their editor's leftovers and writes into it. Hidden directories are skipped; a .bbl is kept when the tree has no .bib, since an arXiv-style source ships only that. Files the paper reaches outside its directory (`outside`, as `closure_of` lists them) land at the same relative position, so `../macros` still resolves.
    """
    paper_dir = paper_dir.resolve()
    reached = [Path(o).resolve() for o in outside if Path(o).is_file()]
    anchor = Path(os.path.commonpath([paper_dir, *reached])) if reached else paper_dir
    root = dest / paper_dir.relative_to(anchor)
    has_bib = any(paper_dir.rglob("*.bib"))

    def ignore(folder: str, names: list[str]) -> set[str]:
        skip = set()
        for n in names:
            if n.startswith(".") and (Path(folder) / n).is_dir():
                skip.add(n)
            elif n.endswith(BUILD_PRODUCTS) and not (n.endswith(".bbl") and not has_bib):
                skip.add(n)
        return skip

    shutil.copytree(paper_dir, root, ignore=ignore, symlinks=False)
    for f in reached:
        target = dest / f.relative_to(anchor)
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, target)
    return root


def which_latexmk() -> str | None:
    return shutil.which("latexmk")


def normalise_engine(engine: str | None, default: str = "pdflatex") -> str:
    e = (engine or default).strip().lower()
    return e if e in ENGINE_FLAGS else default


def compile_document(
    root: Path,
    base: str,
    tex: str | Path,
    outdir: Path,
    engine: str = "pdflatex",
    halt_on_error: bool = True,
    timeout: int = 600,
    started: Callable[[subprocess.Popen[str]], None] | None = None,
) -> CompileResult:
    """Compile a document from `base`, the quilt-relative directory it compiles from (P12), in a clean copy of that directory (`stage_document`).

    A document's directory holds whatever its author's editor left there, and latexmk reads a `.bcf`, `.aux` or `.toc` it finds in its working directory and runs biber there even under `-outdir`; compiling the directory in place both depends on those leftovers and writes into it. The log's relative names are the document's directory's, which `CompileResult.cwd` says.

    Parameters
    ----------
    root : Path
        The quilt root.
    base : str
        The document's directory, `ScanResult.base_of`; '' at the root.
    tex : str or Path
        The file to compile, quilt-relative or absolute; named to latexmk from `base`, so an agent copy compiles as `../.loom/copies/x.tex` from its source's directory.
    outdir : Path
        Where latexmk writes.
    engine : str, default 'pdflatex'
    halt_on_error : bool, default True
    timeout : int, default 600
        Seconds.
    started : callable, optional
        Handed latexmk's process as it starts, for a caller that may end it with `stop_run`.

    Returns
    -------
    CompileResult
        Its `pdf` and `aux` are None when this run made no PDF, though the last good ones stay in `outdir`.
    """
    tex_rel = Path(tex).relative_to(root).as_posix() if Path(tex).is_absolute() else Path(tex).as_posix()
    with tempfile.TemporaryDirectory(prefix="loom-compile-") as tmp:
        stage = stage_document(root, base, [tex_rel], Path(tmp))
        cwd = stage / base
        res = compile_tex(cwd, os.path.relpath(stage / tex_rel, cwd), outdir, engine, halt_on_error, timeout, started)
    res.cwd = root / base
    return res


def stage_document(root: Path, base: str, extra: list[str], dest: Path) -> Path:
    """A copy of the document directory `base` under `dest`, at its quilt-relative place, for latexmk to run in; returns `dest`.

    Left out: build products (`BUILD_PRODUCTS`; a `.bbl` stays when the directory has no `.bib`, as an arXiv source ships only that), hidden directories, the directories never read as a document's (`scan.source.SKIP_DIRS`), and the sync directory. `extra` (quilt-relative files, the document itself when it sits elsewhere, as an agent copy or a closure does) is copied to its own place. Files are copied, never linked, since a package may rewrite a file in its working directory (a TikZ externalisation, a `filecontents`).
    """
    from loom.scan.source import SKIP_DIRS
    from loom.sync import skipped_directory

    synced = skipped_directory(root)
    top = root / base
    has_bib = any(top.rglob("*.bib"))

    def ignore(folder: str, names: list[str]) -> set[str]:
        rel = Path(folder).relative_to(root).as_posix()
        skip = set()
        for n in names:
            path = Path(folder) / n
            where = f"{rel}/{n}" if rel != "." else n
            if path.is_dir() and (n.startswith(".") or n in SKIP_DIRS or where == synced):
                skip.add(n)
            elif n.endswith(BUILD_PRODUCTS) and not (n.endswith(".bbl") and not has_bib):
                skip.add(n)
        return skip

    shutil.copytree(top, dest / base, ignore=ignore, dirs_exist_ok=True)
    for rel in extra:
        target = dest / rel
        if (root / rel).is_file() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, target)
    return dest


def compile_tex(
    root: Path,
    tex_rel: str,
    outdir: Path,
    engine: str = "pdflatex",
    halt_on_error: bool = True,
    timeout: int = 600,
    started: Callable[[subprocess.Popen[str]], None] | None = None,
) -> CompileResult:
    """Compile `tex_rel` (relative to `root`) with latexmk into `outdir`; return a result even when latexmk is missing.

    latexmk reads no rc file (`-norc`): one in a quilt is a Perl program, and one at home may turn on shell escape. The run writes into a scratch directory beside `outdir`, seeded with `outdir`'s files so latexmk still runs only the passes it needs, and its output replaces `outdir`'s only when it made a PDF: a failed run leaves the last good PDF and aux in place, and only its log is kept. The run is a process group of its own, killed whole on timeout or by `stop_run` on the process `started` is handed.
    """
    engine = normalise_engine(engine)
    exe = which_latexmk()
    outdir.mkdir(parents=True, exist_ok=True)
    if exe is None:
        return CompileResult(False, engine, outdir, 127, errors=["latexmk is not installed"])
    stem = Path(tex_rel).stem
    made = {f"{stem}.pdf", f"{stem}.dvi"}
    run = Path(tempfile.mkdtemp(prefix=f".{outdir.name}.run-", dir=outdir.parent))
    try:
        # what tells this run's success is a PDF of its own making, and its log must be its own
        shutil.copytree(
            outdir,
            run,
            dirs_exist_ok=True,
            ignore=lambda d, names: {n for n in names if Path(d) == outdir and (n in made or n == f"{stem}.log")},
        )
        cmd = [exe, "-norc", *ENGINE_FLAGS[engine], "-interaction=nonstopmode", f"-outdir={run}"]
        if halt_on_error:
            cmd.append("-halt-on-error")
        cmd.append(tex_rel)
        proc = subprocess.Popen(
            cmd,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            env=os.environ.copy(),
            start_new_session=True,
        )
        if started is not None:
            started(proc)
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_run(proc)
            proc.communicate()
            return CompileResult(False, engine, outdir, 124, errors=[f"latexmk timed out after {timeout}s"])
        made_one = any((run / n).is_file() for n in made)
        for f in sorted(run.rglob("*")) if made_one else [run / f"{stem}.log"]:
            if f.is_file():
                target = outdir / f.relative_to(run)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(f, target)
    finally:
        shutil.rmtree(run, ignore_errors=True)
    log = outdir / f"{stem}.log"
    errors: list[str] = []
    warnings: list[str] = []
    if log.exists():
        text = log.read_text(encoding="utf-8", errors="replace")
        errors = re.findall(r"^! .*$", text, re.M)
        warnings = re.findall(r"^(?:LaTeX|Package \w+|Class \w+) Warning: .*$", text, re.M)
    pdf = outdir / f"{stem}.pdf"
    aux = outdir / f"{stem}.aux"
    return CompileResult(
        proc.returncode == 0 and made_one and pdf.exists(),
        engine,
        outdir,
        proc.returncode,
        out + err,
        errors,
        pdf if made_one and pdf.exists() else None,
        aux if made_one and aux.exists() else None,
        log if log.exists() else None,
        warnings,
        root,
    )


def stop_run(proc: subprocess.Popen[str]) -> None:
    """End a compile `compile_tex` started, with every program latexmk ran: TERM to its process group, then KILL to what is left after two seconds."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(proc.pid, signal.SIGKILL)
