"""Identity candidates for works whose bibliography entry states no identifier (book 8.9.1).

A work with no DOI, eprint, MR or Zbl number is filed under a synthetic `work:<hash>`, which names it consistently but cannot be fetched or joined with anyone else's copy. This module asks zbMATH Open and Crossref which work an entry most likely is, and returns *candidates*: an identifier, where it came from, what it matched and how well. It never changes a work's identity and never writes the bibliography. A candidate becomes an identity when the author adds the field to their own entry, at which point it is declared like any other.

Every returned record is scored here rather than trusting either service's own score, so a confidence means the same thing whichever service answered. The core takes a `Query`, which a bibliography entry or a formatted reference string both reduce to.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loom.refs.identity import WorkId, synthetic
from loom.scan.bib import BibEntry
from loom.version import __version__

USER_AGENT = f"loom/{__version__} (+https://github.com/ikmartin/loom)"
ZBMATH = "https://api.zbmath.org/v1/document/_search"
CROSSREF = "https://api.crossref.org/works"

STRONG = 0.9
POSSIBLE = 0.75
# Seconds between two requests to one service. Crossref's public pool reports one request per second; zbMATH Open asks for a reasonable rate and states no number, so it gets the same.
SPACING = 1.0

Http = Callable[[str, dict[str, str]], bytes]


class ResolveRefused(Exception):
    """Looking up is off, the entry has too little to look up, or a service could not be reached."""


class NothingFound(ResolveRefused):
    """A service answered that it has no such record, which zbMATH Open says with a 404; a lookup with no match, not a failure."""


@dataclass(frozen=True)
class Query:
    """What is known about a work: the text a service is searched with, and the facts a match is scored against."""

    title: str
    surnames: tuple[str, ...] = ()
    year: str = ""
    text: str = ""

    @property
    def bibliographic(self) -> str:
        """One free-text reference string, which is what Crossref's `query.bibliographic` matches best."""
        return self.text or " ".join(x for x in [" ".join(self.surnames), self.title, self.year] if x)


@dataclass
class Candidate:
    """One identifier a service proposed for a work, with what it matched."""

    id: str
    source: str
    confidence: float
    title: str
    authors: list[str] = field(default_factory=list)
    year: str = ""
    also: list[str] = field(default_factory=list)

    @property
    def strength(self) -> str:
        return "strong" if self.confidence >= STRONG else "possible"


def _plain(text: str) -> str:
    """Bibliography markup removed: braces, accent commands and math delimiters, so `{{Gromov}}--{{Witten}}` compares as `Gromov-Witten`."""
    t = re.sub(r"\\[`'^\"~=.uvHck]\s*\{?\s*([A-Za-z])\s*\}?", r"\1", text)
    t = re.sub(r"\\[A-Za-z]+\s*", " ", t)
    t = t.replace("{", "").replace("}", "").replace("$", "").replace("--", "-")
    return re.sub(r"\s+", " ", t).strip()


def _fold(text: str) -> str:
    """Lowercase ASCII words, for comparing titles and names written with different conventions."""
    t = unicodedata.normalize("NFKD", _plain(text))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def query_for(entry: BibEntry) -> Query:
    """The query for a bibliography entry: its title, the surnames of its authors, and its year."""
    surnames: list[str] = []
    for part in re.split(r"\s+and\s+", entry.fields.get("author", "")):
        part = _plain(part)
        if not part or part.lower() == "others":
            continue
        surnames.append(part.split(",")[0].strip() if "," in part else part.split()[-1])
    # biblatex writes `date = {1998-06}` where BibTeX writes `year = {1998}`
    year = (entry.fields.get("year") or entry.fields.get("date") or "").strip()[:4]
    return Query(_plain(entry.fields.get("title", "")), tuple(surnames), year)


def _surname(name: str) -> str:
    """A name's surname, folded: what precedes the comma in `Arabia, Alberto`, the last word in `Alberto Arabia`."""
    folded = _fold(name.split(",")[0] if "," in name else name).split()
    return folded[-1] if folded else ""


