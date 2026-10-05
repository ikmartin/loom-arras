"""What a document is, read off the document itself (book 8.14): the signals a pile of PDFs is matched by, and the rule `loom library add` files on.

**A match is strong only when the document says so plainly**: an identifier on its first pages equals the entry's, or its whole title is the entry's and the entry's first author leads its byline. Anything weaker is a guess and is skipped with its reason, because a wrong PDF filed against the right entry is worse than an unfiled one: the corpus this was built against has 25 files for 22 entries, eleven of which match nothing at all, and two weak signals once filed "Logarithmic geometry and moduli" as Olsson's 2003 paper.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from loom.refs.fetch import ARRIVAL, title_ratio
from loom.refs.identity import declared, identify
from loom.refs.pages import page_texts, sha256_of
from loom.refs.resolve import _fold, query_for
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


#: How strongly a document names an entry: an identifier on its pages outranks its title and byline.
IDENTIFIER, TITLE_AND_AUTHOR = 2, 1
#: What separates one name of a byline from the next.
_NAMES = re.compile(r",|;|&|·|\band\b|\s{3,}", re.I)


@dataclass
class Strong:
    """One entry a document names plainly, how strongly, and the evidence in words."""

    citekey: str
    strength: int
    how: str


@dataclass
class Identity:
    """What one document shows it is: every entry it names plainly, strongest first, and why its nearest weaker guess is not one."""

    path: Path
    strong: list[Strong] = field(default_factory=list)
    #: Why nothing matched plainly, naming the nearest entry when there is one; '' when something did.
    weak: str = ""
    #: That nearest entry's citekey, '' when there is none.
    nearest: str = ""
    #: The evidence read, kept for `shortfall`: page one's lines, folded, and the identifiers on the first pages.
    lines: list[str] = field(default_factory=list)
    dois: set[str] = field(default_factory=set)
    arxivs: set[str] = field(default_factory=set)
    #: For a LaTeX source: its own `\\title` and first `\\author`, '' where it declares none.
    title: str = ""
    author: str = ""
    kind: str = "pdf"

    def of(self, citekey: str) -> Strong | None:
        """The strong match naming `citekey`, or None."""
        return next((m for m in self.strong if m.citekey == citekey), None)

    def best(self) -> list[Strong]:
        """The entries tied at the top strength: one is a match, two or more are a tie a person settles."""
        top = self.strong[0].strength if self.strong else 0
        return [m for m in self.strong if m.strength == top]

    def refusal_for(self, citekey: str, entry: BibEntry) -> str:
        """Why this document is not `citekey`'s, or '' when nothing says it is not: the check `add --for` runs.

        A PDF must name the work plainly. A LaTeX source is held to the arrival check a fetched one passes: its own `\\title` must not be another work's, since a source that declares none cannot be checked and is kept. Either way, a document naming another entry more strongly is that entry's.
        """
        mine = self.of(citekey)
        other = next((m for m in self.strong if m.citekey != citekey), None)
        if other is not None and (mine is None or other.strength > mine.strength):
            return f"it is {other.citekey}'s: {other.how}"
        if mine is not None:
            return ""
        if self.kind == "source":
            if self.title and title_ratio(str(entry.fields.get("title") or ""), self.title) < ARRIVAL:
                return f"its \\title is {self.title!r}, not {citekey}'s"
            return ""
        return f"it does not show it is {citekey}: " + shortfall(self, entry)


def _title_span(folded: list[str], title: str) -> tuple[int, int] | None:
    """Where on page one a title is set whole, over one to three lines: (first line, line after it)."""
    for i in range(len(folded)):
        for k in (1, 2, 3):
            if i + k <= len(folded) and " ".join(folded[i : i + k]) == title:
                return i, i + k
    return None


#: An affiliation mark set after a name: a digit, `*`, a dagger, or a superscript, which the text layer prints inline.
_MARKS = re.compile(r"[0-9*†‡§¶⁰¹²³⁴⁵⁶⁷⁸⁹ᵃ-ᵿ]+")


def _leader(line: str) -> str:
    """The first name of a byline: what precedes the first comma, `and` or `&`, folded.

    Affiliation marks go first, and the commas they leave stray (`K. Behrend1 , B. Fantechi2`, `, B. Fantechi`), so the first name is read as the byline prints it.
    """
    line = _MARKS.sub(" ", re.sub(r"^\s*by\s+", "", line, flags=re.I))
    line = re.sub(r"(?:\s*,)+", ",", line).strip(" ,")
    return _fold(_NAMES.split(line)[0])


def _first_surname(entry: BibEntry) -> str:
    names = query_for(entry).surnames
    return _fold(names[0]) if names else ""


#: A line the text layer sets between a title and its byline that is not a name: arXiv's margin stamp.
_STAMP = re.compile(r"^arXiv:\S+\s*\[", re.I)
#: A line that is one name and nothing else, as a byline set one name a line prints it.
_ONE_NAME = re.compile(r"^(?:[A-Z][\w'’.-]*\.?\s+){1,3}[A-Z][\w'’-]+$")


def _named_first(surname: str, line: str) -> bool:
    """Whether `surname` (folded) is the first name of byline `line`: its words, or with the text layer's stray spaces closed up (`M at th i e u Rom ag n y`)."""
    leader = _leader(line)
    if f" {surname} " in f" {leader} ":
        return True
    # closed up only where the layer did split the letters: three fragments of a name, not one initial
    spaced = sum(1 for w in leader.split() if len(w) <= 2) >= 3
    return spaced and len(surname) >= 4 and leader.replace(" ", "").endswith(surname.replace(" ", ""))


