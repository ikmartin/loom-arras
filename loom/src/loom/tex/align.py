"""Where rendered text came from in its LaTeX source: its words, in order, with mathematics as gaps (plan 0.29).

A rendering and its source share little but their words: the source has macros, braces, comments and line breaks, the rendering ligatures, curly quotes and the numbers TeX worked out. Both are reduced to words, letters lower-cased and digits dropped, and a run of rendered words is placed where the same run stands in the source, the occurrence nearest where the renderer said it began.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from bisect import bisect_left
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

_WORD = re.compile(r"[^\W\d_]+")
#: Display environments whose body is mathematics, and so a gap in the words.
MATH_ENVS = frozenset(
    "equation equation* align align* gather gather* multline multline* flalign flalign* alignat alignat* eqnarray eqnarray* displaymath math split".split()
)
#: Commands whose next braced argument TeX never prints as words: names, keys, addresses and lengths.
SILENT = frozenset(
    "label ref eqref pageref cref Cref autoref cite citep citet nocite bibitem href includegraphics input include usepackage begin end hspace vspace setlength addtocounter setcounter newcommand renewcommand def documentclass bibliography bibliographystyle color textcolor".split()
)
#: Citations, whose notes in square brackets print inside the citation TeX makes, and so are made like its key.
CITES = frozenset(
    "cite citep citet citealt citealp citeauthor citeyear Cite parencite textcite autocite footcite".split()
)
SILENT = SILENT | CITES


def _closing_bracket(text: str, at: int) -> int:
    """Where the square bracket opened at `at` closes, braces inside it skipped; the end of the text when it never does."""
    depth = 0
    for k in range(at + 1, len(text)):
        c = text[k]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == "]" and depth <= 0:
            return k
    return len(text) - 1


#: An accented letter as LaTeX writes it, `\'e`, `\'{e}` or `{\'e}`, read as its letter so the word it stands in stays one word.
_ACCENT = re.compile(
    r"\{\\(?:['`^\"~=.]|[uvHcdbrk](?![A-Za-z]))\s*(?:\{\s*(\\[ij]|[A-Za-z])\s*\}|(\\[ij]|[A-Za-z]))\}"
    r"|\\(?:['`^\"~=.]|[uvHcdbrk](?![A-Za-z]))\s*(?:\{\s*(\\[ij]|[A-Za-z])\s*\}|(\\[ij]|[A-Za-z]))"
)
#: A braced argument shaped like a label or a key: no space, a colon inside, `{thm:main}` or `{sec:intro.2}`.
_LABELISH = re.compile(r"\{[\w.+/-]+:[\w:.+/-]*\}")
#: Letters LaTeX writes as commands, `\ss`, `\o`, `\ae`, `\i`, read as the letters they fold to.
_LETTER = re.compile(r"\\(ss|o|O|ae|AE|oe|OE|aa|AA|l|L|i|j)(?![A-Za-z])(?:\{\})?")
_FOLDED = {
    "ss": "ss",
    "o": "o",
    "O": "o",
    "ae": "ae",
    "AE": "ae",
    "oe": "oe",
    "OE": "oe",
    "aa": "a",
    "AA": "a",
    "l": "l",
    "L": "l",
    "i": "i",
    "j": "j",
}
#: Letters compatibility decomposition leaves whole, folded as their LaTeX spelling is.
_WHOLE = str.maketrans({"ø": "o", "æ": "ae", "œ": "oe", "ł": "l", "đ": "d", "ı": "i", "ȷ": "j", "ð": "d", "þ": "th"})


@dataclass(frozen=True)
class Word:
    """A word and where it stands: its folded text and its character offsets."""

    text: str
    start: int
    end: int


def fold(text: str) -> str:
    """Text as both sides are compared: decomposed so `ﬁ` is `fi` and `é` is `e`, its accents dropped, and lower-cased."""
    bare = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return unicodedata.normalize("NFKC", bare).casefold().translate(_WHOLE)


def rendered_words(text: str) -> list[str]:
    """The words of rendered text, folded; digits, punctuation and spacing fall away."""
    return _WORD.findall(fold(text))


def _word_at(clean: str, i: int) -> tuple[str, int]:
    """The word that starts at `i`, its accented and spelled-out letters read as letters, and where it ends; '' where none does."""
    letters: list[str] = []
    j = i
    while j < len(clean):
        if (m := _WORD.match(clean, j)) is not None:
            letters.append(m.group(0))
        elif (m := _ACCENT.match(clean, j)) is not None:
            base = next(g for g in m.groups() if g)
            letters.append(base.lstrip("\\"))
        elif (m := _LETTER.match(clean, j)) is not None:
            letters.append(_FOLDED[m.group(1)])
        else:
            break
        j = m.end()
    return fold("".join(letters)), j


def source_words(
    clean: str,
    macros: Mapping[str, str] | None = None,
    environments: Mapping[str, str] | None = None,
    *,
    _nesting: int = 0,
) -> list[Word]:
    """The words a reader sees of LaTeX source `clean`, comments already blanked: none from a control sequence's name, from mathematics, or from the arguments `SILENT` names.

    `macros` maps the author's macros, by name without the backslash, to their definitions, and `environments` the author's environments to the code each opens with: each stands for the words that code prints, at the offsets of the macro or the `\\begin`, so `\\thmref{x}` reads "Theorem" as the rendering does.
    """
    out: list[Word] = []
    i, n = 0, len(clean)
    math_end: str | None = None
    silent = 0  # braces still open inside an argument that prints nothing
    depth = 0
    pending_silent = False
    optional = False  # inside the optional argument before a silent one, whose words print
    citing = False  # the silent argument awaited is a citation's, whose note is made too
    while i < n:
        c = clean[i]
        if math_end is None and c in "\\{" and (_ACCENT.match(clean, i) or _LETTER.match(clean, i)):
            word, j = _word_at(clean, i)
            if not silent and word:
                out.append(Word(word, i, j))
            pending_silent = pending_silent and optional
            i = j
            continue
        if c == "\\":
            m = re.match(r"\\([A-Za-z@]+\*?|.)", clean[i:])
            name = m.group(1) if m else ""
            j = i + (len(m.group(0)) if m else 1)
            if math_end is None:
                if name in ("(", "["):
                    math_end = "\\)" if name == "(" else "\\]"
                elif name == "begin":
                    env = re.match(r"\s*\{([^}]*)\}", clean[j:])
                    if env and env.group(1) in MATH_ENVS:
                        close = clean.find(f"\\end{{{env.group(1)}}}", j)
                        j = n if close < 0 else close + len(env.group(1)) + 6
                        i = j
                        continue
                    if env and environments and env.group(1) in environments and not silent and _nesting < 3:
                        # what the author's environment prints as it opens, `{\bf Theorem.}`, stood where it begins
                        opening = re.sub(r"#\d", " ", environments[env.group(1)])
                        out.extend(
                            Word(w.text, i, j + env.end())
                            for w in source_words(opening, macros, environments, _nesting=_nesting + 1)
                        )
                if name.rstrip("*") in SILENT:
                    pending_silent = True
                    citing = name.rstrip("*") in CITES
                elif macros and name in macros and not silent and _nesting < 3:
                    # what the author's macro prints, read from its definition and stood where the macro is: `\thmref{x}` prints "Theorem"
                    body = re.sub(r"#\d", " ", macros[name])
                    out.extend(
                        Word(w.text, i, j) for w in source_words(body, macros, environments, _nesting=_nesting + 1)
                    )
            elif clean.startswith(math_end, i):
                math_end = None
                j = i + 2
            i = j
            continue
        if math_end is not None:
            if math_end == "$" and c == "$":
                math_end = None
            elif math_end == "$$" and clean.startswith("$$", i):
                math_end = None
                i += 1
            i += 1
            continue
        if c == "$":
            math_end = "$$" if clean.startswith("$$", i) else "$"
            i += 2 if math_end == "$$" else 1
            continue
        if c == "{":
            depth += 1
            # an argument shaped like a label prints nothing whatever macro takes it: `\thmref{thm:main}` prints a number
            if (pending_silent or _LABELISH.match(clean, i)) and not silent:
                silent = depth
            pending_silent = False
            i += 1
            continue
        if c == "}":
            if silent == depth:
                silent = 0
            depth -= 1
            i += 1
            continue
        if c == "[" and pending_silent and citing:
            # a citation's note prints inside what TeX makes of the citation, which the rendering marks as made
            close = _closing_bracket(clean, i)
            i = close + 1
            continue
        if c == "[" and pending_silent and not optional:
            optional = (
                True  # an optional argument before the silent one is read as words: `\cite[Theorem 4]{key}` prints it
            )
            i += 1
            continue
        if c == "]" and optional:
            optional = False
            i += 1
            continue
        if not c.isspace() and not optional:
            pending_silent = pending_silent and c == "*"
        word, j = _word_at(clean, i)
        if word:
            if not silent:
                out.append(Word(word, i, j))
            i = j
        else:
            i += 1
    return out


@dataclass(frozen=True)
class Place:
    """Where a block's words stand in the source: offsets of its first and last word, and whether every word was found in order with none between."""

    start: int
    end: int
    exact: bool


