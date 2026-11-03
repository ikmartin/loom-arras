"""The global identity of a cited work.

A citekey names a work inside one quilt and changes whenever the author re-exports their bibliography; a global identifier names the same work on two machines. Local identifiers are for authoring, global identifiers are for joining: `\\cite` and node ids keep the local names, and everything that has to agree across quilts -- the `refs/` layout, deduplication, fetching -- keys on what this module returns.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from loom.scan.bib import BibEntry

# Resolution order. A DOI is preferred because it names the published work, which is what a bibliography cites; an eprint names a specific preprint, which is usually what loom can actually fetch. Both are kept when both exist: they are different facts, not competing answers.
SCHEMES = ("doi", "arxiv", "mr", "zbl", "work")
DISPLAY = {"arxiv": "arXiv", "doi": "doi", "mr": "MR", "zbl": "Zbl", "work": "work"}

_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf|e-print)/([^\s?#]+)", re.I)
_DOI_URL = re.compile(r"(?:doi\.org/|dx\.doi\.org/)(10\.[^\s?#]+)", re.I)
_DOI_BARE = re.compile(r"^10\.\d{4,9}/\S+$")
_ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(\S+)$", re.I)
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


@dataclass(frozen=True)
class WorkId:
    """One global identifier for a work: its scheme, its value, and where the binding came from."""

    scheme: str
    value: str
    provenance: str = "declared"

    def __str__(self) -> str:
        return f"{DISPLAY.get(self.scheme, self.scheme)}:{self.value}"

    @property
    def path(self) -> str:
        """The `refs/` directory for this work, as `<scheme>/<sanitised value>`.

        The scheme is a directory of its own so that sanitisation rules stay local to a scheme and two schemes cannot collide on one string. Nobody navigates here by hand -- loom and arras surface it -- so the value is mangled for safety rather than for looks.
        """
        return f"{self.scheme}/{sanitise(self.value)}"

    @property
    def preprint(self) -> bool:
        return self.scheme == "arxiv"

    @property
    def published(self) -> bool:
        return self.scheme in ("doi", "mr", "zbl")


def sanitise(value: str) -> str:
    """A path-safe form of an identifier's value: DOIs carry slashes and old arXiv ids carry them too.

    One-way. The identifier itself is recorded in the digest header and the manifest, so nothing needs to read it back out of a path. Two values differing only where they are mangled would collide; no real DOI pair does.
    """
    return _UNSAFE.sub("_", value.strip())


def parse(text: str) -> WorkId | None:
    """A `scheme:value` identifier as written in a digest header, or None if it is not one."""
    raw = text.strip()
    if ":" not in raw:
        return None
    scheme, _, value = raw.partition(":")
    scheme = scheme.strip().lower()
    if scheme not in SCHEMES or not value.strip():
        return None
    return WorkId(scheme, value.strip())


def _eprint(entry: BibEntry) -> str | None:
    """The arXiv identifier of an entry, from `eprint` when the archive is arXiv or unstated."""
    e = entry.eprint
    if not e:
        return None
    kind = (entry.fields.get("eprinttype") or entry.fields.get("archiveprefix") or "arxiv").strip().lower()
    if kind != "arxiv":
        return None
    e = re.sub(r"^arxiv:", "", e.strip(), flags=re.I)
    if e and entry.version and not re.search(r"v\d+$", e):
        e = f"{e}v{entry.version}"
    return e or None


def _from_url(entry: BibEntry) -> WorkId | None:
    """An identifier recovered from a `url` field, for entries that carry the link but not the field."""
    url = entry.fields.get("url", "")
    if m := _ARXIV_URL.search(url):
        return WorkId("arxiv", m.group(1), "declared")
    if m := _DOI_URL.search(url):
        return WorkId("doi", m.group(1), "declared")
    return None


def declared(entry: BibEntry) -> list[WorkId]:
    """Every global identifier the entry states, in resolution order, most authoritative first.

    Returns both a DOI and an eprint when the entry has both, since they name different artifacts of one work.
    """
    out: list[WorkId] = []
    doi = entry.fields.get("doi", "").strip()
    if doi and (_DOI_BARE.match(doi) or doi.startswith("10.")):
        # arXiv mints its own DOIs under 10.48550, so such a DOI names a preprint and not a published article.
        # Normalising it means one artifact has one directory however the bibliography happened to record it, and
        # keeps `published` honest: a 10.48550 DOI must not make loom:unverified-locators think the work is in print.
        if m := _ARXIV_DOI.match(doi):
            out.append(WorkId("arxiv", m.group(1), "declared"))
        else:
            out.append(WorkId("doi", doi, "declared"))
    if (e := _eprint(entry)) and not any(w.scheme == "arxiv" for w in out):
        out.append(WorkId("arxiv", e, "declared"))
    for field, scheme in (("mrnumber", "mr"), ("zbl", "zbl"), ("zblnumber", "zbl")):
        v = entry.fields.get(field, "").strip()
        if v and not any(w.scheme == scheme for w in out):
            out.append(WorkId(scheme, v, "declared"))
    if not out and (w := _from_url(entry)):
        out.append(w)
    return out


def _normalised(entry: BibEntry) -> str:
    """The author surnames, title and year of an entry, flattened so two machines agree byte for byte."""
    author = entry.fields.get("author", "")
    surnames = []
    for part in re.split(r"\s+and\s+", author):
        part = part.strip()
        if not part:
            continue
        surnames.append(part.split(",")[0] if "," in part else part.split()[-1] if part.split() else "")
    title = entry.fields.get("title", "")
    year = entry.fields.get("year", "")
    raw = "|".join(["+".join(surnames), title, year])
    folded = unicodedata.normalize("NFKD", raw)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9|+]+", "", folded.lower())


def synthetic(entry: BibEntry) -> WorkId:
    """A deterministic `work:<hash>` for an entry that states no identifier.

    Determinism across machines is the point: it is what lets two people's corpora merge on a book that has no DOI. Derived from the entry, so nothing needs storing.
    """
    digest = hashlib.sha256(_normalised(entry).encode("utf-8")).hexdigest()[:8]
    return WorkId("work", digest, "declared")


def identify(entry: BibEntry | None) -> list[WorkId]:
    """Every global identifier for a bibliography entry, most authoritative first.

    Parameters
    ----------
    entry : BibEntry or None
        The entry to identify; None yields an empty list, since a work with no entry has nothing to identify it by.

    Returns
    -------
    list of WorkId
        The declared identifiers in resolution order, or a single deterministic `work:<hash>` when the entry declares none. Never empty for a real entry, so a work always has somewhere to be filed.

    See Also
    --------
    declared : only what the entry states, without the synthetic fallback.
    """
    if entry is None:
        return []
    found = declared(entry)
    return found if found else [synthetic(entry)]


def primary(entry: BibEntry | None) -> WorkId | None:
    """The identifier a work's `refs/` directory is named by: the first of `identify`."""
    ids = identify(entry)
    return ids[0] if ids else None


