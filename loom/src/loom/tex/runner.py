"""Run latexmk from the quilt root into a build subdirectory (book 4.4.8, 9.6).

The engine is the master's `% !TEX program` if present, else `[quilt] engine`. Nothing is set in the environment: loom.sty and local styles must sit at the root, which is what makes the quilt compile on Overleaf too. Tests isolate HOME and the TeX trees through the environment they run in.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
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

    @property
    def first_error(self) -> str:
        """The first `! ` line of the log, which is what LaTeX calls an error; latexmk's closing advice is not one."""
        if self.errors:
            return self.errors[0]
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


def which_latexmk() -> str | None:
    return shutil.which("latexmk")


def normalise_engine(engine: str | None, default: str = "pdflatex") -> str:
    e = (engine or default).strip().lower()
    return e if e in ENGINE_FLAGS else default


def compile_tex(
    root: Path, tex_rel: str, outdir: Path, engine: str = "pdflatex", halt_on_error: bool = True, timeout: int = 600
) -> CompileResult:
    """Compile `tex_rel` (relative to `root`) with latexmk into `outdir`; return a result even when latexmk is missing."""
    engine = normalise_engine(engine)
    exe = which_latexmk()
    outdir.mkdir(parents=True, exist_ok=True)
    if exe is None:
        return CompileResult(False, engine, outdir, 127, errors=["latexmk is not installed"])
    cmd = [exe, *ENGINE_FLAGS[engine], "-interaction=nonstopmode", f"-outdir={outdir}"]
    if halt_on_error:
        cmd.append("-halt-on-error")
    cmd.append(tex_rel)
    try:
        proc = subprocess.run(
            cmd,
            cwd=root,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        return CompileResult(False, engine, outdir, 124, errors=[f"latexmk timed out after {timeout}s"])
    stem = Path(tex_rel).stem
    log = outdir / f"{stem}.log"
    errors: list[str] = []
    warnings: list[str] = []
    if log.exists():
        text = log.read_text(encoding="utf-8", errors="replace")
        errors = re.findall(r"^! .*$", text, re.M)
        warnings = re.findall(r"^(?:LaTeX|Package \w+|Class \w+) Warning: .*$", text, re.M)
    pdf = outdir / f"{stem}.pdf"
    aux = outdir / f"{stem}.aux"
    ok = proc.returncode == 0 and pdf.exists()
    return CompileResult(
        ok,
        engine,
        outdir,
        proc.returncode,
        proc.stdout + proc.stderr,
        errors,
        pdf if pdf.exists() else None,
        aux if aux.exists() else None,
        log if log.exists() else None,
        warnings,
    )