class Source:
    """A source file's words, indexed once for every block placed in it."""

    def __init__(
        self, clean: str, macros: Mapping[str, str] | None = None, environments: Mapping[str, str] | None = None
    ) -> None:
        self.words = source_words(clean, macros, environments)
        self.texts = [w.text for w in self.words]
        self.starts = [w.start for w in self.words]
        self.at: dict[str, list[int]] = {}
        for i, t in enumerate(self.texts):
            self.at.setdefault(t, []).append(i)

    def place(
        self, words: list[str], near: int, *, window: int = 400, heads: frozenset[str] = frozenset()
    ) -> Place | None:
        """Place rendered `words` here, preferring the occurrence nearest the offset `near` (`place_run`).

        An exact place is the words as one unbroken run, less any leading words in `heads`: a theorem's name, which a style that puts the number first leaves outside the head TeX4ht marks.
        """
        lead = 0
        while lead < len(words) - 1 and words[lead] in heads:
            lead += 1
        found = place_run(self.texts, words[lead:], bisect_left(self.starts, near), window=window, at=self.at)
        if found is None:
            return None
        first, last, exact = found
        return Place(self.words[first].start, self.words[last].end, exact)


def place_run(
    texts: Sequence[str],
    words: Sequence[str],
    near: int,
    *,
    window: int = 400,
    at: Mapping[str, Sequence[int]] | None = None,
) -> tuple[int, int, bool] | None:
    """Where the run `words` stands in `texts`, the occurrence nearest the index `near` preferred.

    Parameters
    ----------
    texts : sequence of str
        The words searched, folded as `words` are.
    words : sequence of str
        The run to place.
    near : int
        The index in `texts` the run is expected at.
    window : int, default 400
        How many words either side of `near` a run that is not whole is looked for in.
    at : mapping of str to sequence of int, optional
        Each word's indices in `texts`, when the caller keeps them; read from `texts` otherwise.

    Returns
    -------
    (int, int, bool) or None
        The indices of the run's first and last words, and whether every word stood in order with none between. Failing a whole run, the matches clustered round the largest one in the window, kept when they hold at least four in five of the words; None when nothing is kept.
    """
    words = list(words)
    if not words or not texts:
        return None
    k = len(words)
    best: int | None = None
    starts = at.get(words[0], ()) if at is not None else [i for i, t in enumerate(texts) if t == words[0]]
    for i in starts:
        if list(texts[i : i + k]) == words and (best is None or abs(i - near) < abs(best - near)):
            best = i
    if best is not None:
        return best, best + k - 1, True
    lo, hi = max(0, near - window), min(len(texts), near + k + window)
    matcher = difflib.SequenceMatcher(None, list(texts[lo:hi]), words, autojunk=False)
    blocks = [b for b in matcher.get_matching_blocks() if b.size]
    if not blocks:
        return None
    # a stray common word far away is no part of the place: grow from the largest match while the next is close on both sides
    gap = max(8, k // 4)
    top = max(range(len(blocks)), key=lambda i: blocks[i].size)
    first = last = top
    while (
        first > 0
        and blocks[first].a - (blocks[first - 1].a + blocks[first - 1].size) <= gap
        and blocks[first].b - (blocks[first - 1].b + blocks[first - 1].size) <= gap
    ):
        first -= 1
    while (
        last < len(blocks) - 1
        and blocks[last + 1].a - (blocks[last].a + blocks[last].size) <= gap
        and blocks[last + 1].b - (blocks[last].b + blocks[last].size) <= gap
    ):
        last += 1
    if sum(b.size for b in blocks[first : last + 1]) * 5 < k * 4:
        return None
    return lo + blocks[first].a, lo + blocks[last].a + blocks[last].size - 1, False


def run_positions(texts: Sequence[str], words: Sequence[str], first: int, last: int) -> list[int | None]:
    """Where each of `words` stands in `texts`, a run `place_run` placed between `first` and `last`.

    Parameters
    ----------
    texts : sequence of str
        The words searched.
    words : sequence of str
        The run that was placed.
    first, last : int
        The indices `place_run` gave.

    Returns
    -------
    list of int or None
        For each word, its own index where it matched, the index of what replaced it where it did not, and for a word dropped from the text the word after the gap, so a place survives the words beside it changing; None where nothing stands for it.
    """
    region = list(texts[first : last + 1])
    out: list[int | None] = [None] * len(words)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, list(words), region, autojunk=False).get_opcodes():
        for i in range(i1, i2):
            if tag == "equal":
                out[i] = first + j1 + (i - i1)
            elif tag == "replace":
                out[i] = first + j1 + min(i - i1, j2 - j1 - 1)
            elif j1 < len(region):
                out[i] = first + j1
    return out
