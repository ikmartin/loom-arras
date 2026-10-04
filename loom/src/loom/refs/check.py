"""What `loom library check` finds wrong with the library (plan 0.18.5): verified anchors that moved, documents that are another work's, digests with no results, section maps that are a guess, and entries sharing one document.

Each finder reads and never writes, and returns `Problem` rows the command groups by `kind`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from loom.scan.bib import BibEntry


@dataclass(frozen=True)
class Problem:
    """One thing wrong: its kind (a key of the command's headings), what it is about, and why."""

    kind: str
    key: str
    why: str
    work: str = ""


def recorded_works(root: Path) -> list[str]:
    """Every citekey with a `digests/<ck>.results.json`, in order."""
    return [p.name[: -len(".results.json")] for p in sorted((root / "digests").glob("*.results.json"))]


def moved_anchors(root: Path, bib: dict[str, BibEntry], works: Iterable[str]) -> tuple[int, list[Problem]]:
    """(how many verified anchors were re-read, those that no longer read as recorded).

    A mechanical result is its own source and is skipped, and so is a verified node's LaTeX: that rendering was judged by a person once, and re-judging it mechanically would claim a check that does not exist.
    """
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map, read_pages
    from loom.refs.proposals import VERIFIED, load_results, locate_quote
    from loom.refs.search import find_in_page

    out: list[Problem] = []
    checked = 0
    for ck in works:
        if ck not in bib:
            continue
        home = work_dir(root, bib[ck])
        m = read_map(home)
        for rid, r in load_results(root, ck).items():
            if r.state != VERIFIED or r.cls == "mechanical":
                continue
            if r.anchor.kind == "tex" and r.anchor.path:
                checked += 1
                try:
                    text = (root / r.anchor.path).read_bytes().decode("utf-8", "surrogateescape")
                except OSError:
                    out.append(Problem("file-gone", rid, f"{r.anchor.path} is not here", ck))
                    continue
                if locate_quote(text, r.source_text) is None:
                    out.append(Problem("transcription-changed", rid, f"{r.anchor.path} no longer reads that way", ck))
                continue
            if r.anchor.kind != "pdf" or not r.anchor.page:
                continue
            checked += 1
            if m is None:
                out.append(Problem("no-page-text", rid, "its work has no page text", ck))
                continue
            if m.sha256 and r.anchor.sha256 and m.sha256 != r.anchor.sha256:
                out.append(Problem("version_mismatch", rid, "the document is not the one this was read from", ck))
                continue
            # the whole span: a verified statement over a page break is re-read over both pages, not its first
            page = read_pages(home, r.anchor.page, max(r.anchor.page, r.anchor.last))
            if page is None:
                out.append(Problem("page-gone", rid, f"p.{r.anchor.page} is no longer there", ck))
            elif not find_in_page(page, r.source_text):
                out.append(Problem("transcription-changed", rid, f"p.{r.anchor.page} no longer reads that way", ck))
    return checked, out


def _title_score(title: str, first_page: str) -> float:
    """How well page one carries `title`, scored as the arrival check (`fetch.carries_title`) scores it."""
    from loom.refs.fetch import title_ratio
    from loom.refs.ingest import title_lines

    return max((title_ratio(title, line) for line in title_lines(first_page)), default=0.0)


def wrong_documents(root: Path, bib: dict[str, BibEntry], works: Iterable[str]) -> list[Problem]:
    """Stored PDFs whose first page does not carry their own entry's title: another entry's (`wrong-document`), or none (`unconfirmed-document`).

    Read from the recorded page text, so a work never mapped is not checked; an entry with no title has nothing to compare.
    """
    from loom.refs.fetch import work_dir
    from loom.refs.ingest import TITLE_MATCH
    from loom.refs.pages import read_page

    out: list[Problem] = []
    for ck in works:
        entry = bib.get(ck)
        title = str(entry.fields.get("title") or "") if entry else ""
        if entry is None or not title:
            continue
        home = work_dir(root, entry)
        first = read_page(home, 1) if (home / "paper.pdf").is_file() else None
        if not first or _title_score(title, first) >= TITLE_MATCH:
            continue
        others = [
            (_title_score(str(e.fields["title"]), first), other)
            for other, e in bib.items()
            if other != ck and e.fields.get("title")
        ]
        best, other = max(others, default=(0.0, ""))
        if best >= TITLE_MATCH:
            out.append(Problem("wrong-document", ck, f"its PDF's first page carries {other}'s title", ck))
        else:
            out.append(Problem("unconfirmed-document", ck, "its PDF's first page does not carry its title", ck))
    return out


def empty_digests(root: Path, works: Iterable[str]) -> list[Problem]:
    """Works with a `digests/<ck>.tex` and no result recorded for it."""
    from loom.refs.proposals import digest_path, load_results

    return [
        Problem("empty-digest", ck, "its digest records no results", ck)
        for ck in works
        if digest_path(root, ck).is_file() and not load_results(root, ck)
    ]


def guessed_maps(root: Path, bib: dict[str, BibEntry], works: Iterable[str]) -> list[Problem]:
    """Section maps `PageMap.suspect` calls a guess: far too few sections for the document's length."""
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map

    out: list[Problem] = []
    for ck in works:
        if ck not in bib:
            continue
        m = read_map(work_dir(root, bib[ck]))
        if m is not None and m.suspect:
            out.append(Problem("guessed-map", ck, f"{len(m.sections)} sections found in {m.pages} pages", ck))
    return out


def duplicate_documents(bib: dict[str, BibEntry], works: Iterable[str] | None = None) -> list[Problem]:
    """Entries that name one stored document by `loom-file` (`scan._duplicates`); with `works`, those touching one of them."""
    from loom.refs.scan import _duplicates

    wanted = set(works) if works is not None else None
    return [
        Problem("duplicate-document", ", ".join(keys), f"{len(keys)} entries name one document", keys[0])
        for _source, keys in _duplicates(bib)
        if wanted is None or wanted & set(keys)
    ]