def arxiv_base(value: str) -> str:
    """An arXiv id without its version: `0805.2065v2` is `0805.2065`, and `solv-int/9901001v1` keeps the "v" its subject holds."""
    return re.sub(r"v\d+$", "", value.strip())


#: The kinds `recognise` tells apart, in the words the viewer shows.
KINDS = {
    "bibtex": "BibTeX entry",
    "doi": "DOI",
    "arxiv": "arXiv",
    "zbl": "zbMATH",
    "mr": "MathSciNet",
    "isbn": "ISBN",
    "unknown": "not recognised",
}

_BIBTEX = re.compile(r"^\s*@\s*[A-Za-z]+\s*[{(]")
_DOI_ANY = re.compile(r"^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/\S+?)[.,;)\]]*$", re.I)
_ARXIV_NEW = r"\d{4}\.\d{4,5}(?:v\d+)?"
_ARXIV_OLD = r"[a-z][a-z-]*(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?"
_ARXIV_ANY = re.compile(
    rf"^(?:arxiv:\s*|https?://(?:www\.|export\.)?arxiv\.org/(?:abs|pdf|e-print)/)?({_ARXIV_NEW}|{_ARXIV_OLD})(?:\.pdf)?/?$",
    re.I,
)
_ZBL = re.compile(r"^(?:zbl\s*:?\s*|zbmath\s*:?\s*|https?://zbmath\.org/(?:\?q=an:)?)(\d{4}\.\d{5}|\d{8})/?$", re.I)
_MR = re.compile(r"^(?:mr\s*:?\s*|https?://mathscinet\.ams\.org/mathscinet-getitem\?mr=(?:MR)?)(\d{5,8})$", re.I)
_ISBN = re.compile(r"^(?:isbn(?:-1[03])?\s*:?\s*)?([0-9][0-9 -]{8,16}[0-9Xx])$", re.I)


