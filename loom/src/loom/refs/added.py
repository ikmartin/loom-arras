"""Works a person adds to the library by hand (plan 0.24.2), written into loom's own bibliography marked `loom-added`, and deleting a work from the library.

The bibliography is loom's file, `.loom/digests/bibliography.bib`, never a document's `.bib`: gathering appends what the documents cite, and an added work is appended beside them. An entry a person corrected by hand is never removed; one loom wrote for a work added here may be, since nothing of the person's is in it.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Mapping
from pathlib import Path

from loom.clock import stamp
from loom.paths import BUILD
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


class NotDeletable(Exception):
    """A work that cannot be deleted from the library now, with the code the API answers: `no-such-work`, `from-document`, `cited`."""

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


def added_entry(key: str, fields: Mapping[str, str], who: str, etype: str = "", source: str = SOURCE) -> Candidate:
    """The entry a work added by hand is written as: `loom-added` says when and by whom, and its other `loom-*` fields are kept as given."""
    own = {k: v for k, v in fields.items() if v}
    own[ADDED] = f"{stamp()}, {who}" if who else stamp()
    return Candidate(key, entry_text(key, etype or ("article" if own.get("journal") else "misc"), own), source)


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
    append_entries(quilt, [added_entry(key, own, who, etype)])
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


def delete_work(result: ScanResult, key: str, who: str) -> str:
    """Delete a work from the library for good, and say what was done.

    Its entry leaves the bibliography, and loom's copy of its document, its page text, its overview and its digest with every result in it leave the store. A primary goes with its versions; a version goes alone. Refused while a document cites it or carries its entry, since gathering would bring it straight back.

    Parameters
    ----------
    result : ScanResult
        The quilt's scan.
    key : str
        The work's citekey.
    who : str
        The author, as the record of any relation removed names them.

    Returns
    -------
    str
        What was deleted, in words.

    Raises
    ------
    NotDeletable
        No such work, one a document's bibliography carries, or one a document cites.
    """
    from loom.refs.build import cited_counts
    from loom.refs.scan import ScanReport, candidates, versions_of

    root = result.quilt.root
    path = root / BIBLIOGRAPHY
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    entries = parse_bib(text)
    if key not in entries:
        raise NotDeletable("no-such-work", f"the library has no work {key}")
    doomed = [key, *versions_of(entries).get(key, [])]
    carried = candidates(result, ScanReport(dry_run=True))
    cited = cited_counts(result)
    for k in doomed:
        if k in carried:
            raise NotDeletable(
                "from-document", f"{k} comes from {carried[k].source}; remove it there, or gathering brings it back"
            )
        if cited.get(k):
            n = cited[k]
            raise NotDeletable(
                "cited", f"{k} is cited by {n} result{'s' if n != 1 else ''} of yours; remove the citations first"
            )
        if _block(text, k) is None:
            raise NotDeletable("no-such-work", f"the library's entry for {k} could not be found in {BIBLIOGRAPHY}")
    held = False
    for k in doomed:
        held = _delete_held(root, k, entries, doomed, who) or held
    # the entries last: what fails before here leaves a work that can be deleted again
    for k in doomed:
        where = _block(text, k)
        assert where is not None
        text = text[: where[0]] + text[where[1] :]
    path.write_text(text, encoding="utf-8")
    also = f" and its {'copy' if len(doomed) == 2 else 'copies'} {', '.join(doomed[1:])}" if doomed[1:] else ""
    return f"deleted {key}{also} from the library" + (", with loom's copy of the PDF" if held else "")


def _delete_held(root: Path, key: str, entries: Mapping[str, BibEntry], doomed: list[str], who: str) -> bool:
    """Everything loom holds for `key` but its entry; whether a store directory went.

    A directory another standing entry also names stays, and so does one a hand-written `loom-file` places outside the store. Relations at its results are removed and recorded; the claims about it are withdrawn.
    """
    from loom.refs.fetch import FetchRefused, work_dir
    from loom.refs.links import read_links, record_removal, remove_link
    from loom.refs.pages import sha256_of, storage_root
    from loom.refs.proposals import digest_path, load_results, log_path, proposed_path, results_path
    from loom.refs.scan import drop_copies
    from loom.refs.unreadable import KINDS, declarations, declare

    ids = set(load_results(root, key))
    for link in [x for x in read_links(root) if {x.frm, x.to} & ids]:
        record_removal(root, remove_link(root, link.id), who, f"{key} deleted from the library")
    for made in (digest_path, proposed_path, results_path, log_path):
        made(root, key).unlink(missing_ok=True)
    for kind in KINDS:
        if key in declarations(root, kind):
            declare(root, kind, key, "deleted from the library", who, undo=True)

    def home_of(entry: BibEntry) -> Path | None:
        try:
            return work_dir(root, entry)
        except FetchRefused:
            return None

    home = home_of(entries[key])
    store = storage_root(root).resolve()
    inside = home is not None and home.resolve() != store and home.resolve().is_relative_to(store)
    shared = any(home_of(e) == home for k, e in entries.items() if k not in doomed)
    goes = inside and not shared and home is not None and home.is_dir()
    hashes = drop_copies(root, key, home if goes else None)
    if goes and home is not None:
        paper = home / "paper.pdf"
        if paper.is_file():
            hashes.append(sha256_of(paper))
        shutil.rmtree(home)
    for sha in hashes:
        if re.fullmatch(r"[0-9a-f]{64}", sha):
            shutil.rmtree(root / BUILD / "uploads" / sha, ignore_errors=True)
    return goes
