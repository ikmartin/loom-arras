"""A minimal BibTeX reader: entry keys and the handful of fields the manifest and digests use (book 8.4, 8.8, specs/manifest.md §13)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from loom.scan.tokenize import match_group

_ENTRY = re.compile(r"@(\w+)\s*[{(]")
_FIELD = re.compile(r"\s*([A-Za-z][\w-]*)\s*=\s*")


@dataclass
class BibEntry:
    key: str
    type: str
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def eprint(self) -> str | None:
        return self.fields.get("eprint")

    @property
    def version(self) -> str | None:
        v = self.fields.get("version")
        if v:
            return v
        e = self.eprint or ""
        m = re.search(r"v(\d+)$", e)
        return m.group(1) if m else None


def _value(text: str, pos: int) -> tuple[str, int]:
    p = pos
    n = len(text)
    parts: list[str] = []
    while p < n:
        while p < n and text[p] in " \t\n":
            p += 1
        if p >= n:
            break
        ch = text[p]
        if ch == "{":
            q = match_group(text, p)
            if q < 0:
                break
            parts.append(text[p + 1 : q - 1])
            p = q
        elif ch == '"':
            q = text.find('"', p + 1)
            q = n if q < 0 else q
            parts.append(text[p + 1 : q])
            p = q + 1
        else:
            m = re.match(r"[^,#}\n]+", text[p:])
            if not m:
                break
            parts.append(m.group(0).strip())
            p += m.end()
        while p < n and text[p] in " \t\n":
            p += 1
        if p < n and text[p] == "#":
            p += 1
            continue
        break
    return "".join(parts), p


def parse_bib(text: str) -> dict[str, BibEntry]:
    entries: dict[str, BibEntry] = {}
    for m in _ENTRY.finditer(text):
        etype = m.group(1).lower()
        open_ch = text[m.end() - 1]
        close_ch = "}" if open_ch == "{" else ")"
        end = match_group(text, m.end() - 1, open_ch, close_ch)
        if end < 0:
            continue
        body = text[m.end() : end - 1]
        if etype in ("comment", "preamble", "string"):
            continue
        key_m = re.match(r"\s*([^,]+?)\s*,", body)
        if not key_m:
            continue
        entry = BibEntry(key=key_m.group(1), type=etype)
        pos = key_m.end()
        while pos < len(body):
            fm = _FIELD.match(body, pos)
            if not fm:
                nxt = body.find(",", pos)
                if nxt < 0:
                    break
                pos = nxt + 1
                continue
            value, pos = _value(body, fm.end())
            entry.fields[fm.group(1).lower()] = re.sub(r"\s+", " ", value).strip()
            nxt = body.find(",", pos)
            if nxt < 0:
                break
            pos = nxt + 1
        entries[entry.key] = entry
    return entries


def citekey_slug(key: str) -> str:
    """Digest id prefix for a citekey: alphanumerics only (book 5.3.1 as amended by the deviation on citekeys with punctuation)."""
    return re.sub(r"[^A-Za-z0-9]", "", key)
