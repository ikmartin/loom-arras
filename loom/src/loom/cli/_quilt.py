"""Quilt loading shared by every command that runs against a quilt."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any

import click

from loom.cli._common import ContentError, EnvError, NotFoundError
from loom.locks import locked
from loom.paths import ID_LOCK
from loom.scan.bib import BibEntry
from loom.scan.quilt import NoQuiltError, Quilt, find_quilt
from loom.scan.scan import ScanResult, scan


def quilt_option(f: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--quilt", "quilt_path", default=None, metavar="PATH", help="Quilt root (default: discovered by walking up)."
    )(f)


def open_quilt(quilt_path: str | None) -> Quilt:
    """The quilt at `--quilt`, else the nearest one above the current directory; outside one, the refusal says how to get into one."""
    try:
        return find_quilt(Path(quilt_path).expanduser() if quilt_path else None)
    except NoQuiltError as exc:
        said = str(exc)
        if said.startswith("not inside a quilt"):
            said += "; cd into one, or make one with loom init DIR"
        raise EnvError(said) from exc


def open_scan(quilt_path: str | None) -> ScanResult:
    """The scan of the quilt at `--quilt`, showing that it is alive when it takes more than a couple of seconds (T6), unless the command already shows progress of its own."""
    from loom.cli.report import Progress

    quilt = open_quilt(quilt_path)
    if Progress.running:
        return scan(quilt)
    with Progress("reading the quilt"):
        return scan(quilt)


@contextmanager
def drawing_ids(quilt_path: str | None) -> Iterator[None]:
    """Hold the quilt's id lock, showing that a wait is alive (T6); outside any quilt, the refusal `open_quilt` gives."""
    from loom.cli.report import Progress

    lock = open_quilt(quilt_path).root / ID_LOCK
    with locked(lock, patience=lambda: Progress("waiting for another loom writing to this quilt")):
        yield


def draws_ids(command: Callable[..., Any]) -> Callable[..., Any]:
    """Hold the quilt's id lock for the whole of a command that draws a node id or plans a history step, its scan included, since what the command must not reuse is read from that scan.

    On `new`, `fork`, `draft` and `stamp`, which write straight after they scan; `history restore` takes `drawing_ids` itself, since its `--quilt` may be its group's. A `dry_run` or `print_only` call draws nothing and takes nothing.

    Parameters
    ----------
    command : callable
        A click callback taking `quilt_path` by keyword.

    Returns
    -------
    callable
        The callback, holding the lock while it runs.
    """

    @wraps(command)
    def holding(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("dry_run") or kwargs.get("print_only"):
            return command(*args, **kwargs)
        with drawing_ids(kwargs.get("quilt_path")):
            return command(*args, **kwargs)

    return holding


def open_bib(quilt_path: str | None) -> tuple[Quilt, dict[str, BibEntry]]:
    """The quilt and its bibliography, read without a scan: for a command that needs a work's entry and nothing the documents say."""
    from loom.scan.bib import BIBLIOGRAPHY, parse_bib
    from loom.scan.source import read_source

    quilt = open_quilt(quilt_path)
    bib = parse_bib(read_source(quilt.root, BIBLIOGRAPHY).text) if (quilt.root / BIBLIOGRAPHY).is_file() else {}
    return quilt, bib


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
    raise NotFoundError("node", f"no such key: {key}")


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
    """Refuse a key that is conflicted: defined by two files, it has no text for anything to act on."""
    n = result.assembly.nodes.get(key)
    if n is not None and n.kind == "conflict":
        from loom.scan.nodes import defined_by

        split = (
            f"loom fork {key} --in FILE splits them" if len(n.conflict) > 1 else "loom id --next gives one a fresh id"
        )
        raise ContentError(
            f"{key} is {defined_by(n.conflict)} and has no text until one definition remains; "
            f"loom lint --nodes shows both, {split}"
        )
