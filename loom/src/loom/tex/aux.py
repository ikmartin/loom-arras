"""Read theorem, section, and equation numbers, and citation labels, from a compiled master's .aux and .bbl (book 5.9.5, 9.6).

Both the plain form `\\newlabel{ID}{{NUMBER}{PAGE}}` and hyperref's `\\newlabel{ID}{{NUMBER}{PAGE}{TITLE}{ANCHOR}{}}` are read; cleveref's `@cref` entries are skipped. Loom never computes a number or a citation label itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from loom.scan.tokenize import match_group

_NEWLABEL = re.compile(r"\\newlabel\{")
_BIBCITE = re.compile(r"\\bibcite\{([^}]*)\}")
_ENTRY = re.compile(r"\\entry\{([^}]*)\}")
_FIELD = re.compile(r"\\field\{(labelalpha|extraalpha)\}\{([^}]*)\}")


@dataclass(frozen=True)
class AuxNumber:
    number: str
    page: int | None


def parse_aux(text: str) -> dict[str, AuxNumber]:
    out: dict[str, AuxNumber] = {}
    for m in _NEWLABEL.finditer(text):
        open_pos = m.end() - 1
        close = match_group(text, open_pos)
        if close < 0:
            continue
        label = text[open_pos + 1 : close - 1]
        if label.endswith("@cref"):
            continue
        rest = close
        if rest >= len(text) or text[rest] != "{":
            continue
        end = match_group(text, rest)
        if end < 0:
            continue
        payload = text[rest + 1 : end - 1]
        parts: list[str] = []
        pos = 0
        while pos < len(payload) and payload[pos] == "{":
            q = match_group(payload, pos)
            if q < 0:
                break
            parts.append(payload[pos + 1 : q - 1])
            pos = q
        if not parts:
            continue
        number = re.sub(r"\\relax\s*", "", parts[0]).strip()
        page: int | None = None
        if len(parts) > 1:
            pm = re.match(r"\s*(\d+)", parts[1])
            page = int(pm.group(1)) if pm else None
        out[re.sub(r"\s+", " ", label).strip()] = AuxNumber(number, page)
    return out


def aux_path_for(root: Path, master_rel: str) -> Path | None:
    """`build/<stem>/<stem>.aux` if present, else the .aux beside the master, else None (book 4.4.8)."""
    stem = Path(master_rel).stem
    candidates = [root / "build" / stem / f"{stem}.aux", root / Path(master_rel).with_suffix(".aux")]
    for c in candidates:
        if c.is_file():
            return c
    return None


def read_numbers(root: Path, master_rel: str) -> dict[str, AuxNumber]:
    p = aux_path_for(root, master_rel)
    if p is None:
        return {}
    return parse_aux(p.read_text(encoding="utf-8", errors="replace"))


def parse_cite_labels(aux: str, bbl: str = "") -> dict[str, str]:
    """Citekey -> the label the compiled document prints for it (`GP99`, `3`).

    BibTeX writes `\\bibcite{KEY}{LABEL}` to the .aux, natbib as `{{LABEL}{YEAR}...}`; biblatex writes `labelalpha` and `extraalpha` per `\\entry` in the .bbl, the latter printed as a letter (GP99a). A numeric biblatex style records no label in either file and yields nothing.
    """
    out: dict[str, str] = {}
    for m in _BIBCITE.finditer(aux):
        open_pos = m.end()
        if open_pos >= len(aux) or aux[open_pos] != "{":
            continue
        end = match_group(aux, open_pos)
        if end < 0:
            continue
        label = aux[open_pos + 1 : end - 1]
        if label.startswith("{"):
            q = match_group(label, 0)
            label = label[1 : q - 1] if q > 0 else label
        out[m.group(1).strip()] = _plain_label(label)
    entries = list(_ENTRY.finditer(bbl))
    for i, m in enumerate(entries):
        block = bbl[m.end() : entries[i + 1].start() if i + 1 < len(entries) else len(bbl)]
        fields: dict[str, str] = {f.group(1): f.group(2) for f in _FIELD.finditer(block)}
        if "labelalpha" in fields:
            extra = fields.get("extraalpha", "")
            suffix = chr(ord("a") + int(extra) - 1) if extra.isdigit() and 0 < int(extra) <= 26 else ""
            out.setdefault(m.group(1).strip(), fields["labelalpha"] + suffix)
    return out


def _plain_label(label: str) -> str:
    """A label as printed: alpha.bst's `{\\etalchar{+}}` is its plus sign, and grouping braces print nothing."""
    label = re.sub(r"\\etalchar\s*\{([^}]*)\}", r"\1", label)
    return re.sub(r"[{}]", "", label).strip()


def read_cite_labels(root: Path, master_rel: str) -> dict[str, str]:
    """The citation labels of a compiled master, from its .aux and the .bbl beside it; empty when it has not been compiled."""
    p = aux_path_for(root, master_rel)
    if p is None:
        return {}
    bbl = p.with_suffix(".bbl")
    return parse_cite_labels(
        p.read_text(encoding="utf-8", errors="replace"),
        bbl.read_text(encoding="utf-8", errors="replace") if bbl.is_file() else "",
    )
