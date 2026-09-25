"""The one way a test runs loom: `run`, and the assertions over it that say what went wrong (plan 0.14.1 phase 2, book 14.1).

`run` lets any exception out of the command, so a crash is a traceback and never an exit code a test can mistake for a refusal. `ok`, `refused` and `json_of` run and assert in one call and, on failure, print the command, its exit code, its stdout and its stderr apart.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, TypeVar

import pytest
from click.testing import CliRunner, Result

from loom.cli import main

T = TypeVar("T")


def run(
    *args: str | Path,
    cwd: Path | str | None = None,
    env: Mapping[str, str | None] | None = None,
    stdin: str | None = None,
) -> Result:
    """Invoke `loom ARGS` in-process, from `cwd` when given; an uncaught exception propagates.

    Parameters
    ----------
    *args : str or Path
        The command line after `loom`.
    cwd : Path or str, optional
        The directory to run from; default the current one. Restored afterwards.
    env : mapping, optional
        Environment overrides for the invocation; a None value unsets.
    stdin : str, optional
        Text on standard input.

    Returns
    -------
    click.testing.Result
        With `stdout` and `stderr` apart; `output` interleaves them.

    See Also
    --------
    ok, refused, json_of : run and assert in one call.
    """
    old = os.getcwd()
    try:
        if cwd is not None:
            os.chdir(cwd)
        return CliRunner().invoke(main, [str(a) for a in args], input=stdin, env=env, catch_exceptions=False)
    finally:
        os.chdir(old)


def describe(args: Iterable[str | Path], r: Result) -> str:
    """The command and everything it said, for an assertion message."""
    cmd = "loom " + " ".join(str(a) for a in args)
    return f"\n$ {cmd}\nexit {r.exit_code}\n--- stdout\n{r.stdout.rstrip()}\n--- stderr\n{r.stderr.rstrip()}\n"


def ok(*args: str | Path, **kw: Any) -> Result:
    """Run and assert exit 0.

    Parameters
    ----------
    *args, **kw
        As for `run`.

    Returns
    -------
    click.testing.Result
    """
    r = run(*args, **kw)
    assert r.exit_code == 0, describe(args, r)
    return r


def exits(code: int, *args: str | Path, match: str | None = None, **kw: Any) -> Result:
    """Run and assert exit `code`, where a nonzero code is an outcome and not a refusal: `build` with an error diagnostic, `lint` finding one.

    Parameters
    ----------
    code : int
        The exit code expected.
    *args, **kw
        As for `run`.
    match : str, optional
        A substring the output must hold, naming the outcome.

    Returns
    -------
    click.testing.Result
    """
    r = run(*args, **kw)
    assert r.exit_code == code, f"expected exit {code}" + describe(args, r)
    assert match is None or match in r.output, f"expected {match!r} in the output" + describe(args, r)
    return r


def refused(*args: str | Path, code: int, match: str, **kw: Any) -> Result:
    """Run and assert loom refused: exit `code`, with `match` in what it said on either stream.

    Parameters
    ----------
    *args, **kw
        As for `run`.
    code : int
        The exit code: 1 for the quilt's content, 2 for the environment or usage (`loom.cli._common`).
    match : str
        A substring of the refusal, so a different refusal with the same code does not pass.

    Returns
    -------
    click.testing.Result
    """
    r = run(*args, **kw)
    assert r.exit_code == code, f"expected a refusal with exit {code}" + describe(args, r)
    assert match in r.output, f"expected {match!r} in the refusal" + describe(args, r)
    return r


def json_of(*args: str | Path, code: int = 0, **kw: Any) -> Any:
    """Run, assert the exit code (default 0), and parse stdout alone as JSON.

    Returns
    -------
    Any
        The parsed document.
    """
    r = exits(code, *args, **kw)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"stdout is not JSON: {e}" + describe(args, r)) from None


def edit(path: Path, old: str, new: str, count: int = 1) -> None:
    """Replace `old` with `new` in a file, failing if `old` is not there: an edit that silently does nothing makes the test after it vacuous."""
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} is not in {path}"
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def same_tree(got: Mapping[str, bytes], expected: Mapping[str, bytes], what: str, regenerate: str) -> None:
    """Compare two trees of file bytes path by path, naming the first path missing (in `expected` only), extra or different, up to five more, and the command that regenerates the expected tree."""
    bad = [
        (rel, "missing" if rel not in got else "extra" if rel not in expected else "different")
        for rel in sorted(set(got) | set(expected))
        if got.get(rel) != expected.get(rel)
    ]
    if bad:
        rel, how = bad[0]
        more = (
            f" (and {len(bad) - 1} more: {', '.join(f'{r} {h}' for r, h in bad[1:6])}{', ...' if len(bad) > 6 else ''})"
        )
        raise AssertionError(
            f"{what}: {rel} is {how}{more if len(bad) > 1 else ''}; if the change is intended, regenerate with `{regenerate}`"
        )


def the(items: Iterable[T], pred: Callable[[T], bool], what: str) -> T:
    """The one item matching `pred`, naming `what` when there is none or more than one."""
    hits = [x for x in items if pred(x)]
    assert len(hits) == 1, f"expected one {what}, found {len(hits)}"
    return hits[0]


class Once:
    """Values made at most once each, every one in its own temporary directory.

    A module- or session-scoped fixture runs before the autouse `isolated_env`, so it would build outside the isolation; a value is made lazily instead, inside the first test that asks and under that test's environment. A maker that raises (or skips) stores nothing, so the next test tries again. Under xdist each worker has its own.
    """

    def __init__(self, factory: pytest.TempPathFactory) -> None:
        self.factory = factory
        self.made: dict[str, Any] = {}

    def get(self, name: str, make: Callable[[Path], Any]) -> Any:
        """The value `make(dir)` returned the first time `name` was asked for, making it now if it was not."""
        if name not in self.made:
            self.made[name] = make(self.factory.mktemp(name))
        return self.made[name]


def copy(q: Path, dest: Path) -> Path:
    """A copy of the quilt `q` at `dest`, for a test that changes it."""
    shutil.copytree(q, dest, symlinks=True)
    return dest


#: The session's templates, set by conftest's `templates` fixture before the first test.
TEMPLATES: Once | None = None


def templated(name: str, dest: Path, make: Callable[[Path], object]) -> None:
    """Fill `dest` with a copy of what `make` wrote the first time this worker asked for `name`: an expensive setup paid once per worker, each test changing its own copy.

    Parameters
    ----------
    name : str
        The template's name; one name, one maker.
    dest : Path
        Where the copy goes; made if absent, merged into if present.
    make : callable
        Fills the directory it is given, as a test would fill its `tmp_path`; it runs under whichever test asks first, so its result must depend on nothing but the directory.

    Returns
    -------
    None
        Paths inside keep their layout relative to `dest`.
    """
    assert TEMPLATES is not None, "the templates fixture has not run"
    src = TEMPLATES.get(name, lambda d: (make(d), d)[1])
    shutil.copytree(src, dest, symlinks=True, dirs_exist_ok=True)
