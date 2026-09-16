"""Digest headers and the checks that read them (book 8.4, 8.8, 8.11): provenance directives, the source version against the bibliography, and `requires:` against the preamble closure."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from loom.scan.directives import list_value

if TYPE_CHECKING:
    from loom.scan.nodes import Assembly
    from loom.scan.preamble import PreambleClosure

ALWAYS_LOADED = {"amsmath", "amsthm", "loom"}
_PACKAGE = re.compile(r"\\(?:usepackage|RequirePackage)\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")


def digest_header(asm: Assembly, file: str) -> dict[str, str]:
    """The key/value directives of a digest file's header."""
    return {d.key: d.value for d in asm.directives.get(file, []) if d.form == "kv"}


def source_version(source: str) -> str | None:
    """The trailing `vN` of an identifier such as `arXiv:0805.2065v2`."""
    m = re.search(r"v(\d+)$", source.strip())
    return m.group(1) if m else None


def extracted_from(header: dict[str, str]) -> str:
    """The artifact a digest's statements and numbers came from.

    `source:` is the pre-0.5 spelling and is still read, so a quilt that has not been upgraded is understood rather than reported as having no provenance at all.
    """
    return (header.get("extracted-from") or header.get("source") or "").strip()


def published_as(header: dict[str, str]) -> str:
    """The work the bibliography cites, when it differs from the artifact that was parsed."""
    return (header.get("published-as") or "").strip()


def loaded_packages(closure: PreambleClosure) -> set[str]:
    """Package names the closure loads with \\usepackage or \\RequirePackage."""
    out: set[str] = set()
    for m in _PACKAGE.finditer(closure.clean_text()):
        for name in m.group(1).split(","):
            name = name.strip()
            if name:
                out.add(name)
    return out


def required_packages(asm: Assembly, file: str) -> list[str]:
    """The digest's `requires:` list."""
    return list_value(digest_header(asm, file).get("requires", ""))


def missing_packages(asm: Assembly, file: str, closure: PreambleClosure | None) -> list[str]:
    """Packages the digest requires that the closure does not load; empty when there is no closure to check against."""
    if closure is None:
        return []
    loaded = loaded_packages(closure) | ALWAYS_LOADED
    return [p for p in required_packages(asm, file) if p not in loaded]
