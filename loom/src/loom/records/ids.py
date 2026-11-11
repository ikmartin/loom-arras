"""The ids of what loom's shared logs hold: an annotation, a note, a session and a link.

Clones of a quilt write apart and merge later, so a number counted from what one clone can see is the number another clone counts too. Each of these ids ends in a token drawn at random instead, so two clones draw two ids. A log's lock still keeps one clone's writers apart.

Two records can still reach one log under one id, by a line a hand-resolved merge kept twice or a draw that came up the same. `repeated` reports that (P13); it drops nothing and renumbers nothing, since which record an id should keep is not loom's to choose.

An id is otherwise opaque: nothing reads an order out of its token, so a listing that wants the oldest first sorts by when a record was written.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from collections.abc import Collection
from itertools import count
from pathlib import Path

#: A day and a token, as the patterns that recognise an id spell them. A token is any run of these characters, so an id written under a counter still reads.
DAY = r"\d{4}-\d{2}-\d{2}"
TOKEN = r"[0-9a-z]+"
ANNOTATION = rf"a-{DAY}-{TOKEN}"
NOTE = rf"n-{DAY}-{TOKEN}"
SESSION = rf"s-{DAY}-{TOKEN}"

#: Crockford's base 32 in lower case: no `i`, `l`, `o` or `u`, so a token survives being read aloud and rarely spells a word.
_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
#: Six characters of five bits. Clones drawing N and M ids in one day share one with odds of about NM / 2^30, and `repeated` says so if they do.
_LENGTH = 6
_BITS = 5 * _LENGTH


def _token(prefix: str, attempt: int) -> str:
    """Random; under LOOM_FIXED_TIME the `attempt`th of one fixed sequence for `prefix`, so that a fixture is reproducible."""
    if os.environ.get("LOOM_FIXED_TIME"):
        digest = hashlib.sha256(f"{prefix}{attempt}".encode()).digest()
        value = int.from_bytes(digest[:8], "big") >> (64 - _BITS)
    else:
        value = secrets.randbits(_BITS)
    return "".join(_ALPHABET[(value >> shift) & 31] for shift in range(_BITS - 5, -1, -5))


def draw(prefix: str, taken: Collection[str]) -> str:
    """`prefix` and a fresh token, the first drawn that `taken` does not hold.

    What is written draws this under its log's lock, so `taken` is still true at the write; a dry run has no lock and writes nothing, so what it prints is an example of what a write would draw.

    Parameters
    ----------
    prefix : str
        Everything before the token: `a-2026-11-05-`, `link-`.
    taken : collection of str
        The ids this clone can already see.

    Returns
    -------
    str
    """
    for attempt in count():
        fresh = prefix + _token(prefix, attempt)
        if fresh not in taken:
            return fresh
    raise AssertionError("count() never ends")


def repeated(root: Path, rel: str, events: tuple[str, ...] = ()) -> list[tuple[int, str]]:
    """Every line of a log that gives an id to a second record: its line number and what to say of it.

    `events` names the events that give a record its id, where every other event only speaks of one; with none, every line is a record. Lines that cannot be read are the log's own reader's to report.
    """
    try:
        lines = (root / rel).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    first: dict[str, tuple[int, str]] = {}
    found: list[tuple[int, str]] = []
    for n, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict) or "id" not in record or (events and record.get("event") not in events):
            continue
        ident = str(record["id"])
        if ident not in first:
            first[ident] = (n, line)
            continue
        at, text = first[ident]
        if line.strip() == text.strip():
            found.append(
                (n, f"line {n} repeats line {at} word for word, so {ident} reads as written twice: delete line {n}")
            )
        else:
            found.append(
                (
                    n,
                    f"lines {at} and {n} are two records under one id, {ident}, so nothing can say which it means: change the id on one of them",
                )
            )
    return found
