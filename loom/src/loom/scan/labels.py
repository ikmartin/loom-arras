"""Id grammar and allocation (book 5.3).

An id is <prefix>-<local>. A prefix that is a citekey slug takes the paper-local form; any other prefix takes four uppercase base-36 characters, which keeps hyphenated human labels from being mistaken for ids. A derived id is a loom-local id with `-ai` after it, `zk-0001-ai`: the id of a node an agent's copy defines, whose counterpart is `zk-0001` (book 5.3).
"""

from __future__ import annotations

import re

LOOMLOCAL = re.compile(r"^[0-9A-Z]{4}$")
PAPERLOCAL = re.compile(r"^[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*$")
PREFIX = re.compile(r"^[A-Za-z0-9]+$")
DERIVED = re.compile(r"^([A-Za-z0-9]+-[0-9A-Z]{4})-ai(?:-[0-9A-Z]{2,})?$")
SUFFIX = "-ai"
# every place a source names a label: its definition, the reference family with \uses, hyperref's optional argument, a `see:` directive, and a child marker
LABEL_DEF = re.compile(r"(\\label\s*\{\s*)([^}\s]+)(\s*\})")
LABEL_REFS = re.compile(r"(\\(?:ref|eqref|cref|Cref|autoref|pageref|vref|Vref|nameref|uses)\*?\s*\{)([^}]*)(\})")
HYPERREF = re.compile(r"(\\hyperref\s*\[)([^\]]*)(\])")
SEE_LINE = re.compile(r"^([ \t]*%[ \t]*!LOOM[ \t]+see[ \t]*:[ \t]*)([^\n]*)()$", re.M)
CHILD_LINE = re.compile(r"^([ \t]*%[ \t]*!LOOM[ \t]+child:[ \t]*)(\S+)()", re.M)
_DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def split_id(label: str) -> tuple[str, str] | None:
    if "-" not in label:
        return None
    prefix, local = label.split("-", 1)
    if not PREFIX.match(prefix) or not local:
        return None
    return prefix, local


def is_id_shaped(label: str, citeslugs: set[str] | frozenset[str] = frozenset()) -> bool:
    parts = split_id(label)
    if parts is None:
        return False
    prefix, local = parts
    if prefix in citeslugs:
        return PAPERLOCAL.match(local) is not None
    return LOOMLOCAL.match(local) is not None or DERIVED.match(label) is not None


def derived_of(label: str) -> str | None:
    """The plain id a derived id names, `zk-0001` for `zk-0001-ai`; None for any other label.

    A citekey-slug prefix never makes a derived id, so a caller that may meet paper-local ids checks `is_id_shaped` with the slugs first.
    """
    m = DERIVED.match(label)
    return m.group(1) if m else None


def plain_key(key: str) -> str:
    """A key with its derived id made plain: `zk-0001-ai/proof` -> `zk-0001/proof`; any other key unchanged."""
    head, sep, rest = key.partition("/")
    plain = derived_of(head)
    return plain + sep + rest if plain else key


def rename_labels(text: str, rename: dict[str, str] | None = None, *, plain: bool = False) -> str:
    """Every label `text` names rewritten: through `rename`, or with `plain` each derived name made plain.

    Covers definitions, references (a comma list keeps its separators), `\\hyperref[...]`, `see:` directives and child markers. `plain` strips the suffix from any name ending in it, since a copy suffixes every label it defines, an equation's included (book 17.7).
    """

    def one(name: str) -> str:
        if rename is not None:
            return rename.get(name, name)
        if plain:
            head, sep, rest = name.partition("/")
            return (re.sub(r"-ai(?:-[0-9A-Z]{2,})?$", "", head)) + sep + rest
        return name

    def names(m: re.Match[str]) -> str:
        parts = re.split(r"(\s*,\s*)", m.group(2))
        out = [
            p if i % 2 else (p[: len(p) - len(p.lstrip())] + one(p.strip()) + p[len(p.rstrip()) :])
            for i, p in enumerate(parts)
        ]
        return m.group(1) + "".join(out) + m.group(3)

    text = LABEL_DEF.sub(lambda m: m.group(1) + one(m.group(2)) + m.group(3), text)
    for pattern in (LABEL_REFS, HYPERREF, SEE_LINE, CHILD_LINE):
        text = pattern.sub(names, text)
    return text


def base36_decode(local: str) -> int:
    value = 0
    for ch in local:
        value = value * 36 + _DIGITS.index(ch)
    return value


def base36_encode(value: int, width: int = 4) -> str:
    out = ""
    while value:
        value, rem = divmod(value, 36)
        out = _DIGITS[rem] + out
    return out.rjust(width, "0")


def next_local(locals_seen: list[str] | set[str]) -> str:
    """The base-36 maximum over the loom-local ids seen, plus one; '0001' when none."""
    best = 0
    for local in locals_seen:
        if LOOMLOCAL.match(local):
            best = max(best, base36_decode(local))
    return base36_encode(best + 1)
