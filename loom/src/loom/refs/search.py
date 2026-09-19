"""Finding text in a cited work's pages, and the one normalisation an anchor is checked under (plan 0.12 §5, digest contract §9.5).

Everything that compares a quotation to a page goes through `normalize` here: `loom refs grep` so a search finds what is on the page, `loom refs locate` so a span can be given geometry, and `loom refs propose` so a proposal is accepted or refused on the same terms it was searched under. Three implementations of "near enough" would mean a quotation that greps but will not anchor, which is the worst failure this layer could have.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
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
    """Where a quotation sits on a page, in PDF user space."""

    page: int
    quad: tuple[float, float, float, float]
    words: int


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
        The union of the matched words' boxes, or None when the words are not on the page.

    See Also
    --------
    loom.refs.pages.token_boxes : produces the output, one page at a time and on demand.
    """
    words = _words(bbox_xml)
    if not words:
        return None
    # A character-offset map rather than a word-sequence match. A word box carries whatever punctuation touches it,
    # so matching "perfect obstruction theory" against the tokens `perfect`, `obstruction`, `theory.` fails on the
    # trailing period -- which is what a real page does to a real quotation.
    flat: list[str] = []
    owner: list[int] = []
    for i, w in enumerate(words):
        piece = normalize(w[4])
        if not piece:
            continue
        if flat:
            flat.append(" ")
            owner.append(i)
        flat.append(piece)
        owner.extend([i] * len(piece))
    text = "".join(flat)
    want = normalize(needle)
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
    )
