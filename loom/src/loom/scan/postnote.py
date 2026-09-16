"""Postnote matching (book 8.7): `\\cite[POSTNOTE]{citekey}` becomes an edge to the digest node whose locator matches, after both sides are normalised.

Normalisation lowercases, expands the abbreviation table, strips `~`, `\\S`, `\\href`, parentheses, trailing part selectors such as `(1)` or `(ii)`, page references, and the words see/cf/also, and folds plurals and Roman numerals; a postnote naming several results is split on commas, semicolons, and `and`, a bare number inheriting the taxon of the part before it.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from loom.scan.model import Diagnostic, Location

if TYPE_CHECKING:
    from loom.scan.edges import EdgeResult
    from loom.scan.nodes import Assembly, NodeRec

ABBREV = {
    "thm": "theorem",
    "theorem": "theorem",
    "theorems": "theorem",
    "lem": "lemma",
    "lemma": "lemma",
    "lemmas": "lemma",
    "lemmata": "lemma",
    "prop": "proposition",
    "proposition": "proposition",
    "propositions": "proposition",
    "cor": "corollary",
    "corollary": "corollary",
    "corollaries": "corollary",
    "def": "definition",
    "defn": "definition",
    "definition": "definition",
    "definitions": "definition",
    "rem": "remark",
    "rmk": "remark",
    "remark": "remark",
    "remarks": "remark",
    "ex": "example",
    "exa": "example",
    "example": "example",
    "examples": "example",
    "sec": "section",
    "sect": "section",
    "section": "section",
    "sections": "section",
    "subsec": "subsection",
    "subsection": "subsection",
    "eq": "equation",
    "eqn": "equation",
    "equation": "equation",
    "equations": "equation",
    "conj": "conjecture",
    "conjecture": "conjecture",
    "constr": "construction",
    "construction": "construction",
    "cond": "condition",
    "condition": "condition",
    "conv": "convention",
    "convention": "convention",
    "notn": "notation",
    "notation": "notation",
    "ch": "chapter",
    "chap": "chapter",
    "chapter": "chapter",
    "chapters": "chapter",
    "app": "appendix",
    "appendix": "appendix",
    "tag": "tag",
    "tags": "tag",
    "ass": "assumption",
    "assumption": "assumption",
    "assumptions": "assumption",
    "hyp": "hypothesis",
    "hypothesis": "hypothesis",
    "q": "question",
    "question": "question",
    "para": "paragraph",
    "paragraph": "paragraph",
    "fig": "figure",
    "figure": "figure",
    "tab": "table",
    "table": "table",
}
TAXON_WORDS = set(ABBREV.values())
ROMAN = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
    "xi": 11,
    "xii": 12,
}
DROP_WORDS = {"see", "cf", "also", "eg", "ie", "the", "of", "in", "compare", "esp", "especially"}
_SPLIT = re.compile(r"\s*(?:;|,|\band\b|&)\s*")
_PAGE = re.compile(r"\b(?:pp?|pages?)\.?\s*\d+\s*(?:--?|–|—)?\s*\d*")
_PART = re.compile(r"\s*\((?:\d+|[ivxl]+|[a-z])\)")
_LOCATOR = re.compile(r"\\cite\s*\[([^\]]*)\]")


def normalize(text: str) -> str:
    """The canonical form of a postnote or locator; '' when nothing but a page reference or filler remains."""
    s = text
    s = re.sub(r"\\href\s*\{[^}]*\}\s*\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\S\b|§", " section ", s)
    s = re.sub(r"\\[A-Za-z@]+\*?\s*", " ", s)
    s = s.replace("~", " ").replace("{", "").replace("}", "").replace("\\", " ")
    s = s.lower()
    s = _PAGE.sub(" ", s)
    s = _PART.sub(" ", s)
    s = s.replace("(", " ").replace(")", " ")
    s = re.sub(r"(?<=[a-z])\.(?=\s|$)", "", s)  # the period of an abbreviation, never the dot inside a.31
    s = re.sub(r"[,;:]+", " ", s)
    words = [w for w in re.split(r"\s+", s.strip()) if w]
    out: list[str] = []
    for w in words:
        if w in DROP_WORDS:
            continue
        out.append(ABBREV.get(w, w))
    for i in range(1, len(out)):
        if out[i] in ROMAN and out[i - 1] in TAXON_WORDS:
            out[i] = str(ROMAN[out[i]])
    return " ".join(out)


def parts(postnote: str) -> list[str]:
    """The normalised results a postnote names: one per comma, semicolon, or `and`; a bare number takes the taxon of the part before it."""
    out: list[str] = []
    last_taxon: str | None = None
    for raw in _SPLIT.split(_PAGE.sub(" ", postnote)):
        n = normalize(raw)
        if not n:
            continue
        words = n.split(" ")
        if words[0] in TAXON_WORDS:
            last_taxon = words[0]
        elif last_taxon and re.match(r"^[a-z]?\d", words[0]):
            n = f"{last_taxon} {n}"
        out.append(n)
    return out


def locator_of(title: str | None) -> str | None:
    """The locator inside a digest node's title, `{\\cite[LOCATOR]{citekey}}`."""
    if not title:
        return None
    m = _LOCATOR.search(title)
    return m.group(1).strip() if m else None