def score(q: Query, title: str, authors: list[str], year: str) -> float:
    """How likely a returned record is the queried work, from 0 to 1.

    The title carries most of the weight, compared as folded words; the first author's surname appearing among the record's authors and a year within one each add a little, since a reprint or an online-first date moves the year and a transliteration moves the name. A title alone that matches exactly still reaches `possible`, never `strong`.

    A query that is only a formatted reference — `A. Arabia, Cycles de Schubert…, Invent. Math. 85 (1986)`, with no title known apart from the text — is scored by the record's title appearing within the text and an author's surname appearing in it, which is what a person checking the match would look for.
    """
    qt, rt = _fold(q.title), _fold(title)
    if not qt or not rt:
        return 0.0
    free_text = bool(q.text) and q.title == q.text
    if free_text:
        ratio = 1.0 if len(rt) >= 12 and f" {rt} " in f" {qt} " else difflib.SequenceMatcher(None, qt, rt).ratio()
    else:
        ratio = difflib.SequenceMatcher(None, qt, rt).ratio()
        # a subtitle one side omits should not sink an otherwise exact title
        if rt.startswith(qt) or qt.startswith(rt):
            ratio = max(ratio, 0.92)
    s = 0.75 * ratio
    folded = " ".join(_fold(a) for a in authors)
    if q.surnames and _fold(q.surnames[0]) and _fold(q.surnames[0]) in folded:
        s += 0.15
    elif free_text and any(len(sn) > 1 and f" {sn} " in f" {qt} " for sn in (_surname(a) for a in authors)):
        s += 0.15
    if q.year[:4].isdigit() and str(year)[:4].isdigit() and abs(int(q.year[:4]) - int(str(year)[:4])) <= 1:
        s += 0.10
    return round(min(1.0, s), 3)


def _zbmath_candidates(q: Query, data: dict[str, Any]) -> list[Candidate]:
    out: list[Candidate] = []
    for r in data.get("result") or []:
        title = r.get("title")
        title = title.get("title", "") if isinstance(title, dict) else str(title or "")
        authors = [a.get("name", "") for a in (r.get("contributors") or {}).get("authors", [])]
        year = str(r.get("year") or "")
        dois = [
            link["identifier"] for link in r.get("links") or [] if link.get("type") == "doi" and link.get("identifier")
        ]
        # zbMATH also knows a work's preprint, which is the identifier loom can actually fetch
        preprints = [
            link["identifier"]
            for link in r.get("links") or []
            if link.get("type") == "arxiv" and link.get("identifier")
        ]
        zbl = str(r.get("identifier") or "")
        conf = score(q, title, authors, year)
        if conf < POSSIBLE:
            continue
        ids = [f"doi:{d}" for d in dois] + ([f"zbl:{zbl}"] if zbl else []) + [f"arxiv:{a}" for a in preprints]
        if not ids:
            continue
        out.append(Candidate(ids[0], "zbMATH Open", conf, title, authors, year, ids[1:]))
    return out


def _crossref_candidates(q: Query, data: dict[str, Any]) -> list[Candidate]:
    out: list[Candidate] = []
    for it in (data.get("message") or {}).get("items", []):
        title = " ".join(it.get("title") or [])
        authors = [" ".join(x for x in [a.get("given", ""), a.get("family", "")] if x) for a in it.get("author") or []]
        parts = ((it.get("issued") or {}).get("date-parts") or [[None]])[0]
        year = str(parts[0]) if parts and parts[0] else ""
        conf = score(q, title, authors, year)
        if conf < POSSIBLE or not it.get("DOI"):
            continue
        out.append(Candidate(f"doi:{it['DOI']}", "Crossref", conf, title, authors, year))
    return out


