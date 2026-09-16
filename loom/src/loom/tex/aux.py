"""Read theorem, section, and equation numbers from a compiled master's .aux (book 5.9.5, 9.6).

Both the plain form `\\newlabel{ID}{{NUMBER}{PAGE}}` and hyperref's `\\newlabel{ID}{{NUMBER}{PAGE}{TITLE}{ANCHOR}{}}` are read; cleveref's `@cref` entries are skipped. Loom never computes a number itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from loom.scan.tokenize import match_group

_NEWLABEL = re.compile(r"\\newlabel\{")


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
