"""The one output layer every command that reports goes through (plan 0.18.3, book 12.1): a verdict, groups, notes, and the same report as JSON.

A command builds a `Report` and calls `emit`. The text leads with the verdict (T1), groups what repeats under a heading with its count and cuts a long list with what it left out (T2), names a next command where action is implied (T3), keeps within 100 columns without ever cutting an identifier (T5), and sends notes to stderr. `--json` prints the same report as one envelope (T8): the verdict, the groups uncut, the notes, and the command's own data under its keys. `Progress` shows that a slow command is alive, on stderr only (T6).
"""

from __future__ import annotations

import sys
import textwrap
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, TextIO

import click

from loom.cli._common import emit_json

#: The width text output keeps within (T5).
WIDTH = 100
#: How many items a group shows before `… and N more`.
LIMIT = 12
#: The envelope's own keys; a command's data must not use them.
ENVELOPE = ("verdict", "ok", "exit", "dry_run", "groups", "notes")


@dataclass
class Item:
    """One line of a group: its text, an identifier placed last and never cut, and the commands that act on it.

    `fixes` print beneath it as `fix:` lines in a group of problems and `next:` lines otherwise; `data` adds fields to the item's JSON.
    """

    text: str
    key: str | None = None
    fixes: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"text": self.text}
        if self.key is not None:
            out["key"] = self.key
        if self.fixes:
            out["fixes"] = list(self.fixes)
        out.update(self.data)
        return out


@dataclass
class Group:
    """What repeats, written once (T2): a heading, its count, its items, and the command that clears or lists them.

    `count` defaults to the number of items; give it when the items stand for more than themselves. `counted=False` leaves the count out of the heading, for a group of summary lines rather than of things (T5: a count says what it counts). `limit` cuts the text (never the JSON); None shows every item. `problem` marks a group whose items need action, so their commands read `fix:`.
    """

    heading: str
    items: list[Item] = field(default_factory=list)
    count: int | None = None
    limit: int | None = LIMIT
    next: str | None = None
    problem: bool = False
    counted: bool = True

    @property
    def size(self) -> int:
        return self.count if self.count is not None else len(self.items)

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"heading": self.heading, "count": self.size, "items": [i.to_json() for i in self.items]}
        if self.next:
            out["next"] = self.next
        return out


@dataclass
class Report:
    """What a command says: a verdict first, then groups, with notes on stderr and the same as one JSON envelope.

    Parameters
    ----------
    verdict : str
        One line answering "did it work, and do I need to do anything?".
    ok : bool, default True
        Whether nothing is wrong; a success that leaves work undone is not ok.
    exit : int, default 0
        The exit code, by book 12.1's rule.
    groups : list of Group, default []
        The detail, in the order a reader needs it.
    notes : list of str, default []
        Lines for stderr: what a script reading stdout must not see.
    data : dict, default {}
        The command's own JSON, beside the envelope's keys.
    dry_run : bool, default False
        The verdict reads `dry run: …`, and the JSON says so.
    lines : list of str, default []
        Lines printed between the verdict and the groups, already laid out: a table whose columns the command aligns.

    See Also
    --------
    Progress : liveness for what is slow, on stderr.
    """

    verdict: str
    ok: bool = True
    exit: int = 0
    groups: list[Group] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    lines: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        clash = [k for k in self.data if k in ENVELOPE]
        if clash:
            raise ValueError(f"a report's data may not use the envelope's keys: {', '.join(clash)}")

    def render(self, width: int = WIDTH) -> str:
        """The text: the verdict, any laid-out lines, then each group, wrapped within `width`."""
        out = wrap(("dry run: " if self.dry_run else "") + self.verdict, width)
        out += [w for line in self.lines for w in wrap(line, width)]
        for g in self.groups:
            if not g.heading and not g.items:
                continue
            out.append("")
            if g.heading:
                out += wrap(f"{g.heading} ({g.size})" if g.counted else g.heading, width)
            shown = g.items if g.limit is None or len(g.items) <= g.limit else g.items[: g.limit]
            indent = "  " if g.heading else ""
            for item in shown:
                text = item.text if item.key is None else (f"{item.text}  {item.key}" if item.text else item.key)
                out += wrap(indent + text, width)
                label = "fix" if g.problem else "next"
                for f in item.fixes:
                    out += wrap(f"{indent}  {label}: {f}", width)
            hidden = g.size - len(shown) if g.count is not None else len(g.items) - len(shown)
            if hidden > 0:
                out += wrap(f"{indent}… and {hidden} more" + (f"; {g.next}" if g.next else ""), width)
            elif g.next:
                out += wrap(f"{indent}{'fix' if g.problem else 'next'}: {g.next}", width)
        return "\n".join(out)

    def to_json(self) -> dict[str, Any]:
        """The envelope (book 12.9): the verdict, ok, exit, the groups uncut, the notes, and the command's data beside them."""
        out: dict[str, Any] = {
            "verdict": self.verdict,
            "ok": self.ok,
            "exit": self.exit,
            "groups": [g.to_json() for g in self.groups if g.heading or g.items],
            "notes": list(self.notes),
        }
        if self.dry_run:
            out["dry_run"] = True
        out.update(self.data)
        return out

    def emit(self, as_json: bool = False) -> None:
        """Print the report, notes to stderr, and end the command with its exit code."""
        for n in self.notes:
            click.echo(n, err=True)
        if as_json:
            emit_json(self.to_json())
        else:
            click.echo(self.render())
        if self.exit:
            click.get_current_context().exit(self.exit)