def http_get(url: str, headers: dict[str, str]) -> bytes:
    """GET with loom's User-Agent. The default transport; tests inject their own."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return bytes(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NothingFound(url.split("?")[0]) from exc
        raise ResolveRefused(f"{url.split('?')[0]}: HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ResolveRefused(f"{url.split('?')[0]}: {exc.reason}") from exc


class Resolver:
    """Asks zbMATH Open, then Crossref, spacing requests to each and caching every answer.

    Parameters
    ----------
    cache : Path or None, default None
        A directory of raw responses keyed by request; a request already answered there is not repeated.
    http : callable, default `http_get`
        `(url, headers) -> bytes`; injected by tests so nothing touches the network.
    contact : str, default ''
        An address sent to Crossref as `mailto`, which routes requests to its polite pool. Sent only when set.
    refresh : bool, default False
        Ignore cached answers and ask again.
    """

    def __init__(
        self, cache: Path | None = None, http: Http = http_get, contact: str = "", refresh: bool = False
    ) -> None:
        self.cache = cache
        self.http = http
        self.contact = contact
        self.refresh = refresh
        self.requests = 0
        self._last: dict[str, float] = {}

    def _get_json(self, service: str, url: str, headers: dict[str, str]) -> dict[str, Any]:
        path = self.cache / (hashlib.sha256(url.encode("utf-8")).hexdigest()[:24] + ".json") if self.cache else None
        if path is not None and path.is_file() and not self.refresh:
            return dict(json.loads(path.read_text(encoding="utf-8")))
        wait = self._last.get(service, 0.0) + SPACING - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last[service] = time.monotonic()
        self.requests += 1
        data = json.loads(self.http(url, headers).decode("utf-8"))
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")
        return dict(data)

    def zbmath(self, q: Query) -> list[Candidate]:
        terms = [f"ti:{q.title}"] + ([f"au:{q.surnames[0]}"] if q.surnames else [])
        params = {"search_string": " & ".join(terms), "page": "0", "results_per_page": "5"}
        return _zbmath_candidates(q, self._get_json("zbmath", ZBMATH + "?" + urllib.parse.urlencode(params), {}))

    def crossref(self, q: Query) -> list[Candidate]:
        params = {"query.bibliographic": q.bibliographic, "rows": "5", "select": "DOI,title,author,issued"}
        if self.contact:
            params["mailto"] = self.contact
        return _crossref_candidates(q, self._get_json("crossref", CROSSREF + "?" + urllib.parse.urlencode(params), {}))

    def candidates(self, q: Query) -> list[Candidate]:
        """Every candidate for a query, best first, one per identifier.

        zbMATH Open is asked first, since it covers mathematics best and gives a Zbl number to works with no DOI. Crossref is asked when zbMATH found nothing strong, or found a strong match with no DOI, since a DOI is the identifier a bibliography most usefully carries. A failure at one service is not a failure of the lookup.
        """
        if not q.title:
            raise ResolveRefused("the entry has no title to look up")
        found: list[Candidate] = []
        errors: list[str] = []
        try:
            found += self.zbmath(q)
        except NothingFound:
            pass
        except (ResolveRefused, ValueError) as exc:
            errors.append(str(exc))
        best = max(found, key=lambda c: c.confidence, default=None)
        if best is None or best.strength != "strong" or not best.id.startswith("doi:"):
            try:
                found += self.crossref(q)
            except NothingFound:
                pass
            except (ResolveRefused, ValueError) as exc:
                errors.append(str(exc))
        if not found and errors:
            raise ResolveRefused("; ".join(errors))
        return merge(found)


RANK = {"doi": 0, "arxiv": 1, "mr": 2, "zbl": 3}


def merge(found: list[Candidate]) -> list[Candidate]:
    """One candidate per work, best first.

    Two services describing the same record — the same identifier, or the same title and year — are one work: their identifiers are pooled and the lead is the most useful of them (a DOI, then a preprint, then MR, then Zbl), and the confidence is the higher of the two. Ties between different works go to the one with the more useful identifier.
    """
    works: list[Candidate] = []
    for c in sorted(found, key=lambda c: -c.confidence):
        ids = {c.id.lower(), *(a.lower() for a in c.also)}
        same = next(
            (
                w
                for w in works
                if ids & {w.id.lower(), *(a.lower() for a in w.also)}
                or (_fold(w.title) == _fold(c.title) and (w.year[:4] == c.year[:4] or not w.year or not c.year))
            ),
            None,
        )
        if same is None:
            ranked = sorted([c.id, *c.also], key=lambda x: RANK.get(x.partition(":")[0], 9))
            works.append(Candidate(ranked[0], c.source, c.confidence, c.title, list(c.authors), c.year, ranked[1:]))
            continue
        pool = [same.id, *same.also] + [
            x for x in [c.id, *c.also] if x.lower() not in {y.lower() for y in [same.id, *same.also]}
        ]
        pool.sort(key=lambda x: RANK.get(x.partition(":")[0], 9))
        same.id, same.also = pool[0], pool[1:]
        if c.source not in same.source:
            same.source += f", {c.source}"
        same.confidence = max(same.confidence, c.confidence)
    works.sort(key=lambda w: (-w.confidence, RANK.get(w.id.partition(":")[0], 9)))
    return works


def record_path(root: Path, entry: BibEntry) -> Path:
    """Where the candidates for an entry are kept: in the directory of the synthetic work it is filed under.

    The synthetic identifier is a hash of the entry's authors, title and year, so editing any of them names a different directory and an answer about the old entry is never shown for the new one.
    """
    return root / "refs" / synthetic(entry).path / "resolved.json"


def save(root: Path, entry: BibEntry, found: list[Candidate]) -> Path:
    """Write an entry's candidates beside its synthetic work; returns the file."""
    path = record_path(root, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "citekey": entry.key,
        "looked_up": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "candidates": [asdict(c) for c in found],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load(root: Path, entry: BibEntry) -> list[Candidate]:
    """The candidates recorded for an entry, or none; reading never touches the network."""
    path = record_path(root, entry)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [Candidate(**c) for c in data.get("candidates", [])]
    except (OSError, ValueError, TypeError):
        return []


def as_workid(c: Candidate) -> WorkId:
    """A candidate's identifier, marked as resolved rather than declared."""
    scheme, _, value = c.id.partition(":")
    return WorkId(scheme, value, "resolved")