@dataclass(frozen=True)
class Recognised:
    """What a pasted text is: its `kind` (a key of `KINDS`), the identifier it carries as loom writes it, and for a BibTeX entry the entry itself."""

    kind: str
    value: str = ""
    entry: BibEntry | None = None

    @property
    def label(self) -> str:
        return KINDS[self.kind]

    @property
    def work_id(self) -> WorkId | None:
        """The identifier a lookup asks after: the one pasted, or the most authoritative one a pasted entry states."""
        if self.kind in ("doi", "arxiv", "zbl", "mr"):
            return WorkId(self.kind, self.value, "declared")
        if self.entry is not None:
            ids = declared(self.entry)
            return ids[0] if ids else None
        return None


def _isbn_ok(digits: str) -> bool:
    """Whether an ISBN-10 or ISBN-13's check digit holds."""
    if len(digits) == 10:
        total = sum((10 - i) * (10 if c in "Xx" else int(c)) for i, c in enumerate(digits))
        return total % 11 == 0 and not any(c in "Xx" for c in digits[:9])
    if len(digits) == 13 and digits.isdigit():
        return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(digits)) % 10 == 0
    return False


def recognise(text: str) -> Recognised:
    """What `text` is, read without the network: a BibTeX entry, a DOI, an arXiv id, a zbMATH number, an MR number, an ISBN, or none of them.

    Parameters
    ----------
    text : str
        What a person pasted: an entry, a bare identifier, a prefixed one (`doi:`, `arXiv:`, `Zbl`, `MR`, `ISBN`) or a link to it.

    Returns
    -------
    Recognised
        Its kind and identifier; a DOI under arXiv's own prefix (10.48550) is the arXiv id it mints, and an entry carries what it parsed to.
    """
    from loom.scan.bib import parse_bib

    raw = text.strip()
    if not raw:
        return Recognised("unknown")
    if _BIBTEX.match(raw):
        entries = list(parse_bib(raw).values())
        return Recognised("bibtex", entries[0].key, entries[0]) if entries else Recognised("unknown")
    if m := _DOI_ANY.match(raw):
        doi = m.group(1)
        if a := _ARXIV_DOI.match(doi):
            return Recognised("arxiv", a.group(1))
        return Recognised("doi", doi)
    if m := _ARXIV_ANY.match(raw):
        return Recognised("arxiv", m.group(1))
    if m := _ZBL.match(raw):
        return Recognised("zbl", m.group(1))
    if m := _MR.match(raw):
        return Recognised("mr", m.group(1))
    if m := _ISBN.match(raw):
        digits = re.sub(r"[ -]", "", m.group(1))
        if _isbn_ok(digits):
            return Recognised("isbn", digits.upper())
    return Recognised("unknown")