def locator_forms(node: NodeRec, slug: str) -> set[str]:
    """Every normalised string that names this digest node: its locator, each part of the locator, and `<taxon> <number>` read off its id."""
    forms: set[str] = set()
    loc = locator_of(node.title)
    if loc:
        forms.add(normalize(loc))
        forms.update(parts(loc))
    for label in [
        node.id,
        *node.aliases,
    ]:  # an alias such as `thm-1.2.1` beside the id `thm-1.0.1` names the same result under an older numbering
        if not label or not label.startswith(slug + "-"):
            continue
        local = label[len(slug) + 1 :]
        if local == "setup":
            forms.add(normalize("standing assumptions"))
        pieces = local.split("-")
        if len(pieces) >= 2 and pieces[0] in ABBREV:
            forms.add(normalize(f"{ABBREV[pieces[0]]} {'-'.join(pieces[1:])}"))  # `thm-A.20` names `theorem a.20`
    forms.discard("")
    return forms


def match(postnote: str, candidates: list[tuple[str, set[str]]]) -> list[str]:
    """Keys of the candidates any part of the postnote names, in candidate order."""
    wanted = set(parts(postnote))
    if not wanted:
        return []
    return [key for key, forms in candidates if forms & wanted]


def postnote_edges(asm: Assembly, res: EdgeResult) -> None:
    """Add a `postnote` edge for every `\\cite[postnote]{citekey}` that names a node of the citekey's digest; warn `loom:unmatched-postnote` when a digest exists but nothing matches."""
    from loom.scan.edges import EdgeRec, _kind_of

    by_citekey: dict[str, list[tuple[str, set[str]]]] = {}
    for key, n in asm.nodes.items():
        ck = asm.digest_files.get(n.file)
        if ck is None or n.kind not in ("environment", "section"):
            continue
        forms = locator_forms(n, asm.prefix_of(ck))
        if forms:
            by_citekey.setdefault(ck, []).append((key, forms))
    for c in res.cites:
        if not c.postnote or c.citekey not in by_citekey:
            continue
        src_node = asm.nodes.get(c.src)
        if src_node is not None and asm.digest_files.get(src_node.file) == c.citekey:
            continue  # a digest node's own locator title cites the paper it digests; that is not a dependency
        kind = _kind_of(src_node.kind) if src_node else "prose"
        hits = [k for k in match(c.postnote, by_citekey[c.citekey]) if k != c.src]
        if hits:
            for to in hits:
                res.edges.append(EdgeRec(c.src, to, kind, "postnote", c.file, c.line, f"{c.citekey}|{c.postnote}"))
        else:
            res.diagnostics.append(
                Diagnostic(
                    "warning",
                    "loom:unmatched-postnote",
                    f"\\cite[{c.postnote}]{{{c.citekey}}} names no result in the digest of {c.citekey}",
                    [Location(c.file, c.line)],
                    [c.src],
                )
            )
