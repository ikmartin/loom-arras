"""Works a person adds to the library by hand (plan 0.24.2): written into loom's own bibliography marked `loom-added`, and taken back out while nothing cites them.

The bibliography is loom's file, `.loom/digests/bibliography.bib`, never a document's `.bib`: gathering appends what the documents cite, and an added work is appended beside them. An entry a person corrected by hand is never removed; one loom wrote for a work added here may be, since nothing of the person's is in it.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from loom.clock import stamp
from loom.refs.scan import Candidate, append_entries
from loom.scan.bib import BIBLIOGRAPHY, BibEntry, parse_bib
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult
from loom.scan.tokenize import match_group

#: The field that marks a work as added by hand: when and by whom.
ADDED = "loom-added"
#: What the bibliography's comment line says an added entry came from.
SOURCE = "the viewer, added by hand"
#: The fields an entry is written in, in this order; any others follow, and `loom-added` closes it.
ORDER = (
    "author",
    "title",
    "year",
    "journal",
    "booktitle",
    "publisher",
    "volume",
    "number",
    "pages",
    "doi",
    "eprint",
    "archiveprefix",
    "zbl",
    "mrnumber",
    "isbn",
    "url",
)


class NotRemovable(Exception):
    """A work that cannot be taken out of the library here, with the code the API answers: `no-such-work`, `not-added`, `cited`."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def entry_text(key: str, etype: str, fields: Mapping[str, str]) -> str:
    """One BibTeX entry, its fields in `ORDER` and then the rest, each braced as written."""
    names = [f for f in ORDER if fields.get(f)] + sorted(
        f for f in fields if f not in ORDER and f != ADDED and fields[f]
    )
    if fields.get(ADDED):
        names.append(ADDED)
    lines = [f"@{etype or 'misc'}{{{key},"] + [f"  {n} = {{{fields[n]}}}," for n in names]
    return "\n".join(lines) + "\n}\n"


def add_entry(quilt: Quilt, fields: Mapping[str, str], key: str, who: str, etype: str = "") -> str:
    """Write a work into the library as added by hand, and return its key.

    Parameters
    ----------
    quilt : Quilt
        The quilt.
    fields : mapping
        The entry's fields, as `refs.lookup.look_up` made them or a pasted entry stated them; loom's own `loom-*` fields are never taken from it.
    key : str
        The key to file it as, which no entry may already have.
    who : str
        Who added it, as the reviewer identity names them.
    etype : str, default ''
        The entry type; '' is `article` when it has a journal, else `misc`.

    Returns
    -------
    str
        The key it was filed as.

    Raises
    ------
    ValueError
        The key is taken, or the entry has no title.
    """
    path = quilt.root / BIBLIOGRAPHY
    taken = set(parse_bib(path.read_text(encoding="utf-8"))) if path.is_file() else set()
    if key in taken:
        raise ValueError(f"the library already has a work filed as {key}")
    own = {k: v for k, v in fields.items() if not k.startswith("loom-") and v}
    if not own.get("title"):
        raise ValueError("the entry has no title, so the library could not show it")
    own[ADDED] = f"{stamp()}, {who}" if who else stamp()
    append_entries(
        quilt, [Candidate(key, entry_text(key, etype or ("article" if own.get("journal") else "misc"), own), SOURCE)]
    )
    return key


def added(entry: BibEntry) -> dict[str, str] | None:
    """When and by whom a work was added by hand, or None for one gathered from a document."""
    raw = entry.fields.get(ADDED, "").strip()
    if not raw:
        return None
    when, _, who = raw.partition(", ")
    return {"when": when.strip(), "who": who.strip()}


def _block(text: str, key: str) -> tuple[int, int] | None:
    """Where the entry `key` stands in the bibliography's text, its `% from` line and the blank line before it included."""
    m = re.search(r"@\s*\w+\s*\{\s*" + re.escape(key) + r"\s*,", text)
    if m is None:
        return None
    brace = text.index("{", m.start())
    end = match_group(text, brace, "{", "}")
    if end < 0:
        return None
    start = m.start()
    before = text.rfind("\n", 0, start - 1) + 1 if start else 0
    if text[before:start].startswith("% from"):
        start = before
        if start > 0 and text[start - 1] == "\n" and text[max(0, start - 2)] == "\n":
            start -= 1
    if end < len(text) and text[end] == "\n":
        end += 1
    return start, end


def remove_entry(result: ScanResult, key: str, who: str) -> str:
    """Take a work added by hand out of the library, while nothing cites it, and say what was done.

    Its entry leaves the bibliography. A document stored for it is set aside, as `loom library ignore` sets one aside, so gathering does not offer it an entry again; nothing is deleted from the store.

    Raises
    ------
    NotRemovable
        No such work, a work gathered from a document, or one a document cites.
    """
    from loom.refs.build import cited_counts
    from loom.refs.fetch import work_dir
    from loom.refs.pages import sha256_of
    from loom.refs.unreadable import declare

    root = result.quilt.root
    path = root / BIBLIOGRAPHY
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    entry = parse_bib(text).get(key)
    if entry is None:
        raise NotRemovable("no-such-work", f"the library has no work {key}")
    if added(entry) is None:
        raise NotRemovable("not-added", f"{key} comes from a document's bibliography; remove it there")
    citing = cited_counts(result).get(key, 0)
    if citing:
        raise NotRemovable(
            "cited",
            f"{key} is cited by {citing} result{'s' if citing != 1 else ''} of yours; remove the citations first",
        )
    where = _block(text, key)
    if where is None:
        raise NotRemovable("no-such-work", f"the library's entry for {key} could not be found in {BIBLIOGRAPHY}")
    paper = Path(work_dir(root, entry)) / "paper.pdf"
    if paper.is_file():
        declare(root, "forget", key, "removed from the library in the viewer", who, sha256=sha256_of(paper))
    path.write_text(text[: where[0]] + text[where[1] :], encoding="utf-8")
    return f"removed {key} from the library" + (", its stored paper set aside" if paper.is_file() else "")
