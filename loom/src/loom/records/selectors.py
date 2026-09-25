"""Text-quote selectors (book 7.5): exact quote with prefix and suffix context, resolved inside a target's own text, never against file paths or line numbers."""

from __future__ import annotations

from dataclasses import dataclass

CONTEXT = 32


@dataclass(frozen=True)
class Selector:
    exact: str
    prefix: str = ""
    suffix: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"exact": self.exact, "prefix": self.prefix, "suffix": self.suffix}

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> Selector:
        return cls(d.get("exact", ""), d.get("prefix", ""), d.get("suffix", ""))


def _norm_map(text: str) -> tuple[str, list[int]]:
    """Whitespace-normalised text with a map from each normalised index to the original index."""
    out: list[str] = []
    idx: list[int] = []
    in_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if not in_space:
                out.append(" ")
                idx.append(i)
            in_space = True
        else:
            out.append(ch)
            idx.append(i)
            in_space = False
    return "".join(out), idx


def find_quote(own_text: str, quote: str) -> list[tuple[int, int]]:
    """Every occurrence of `quote` in `own_text`, compared with whitespace normalised; returns original-offset spans.

    A quote a reader selected on the page is not the source: math comes as `$tex$` whatever the source's delimiters, and `\\emph{x}` comes as `x`. When the plain comparison finds nothing, both sides are compared as that projection, and the spans are still offsets into the source.
    """
    return _find_normalised(own_text, quote) or _find_projected(own_text, quote)


_SIMPLE = ("emph", "textit", "textbf", "texttt", "textrm", "textsf", "textsc", "textup")
#: What the renderer prints for the source's quotes and dashes (`ligatures` in render/convert.py), longest first: a reader's selection carries `Ehrhart’s` where the source has `Ehrhart's`.
_TYPOGRAPHY = {"---": "—", "--": "–", "``": "“", "''": "”", "`": "‘", "'": "’"}


def _project(text: str) -> tuple[str, list[tuple[int, int]]]:
    """`text` as a reader sees it, each character mapped to the source range it came from: math delimiters as `$`/`$$`, the simple text macros unwrapped, `~` a space, quotes and dashes as printed, whitespace collapsed."""
    out: list[str] = []
    where: list[tuple[int, int]] = []
    dropped: list[bool] = []  # per open brace: whether it belongs to an unwrapped macro
    i, n = 0, len(text)

    def put(s: str, a: int, b: int) -> None:
        for ch in s:
            if ch.isspace():
                if out and out[-1] == " ":
                    where[-1] = (where[-1][0], b)
                    continue
                ch = " "
            out.append(ch)
            where.append((a, b))

    while i < n:
        two = text[i : i + 2]
        if two in ("\\(", "\\)"):
            put("$", i, i + 2)
            i += 2
        elif two in ("\\[", "\\]", "$$"):
            put("$$", i, i + 2)
            i += 2
        elif text[i] == "\\" and (m := _simple_macro(text, i)):
            dropped.append(True)
            i = m
        elif text[i] == "{":
            dropped.append(False)
            put("{", i, i + 1)
            i += 1
        elif text[i] == "}":
            if not (dropped and dropped.pop()):
                put("}", i, i + 1)
            i += 1
        elif text[i] == "~":
            put(" ", i, i + 1)
            i += 1
        elif typo := next((t for t in _TYPOGRAPHY if text.startswith(t, i)), None):
            put(_TYPOGRAPHY[typo], i, i + len(typo))
            i += len(typo)
        else:
            put(text[i], i, i + 1)
            i += 1
    return "".join(out), where


def _simple_macro(text: str, i: int) -> int | None:
    """If a simple text macro and its opening brace start at `i`, the offset just past the brace."""
    for name in _SIMPLE:
        head = "\\" + name + "{"
        if text.startswith(head, i):
            return i + len(head)
    return None


def _find_projected(own_text: str, quote: str) -> list[tuple[int, int]]:
    pt, where = _project(own_text)
    pq = _project(quote)[0].strip()
    if not pq:
        return []
    out: list[tuple[int, int]] = []
    k = pt.find(pq)
    while k >= 0:
        out.append((where[k][0], where[k + len(pq) - 1][1]))
        k = pt.find(pq, k + 1)
    return out


def _find_normalised(own_text: str, quote: str) -> list[tuple[int, int]]:
    nt, nmap = _norm_map(own_text)
    nq, _ = _norm_map(quote)
    nq = nq.strip()
    if not nq:
        return []
    out: list[tuple[int, int]] = []
    start = 0
    while True:
        k = nt.find(nq, start)
        if k < 0:
            break
        a = nmap[k]
        b = nmap[k + len(nq) - 1] + 1
        out.append((a, b))
        start = k + 1
    return out


def make_selector(own_text: str, quote: str) -> Selector:
    spans = find_quote(own_text, quote)
    if len(spans) != 1:
        raise ValueError("quote must occur exactly once")
    a, b = spans[0]
    return Selector(own_text[a:b], own_text[max(0, a - CONTEXT) : a], own_text[b : b + CONTEXT])


def _common_suffix_len(a: str, b: str) -> int:
    n = 0
    while n < len(a) and n < len(b) and a[-1 - n] == b[-1 - n]:
        n += 1
    return n


def _common_prefix_len(a: str, b: str) -> int:
    n = 0
    while n < len(a) and n < len(b) and a[n] == b[n]:
        n += 1
    return n


def resolve_selector(own_text: str, sel: Selector) -> tuple[int, int] | None:
    """Book 7.5.2: the unique exact occurrence, else the one whose context matches best, else the whitespace-normalised match, else None (detached)."""
    spans: list[tuple[int, int]] = []
    start = 0
    while True:
        k = own_text.find(sel.exact, start)
        if k < 0:
            break
        spans.append((k, k + len(sel.exact)))
        start = k + 1
    if not spans:
        spans = find_quote(own_text, sel.exact)
    if not spans:
        return None
    if len(spans) == 1:
        return spans[0]

    def score(span: tuple[int, int]) -> int:
        a, b = span
        return _common_suffix_len(own_text[max(0, a - CONTEXT) : a], sel.prefix) + _common_prefix_len(
            own_text[b : b + CONTEXT], sel.suffix
        )

    return max(spans, key=score)
