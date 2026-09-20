"""Matching a pile of PDFs to the bibliography (plan 0.12 §10 stage 8, §12.2).

Last in the build order, because a quilt's PDFs arrive a few at a time through `loom refs add` and `loom refs fetch`, so this is a convenience rather than the path. It is still worth having: the corpus this was built against has 25 files for 22 entries, of which 11 match nothing at all -- background reading, and the author's own paper -- so the interesting behaviour is refusing, not matching.

Three signals, cheapest first, and **two agreeing signals attach**. Everything else goes to `loom refs match` with its evidence. The threshold is a default rather than a finding: §12.2 leaves it open until someone scores a real pile by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from loom.refs.fetch import title_ratio
from loom.refs.identity import identify
from loom.refs.pages import page_texts, sha256_of
from loom.refs.resolve import query_for
from loom.scan.bib import BibEntry

_DOI = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b")
_ARXIV = re.compile(r"arXiv[:\s]\s*(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)", re.I)
# A title on page one: the longest early line that is not a running head, a date or an author list.
_NOT_TITLE = re.compile(r"^\s*(abstract|introduction|contents|arxiv|doi|vol\.|\d+\s*$|by\b)", re.I)
#: How alike two titles must be for either title signal to fire. Two of these agreeing is what attaches a PDF.
TITLE_MATCH = 0.75
#: How much of page one is the title block. Beyond it are the abstract and the first citations, and a paper that
#: cites another paper's title was being filed as that paper: Khan 2019 became Behrend-Fantechi 1997 this way.
TOP_LINES = 18
#: The characters of page one that hold the author block, for the same reason.
BYLINE_CHARS = 600
#: How far ahead of the runner-up the winner must be. Two papers whose titles differ by a subtitle score alike, and
#: filing the wrong one confidently is the failure this command exists to avoid, so a near-tie goes to a person.
MARGIN = 0.15


@dataclass
class Signal:
    """One piece of evidence that a PDF is a bibliography entry."""

    kind: str
    citekey: str
    strength: float
    detail: str = ""


@dataclass
class Candidate:
    """What one PDF looks like it is."""

    path: Path
    sha256: str
    pages: int = 0
    signals: list[Signal] = field(default_factory=list)

    def ranked(self) -> list[tuple[str, float, list[Signal]]]:
        """Every entry the signals named, best first."""
        by_key: dict[str, list[Signal]] = {}
        for s in self.signals:
            by_key.setdefault(s.citekey, []).append(s)
        rows = [(k, sum(s.strength for s in v), v) for k, v in by_key.items()]
        rows.sort(key=lambda r: (len(r[2]), r[1]), reverse=True)
        return rows

    def best(self) -> tuple[str, float, list[Signal]]:
        """(citekey, summed strength, the signals that named it) for the entry with most support; ('', 0, []) for none."""
        rows = self.ranked()
        return rows[0] if rows else ("", 0.0, [])

    @property
    def ambiguous(self) -> bool:
        """Whether a second entry is close enough behind that the winner is a guess."""
        rows = self.ranked()
        return len(rows) > 1 and rows[0][1] - rows[1][1] < MARGIN

    @property
    def attachable(self) -> bool:
        """Two agreeing signals, or one identifier read straight off the page -- and no close runner-up.

        An identifier is near-certain on its own. Titles are not: two papers whose titles differ by a subtitle both score highly against either, and a confident wrong filing is worse than an unfiled PDF.
        """
        _ck, _score, sigs = self.best()
        if any(s.kind in ("doi", "arxiv") for s in sigs):
            return True
        return len(sigs) >= 2 and not self.ambiguous


def title_lines(first_page: str) -> list[str]:
    """Lines near the top of page one that could be a title.

    Every plausible line is returned rather than one guess. Guessing picked the *longest* early line, which on a real paper is a paragraph of the abstract rather than the title, and the signal fired for nothing across a 25-paper corpus.
    """
    out: list[str] = []
    for line in first_page.splitlines()[:TOP_LINES]:
        s = " ".join(line.split())
        if 10 <= len(s) <= 140 and not _NOT_TITLE.match(s) and sum(c.isdigit() for c in s) <= 6:
            out.append(s)
    # a title set over two lines is one title
    return out + [f"{a} {b}" for a, b in zip(out, out[1:], strict=False) if len(a) + len(b) <= 140]


def filename_title(stem: str) -> str:
    """The title part of a filename like `Author and Author - 2019 - The Real Title`.

    Zotero and most reference managers write that shape, and comparing the whole stem to a title scores the authors and the year against nothing -- which is why two papers that *are* in the bibliography matched none of it.
    """
    m = re.match(r"^.{0,80}?\s-\s(?:\d{4}\s-\s)?(.+)$", stem)
    return (m.group(1) if m else stem).strip()


def identifiers_in(text: str) -> tuple[set[str], set[str]]:
    """(DOIs, arXiv ids) appearing in some text, lowercased for comparison."""
    dois = {m.group(0).rstrip(".,;)").lower() for m in _DOI.finditer(text)}
    arxivs = {m.group(1).lower() for m in _ARXIV.finditer(text)}
    return dois, arxivs


def look_at(pdf: Path, bib: dict[str, BibEntry]) -> Candidate:
    """Run every signal over one PDF; reads the file and nothing else, and never writes.

    Parameters
    ----------
    pdf : Path
        The file to identify.
    bib : dict
        The bibliography, by citekey.

    Returns
    -------
    Candidate
        What was found, with one `Signal` per piece of evidence.

    See Also
    --------
    Candidate.attachable : whether the evidence is enough to file it without asking.
    """
    out = Candidate(path=pdf, sha256=sha256_of(pdf))
    try:
        pages = page_texts(pdf)
    except Exception:  # noqa: BLE001 -- an unreadable PDF is a thing to report, not a thing to crash on
        return out
    out.pages = len(pages)
    head = "\n".join(pages[:2])
    dois, arxivs = identifiers_in(head)
    for ck, entry in bib.items():
        for wid in identify(entry):
            value = str(wid).split(":", 1)[-1].lower()
            if wid.scheme == "doi" and value in dois:
                out.signals.append(Signal("doi", ck, 1.0, value))
            elif wid.scheme == "arxiv" and value.split("v")[0] in {a.split("v")[0] for a in arxivs}:
                out.signals.append(Signal("arxiv", ck, 1.0, value))
    lines = title_lines(pages[0] if pages else "")
    from_name = filename_title(pdf.stem)
    byline = f"{pdf.stem} {(pages[0] if pages else '')[:BYLINE_CHARS]}".lower()
    for ck, entry in bib.items():
        want = str(entry.fields.get("title") or "")
        if not want:
            continue
        best_line, page_score = "", 0.0
        for line in lines:
            s = title_ratio(want, line)
            if s > page_score:
                best_line, page_score = line, s
        name_score = title_ratio(want, from_name)
        # the surname is what separates two papers whose titles differ only by a subtitle
        surnames = [s.lower() for s in query_for(entry).surnames[:2] if len(s) > 2]
        if surnames and surnames[0] in byline:
            out.signals.append(Signal("first-author", ck, 0.5, surnames[0]))
        if page_score >= TITLE_MATCH:
            out.signals.append(Signal("title-on-page", ck, round(page_score, 3), best_line[:60]))
        if name_score >= TITLE_MATCH:
            out.signals.append(Signal("title-in-filename", ck, round(name_score, 3), from_name[:60]))
    return out
