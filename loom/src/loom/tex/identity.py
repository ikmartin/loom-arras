"""The identity test (book 6.6): compiled text before and after import, atomize, or inline must agree modulo whitespace, and label numbers must not move."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from loom.tex.aux import parse_aux
from loom.tex.runner import CompileResult, compile_tex


@dataclass
class IdentityResult:
    passed: bool
    skipped: str | None = None
    first_difference: tuple[str, str] | None = None
    changed_numbers: dict[str, tuple[str, str]] = field(default_factory=dict)
    before: CompileResult | None = None
    after: CompileResult | None = None

    def summary(self) -> str:
        if self.skipped:
            return f"Identity test: skipped ({self.skipped})"
        if self.passed:
            return "Identity test: pass (pdftotext identical)"
        lines = ["Identity test: FAIL"]
        if self.first_difference:
            a, b = self.first_difference
            lines.append(f"  before: {a[:100]}")
            lines.append(f"  after:  {b[:100]}")
        for lab, (x, y) in list(self.changed_numbers.items())[:10]:
            lines.append(f"  {lab}: {x} -> {y}")
        return "\n".join(lines)


def pdftotext(pdf: Path) -> str | None:
    exe = shutil.which("pdftotext")
    if exe is None:
        return None
    proc = subprocess.run(
        [exe, "-layout", str(pdf), "-"], capture_output=True, text=True, errors="replace", check=False
    )
    return proc.stdout if proc.returncode == 0 else None


def _collapse(text: str) -> list[str]:
    return [ln for ln in (re.sub(r"\s+", " ", line).strip() for line in text.splitlines()) if ln]


def identity_test(
    before_root: Path, before_rel: str, after_root: Path, after_rel: str, scratch: Path, engine: str = "pdflatex"
) -> IdentityResult:
    if shutil.which("pdftotext") is None:
        return IdentityResult(True, skipped="pdftotext is not installed")
    b = compile_tex(before_root, before_rel, scratch / "before", engine, halt_on_error=False)
    a = compile_tex(after_root, after_rel, scratch / "after", engine, halt_on_error=False)
    res = IdentityResult(False, before=b, after=a)
    if b.pdf is None or a.pdf is None:
        res.skipped = "a document did not compile: " + (b.first_error if b.pdf is None else a.first_error)
        return res
    tb, ta = pdftotext(b.pdf), pdftotext(a.pdf)
    if tb is None or ta is None:
        res.skipped = "pdftotext failed"
        return res
    lb, la = _collapse(tb), _collapse(ta)
    if lb != la:
        for x, y in zip(lb, la, strict=False):
            if x != y:
                res.first_difference = (x, y)
                break
        else:
            res.first_difference = (lb[len(la)] if len(lb) > len(la) else "", la[len(lb)] if len(la) > len(lb) else "")
    if b.aux and a.aux:
        nb, na = parse_aux(b.aux.read_text(errors="replace")), parse_aux(a.aux.read_text(errors="replace"))
        for lab in set(nb) & set(na):
            if nb[lab].number != na[lab].number:
                res.changed_numbers[lab] = (nb[lab].number, na[lab].number)
    res.passed = lb == la and not res.changed_numbers
    return res
