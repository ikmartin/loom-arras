"""`loom digest import PATH [--as CITEKEY]` (book 8.10): copy a digest into this quilt's `refs/`, renaming its citekey and every prefixed id, label, and citation when `--as` says so."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from loom.scan.bib import citekey_slug
from loom.scan.digests import ALWAYS_LOADED, loaded_packages
from loom.scan.directives import list_value
from loom.scan.scan import ScanResult

_HEADER = re.compile(r"^%\s*!LOOM\s+digest:\s*(\S+)\s*$", re.M)
_ENV = re.compile(r"\\begin\{([A-Za-z*]+)\}")


@dataclass
class DigestImport:
    old_citekey: str
    citekey: str
    text: str
    target: str
    renamed: int = 0
    missing_packages: list[str] = field(default_factory=list)
    undeclared_envs: list[str] = field(default_factory=list)


def plan_digest_import(result: ScanResult, path: Path, as_citekey: str | None) -> DigestImport:
    """Read the digest at `path`, rewrite it for this quilt, and say what it needs; nothing is written."""
    text = path.read_text(encoding="utf-8")
    m = _HEADER.search(text)
    if m is None:
        raise ValueError(f"{path} has no `% !LOOM digest:` header")
    old = m.group(1)
    new = as_citekey or old
    old_slug, new_slug = citekey_slug(old), citekey_slug(new)
    renamed = 0
    if new != old:
        text, n1 = _HEADER.subn(f"% !LOOM digest: {new}", text, count=1)
        text, n2 = re.subn(
            r"(\\(?:label|ref|eqref|cref|Cref|autoref)\{)" + re.escape(old_slug) + r"-", r"\g<1>" + new_slug + "-", text
        )
        text, n3 = re.subn(r"(\\cite(?:\[[^\]]*\])?\{)" + re.escape(old) + r"(\})", r"\g<1>" + new + r"\g<2>", text)

        def uses_repl(mm: re.Match[str]) -> str:
            inner = re.sub(r"\b" + re.escape(old_slug) + r"-", new_slug + "-", mm.group(2))
            return mm.group(1) + inner + "}"

        text, n4 = re.subn(r"(\\uses\{)([^}]*)\}", uses_repl, text)
        renamed = n1 + n2 + n3 + n4
    header = {k: v for k, v in re.findall(r"^%\s*!LOOM\s+([a-z]+):\s*(.*)$", text, re.M)}
    dm = result.default_master
    loaded = (loaded_packages(result.closures[dm]) if dm and dm in result.closures else set()) | ALWAYS_LOADED
    missing = [p for p in list_value(header.get("requires", "")) if p not in loaded]
    declared = set(result.taxa) | {"proof", "document", "equation", "align", "itemize", "enumerate", "description"}
    undeclared = sorted({e for e in _ENV.findall(text) if e not in declared and not e.endswith("*") and e[0].islower()})
    undeclared = [e for e in undeclared if e in {t for t in re.findall(r"\\begin\{([a-z]+)\}\s*\[\{\\cite", text)}]
    return DigestImport(old, new, text, f"refs/{new}.tex", renamed, missing, undeclared)


def write_digest_import(root: Path, plan: DigestImport) -> Path:
    dest = root / plan.target
    if dest.exists():
        raise FileExistsError(str(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plan.text, encoding="utf-8")
    return dest
