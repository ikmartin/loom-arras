"""Page text and the section map for a cited work's PDF (plan 0.12 §4.2, build stage 1).

Deterministic and eager: no model, no judgement, nothing to review. This is tier 1 of §3, so it is recomputed whenever the artifact changes and never ranked, queued or asked about.

**Plain text, not `-bbox-layout`.** Measured on this corpus: 2.2 KB a page plain against 59.7 KB with token geometry, which over a 600-page bibliography is 1.4 MB against 36.5 MB. The page text is committed so that a coauthor holding no PDF can still re-check an anchor (§4.2), and that only works if it is small. Geometry is written per page, on demand, the first time `loom refs locate` needs it.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

# A numbered heading: "3", "3.1", "A.2". A bare single capital is deliberately NOT a number -- "C (F ) = Spec Sym(F )"
# and "E = C x_D X" are lines from a real paper in this corpus, and a lone letter matches far more mathematics than
# it does appendices. An appendix is found by the word, or by a letter that carries a subsection number.
_NUMBERED = re.compile(r"^\s{0,8}(\d{1,2}(?:\.\d{1,2}){0,2}|[A-F]\.\d{1,2}(?:\.\d{1,2})?)\.?\s+([^\s\d].{2,120})\s*$")
_APPENDIX = re.compile(r"^\s{0,8}Appendix\s+([A-F])\b\.?\s*[:.]?\s*(.{0,70})\s*$", re.I)
_UNNUMBERED = re.compile(
    r"^\s{0,8}(Abstract|Introduction|Preliminaries|Notation|Conventions|Acknowledg(?:e)?ments|References|Bibliography)\s*$",
    re.I,
)
# Lines that look like headings but are results, figures or running heads: never a section.
_NOT_A_HEADING = re.compile(
    r"^\s*(theorem|lemma|proposition|corollary|definition|remark|example|proof|figure|table|equation|claim|conjecture|construction|notation|case|step)\b",
    re.I,
)
# A table-of-contents line: dot leaders, or a title that ends in whitespace and a page number. The contents page
# lists every heading in the paper, so a pass that takes it at face value puts the whole document on page 1.
_TOC_LINE = re.compile(r"(\.\s*){4,}|\u2026|\s\.{2,}\s*\d+\s*$|^\s*\S.*\s{3,}\d{1,3}\s*$")
# Mathematics in a line that otherwise parses as a heading.
_MATHY = re.compile(r"[=→←⇒⊗⊕×∈⊆∼≅∗†‡∫∑∏√≤≥≠±∞]|\\[a-zA-Z]+|\^|_\{|\$")


class MapRefused(Exception):
    """There is no PDF, or the toolchain cannot read it."""


@dataclass
class Section:
    """One heading found in the page text, and where it starts."""

    n: str
    title: str
    page: int


@dataclass
class PageMap:
    """What a deterministic pass got out of one work's PDF."""

    sha256: str
    pages: int
    sections: list[Section] = field(default_factory=list)
    chars: int = 0

    @property
    def suspect(self) -> bool:
        """A map with far too few sections for its length, which is a guess rather than a map.

        The detector is tuned on papers. Alper's 679-page lecture notes came out as seven "sections", every one a
        footnote or a sentence opening: early junk took the numbers 1 to 3 and the real chapters were then rejected as
        going backwards. A map like that is reported as unreliable rather than shown as the book's structure.
        """
        return self.pages >= 60 and len(self.sections) * 40 < self.pages

    def section_of(self, page: int) -> Section | None:
        """The last section to have started at or before `page`; None when nothing was detected before it."""
        found = None
        for s in self.sections:
            if s.page <= page:
                found = s
            else:
                break
        return found


#: Loom's own store of other people's documents (book 8.16): everything it fetched or copied, keyed by the work's identifier. The author's seed space is `refs/` at the quilt root, which loom reads and never writes.
STORAGE = "digests/storage"


def storage_root(root: Path) -> Path:
    """The quilt's document store."""
    return root / STORAGE


