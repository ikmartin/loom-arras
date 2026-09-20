"""Quilt loading shared by every command that runs against a quilt."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError
from loom.scan.quilt import NoQuiltError, Quilt, find_quilt
from loom.scan.scan import ScanResult, scan


def quilt_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--quilt", "quilt_path", default=None, metavar="PATH", help="Quilt root (default: discovered by walking up)."
    )(f)


def open_quilt(quilt_path: str | None) -> Quilt:
    try:
        return find_quilt(Path(quilt_path).expanduser() if quilt_path else None)
    except NoQuiltError as exc:
        raise EnvError(str(exc)) from exc


def open_scan(quilt_path: str | None) -> ScanResult:
    return scan(open_quilt(quilt_path))


def resolve_key(result: ScanResult, key: str) -> str:
    """Accept an id, an alias, a proof key, a qualified key, or a master path; return the canonical key or raise."""
    nodes = result.assembly.nodes
    if key in nodes:
        return key
    if key in result.assembly.regions:
        return key
    target = result.assembly.labels.get(key)
    if target is not None:
        return target
    if "/proof" in key:
        stem, rest = key.split("/proof", 1)
        base = result.assembly.labels.get(stem, stem)
        cand = f"{base}/proof{rest}"
        if cand in nodes:
            return cand
    raise EnvError(f"no such key: {key}")


def describe(result: ScanResult, key: str) -> str:
    """`rl-0004 (Lemma 3.4)` when a number is known, else `rl-0004 (Lemma)`; masters and files by path."""
    n = result.assembly.nodes.get(key)
    if n is None:
        return key
    if n.kind in ("master", "file"):
        return key
    taxon = n.taxon or n.kind
    return f"{key} ({taxon})"


def require_text(result: ScanResult, key: str) -> None:
    """Refuse a key that is conflicted: defined by two files, it has no text for anything to act on (book 5.3.5)."""
    n = result.assembly.nodes.get(key)
    if n is not None and n.kind == "conflict":
        raise ContentError(
            f"{key} is defined by {' and '.join(n.conflict)} and has no text until one definition remains; "
            f"loom lint --nodes shows both, loom fork {key} --in FILE splits them"
        )
