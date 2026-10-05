"""How every `loom library` command names a work and a result (plan 0.18.5): one resolver for each, and the session log a reader writes."""

from __future__ import annotations

import functools
import shlex
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

import click

from loom.cli._common import EnvError, NotFoundError
from loom.cli.report import Group
from loom.scan.bib import BibEntry
from loom.scan.scan import ScanResult

F = TypeVar("F", bound=Callable[..., Any])


def logged(name: str) -> Callable[[F], F]:
    """Give a `library` command `--session`, logging the call to that session as `loom source --session` does.

    The session is resolved before the command runs, so an unknown one is refused with nothing printed or written; the line is written once the command has answered, so a refused call logs nothing, and it holds what was typed as a command line: arguments, then each option given with its flag, no default.
    """

    def wrap(f: F) -> F:
        @click.option(
            "--session",
            "run_dir",
            default=None,
            envvar="LOOM_SESSION",
            metavar="SESSION",
            help="Log this call to the session.",
        )
        @functools.wraps(f)
        def inner(*args: Any, run_dir: str | None = None, **kwargs: Any) -> Any:
            if not run_dir:
                return f(*args, **kwargs)
            from click.core import ParameterSource

            from loom.cli._quilt import open_quilt
            from loom.cli.build_cmds import log_run

            ctx = click.get_current_context()
            words: list[str] = []
            opts: list[str] = []
            for p in ctx.command.params:
                k = p.name or ""
                v = kwargs.get(k)
                if k in ("quilt_path", "run_dir") or ctx.get_parameter_source(k) is ParameterSource.DEFAULT:
                    continue
                if v in (None, False, (), ""):
                    continue
                values = [str(x) for x in (v if isinstance(v, (tuple, list)) else (v,))]
                if isinstance(p, click.Argument):
                    words += [shlex.quote(x) for x in values]
                elif v is True:
                    opts.append(p.opts[0])
                else:
                    opts += [f"{p.opts[0]} {shlex.quote(x)}" for x in values]
            line = " ".join(["loom library", name, *words, *opts])
            root = open_quilt(kwargs.get("quilt_path")).root
            session(root, run_dir)
            try:
                out = f(*args, **kwargs)
            except click.exceptions.Exit:
                # a report that exits nonzero still answered; a refusal is a ClickException, and logs nothing
                log_run(run_dir, line, root)
                raise
            log_run(run_dir, line, root)
            return out

        return cast(F, inner)

    return wrap


def session(root: Path, run_dir: str | None) -> str:
    """The id of the session `--session` names, '' with none; an unknown one is refused, exit 2, before the caller prints or writes anything."""
    if not run_dir:
        return ""
    from loom.cli._common import find_session

    return str(find_session(root, run_dir).id)


def present(*groups: Group) -> list[Group]:
    """The groups that hold something; an empty one would print a heading over nothing."""
    return [g for g in groups if g.items]


def home(result: ScanResult, citekey: str) -> Path:
    """The work's directory in loom's store, where `work_dir` says every other reader looks."""
    return home_in(result.quilt.root, result.bib, citekey)


def home_in(root: Path, bib: dict[str, BibEntry], citekey: str) -> Path:
    """`home` from a bibliography read without a scan (`open_bib`)."""
    from loom.refs.fetch import work_dir

    entry = bib.get(citekey)
    if entry is None:
        raise NotFoundError("work", f"{citekey} is not in the bibliography, so it has no identity to file under")
    return work_dir(root, entry)


def citekey_of_id(result: ScanResult, rid: str) -> str | None:
    """The citekey whose digest prefix begins result id `rid` (`Calloway14-prop-3.2` -> `Calloway14`), longest prefix first; None when none does."""
    prefixes = sorted(((result.assembly.prefix_of(ck), ck) for ck in result.bib), key=lambda p: -len(p[0]))
    return next((ck for p, ck in prefixes if rid.startswith(p + "-")), None)


def works(result: ScanResult, needles: tuple[str, ...]) -> set[str]:
    """Citekeys for each argument: an exact citekey, a result id's work, else every entry whose citekey, author or title contains it.

    An argument that matches nothing is refused by name rather than answered with an empty table, which read as "nothing is known about that work". A fragment matching only a work and its versions names the work, and says so on stderr.
    """
    from loom.refs.resolve import _fold
    from loom.refs.scan import one_work_of, versions_of

    out: set[str] = set()
    for needle in needles:
        if needle in result.bib:
            out.add(needle)
            continue
        by_id = citekey_of_id(result, needle)
        if by_id is not None:
            out.add(by_id)
            continue
        want = _fold(needle)
        hits = {
            ck
            for ck, e in result.bib.items()
            if want
            and (
                want in _fold(ck)
                or want in _fold(e.fields.get("author", ""))
                or want in _fold(e.fields.get("title", ""))
            )
        }
        if not hits:
            raise NotFoundError("work", f"{needle!r} names no work: no citekey, result id, author or title matches it")
        top = one_work_of(sorted(hits), result.bib) if len(hits) > 1 else ""
        if top:
            others = versions_of(result.bib)[top]
            are = "is another document" if len(others) == 1 else "are other documents"
            click.echo(f"{needle!r} names {top}; {', '.join(others)} {are} of it", err=True)
            hits = {top}
        out |= hits
    return out


def one_work(result: ScanResult, needle: str) -> str:
    """The one citekey `needle` names, for a command that reads a single work; several matches are refused by name."""
    hits = sorted(works(result, (needle,)))
    if len(hits) > 1:
        shown = ", ".join(hits[:6]) + (f" and {len(hits) - 6} more" if len(hits) > 6 else "")
        raise EnvError(f"{needle!r} names {len(hits)} works: {shown}; give one citekey")
    return hits[0]


def is_suggestion(target: str) -> bool:
    """Whether `target` is an annotation id (`a-…`), a citation suggestion's, rather than a result id."""
    from loom.records.log import ID

    return ID.match(target) is not None


def find_result(result: ScanResult, target: str) -> tuple[str, str, dict[str, Any]]:
    """(citekey, id, that work's results); an id recorded nowhere is an argument naming nothing, exit 2."""
    from loom.refs.proposals import find_result as find

    try:
        return find(result, target)
    except LookupError as exc:
        raise NotFoundError("result", str(exc)) from exc
