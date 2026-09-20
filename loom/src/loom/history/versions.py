"""Addresses and versions (book 17.4, 17.5): `rl-0001@3` names the text key `rl-0001` had at step 3, a proof by `rl-0001/proof@paper-v2`."""

from __future__ import annotations

import re
from pathlib import Path

from loom.history.ledger import History, Version
from loom.scan.scan import ScanResult

_ADDRESS = re.compile(r"^(?P<key>[^@\s]+)@(?P<ref>[^@\s]+)$")
_CHILD = re.compile(r"^[ \t]*%[ \t]*!LOOM[ \t]+child:[ \t]*(\S+)[ \t]*$", re.M)


def parse_address(addr: str) -> tuple[str, str] | None:
    m = _ADDRESS.match(addr.strip())
    return (m.group("key"), m.group("ref")) if m else None


def version_filename(key: str) -> str:
    """`rl-0001.tex`, `rl-0001.proof.tex`, `rl-0001.proof.2.tex`: the naming `atomize` already uses for deferred proofs."""
    return key.replace("/proof/", ".proof.").replace("/proof", ".proof") + ".tex"


def version_at(history: History, key: str, ref: str) -> Version | None:
    """The version `key` had at the step `ref` names: frozen there or carried over from an earlier step; None when the step or the key is unknown there."""
    step = history.resolve_step(ref)
    if step is None or step.step is None:
        return None
    state = history.state_at(step.step)
    if key not in state:
        return None
    n, h = state[key]
    frozen = history.step(n)
    if frozen is None:
        return None
    return Version(key, n, h, frozen.dir or "", frozen.name, (frozen.get("of") or {}).get(key))


def version_path(history: History, v: Version) -> Path:
    return history.dir / v.dir / version_filename(v.key)


def read_version(history: History, key: str, ref: str) -> tuple[Version, str]:
    """The version and its raw text; LookupError names what is missing."""
    v = version_at(history, key, ref)
    if v is None:
        if history.resolve_step(ref) is None:
            raise LookupError(f"no step {ref} in the history")
        raise LookupError(f"{key} has no version at step {ref}")
    p = version_path(history, v)
    if not p.is_file():
        raise LookupError(f"the record for {key}@{v.step} is missing: {p.relative_to(history.dir.parent.parent)}")
    return v, p.read_text(encoding="utf-8")


def materialize(text: str, result: ScanResult) -> str:
    """A version's text with every `% !LOOM child: KEY` marker replaced by the head's current region text of KEY; LookupError when a child no longer exists."""

    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        n = result.nodes.get(key)
        if n is None:
            raise LookupError(f"the version stands for {key}, which the quilt no longer has")
        src = result.files[n.file]
        return src.text[n.start : n.end].rstrip("\n")

    return _CHILD.sub(repl, text)


def has_markers(text: str) -> bool:
    return bool(_CHILD.search(text))


def matching_version(history: History, key: str, current_hash: str) -> Version | None:
    """The latest recorded version of `key` whose hash is `current_hash`, so a viewer can say "text of @3"."""
    for v in reversed(history.versions_of(key)):
        if v.hash == current_hash:
            return v
    return None
