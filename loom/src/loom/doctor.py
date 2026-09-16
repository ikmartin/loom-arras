"""Environment report behind `loom doctor`: which external tools exist, where the arras bundle is, who the author is.

Tool lookups go through shutil.which so tests can point PATH at the fake TeX shim. Hints are per platform because the first user has basic computer competency and a TeX distribution, nothing more.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any

from loom.arras_bundle import find_bundle
from loom.scan.quilt import NoAuthorError, resolve_author
from loom.version import INTERFACE_VERSION, __version__

_MAC = platform.system() == "Darwin"


def _hint(tex: bool = False, poppler: bool = False) -> str:
    if tex:
        return (
            "brew install --cask mactex-no-gui"
            if _MAC
            else "install TeX Live (https://tug.org/texlive) or apt install texlive-full"
        )
    if poppler:
        return "brew install poppler" if _MAC else "apt install poppler-utils"
    return "brew install git" if _MAC else "apt install git"


# name, required, version flag, hint
_TOOLS: list[tuple[str, bool, list[str], str]] = [
    ("latexmk", True, ["-v"], _hint(tex=True)),
    ("pdflatex", True, ["--version"], _hint(tex=True)),
    ("dvisvgm", True, ["--version"], _hint(tex=True)),
    ("bibtex", False, ["--version"], _hint(tex=True)),
    ("biber", False, ["--version"], _hint(tex=True)),
    ("lualatex", False, ["--version"], _hint(tex=True)),
    ("kpsewhich", False, ["--version"], _hint(tex=True)),
    ("pdftotext", False, ["-v"], _hint(poppler=True)),
    ("pdfinfo", False, ["-v"], _hint(poppler=True)),
    ("git", False, ["--version"], _hint()),
]


@dataclass
class ToolReport:
    name: str
    required: bool
    path: str | None
    version: str | None
    hint: str

    @property
    def missing(self) -> bool:
        return self.path is None


@dataclass
class DoctorReport:
    python: str
    loom: str
    interface_version: int
    tools: list[ToolReport] = field(default_factory=list)
    author: str | None = None
    author_source: str = ""
    bundle_path: str | None = None
    bundle_source: str = ""
    bundle_version: str = ""

    @property
    def ok(self) -> bool:
        return not any(t.required and t.missing for t in self.tools)

    def to_dict(self) -> dict[str, Any]:
        return {
            "python": self.python,
            "loom": self.loom,
            "interface_version": self.interface_version,
            "ok": self.ok,
            "tools": [
                {"name": t.name, "required": t.required, "path": t.path, "version": t.version, "hint": t.hint}
                for t in self.tools
            ],
            "author": {"name": self.author, "source": self.author_source},
            "arras": {"path": self.bundle_path, "source": self.bundle_source, "version": self.bundle_version},
        }

    def render(self) -> str:
        lines = [f"loom {self.loom}  (interface version {self.interface_version})", f"python {self.python}", ""]
        for t in self.tools:
            tag = "required" if t.required else "optional"
            if t.missing:
                lines.append(f"  {t.name:<10} MISSING ({tag})  try: {t.hint}")
            else:
                lines.append(f"  {t.name:<10} {t.version or 'found':<40} {t.path}")
        lines.append("")
        if self.author:
            lines.append(f"author: {self.author}  (from {self.author_source})")
        else:
            lines.append(f"author: none  ({self.author_source})")
        if self.bundle_path:
            lines.append(f"arras bundle: {self.bundle_path}  ({self.bundle_source}, {self.bundle_version})")
        else:
            lines.append(f"arras bundle: not found  ({self.bundle_source})")
        lines.append("")
        lines.append("ok" if self.ok else "problems: a required tool is missing (exit 2)")
        return "\n".join(lines)


def _version_of(path: str, flag: list[str]) -> str | None:
    try:
        proc = subprocess.run([path, *flag], capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    out = (proc.stdout or proc.stderr).strip().splitlines()
    return out[0][:60] if out else None


def check_tools() -> list[ToolReport]:
    """Locate every external tool loom may call, with its first version line."""
    reports = []
    for name, required, flag, hint in _TOOLS:
        path = shutil.which(name)
        version = _version_of(path, flag) if path else None
        reports.append(ToolReport(name, required, path, version, hint))
    return reports


def run_doctor() -> DoctorReport:
    report = DoctorReport(
        python=sys.version.split()[0],
        loom=__version__,
        interface_version=INTERFACE_VERSION,
        tools=check_tools(),
    )
    try:
        report.author, report.author_source = resolve_author(None)
    except NoAuthorError as exc:
        report.author, report.author_source = None, str(exc)
    bundle = find_bundle()
    if bundle is not None:
        report.bundle_path, report.bundle_source, report.bundle_version = (
            str(bundle.path),
            bundle.source,
            bundle.version,
        )
    else:
        report.bundle_source = "no vendored bundle, no LOOM_ARRAS_BUNDLE, no arras package"
    return report
