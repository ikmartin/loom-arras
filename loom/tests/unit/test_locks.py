"""`loom.locks`: what `locked` promises on its own, whoever holds it: exclusion across threads and processes, a clean refusal rather than a hang, and a lock that dies with its holder."""

from __future__ import annotations

import errno
import importlib.util
import signal
import subprocess
import sys
import threading
import time
import types
from pathlib import Path

import pytest

import loom
from loom.cli._common import EnvError
from loom.locks import locked
from loom.paths import ID_LOCK
from tests.helpers import ok
from tests.unit._quilts import demo

HOLDER = """
import pathlib, sys, time
from loom.locks import locked
with locked(pathlib.Path(sys.argv[1])):
    pathlib.Path(sys.argv[2]).write_text("")
    time.sleep(600)
"""


def holder(path: Path, tmp_path: Path) -> subprocess.Popen[bytes]:
    """A process holding the lock on `path` until it is killed."""
    ready = tmp_path / "ready"
    p = subprocess.Popen([sys.executable, "-c", HOLDER, str(path), str(ready)])
    deadline = time.monotonic() + 120
    while not ready.exists():
        assert p.poll() is None and time.monotonic() < deadline
        time.sleep(0.01)
    return p


@pytest.mark.skipif(sys.platform == "win32", reason="SIGKILL")
def test_a_held_lock_refuses_after_the_wait_and_goes_with_its_holder(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    p = holder(path, tmp_path)
    try:
        with pytest.raises(EnvError, match="wrote nothing; run it again"):
            with locked(path, wait=0.1):
                pytest.fail("the lock was held by another process")
    finally:
        p.send_signal(signal.SIGKILL)
        p.wait()
    with locked(path, wait=30):  # nothing to clear: the kernel let go when the holder died
        pass


def test_threads_exclude_one_another_and_a_thread_may_hold_a_lock_twice(tmp_path: Path) -> None:
    """`loom serve` writes from many threads, and an allocator that holds a log's lock calls what appends to it."""
    path = tmp_path / "log.jsonl"
    inside = 0
    most = 0

    def writer() -> None:
        nonlocal inside, most
        with locked(path), locked(path):  # the second would wait on itself forever if it were not reentrant
            inside += 1
            most = max(most, inside)
            time.sleep(0.01)
            inside -= 1

    threads = [threading.Thread(target=writer) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert most == 1


def test_patience_is_entered_only_while_waiting(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    waits: list[str] = []

    class Patience:
        def __enter__(self) -> None:
            waits.append("waiting")

        def __exit__(self, *exc: object) -> None:
            waits.append("got it")

    with locked(path, patience=Patience):
        pass
    assert waits == []
    p = holder(path, tmp_path)
    try:
        with pytest.raises(EnvError):
            with locked(path, wait=0.05, patience=Patience):
                pass
    finally:
        p.kill()
        p.wait()
    assert waits == ["waiting", "got it"]


def test_locking_a_log_changes_nothing_in_it(tmp_path: Path) -> None:
    path = tmp_path / "log.jsonl"
    path.write_text("line\n", encoding="utf-8")
    before = path.stat().st_mtime_ns
    with locked(path):
        pass
    assert path.read_text(encoding="utf-8") == "line\n" and path.stat().st_mtime_ns == before


def test_a_filesystem_with_no_locks_says_so_and_the_write_goes_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """P13: an NFS mount without a lock daemon is no reason to stop someone working."""
    import loom.locks as locks

    def refuses(fd: int) -> bool:
        raise OSError(errno.ENOLCK, "no locks available")

    monkeypatch.setattr(locks, "_try", refuses)
    monkeypatch.setattr(locks, "_warned", False)
    released: list[int] = []
    monkeypatch.setattr(locks, "_release", released.append)
    ran = []
    for _ in range(2):
        with locked(tmp_path / "log.jsonl"):
            ran.append(True)
    assert ran == [True, True] and not released  # nothing was taken, so nothing is let go
    assert capsys.readouterr().err.count("takes no file locks") == 1


def test_another_os_error_is_not_mistaken_for_a_filesystem_with_no_locks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import loom.locks as locks

    def breaks(fd: int) -> bool:
        raise OSError(errno.EIO, "input/output error")

    monkeypatch.setattr(locks, "_try", breaks)
    with pytest.raises(OSError, match="input/output"):
        with locked(tmp_path / "log.jsonl"):
            pass


def test_on_windows_the_lock_sits_past_the_end_of_the_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows locks are mandatory, so a lock on a log's bytes would refuse its readers. No Windows runs this suite: this is `msvcrt` as documented, faked, and says only that the branch does what it means to."""
    calls: list[tuple[int, int, int]] = []
    held: list[int] = []

    def locking(fd: int, mode: int, n: int) -> None:
        import os

        calls.append((os.lseek(fd, 0, os.SEEK_CUR), mode, n))
        if mode == fake.LK_NBLCK:
            if held:
                raise OSError(errno.EACCES, "denied")
            held.append(fd)
        else:
            held.remove(fd)

    fake = types.ModuleType("msvcrt")
    fake.LK_NBLCK, fake.LK_UNLCK = 2, 0  # type: ignore[attr-defined]
    fake.locking = locking  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    spec = importlib.util.spec_from_file_location("loom_locks_on_windows", Path(loom.__file__).parent / "locks.py")
    assert spec is not None and spec.loader is not None
    windows = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "loom_locks_on_windows", windows)
    spec.loader.exec_module(windows)
    monkeypatch.undo()

    path = tmp_path / "log.jsonl"
    with windows.locked(path):
        other = threading.Thread(target=lambda: seen.append(_refused(windows, path)))
        seen: list[bool] = []
        other.start()
        other.join()
    assert seen == [True]
    assert calls[0] == (windows._FAR, fake.LK_NBLCK, 1) and calls[-1] == (windows._FAR, fake.LK_UNLCK, 1)
    assert not held and path.read_bytes() == b""


def _refused(locks: types.ModuleType, path: Path) -> bool:
    try:
        with locks.locked(path, wait=0.05):
            return False
    except EnvError:
        return True


def test_only_the_locks_module_says_how_a_platform_locks() -> None:
    """`import fcntl` anywhere at the top of a module stops loom importing at all on Windows."""
    src = Path(loom.__file__).parent
    said = [p.relative_to(src).as_posix() for p in src.rglob("*.py") if "import fcntl" in p.read_text(encoding="utf-8")]
    assert said == ["locks.py"]


@pytest.mark.parametrize(
    ("args", "made"),
    [
        (["new", "definition", "T", "--dry-run"], False),
        (["new", "definition", "--print"], False),
        (["new", "definition", "T"], True),
    ],
)
def test_a_command_that_draws_nothing_takes_no_lock(tmp_path: Path, args: list[str], made: bool) -> None:
    """A dry run touches nothing, the lock's file included."""
    q = demo(tmp_path)
    ok(*args, "--as", "X Agent", cwd=q)
    assert (q / ID_LOCK).exists() is made
