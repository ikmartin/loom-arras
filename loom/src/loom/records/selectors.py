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
    """Every occurrence of `quote` in `own_text`, compared with whitespace normalised; returns original-offset spans."""
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