def _leads(identity: Identity, entry: BibEntry, span: tuple[int, int] | None) -> bool:
    """Whether the entry's first author leads the byline beside its title.

    The byline is the line after the title, past an arXiv stamp; else the line before it, or the first of a run of lines above it that each hold one name.
    """
    surname = _first_surname(entry)
    if not surname:
        return False
    if identity.kind == "source":
        return _named_first(surname, identity.author)
    if span is None:
        return False
    lines = identity.lines
    after = span[1]
    while after < len(lines) and _STAMP.match(lines[after]):
        after += 1
    near = [lines[after]] if after < len(lines) else []
    if span[0] > 0:
        near.append(lines[span[0] - 1])
        top = span[0]
        while top > 0 and _ONE_NAME.match(lines[top - 1]):
            top -= 1
        if top < span[0] - 1:
            near.append(lines[top])
    return any(_named_first(surname, line) for line in near)


def shortfall(identity: Identity, entry: BibEntry) -> str:
    """What the document lacks to be `entry`'s plainly, in words: the reason a weak match is skipped or an `add --for` refused."""
    title = _fold(str(entry.fields.get("title") or ""))
    surname = _first_surname(entry)
    shown = query_for(entry).surnames[0] if query_for(entry).surnames else "its first author"
    if identity.kind == "source":
        span: tuple[int, int] | None = (0, 0) if title and _fold(identity.title) == title else None
    else:
        span = _title_span([_fold(x) for x in identity.lines], title) if title else None
    problems = []
    if span is None:
        problems.append(f"its title is not {entry.key}'s in full")
    if not surname:
        problems.append(f"{entry.key} names no author to look for in its byline")
    elif not _leads(identity, entry, span):
        named = surname and (
            surname in _fold(_MARKS.sub(" ", identity.author)).split()
            or any(surname in _fold(_MARKS.sub(" ", x)).split() for x in identity.lines[:TOP_LINES])
        )
        problems.append(f"{shown} does not lead its byline" if named else f"{shown} is not in its byline")
    return " and ".join(problems) if problems else "it names the work only weakly"


def _strong(identity: Identity, bib: dict[str, BibEntry]) -> list[Strong]:
    """Every entry the document names plainly, strongest first, then by citekey."""
    found: list[Strong] = []
    folded = [_fold(x) for x in identity.lines]
    for ck, entry in bib.items():
        hit = None
        for wid in declared(entry):
            value = wid.value.lower()
            if wid.scheme == "doi" and value in identity.dois:
                hit = Strong(ck, IDENTIFIER, f"doi:{wid.value} is on its first pages")
            elif wid.scheme == "arxiv" and value.split("v")[0] in {a.split("v")[0] for a in identity.arxivs}:
                hit = Strong(ck, IDENTIFIER, f"arXiv:{wid.value} is on its first pages")
            if hit:
                break
        title = _fold(str(entry.fields.get("title") or ""))
        if hit is None and title:
            if identity.kind == "source":
                span: tuple[int, int] | None = (0, 0) if _fold(identity.title) == title else None
            else:
                span = _title_span(folded, title)
            if span is not None and _leads(identity, entry, span):
                hit = Strong(
                    ck,
                    TITLE_AND_AUTHOR,
                    f"its title is the entry's and {query_for(entry).surnames[0]} leads its byline",
                )
        if hit:
            found.append(hit)
    found.sort(key=lambda m: (-m.strength, m.citekey))
    return found


