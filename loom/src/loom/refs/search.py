"""Finding text in a cited work's pages, and the one normalisation an anchor is checked under (plan 0.12 §5, digest contract §9.5).

Everything that compares a quotation to a page goes through `normalize` here: `loom refs grep` so a search finds what is on the page, `loom refs locate` so a span can be given geometry, and `loom refs propose` so a proposal is accepted or refused on the same terms it was searched under. Three implementations of "near enough" would mean a quotation that greps but will not anchor, which is the worst failure this layer could have.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# What a PDF text layer does to a document, undone. Ligatures are the common case; the rest turn up in older
# scans and in anything typeset before Unicode was settled.
_FOLD = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
    "‘": "'", "’": "'", "“": '"', "”": '"', "′": "'", "´": "'", "`": "'",
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    "­": "",
}  # fmt: skip
_FOLD_RE = re.compile("|".join(map(re.escape, _FOLD)))
# One `<word>` of pdftotext's `-bbox-layout` output. Scanned rather than parsed as XML on purpose: the content of a
# word is whatever byte the font mapped, and a mathematics paper is full of glyphs that land on control codepoints
# (U+000F among them), which no XML parser will accept. Every page of every paper in this corpus failed to parse.
_WORD = re.compile(
    r'<word\s+xMin="([\d.eE+-]+)"\s+yMin="([\d.eE+-]+)"\s+xMax="([\d.eE+-]+)"\s+yMax="([\d.eE+-]+)"\s*>(.*?)</word>',
    re.S,
)
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_ENTITY = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&apos;": "'"}

# A word broken across a line: "morph-\nism" is one word on the page and two in the text layer.
_HYPHEN_BREAK = re.compile(r"-\s*\n\s*")
_SPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """The form two pieces of text are compared in: ligatures folded, hyphenation across lines joined, whitespace flattened.

    Parameters
    ----------
    text : str
        Page text or a quotation, either way as it was written.

    Returns
    -------
    str
        The comparison form. Case is **kept**: a statement's capitals are part of it, and folding them would let "let X be Finite" pass as the paper's words.

    See Also
    --------
    find_in_page : the search this normalisation exists for.
    """
    t = unicodedata.normalize("NFKC", text)
    t = _HYPHEN_BREAK.sub("", t)
    t = _FOLD_RE.sub(lambda m: _FOLD[m.group()], t)
    return _SPACE.sub(" ", t).strip()


def find_in_page(page: str, needle: str) -> bool:
    """Whether `needle` appears on `page`, both normalised. This is the whole of digest contract §9.5."""
    n = normalize(needle)
    return bool(n) and n in normalize(page)


# What `words_not_on_page` drops before comparing: mathematics, which the text layer spells as glyph soup, and
# control words with the label-like arguments of the ones that name things rather than say them.
_MATH = re.compile(
    r"\$\$.*?\$\$|\$.*?\$|\\\(.*?\\\)|\\\[.*?\\\]"
    r"|\\begin\{(equation|align|gather|multline|eqnarray|displaymath)(\*?)\}.*?\\end\{\1\2\}",
    re.S,
)
_NAMING = re.compile(r"\\(?:ref|eqref|cref|Cref|label|cite[a-z]*|begin|end)\*?(?:\[[^\]]*\])*\{[^{}]*\}")
_COMPOUND = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)+")
_CONTROL_WORD = re.compile(r"\\[A-Za-z@]+\*?")
_PROSE = re.compile(r"[A-Za-z]{3,}")


def words_not_on_page(statement: str, source_text: str) -> list[str]:
    """The prose words of a rendering that its quoted source text does not contain, in order, once each.

    Parameters
    ----------
    statement : str
        The LaTeX rendering of a result.
    source_text : str
        The page's own words it claims to render.

    Returns
    -------
    list of str
        Words of three or more letters outside mathematics, compared without case (a capital at a sentence start is not an addition). What is left is the agent's: a gloss, an inlined definition, a clause from elsewhere. Five of thirteen Brion renderings in the third study run carried one, after the orientation said "the paper's words only".
    """
    prose = normalize(_CONTROL_WORD.sub(" ", _NAMING.sub(" ", _MATH.sub(" ", statement))))
    have = {w.lower() for w in _PROSE.findall(normalize(source_text))}
    for compound in _COMPOUND.findall(prose):
        # "pull-backs" broken over a line on the page is "pullbacks" once the break is joined
        if compound.replace("-", "").lower() in have:
            have.update(part.lower() for part in compound.split("-"))
    out: list[str] = []
    seen: set[str] = set()
    for w in _PROSE.findall(prose):
        if w.lower() not in have and w.lower() not in seen:
            seen.add(w.lower())
            out.append(w)
    return out


@dataclass
class Hit:
    """One page a search matched, with enough context to decide whether to read it."""

    citekey: str
    page: int
    section: str
    context: str


def _context(page: str, needle: str, width: int = 70) -> str:
    """The matched text with a little either side, on one line; '' when the page does not contain it."""
    flat = normalize(page)
    i = flat.find(normalize(needle))
    if i < 0:
        return ""
    lo, hi = max(0, i - width // 2), min(len(flat), i + len(normalize(needle)) + width // 2)
    return ("…" if lo else "") + flat[lo:hi] + ("…" if hi < len(flat) else "")


def grep_work(home: Path, citekey: str, needle: str) -> list[Hit]:
    """Every page of one mapped work whose text contains `needle`; reads the committed page text, never the PDF."""
    from loom.refs.pages import read_map

    out: list[Hit] = []
    m = read_map(home)
    pages = sorted((home / "pages").glob("*.txt"))
    for path in pages:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not find_in_page(text, needle):
            continue
        n = int(path.stem)
        sec = m.section_of(n) if m else None
        label = f"{sec.n} {sec.title}".strip() if sec else ""
        out.append(Hit(citekey=citekey, page=n, section=label, context=_context(text, needle)))
    return out


@dataclass
class Span:
    """Where a quotation sits on a page, in points with the origin at the TOP LEFT.

    That is the space `pdftotext -bbox-layout` emits, not PDF user space, whose origin is the bottom left. The two differ by a vertical flip, so a renderer handed these as user-space coordinates draws every highlight mirrored.
    """

    page: int
    quad: tuple[float, float, float, float]
    words: int
    #: One rectangle per line the quotation covers, in the same space. A single union box over three lines swallows the column between them, so this is what a highlight is drawn from; `quad` remains the union, for a caller that wants one number.
    lines: list[tuple[float, float, float, float]] = field(default_factory=list)


def _words(bbox: str) -> list[tuple[float, float, float, float, str]]:
    """Every word box in one page of `-bbox-layout` output, as (xMin, yMin, xMax, yMax, text)."""
    out: list[tuple[float, float, float, float, str]] = []
    for m in _WORD.finditer(bbox):
        raw = m.group(5)
        for ent, ch in _ENTITY.items():
            raw = raw.replace(ent, ch)
        out.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), _CONTROL.sub("", raw)))
    return out


def locate_span(bbox_xml: str, needle: str, page: int) -> Span | None:
    """The bounding box of `needle` on a page, from pdftotext's `-bbox-layout` output.

    Parameters
    ----------
    bbox_xml : str
        One page of `pdftotext -bbox-layout` output.
    needle : str
        The quotation to find, compared under `normalize`.
    page : int
        The page number, carried into the result.

    Returns
    -------
    Span or None
        The union of the matched words' boxes, one rectangle per line in `lines`, or None when the words are not on the page.

    See Also
    --------
    loom.refs.pages.token_boxes : produces the output, one page at a time and on demand.
    loom.refs.search.find_in_page : the strict comparison, which is what a claim is checked against.
    """
    words = _words(bbox_xml)
    if not words:
        return None
    text, owner = _flat(words)
    want = _loose(needle)
    if not want:
        return None
    at = text.find(want)
    if at < 0:
        return None
    hit = sorted(set(owner[at : at + len(want)]))
    if not hit:
        return None
    boxes = [words[i] for i in hit]
    return Span(
        page=page,
        quad=(min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)),
        words=len(boxes),
        lines=_by_line(boxes),
    )


#: Dropped from both sides when looking for a quotation's geometry: spaces, and the hyphens a line break leaves behind.
_LOOSE = {" ", "-", "‐", "‑"}


def _loose(s: str) -> str:
    """A quotation reduced to what two extractions of one page agree on.

    `pages/NNNN.txt` comes from plain `pdftotext` and the word boxes from `-bbox-layout`: two readings of the same page that disagree about spacing around mathematics (`hσ2 i` against `hσ2i`) and about hyphens a line break left behind (`denom-` `inators` against `denominators`). Measured over five documents, matching under `normalize` alone placed 81% of quotations and as little as 47% on a real arXiv paper; dropping spaces and hyphens from both sides placed 100%, with the matched span covering the right number of words in every case.

    This looseness is for **drawing only**. `find_in_page` stays strict, because a highlight two lines off is visible and a transcription wrongly called faithful is not.
    """
    return "".join(c for c in normalize(s) if c not in _LOOSE)


def _flat(words: list[tuple[float, float, float, float, str]]) -> tuple[str, list[int]]:
    """The page as one loose string, with the word each character came from.

    A character-offset map rather than a word-sequence match: a word box carries whatever punctuation touches it, so matching "perfect obstruction theory" against the tokens `perfect`, `obstruction`, `theory.` fails on the trailing period -- which is what a real page does to a real quotation.
    """
    flat: list[str] = []
    owner: list[int] = []
    for i, w in enumerate(words):
        piece = _loose(w[4])
        if not piece:
            continue
        flat.append(piece)
        owner.extend([i] * len(piece))
    return "".join(flat), owner


def _by_line(boxes: list[tuple[float, float, float, float, str]]) -> list[tuple[float, float, float, float]]:
    """One rectangle per line of a matched quotation, from word boxes that overlap vertically.

    The word regex ignores the `<line>` elements on purpose (`_words`), so lines are recovered from the geometry: two words are on one line when their vertical extents overlap by more than half of the shorter one, which holds for subscripts and superscripts and separates a line from the next.
    """
    out: list[tuple[float, float, float, float]] = []
    for b in sorted(boxes, key=lambda w: (w[1], w[0])):
        if out:
            x0, y0, x1, y1 = out[-1]
            overlap = min(y1, b[3]) - max(y0, b[1])
            if overlap > 0.5 * min(y1 - y0, b[3] - b[1]):
                out[-1] = (min(x0, b[0]), min(y0, b[1]), max(x1, b[2]), max(y1, b[3]))
                continue
        out.append((b[0], b[1], b[2], b[3]))
    return out


def locate_offsets(page_text: str, needle: str) -> tuple[int, int] | None:
    """Where `needle` sits in a page's committed text, as offsets into that text; None when it is not there.

    The counterpart of `locate_span`, and deliberately the same tolerance: the reader's selection came from a third extraction again -- the viewer's own text layer -- so spacing around mathematics and a hyphen left by a line break must not decide whether an anchor can be recorded. Offsets index the raw text as committed, not a normalised copy of it, because that file is what a coauthor with no PDF checks an anchor against.
    """
    keep: list[int] = []
    flat: list[str] = []
    for i, ch in enumerate(page_text):
        piece = _loose(ch)
        if piece:
            flat.append(piece)
            keep.extend([i] * len(piece))
    text = "".join(flat)
    want = _loose(needle)
    if not want:
        return None
    at = text.find(want)
    if at < 0:
        return None
    return keep[at], keep[at + len(want) - 1] + 1


def statement_span(page_text: str, label: str, statement: str) -> tuple[int, int] | None:
    """Where a result's statement sits in a page's committed text: from its printed label to its last words.

    A digest node is a transcription of a statement, and what a reader wants to see of it is the statement — not the page it happens to be on. The two ends are found differently because the page offers different evidence for each. The **start** is the printed label, `Proposition 2.1`, which is on the page in exactly the form a reader sees. The **end** cannot be matched the same way: the statement is LaTeX and its mathematics is not on the page as typed, so what is searched for is the last run of three prose words that survives stripping the mathematics out, and the span ends where that run ends.

    Parameters
    ----------
    page_text : str
        The page's committed text, as `pages/NNNN.txt` holds it.
    label : str
        The result as the paper prints it, `Proposition 2.1`.
    statement : str
        The result's LaTeX, whose prose supplies the end.

    Returns
    -------
    tuple of (int, int), or None
        Offsets into `page_text`, or None when the label is not on the page. A statement whose prose cannot be found — one that is nearly all mathematics, or one that runs onto the next page — ends at its label, which is short but never wrong.
    """
    head = locate_offsets(page_text, label)
    if head is None:
        return None
    start, end = head
    prose = _PROSE.findall(normalize(_CONTROL_WORD.sub(" ", _NAMING.sub(" ", _MATH.sub(" ", statement)))))
    rest = page_text[start:]
    for i in range(len(prose) - 3, -1, -1):
        found = locate_offsets(rest, " ".join(prose[i : i + 3]))
        if found is not None and start + found[1] > end:
            return start, start + found[1]
    return start, end


def words_in_boxes(bbox_xml: str, rects: list[list[float]]) -> str:
    """The page's own words under a reader's rectangles, in reading order.

    A box anchor records no offsets, so this is the best text it can carry: unreliable by construction, since a box is drawn exactly where the text layer could not be trusted, but enough for a list to show something and for a search to reach it in principle.
    """
    out: list[str] = []
    for w in _words(bbox_xml):
        for x0, y0, x1, y1 in rects:
            if w[0] >= x0 - 1 and w[2] <= x1 + 1 and w[1] >= y0 - 1 and w[3] <= y1 + 1:
                out.append(w[4])
                break
    return _SPACE.sub(" ", " ".join(out)).strip()
