"""Id grammar and allocation (book 5.3).

An id is <prefix>-<local>. A prefix that is a citekey slug takes the paper-local form; any other prefix takes four uppercase base-36 characters, which keeps hyphenated human labels from being mistaken for ids. A derived id is a loom-local id with `-ai` after it, `zk-0001-ai`: the id of a node an agent's copy defines, whose counterpart is `zk-0001` (book 5.3).
"""

from __future__ import annotations

import re

LOOMLOCAL = re.compile(r"^[0-9A-Z]{4}$")
PAPERLOCAL = re.compile(r"^[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*$")
PREFIX = re.compile(r"^[A-Za-z0-9]+$")
DERIVED = re.compile(r"^([A-Za-z0-9]+-[0-9A-Z]{4})-ai$")
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
