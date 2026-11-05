"""`locked`: one writer at a time, across processes, between reading what is taken and writing what is new.

Every id loom draws is the highest one it can see, plus one, so two writers that read at the same moment draw the same id. Holding a lock from the read to the write closes that, whichever process each writer is: two `loom` shells, two `loom mcp` servers, or a server and the viewer. A log's numbers are drawn under a lock on that log. Node ids are read from the whole quilt, so they take `paths.ID_LOCK`, a file that holds nothing.

The lock is the operating system's, so it goes when its holder dies and never needs clearing. It is advisory on POSIX and a single byte far past the end of the file on Windows, so readers of a locked log read on without waiting, and neither changes the file.
"""

from __future__ import annotations

import errno
import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from pathlib import Path

#: How long a writer waits, in seconds, before refusing. A hold is a read and a write, or a scan and a write, and N writers queue, so this is far longer than any one of them.
WAIT = 120.0
#: Where the Windows lock sits, past the end of any log.
_FAR = 2**40
#: What an operating system says when a filesystem takes no locks at all, which is not the same as a lock being held.
_UNSUPPORTED = {errno.ENOLCK, errno.ENOTSUP, errno.EOPNOTSUPP, errno.ENOSYS}

if sys.platform == "win32":
    import msvcrt

    def _try(fd: int) -> bool:
        """Take the lock if it is free; False when another holds it."""
        os.lseek(fd, _FAR, os.SEEK_SET)
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EDEADLK):
                return False
            raise
        return True

    def _release(fd: int) -> None:
        os.lseek(fd, _FAR, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try(fd: int) -> bool:
        """Take the lock if it is free; False when another holds it."""
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True

    def _release(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


_mine = threading.local()
_warned = False


def _no_locks(path: Path) -> None:
    """Say once that this filesystem cannot keep writers apart, and let the write go on (P13): `loom new` still never overwrites, since it creates its file exclusively."""
    global _warned
    if not _warned:
        import click

        click.echo(
            f"loom: {path}: this filesystem takes no file locks, so two writers at once could draw one id", err=True
        )
        _warned = True


def _busy(path: Path, wait: float) -> Exception:
    """The refusal when the lock stays held; a click error, so a command exits 2 and the write API answers it."""
    from loom.cli._common import EnvError

    return EnvError(
        f"another loom process has been writing to {path} for {wait:.0f} seconds, so this wrote nothing; run it again. "
        "The lock goes when that process ends, so there is nothing to clear."
    )


def _take(fd: int, path: Path, wait: float, patience: Callable[[], AbstractContextManager[object]] | None) -> bool:
    """Take the lock on `fd`, waiting up to `wait` seconds; whether it was taken, False on a filesystem with no locks."""
    try:
        if _try(fd):
            return True
        deadline = time.monotonic() + wait
        pause = 0.002
        with patience() if patience is not None else nullcontext():
            while not _try(fd):
                if time.monotonic() >= deadline:
                    raise _busy(path, wait)
                time.sleep(pause)
                pause = min(pause * 2, 0.05)
    except OSError as exc:
        if exc.errno not in _UNSUPPORTED:
            raise
        _no_locks(path)
        return False
    return True


@contextmanager
def locked(
    path: Path, *, wait: float | None = None, patience: Callable[[], AbstractContextManager[object]] | None = None
) -> Iterator[None]:
    """Hold the exclusive lock on `path`, across processes and threads, for the length of the block.

    Parameters
    ----------
    path : Path
        The file to lock: a log the block reads and appends to through its own handles, or a file that exists only to be locked. Made, empty, when absent, with its directory.
    wait : float, optional
        Seconds to wait before refusing; default `WAIT`.
    patience : callable, optional
        Makes a context manager entered only while actually waiting, for a command that shows it is alive.

    Yields
    ------
    None
        Reentrant within a thread: a block that already holds `path` holds it still.

    Raises
    ------
    EnvError
        When another process holds the lock for all of `wait`; nothing has been written.
    """
    key = os.path.realpath(path)
    held: set[str] = _mine.__dict__.setdefault("held", set())
    if key in held:
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # read-only is enough to lock, and never changes the file
    fd = os.open(path, os.O_RDONLY | os.O_CREAT, 0o666)
    try:
        took = _take(fd, path, WAIT if wait is None else wait, patience)
        held.add(key)
        try:
            yield
        finally:
            held.discard(key)
            if took:
                _release(fd)
    finally:
        os.close(fd)
