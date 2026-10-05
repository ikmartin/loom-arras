"""What `loom library check` finds wrong with the library (plan 0.18.5): verified anchors that moved, documents that are another work's, digests with no results, section maps that are a guess, and entries sharing one document.

Each finder reads and never writes, and returns `Problem` rows the command groups by `kind`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from loom.scan.bib import BibEntry
from loom.scan.model import Diagnostic
from loom.scan.scan import ScanResult

#: A `(stage, item, n, total)` callback, as `cli.report.Progress.told` takes one.
OnProgress = Callable[[str, str, int, int], None]


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
    """(how many person-verified anchors were re-read, those that no longer read as recorded).

    A mechanical result is its own source and is skipped, verified or not, and so is a verified node's LaTeX: that rendering was judged by a person once, and re-judging it mechanically would claim a check that does not exist. A quotation no longer on its page is not moved when the author verified it again against the page as it now reads (`proposals.read_at_verify`).
    """
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map
    from loom.refs.proposals import (
        VERIFIED,
        anchored_text,
        load_results,
        locate_quote,
        read_at_verify,
        state_of,
        text_sha,
    )
    from loom.refs.search import find_in_page

    out: list[Problem] = []
    checked = 0
    for ck in works:
        if ck not in bib:
            continue
        home = work_dir(root, bib[ck])
        m = read_map(home)
        for rid, r in load_results(root, ck).items():
            if state_of(r) != VERIFIED or r.cls == "mechanical":
                continue
            if r.anchor.kind == "tex" and r.anchor.path:
                checked += 1
                text = anchored_text(root, home, r)
                if text is None:
                    out.append(Problem("file-gone", rid, f"{r.anchor.path} is not here", ck))
                elif locate_quote(text, r.source_text) is None and read_at_verify(r) != text_sha(text):
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
            page = anchored_text(root, home, r)
            if page is None:
                out.append(Problem("page-gone", rid, f"p.{r.anchor.page} is no longer there", ck))
            elif not find_in_page(page, r.source_text) and read_at_verify(r) != text_sha(page):
                # a page the author re-read and verified against as it now reads is not moved
                out.append(Problem("transcription-changed", rid, f"p.{r.anchor.page} no longer reads that way", ck))
    return checked, out


def _title_score(title: str, first_page: str) -> float:
    """How well page one carries `title`, scored as the arrival check (`fetch.carries_title`) scores it."""
    from loom.refs.fetch import title_ratio
    from loom.refs.ingest import title_lines

    return max((title_ratio(title, line) for line in title_lines(first_page)), default=0.0)


def wrong_documents(
    root: Path, bib: dict[str, BibEntry], works: Iterable[str], *, progress: OnProgress | None = None
) -> list[Problem]:
    """Stored PDFs that fail the strong match for their own entry (`ingest.identify_stored`): another entry's (`wrong-document`), or not shown to be the work (`unconfirmed-document`).

    Another entry's when it names that entry plainly, or carries that entry's title and not its own; a version of the same work is never another's. Read from the recorded page text, so a work never mapped is not checked, and a work whose document the author set aside is not checked either.
    """
    from loom.refs.fetch import work_dir
    from loom.refs.ingest import TITLE_MATCH, identify_stored, shortfall
    from loom.refs.pages import read_page
    from loom.refs.scan import primary_of
    from loom.refs.unreadable import declarations

    tops = primary_of(bib)
    aside = declarations(root, "forget")
    out: list[Problem] = []
    listed = list(works)
    for i, ck in enumerate(listed, 1):
        if progress is not None:
            progress("checking documents", ck, i, len(listed))
        entry = bib.get(ck)
        if entry is None or ck in aside:
            continue
        home = work_dir(root, entry)
        if not (home / "paper.pdf").is_file():
            continue
        identity = identify_stored(home, bib)
        if identity is None:
            continue
        work = tops.get(ck, ck)
        mine = identity.of(ck)
        other = next((m for m in identity.strong if tops.get(m.citekey, m.citekey) != work), None)
        if other is not None and (mine is None or other.strength > mine.strength):
            out.append(Problem("wrong-document", ck, f"it is {other.citekey}'s: {other.how}", ck))
            continue
        if mine is not None or any(tops.get(m.citekey, m.citekey) == work for m in identity.strong):
            continue
        first = read_page(home, 1) or ""
        title = str(entry.fields.get("title") or "")
        theirs = [
            (_title_score(str(e.fields["title"]), first), key)
            for key, e in bib.items()
            if tops.get(key, key) != work and e.fields.get("title")
        ]
        best, named = max(theirs, default=(0.0, ""))
        if best >= TITLE_MATCH and (not title or _title_score(title, first) < TITLE_MATCH):
            out.append(Problem("wrong-document", ck, f"its PDF's first page carries {named}'s title", ck))
        else:
            out.append(
                Problem(
                    "unconfirmed-document", ck, f"it does not show it is the work: {shortfall(identity, entry)}", ck
                )
            )
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


def duplicate_documents(
    root: Path, bib: dict[str, BibEntry], works: Iterable[str] | None = None, *, progress: OnProgress | None = None
) -> list[Problem]:
    """Entries holding one document, once per work; with `works`, those touching one of them.

    Two kinds, merged by work: entries naming one stored document by `loom-file` (`scan._duplicates`), and versions of a work whose stored PDFs are copies of each other by the filing rule (`scan.same_document`), which an earlier loom filed as versions. An entry the author set aside (`library ignore`) is the cleared copy and is left out.
    """
    from loom.refs.scan import _duplicates, _own_account, primary_of, same_document, stored_versions, versions_of
    from loom.refs.unreadable import declarations

    aside = set(declarations(root, "forget"))
    tops = primary_of(bib)
    keys: dict[str, set[str]] = {}
    why: dict[str, list[str]] = {}
    for _source, named in _duplicates(bib, aside):
        work = tops.get(named[0], named[0])
        keys.setdefault(work, set()).update(named)
        why.setdefault(work, []).append(f"{len(named)} entries name one document")
    tops_with_versions = list(versions_of(bib))
    for n, top in enumerate(tops_with_versions, 1):
        if progress is not None:
            progress("comparing versions", top, n, len(tops_with_versions))
        stored = [(e, p) for e, p in stored_versions(root, bib, top) if p.is_file() and e.key not in aside]
        for i, (entry, path) in enumerate(stored):
            same, reason = same_document(path, _own_account(path)[0], stored[:i])
            if same:
                keys.setdefault(top, set()).update({same, entry.key})
                why.setdefault(top, []).append(f"{entry.key} is a copy of {same}'s document: {reason}")
    wanted = set(works) if works is not None else None
    return [
        Problem("duplicate-document", ", ".join(sorted(ks)), "; ".join(why[work]), work)
        for work, ks in sorted(keys.items())
        if wanted is None or wanted & ks
    ]


def uncited_lint(result: ScanResult, diags: Iterable[Diagnostic], works: Iterable[str]) -> list[Problem]:
    """Works nothing cites whose digest lint finds wrong, each with its count by severity (`cli.diagnostics.Owners`).

    `diags` is what `loom lint` reports, so the counts are the ones its single line for these works sums; no exit code counts them, so this is the one place they are listed by work.
    """
    from loom.cli.diagnostics import UNCITED, Owners
    from loom.cli.report import counted

    owners = Owners(result)
    wanted = set(works)
    per: dict[str, list[str]] = {}
    for d in diags:
        if owners.of(d) == UNCITED:
            for ck in owners.works(d) & wanted:
                per.setdefault(ck, []).append(d.severity)
    out: list[Problem] = []
    for ck, severities in sorted(per.items()):
        said = ", ".join(counted(severities.count(s), s) for s in ("error", "warning", "info") if s in severities)
        out.append(Problem("uncited-lint", ck, f"lint finds {said}", ck))
    return out
