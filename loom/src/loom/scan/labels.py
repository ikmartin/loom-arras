"""Id grammar and allocation (book 5.3).

An id is <prefix>-<local>. A prefix that is a citekey slug takes the paper-local form; any other prefix takes four uppercase base-36 characters, which keeps hyphenated human labels from being mistaken for ids.
"""

from __future__ import annotations

import re

LOOMLOCAL = re.compile(r"^[0-9A-Z]{4}$")
PAPERLOCAL = re.compile(r"^[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*$")
PREFIX = re.compile(r"^[A-Za-z0-9]+$")
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
    return LOOMLOCAL.match(local) is not None


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