def wrap(line: str, width: int = WIDTH) -> list[str]:
    """`line` within `width`, broken at spaces under a hanging indent two deeper than its own; a word longer than the width (an identifier, a path) is never cut, so it stands alone on its line."""
    if len(line) <= width:
        return [line]
    lead = len(line) - len(line.lstrip(" "))
    return textwrap.wrap(
        line,
        width=width,
        initial_indent="",
        subsequent_indent=" " * (lead + 2),
        break_long_words=False,
        break_on_hyphens=False,
        drop_whitespace=True,
    ) or [line]


def table(rows: Iterable[tuple[str, ...]], gap: int = 2) -> list[str]:
    """Rows aligned in columns, each column as wide as its widest cell; put an identifier in the last column, which is never padded."""
    rows = [tuple(r) for r in rows]
    if not rows:
        return []
    widths = [max(len(r[i]) for r in rows if i < len(r)) for i in range(max(len(r) for r in rows))]
    out = []
    for r in rows:
        cells = [c.ljust(widths[i]) if i < len(r) - 1 else c for i, c in enumerate(r)]
        out.append((" " * gap).join(cells).rstrip())
    return out


def counted(n: int, one: str, many: str | None = None) -> str:
    """`n` with the noun it counts, singular or plural: `1 error`, `3 errors`."""
    return f"{n} {one if n == 1 else (many or one + 's')}"


class Progress:
    """That a slow command is alive (T6): the stage, the item, its place in the count, and the time elapsed, on stderr only.

    Silent for its first `quiet` seconds, so a command that finishes quickly prints nothing. On a terminal it is one line that rewrites itself; elsewhere a plain line at most every `every` seconds and at each stage. An item that runs past `slow` seconds says so. Use as a context manager; `ticking=False` leaves the clock to the caller's `tick`, which is how it is tested.

    Parameters
    ----------
    stage : str
        What is being done, e.g. `rendering`.
    total : int, optional
        How many items the stage has.
    stream : TextIO, optional
        Where to write; default stderr.
    tty : bool, optional
        Whether `stream` is a terminal; default asked of it.
    clock : callable, default time.monotonic
    quiet, every, slow : float, defaults 2, 2 and 15
    ticking : bool, default True
        Refresh from a background thread once a second.
    """

    def __init__(
        self,
        stage: str,
        total: int | None = None,
        *,
        stream: TextIO | None = None,
        tty: bool | None = None,
        clock: Callable[[], float] = time.monotonic,
        quiet: float = 2.0,
        every: float = 2.0,
        slow: float = 15.0,
        ticking: bool = True,
    ) -> None:
        self.stream = stream if stream is not None else sys.stderr
        self.tty = self.stream.isatty() if tty is None else tty
        self.clock = clock
        self.quiet, self.every, self.slow = quiet, every, slow
        self.started = clock()
        self.stage, self.total, self.n, self.current = stage, total, 0, ""
        self.item_started = self.started
        self.last_line = ""
        self.last_written = float("-inf")
        self.drawn = False
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True) if ticking else None

    def __enter__(self) -> Progress:
        if self._thread is not None:
            self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        with self._lock:
            if self.tty and self.drawn:
                self.stream.write("\n")
                self.stream.flush()

    def item(self, name: str) -> None:
        """Begin the next item."""
        with self._lock:
            self.n += 1
            self.current = name
            self.item_started = self.clock()
        self.tick()

    def next_stage(self, stage: str, total: int | None = None) -> None:
        """Move to another stage, its count starting again."""
        with self._lock:
            self.stage, self.total, self.n, self.current = stage, total, 0, ""
            self.item_started = self.clock()
        self.tick(force=True)

    def told(self, stage: str, item: str, n: int, total: int | None) -> None:
        """Follow a `(stage, item, n, total)` callback, as `render.build.build` and `refs.build.build_refs` give one."""
        if stage != self.stage:
            self.next_stage(stage, total)
        if item:
            with self._lock:
                self.n = n - 1
            self.item(item)

    def line(self) -> str:
        now = self.clock()
        parts = [self.stage]
        if self.total:
            parts.append(f"{self.n}/{self.total}")
        if self.current:
            parts.append(self.current)
        parts.append(_clock(now - self.started))
        if self.current and now - self.item_started >= self.slow:
            parts.append(f"still working, {int(now - self.item_started)} s")
        return "  ".join(parts)

    def tick(self, force: bool = False) -> None:
        """Write the line if it is due: after the quiet period, and off a terminal at most every `every` seconds or at a stage."""
        with self._lock:
            now = self.clock()
            if now - self.started < self.quiet:
                return
            text = self.line()
            if self.tty:
                if text != self.last_line:
                    self.stream.write("\r\x1b[2K" + text[: WIDTH - 1])
                    self.stream.flush()
                    self.drawn = True
            elif force or now - self.last_written >= self.every:
                if text != self.last_line:
                    self.stream.write(text + "\n")
                    self.stream.flush()
                    self.last_written = now
            self.last_line = text

    def _run(self) -> None:
        while not self._stop.wait(1.0):
            self.tick()


def _clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"
