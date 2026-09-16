"""The diagnostic code table (docs/specs/diagnostics.md plus the codes implementation added).

Reserved codes have no namespace and cannot be silenced; loom codes are namespaced and can be, except those marked fixed. Every code emitted anywhere must appear here; the coverage test checks it.
"""

from __future__ import annotations

RESERVED: dict[str, str] = {
    "duplicate-id": "error",
    "dangling-link": "error",
    "missing-include": "error",
    "double-inclusion": "error",
    "inclusion-cycle": "error",
    "unreachable": "info",
}

LOOM: dict[str, tuple[str, bool]] = {  # code -> (severity, fixed)
    "loom:environment-spans-files": ("error", False),
    "loom:line-anchoring": ("error", True),
    "loom:unknown-environment": ("error", False),
    "loom:unattached-proof": ("error", False),
    "loom:multi-target-proof": ("warning", False),
    "loom:reference-to-loose": ("error", False),
    "loom:duplicate-label": ("error", False),
    "loom:macros-unloaded": ("error", False),
    "loom:macro-shadowed": ("warning", False),
    "loom:taxon-conflict": ("warning", False),
    "loom:prefix-is-citekey": ("warning", False),
    "loom:unknown-directive": ("warning", False),
    "loom:documentclass-outside-drafts": ("info", False),
    "loom:unlabelled-node": ("info", False),
    "loom:positional-proof-key": ("info", False),
    "loom:unexpected-proof": ("info", False),
    "loom:missing-proof": ("warning", False),
    "loom:equation-in-proof-referenced": ("warning", False),
    "loom:uses-missing": ("info", False),
    "loom:uses-unused": ("info", False),
    "loom:dependency-cycle": ("warning", False),
    "loom:converter-fallback": ("info", False),
    "loom:bundle-failed": ("error", False),
    "loom:atomize-target-exists": ("error", True),
    "loom:import-outside-tree": ("warning", False),
    "loom:retired-ledger-key": ("info", False),
    "loom:detached-annotation": ("info", False),
    "loom:previous-key-match": ("info", False),
    "loom:unmatched-postnote": ("warning", False),
    "loom:undigested-citekey": ("info", False),
    "loom:version-mismatch": ("warning", False),
    "loom:missing-package": ("warning", False),
    "loom:digest-without-bib": ("warning", False),
    "loom:interface-version": ("error", True),
    # added by the implementation (recorded in docs/deviations.md)
    "loom:non-utf8-source": ("warning", False),
    "loom:unknown-theoremstyle": ("warning", False),
    "loom:taxon-name-macro": ("info", False),
    "loom:citekey-slug-collision": ("error", False),
    "loom:main-not-found": ("warning", False),
    "loom:foreign-annotations": ("warning", False),
    "loom:agent-wrote-outside-run": ("error", False),
}

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def severity_of(code: str) -> str | None:
    if code in RESERVED:
        return RESERVED[code]
    if code in LOOM:
        return LOOM[code][0]
    return None


def can_disable(code: str) -> bool:
    return code in LOOM and not LOOM[code][1]


def all_codes() -> list[str]:
    return sorted(RESERVED) + sorted(LOOM)