def sha256_of(path: Path) -> str:
    """The artifact's content hash, which is what an anchor names (digest contract §9.2)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _pdftotext(args: list[str]) -> str:
    try:
        proc = subprocess.run(["pdftotext", *args], capture_output=True, text=True, timeout=300, check=False)
    except FileNotFoundError as exc:
        raise MapRefused("pdftotext is not installed (it ships with poppler; `brew install poppler`)") from exc
    except subprocess.TimeoutExpired as exc:
        raise MapRefused("pdftotext did not finish within five minutes") from exc
    if proc.returncode != 0:
        raise MapRefused(f"pdftotext failed: {proc.stderr.strip()[:200]}")
    return proc.stdout


def page_texts(pdf: Path) -> list[str]:
    """Every page of `pdf` as plain text, in order.

    One subprocess for the whole document: pdftotext separates pages with a form feed, which is cheaper and more reliable than one invocation per page.
    """
    raw = _pdftotext(["-q", str(pdf), "-"])
    pages = raw.split("\f")
    # a trailing form feed leaves an empty final element that is not a page
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def token_boxes(pdf: Path, page: int) -> str:
    """The `-bbox-layout` XML for one page, for `loom refs locate`; written per page on demand, never in bulk (§4.2)."""
    return _pdftotext(["-q", "-bbox-layout", "-f", str(page), "-l", str(page), str(pdf), "-"])


def _clean_title(raw: str) -> str:
    """A heading's own words, with a run-in paragraph and any dot leaders cut off.

    Several papers here set headings run-in: "1 Introduction. The purpose of this paper is to prove..." is one line, so a title taken whole swallows the first sentence. The cut is the first sentence boundary -- a period, then a space, then a capital.
    """
    t = re.split(r"(?:\s*\.\s*){3,}", raw)[0]
    t = re.sub(r"\s{2,}\d{1,3}\s*$", "", t)
    m = re.search(r"\.\s+(?=[A-Z(])", t)
    if m:
        t = t[: m.start()]
    return t.strip().strip(".").strip()


def _plausible(title: str) -> bool:
    """Whether a cleaned title reads as a heading rather than as a line of mathematics."""
    if not (2 <= len(title) <= 70) or not title[0].isupper():
        return False
    if _MATHY.search(title) or _NOT_A_HEADING.match(title):
        return False
    return sum(c.isdigit() for c in title) <= 3


def _monotonic(found: list[Section]) -> list[Section]:
    """Keep only headings whose top-level number does not go backwards.

    A paper's sections count up. A "3.2" appearing before any "3", or a "0" two thirds of the way through, is a cross-reference, a running head or a fragment of a formula -- and this is the one filter that needs no guess about what a heading looks like.
    """
    out: list[Section] = []
    top = 0
    for s in found:
        if not s.n or not s.n[0].isdigit():
            out.append(s)
            continue
        head = int(s.n.split(".")[0])
        if head < top or head > top + 1:
            continue
        top = max(top, head)
        out.append(s)
    return out


def _candidates(text: str, page: int) -> list[Section]:
    """Every heading-shaped line on one page, before any cross-page filtering."""
    out: list[Section] = []
    seen: set[str] = set()
    for line in text.splitlines():
        if not line.strip() or _NOT_A_HEADING.match(line) or _TOC_LINE.search(line):
            continue
        m = _NUMBERED.match(line)
        if m:
            n, title = m.group(1), _clean_title(m.group(2))
            if n not in seen and _plausible(title):
                seen.add(n)
                out.append(Section(n=n, title=title, page=page))
            continue
        a = _APPENDIX.match(line)
        if a:
            key = f"App{a.group(1).upper()}"
            if key not in seen:
                seen.add(key)
                out.append(Section(n=a.group(1).upper(), title=_clean_title(a.group(2)) or "Appendix", page=page))
            continue
        u = _UNNUMBERED.match(line)
        if u and u.group(1).title() not in seen:
            seen.add(u.group(1).title())
            out.append(Section(n="", title=u.group(1).title(), page=page))
    return out


# A page carrying this many heading-shaped lines is the table of contents, which lists the whole paper. Believing
# it puts every section of a fifty-page paper on page 1 -- which is what the first version of this pass did.
CONTENTS_PAGE = 5


def _after_the_references(found: list[Section], pages: int) -> list[Section]:
    """Drop numbered headings that follow the reference list; a numbered bibliography reads exactly like a section list."""
    cut = 0
    for s in found:
        if not s.n and s.title in ("References", "Bibliography") and s.page > pages * 0.5:
            cut = s.page
    return [s for s in found if not (cut and s.n and s.page >= cut)]


def find_sections(pages: list[str]) -> list[Section]:
    """Headings across the whole document, in order, each with the page it starts on.

    Numbering and shape only, no font sizes: plain text carries no font information, and the numbering is what a section map is for -- turning "pages 210-240" into "chapter 4".

    Four things this corpus forced, each from a paper that broke the version before it: a contents page is skipped whole rather than line by line, a run-in heading is cut at its first sentence, a numbered bibliography entry after the reference list is not a section, and a heading whose top-level number goes backwards is dropped.
    """
    found: list[Section] = []
    seen: set[str] = set()
    for i, text in enumerate(pages, start=1):
        page_found = _candidates(text, i)
        if len(page_found) >= CONTENTS_PAGE:
            continue  # the contents page: it names every heading, and none of them start here
        for s in page_found:
            key = s.n or s.title
            if key in seen:
                continue
            seen.add(key)
            found.append(s)
    return _after_the_references(_monotonic(found), len(pages))


def write_map(home: Path, pdf: Path) -> PageMap:
    """Write `pages/NNNN.txt` and `sections.json` under `home`; returns what was found.

    Parameters
    ----------
    home : Path
        The work's directory under `refs/`.
    pdf : Path
        The artifact to read.

    Returns
    -------
    PageMap
        The artifact's hash, its page count and every heading found.

    See Also
    --------
    read_map : the same record, read back without the PDF.
    """
    pages = page_texts(pdf)
    out = home / "pages"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.txt"):
        old.unlink()
    chars = 0
    for i, text in enumerate(pages, start=1):
        body = text.strip("\n")
        (out / f"{i:04d}.txt").write_text(body + "\n", encoding="utf-8")
        chars += len(body)
    m = PageMap(sha256=sha256_of(pdf), pages=len(pages), sections=find_sections(pages), chars=chars)
    (home / "sections.json").write_text(
        json.dumps(
            {"sha256": m.sha256, "pages": m.pages, "chars": m.chars, "sections": [asdict(s) for s in m.sections]},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return m


def read_map(home: Path) -> PageMap | None:
    """The recorded map, or None when this work has never been mapped; never touches the PDF."""
    path = home / "sections.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PageMap(
            sha256=str(data.get("sha256", "")),
            pages=int(data.get("pages", 0)),
            chars=int(data.get("chars", 0)),
            sections=[
                Section(n=str(s.get("n", "")), title=str(s.get("title", "")), page=int(s["page"]))
                for s in data.get("sections", [])
            ],
        )
    except (OSError, ValueError, TypeError, KeyError):
        return None


def is_current(home: Path, pdf: Path) -> bool:
    """Whether the recorded map was made from the PDF that is there now; a changed artifact re-maps (§3's rule)."""
    m = read_map(home)
    return m is not None and bool(m.sha256) and m.sha256 == sha256_of(pdf)


def read_page(home: Path, page: int) -> str | None:
    """One page's recorded text, or None when it was never written; this is what an anchor is checked against."""
    path = home / "pages" / f"{page:04d}.txt"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


_FOLIO = re.compile(r"\s*\d{1,4}\s*")


def _drop_folio(rows: list[str], *, head: bool) -> list[str]:
    """`rows` without a printed page number among the first (head) or last two non-blank lines."""
    idx = [i for i, row in enumerate(rows) if row.strip()]
    edge = idx[:2] if head else idx[-2:]
    doomed = {i for i in edge if _FOLIO.fullmatch(rows[i])}
    return [row for i, row in enumerate(rows) if i not in doomed]


def read_pages(home: Path, first: int, last: int) -> str | None:
    """The recorded text of pages `first`..`last` as one text, or None when any of them was never written.

    At each join a line that is only a number, among the last two lines of a page or the first two of the next, is the book's printed folio and is dropped: a statement over a page break is quoted without it, and the study's quotation of Alper's Definition 7.5.5 matched only once the agent typed "345" into it. A lone number anywhere else on a page is content and stays; a single page comes back exactly as recorded.
    """
    texts = [read_page(home, n) for n in range(first, max(first, last) + 1)]
    if any(t is None for t in texts):
        return None
    if len(texts) == 1:
        return texts[0]
    parts: list[str] = []
    for i, text in enumerate(texts):
        rows = (text or "").splitlines()
        if i > 0:
            rows = _drop_folio(rows, head=True)
        if i < len(texts) - 1:
            rows = _drop_folio(rows, head=False)
        parts.append("\n".join(rows))
    return "\n".join(parts)