def identify_document(pdf: Path, bib: dict[str, BibEntry]) -> Identity:
    """What a PDF shows it is, by the rule in the module docstring; reads the file and nothing else.

    Parameters
    ----------
    pdf : Path
        The document.
    bib : dict of str to BibEntry
        The bibliography, by citekey.

    Returns
    -------
    Identity
        Every entry it names plainly, strongest first; with none, `weak` says why its nearest guess falls short.

    See Also
    --------
    identify_source : the same for a LaTeX source.
    look_at : the weaker signals a guess is made of.
    """
    out = Identity(path=pdf)
    try:
        pages = page_texts(pdf)
    except Exception:  # noqa: BLE001 -- an unreadable PDF is skipped with its reason, never a crash
        out.weak = "its text cannot be read: no text layer, or no pdftotext"
        return out
    out.dois, out.arxivs = identifiers_in("\n".join(pages[:2]))
    out.lines = [" ".join(x.split()) for x in (pages[0] if pages else "").splitlines()[:TOP_LINES] if x.strip()]
    out.strong = _strong(out, bib)
    if not out.strong:
        guess, _score, sigs = look_at(pdf, bib).best()
        out.nearest = guess
        named = ", ".join(sorted({*out.dois, *(f"arXiv:{a}" for a in out.arxivs)}))
        out.weak = (
            f"{guess} is the nearest entry, on {', '.join(s.kind for s in sigs)}, but {shortfall(out, bib[guess])}"
            if guess
            else f"it names {named}, which no entry states"
            if named
            else "nothing in the bibliography matches it"
        )
    return out


def identify_stored(home: Path, bib: dict[str, BibEntry]) -> Identity | None:
    """What a stored PDF shows it is, read from the page text the store recorded rather than from the PDF; None when no page one was recorded.

    The rule is `identify_document`'s; `weak` is left empty, since `shortfall` says what one entry lacks.
    """
    from loom.refs.pages import read_page

    first = read_page(home, 1)
    if first is None:
        return None
    out = Identity(path=home / "paper.pdf")
    out.dois, out.arxivs = identifiers_in(first + "\n" + (read_page(home, 2) or ""))
    out.lines = [" ".join(x.split()) for x in first.splitlines()[:TOP_LINES] if x.strip()]
    out.strong = _strong(out, bib)
    return out


def identify_source(path: Path, bib: dict[str, BibEntry]) -> Identity:
    """What a LaTeX source shows it is: its own `\\title` whole, with the entry's first author leading its first `\\author`.

    `path` is a `.tex` file or a directory of them; an arXiv source carries no identifier of its own, so title and byline are the only evidence.
    """
    from loom.refs.fetch import source_title

    files = [path] if path.is_file() else sorted(path.rglob("*.tex"))[:40]
    out = Identity(path=path, kind="source")
    if path.is_file():
        out.title = _declared(path, "title")
    else:
        out.title = source_title(path)
    out.author = next((a for f in files if (a := _declared(f, "author"))), "")
    out.strong = _strong(out, bib)
    if not out.strong:
        guess = max(
            (ck for ck, e in bib.items() if out.title and e.fields.get("title")),
            key=lambda ck: title_ratio(str(bib[ck].fields.get("title") or ""), out.title),
            default="",
        )
        out.weak = (
            "it declares no \\title to match"
            if not out.title
            else f"{guess} is the nearest entry, but {shortfall(out, bib[guess])}"
            if guess
            else "nothing in the bibliography matches it"
        )
    return out


def _declared(path: Path, command: str) -> str:
    """The argument of the first `\\title` or `\\author` in one file, '' when it has none."""
    from loom.refs.fetch import _balanced

    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
    except OSError:
        return ""
    m = re.search(r"\\" + command + r"\s*(?:\[[^\]]*\])?\s*\{", text)
    return _balanced(text, m.end() - 1).strip() if m else ""
