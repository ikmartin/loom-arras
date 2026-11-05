"""A Markdown file's task items, the boxes the viewer draws from `- [ ]`, and the tick that flips one.

A box's state is its text in the file, so an editor and an agent read what the viewer shows. The publisher marks each item with its line and a hash of that line less its box, so a tick survives other ticks and refuses a line that has since changed.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.scan.quilt import Quilt

#: The ledger's line for a box ticked or unticked, a plain line beside the steps.
TICK = "tick"
#: The most of an item's words a ledger line keeps.
WORDS = 200

_BOX = re.compile(r"\[( |x|X)\]")
#: How an item's words open when it is a task: a box and the space after it.
_OPENS = re.compile(r"\[( |x|X)\]\s+")
_LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+")


@dataclass(frozen=True)
class Task:
    """One box of a file: its 0-based source line, its state, and the hash of that line less its box."""

    line: int
    done: bool
    mark: str

    @property
    def id(self) -> str:
        """What the published body names the box by and a tick sends back."""
        return f"{self.line + 1}:{self.mark}"


class TickRefused(Exception):
    """A tick that cannot be made, and why; `code` is the write API's."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def split_lines(text: str) -> list[str]:
    """`text` a line at a time with each line's ending, by the breaks Markdown counts: joined, they are `text` exactly."""
    return _LINE.findall(text)


def _mark(line: str) -> str:
    return hashlib.sha256(_BOX.sub("[]", line.rstrip("\r\n"), count=1).encode()).hexdigest()[:8]


def mark_items(text: str, found: list[Task] | None) -> Callable[[list[Any]], None]:
    """The token pass that makes each task item of `text`'s Markdown a `li.task`, its box taken out of its words.

    With `found`, each item carries `data-task` and is added to it, which is what makes its box tickable; without, as for a notebook's cell, whose lines are no file's, the box is only drawn. Runs on `render_markdown`'s own parse, so what is a task (not a fence, not raw HTML) is what the page shows.
    """
    from loom.records.store import source_line

    lines = split_lines(text) if found is not None else []
    where = source_line(text) if found is not None else None

    def mark(tokens: list[Any]) -> None:
        for i, tok in enumerate(tokens):
            if tok.type != "list_item_open" or i + 2 >= len(tokens) or tokens[i + 1].type != "paragraph_open":
                continue
            inline = tokens[i + 2]
            first = (inline.children or [None])[0] if inline.type == "inline" else None
            if first is None or first.type != "text":
                continue
            opens = _OPENS.match(first.content)
            if opens is None:
                continue
            done = opens.group(1) != " "
            first.content = first.content[opens.end() :]
            tok.attrSet("class", "task")
            tok.attrSet("data-done", "true" if done else "false")
            if found is None or where is None or not inline.map:
                continue
            at = where(inline.map[0])
            if at < len(lines) and _BOX.search(lines[at]):
                task = Task(at, done, _mark(lines[at]))
                tok.attrSet("data-task", task.id)
                found.append(task)

    return mark


def items(text: str) -> list[Task]:
    """Every tickable box of a Markdown file's text, in order."""
    from loom.files import render_file_markdown

    found: list[Task] = []
    render_file_markdown(text, "", {}, tasks=found)
    return found


def tick(quilt: Quilt, who: str, path: str, task: str, done: bool) -> bool:
    """Set the box `task` of the Markdown file `path` to `done`; whether the file changed.

    The person's act (P7): the old text goes into the history first, one character of the file changes, the same change goes into `who`'s look so that it is not listed back to them (`looks.take_line`), and the ledger records it. A box already in that state writes nothing. Raises TickRefused for a file the viewer does not show, one that is not Markdown, and a line that no longer reads as the page drew it.
    """
    from loom.files import Shown, kind_of
    from loom.history.acts import write_file
    from loom.history.ledger import append_entry
    from loom.looks import take_line
    from loom.records.snapshots import write_raw

    root = quilt.root.resolve()
    target = (quilt.root / path).resolve()
    if not Shown.of(quilt).is_shown(path) or not target.is_relative_to(root) or not target.is_file():
        raise TickRefused("no-such-file", f"{path} is not a file the viewer shows")
    if kind_of(quilt.root, path) != "markdown":
        raise TickRefused("not-a-task", f"{path} is not a Markdown file, so it has no boxes to tick")
    try:
        text = target.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TickRefused("not-a-task", f"{path} is not UTF-8 text, so loom leaves it as it is") from exc
    got = next((t for t in items(text) if t.id == task), None)
    if got is None:
        raise TickRefused("stale", f"{path} changed since the page was drawn; look at it again")
    if got.done == done:
        return False
    lines = split_lines(text)
    source = lines[got.line]
    box = _BOX.search(source)
    assert box is not None  # an item is only ever marked on a line holding a box
    lines[got.line] = source[: box.start()] + ("[x]" if done else "[ ]") + source[box.end() :]
    after = "".join(lines)
    before = write_raw(quilt.root, text, quilt.history_dir)
    write_file(target, after)
    if who:
        take_line(quilt, who, path, text, after, got.line)
    words = source[box.end() :].strip()[:WORDS]
    entry = {"path": path, "line": got.line + 1, "done": done, "words": words, "from": before}
    append_entry(quilt.history_dir, TICK, entry, who or None)
    return True
