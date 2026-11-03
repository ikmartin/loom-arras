"""Looking one pasted identifier up, for a work a person adds to the library by hand (plan 0.24.2).

A DOI is asked of doi.org by content negotiation, which answers for every registry's DOIs, so its 404 means the DOI names nothing. An arXiv id is asked of the arXiv API, a zbMATH number of zbMATH Open. A BibTeX entry needs nothing asked: it is what it says. ISBNs and MathSciNet numbers are recognised and not looked up, since loom uses no service for them. Every answer says what it found, the key the work would be filed as, whether loom can digest it, and which works in the library may already be it.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from loom.refs.identity import KINDS, Recognised, WorkId, arxiv_base, declared, recognise
from loom.refs.resolve import ZBMATH, Http, NothingFound, ResolveRefused, _fold, http_get
from loom.scan.bib import BibEntry

DOI_ORG = "https://doi.org/"
ARXIV_API = "https://export.arxiv.org/api/query"
_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV_NS = "{http://arxiv.org/schemas/atom}"
#: The fields of a pasted entry loom keeps: its own `loom-*` fields are loom's to write, never a paste's.
_OWN = re.compile(r"^loom-")


@dataclass
class Found:
    """What a lookup found.

    `state` is `found`, `missing` (the identifier names nothing), `unreachable` (the service could not be asked; `message` says why), `offline` (it needs the network, which this run may not use) or `cannot` (an ISBN, a MathSciNet number, or text that is no identifier). `digest` is `source` when a LaTeX source can be fetched (an arXiv id), else `lookup`: a run looks for an arXiv copy by title, and failing that the person files the PDF and an agent proposes results from its pages.
    """

    state: str
    kind: str
    value: str = ""
    entry: dict[str, str] = field(default_factory=dict)
    key: str = ""
    digest: str = ""
    duplicates: list[str] = field(default_factory=list)
    message: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "kind": self.kind,
            "label": KINDS[self.kind],
            "value": self.value,
            "entry": dict(self.entry),
            "key": self.key,
            "digest": self.digest,
            "duplicates": list(self.duplicates),
            "message": self.message,
        }


def _surnames(author: str) -> list[str]:
    out = []
    for part in re.split(r"\s+and\s+", author):
        part = part.strip()
        if part:
            out.append(part.split(",")[0].strip() if "," in part else part.split()[-1])
    return out


def key_for(entry: Mapping[str, str], taken: set[str], wanted: str = "") -> str:
    """The key a work is filed as: `wanted` when it is free, else the first author's surname's first three letters and the year's last two (`Man08`); a taken one gets a letter (`Man08A`)."""
    from loom.refs.scan import _free_key

    if wanted and wanted not in taken:
        return wanted
    surname = (_surnames(entry.get("author", "")) or ["Work"])[0]
    letters = re.sub(r"[^A-Za-z]", "", unicodedata.normalize("NFKD", surname)) or "Work"
    year = re.sub(r"\D", "", entry.get("year", ""))[-2:]
    base = wanted or (letters[:1].upper() + letters[1:3].lower() + year)
    return base if base not in taken else _free_key(base, taken)


def duplicates(entry: Mapping[str, str], wid: WorkId | None, bib: Mapping[str, BibEntry]) -> list[str]:
    """The works already in the library that may be this one: the same identifier, an arXiv id compared without its version, or the same title and year."""
    ids = {
        (w.scheme, arxiv_base(w.value) if w.scheme == "arxiv" else w.value.lower())
        for w in declared(BibEntry("", "misc", dict(entry)))
    }
    if wid is not None:
        ids.add((wid.scheme, arxiv_base(wid.value) if wid.scheme == "arxiv" else wid.value.lower()))
    title, year = _fold(entry.get("title", "")), entry.get("year", "")
    out = []
    for key, other in bib.items():
        theirs = {(w.scheme, arxiv_base(w.value) if w.scheme == "arxiv" else w.value.lower()) for w in declared(other)}
        same_title = title and _fold(other.fields.get("title", "")) == title and other.fields.get("year", "") == year
        if ids & theirs or same_title:
            out.append(key)
    return sorted(out, key=str.lower)


def _from_csl(data: dict[str, Any]) -> dict[str, str]:
    """BibTeX fields from doi.org's CSL JSON."""
    title = data.get("title") or ""
    title = " ".join(title) if isinstance(title, list) else str(title)
    authors = [
        ", ".join(x for x in [a.get("family", ""), a.get("given", "")] if x) or a.get("literal", "")
        for a in data.get("author") or []
    ]
    parts = ((data.get("issued") or data.get("published") or {}).get("date-parts") or [[None]])[0]
    venue = data.get("container-title") or ""
    venue = " ".join(venue) if isinstance(venue, list) else str(venue)
    out = {
        "author": " and ".join(a for a in authors if a),
        "title": title,
        "year": str(parts[0]) if parts and parts[0] else "",
        "journal" if venue else "publisher": venue or str(data.get("publisher") or ""),
        "doi": str(data.get("DOI") or ""),
    }
    return {k: v for k, v in out.items() if v}


def _from_atom(data: bytes, asked: str) -> dict[str, str] | None:
    """BibTeX fields from the arXiv API's Atom feed, or None when it holds no paper (arXiv answers an unknown id with an error entry)."""
    root = ET.fromstring(data)  # noqa: S314 -- the arXiv API's own feed, parsed for text only
    for entry in root.iter(f"{_ATOM}entry"):
        ident = (entry.findtext(f"{_ATOM}id") or "").strip()
        if not ident or "/api/errors" in ident:
            continue
        title = re.sub(r"\s+", " ", entry.findtext(f"{_ATOM}title") or "").strip()
        names = [re.sub(r"\s+", " ", a.findtext(f"{_ATOM}name") or "").strip() for a in entry.iter(f"{_ATOM}author")]
        authors = [f"{n.split()[-1]}, {' '.join(n.split()[:-1])}".strip(", ") for n in names if n]
        out = {
            "author": " and ".join(authors),
            "title": title,
            "year": (entry.findtext(f"{_ATOM}published") or "")[:4],
            "eprint": asked,
            "archiveprefix": "arXiv",
            "doi": (entry.findtext(f"{_ARXIV_NS}doi") or "").strip(),
            "journal": (entry.findtext(f"{_ARXIV_NS}journal_ref") or "").strip(),
        }
        return {k: v for k, v in out.items() if v} if title else None
    return None


def _from_zbmath(data: dict[str, Any], zbl: str) -> dict[str, str] | None:
    """BibTeX fields from zbMATH Open's answer, read as `refs.resolve` reads its candidates, or None when it holds no document."""
    for r in data.get("result") or []:
        title = r.get("title")
        title = title.get("title", "") if isinstance(title, dict) else str(title or "")
        authors = [a.get("name", "") for a in (r.get("contributors") or {}).get("authors", []) if a.get("name")]
        links = r.get("links") or []
        doi = next((x["identifier"] for x in links if x.get("type") == "doi" and x.get("identifier")), "")
        arxiv = next((x["identifier"] for x in links if x.get("type") == "arxiv" and x.get("identifier")), "")
        out = {
            "author": " and ".join(authors),
            "title": title,
            "year": str(r.get("year") or ""),
            "zbl": zbl,
            "doi": doi,
        }
        if arxiv:
            out.update(eprint=arxiv, archiveprefix="arXiv")
        return {k: v for k, v in out.items() if v}
    return None


def look_up(text: str | Recognised, bib: Mapping[str, BibEntry], *, online: bool, http: Http | None = None) -> Found:
    """What a pasted text names, as an entry loom would write for it.

    Parameters
    ----------
    text : str or Recognised
        What was pasted, or what `recognise` made of it.
    bib : mapping
        The library's entries, for the key and the duplicates.
    online : bool
        Whether this lookup may use the network: `[library] online`, or the person's allowance for this one. A BibTeX entry never needs it.
    http : callable, optional
        `(url, headers) -> bytes`; default `refs.resolve.http_get`, which raises `NothingFound` on a 404.

    Returns
    -------
    Found
        Its state, and when found the entry, the key, whether loom can digest it and the works it may duplicate.
    """
    rec = text if isinstance(text, Recognised) else recognise(text)
    if rec.kind in ("isbn", "mr", "unknown"):
        why = (
            "Loom has no service to look this up: paste its DOI, its arXiv id or its BibTeX entry instead."
            if rec.kind != "unknown"
            else "This is not an identifier loom recognises: paste a DOI, an arXiv id, a zbMATH number or a BibTeX entry."
        )
        return Found("cannot", rec.kind, rec.value, message=why)
    if rec.kind == "bibtex":
        assert rec.entry is not None
        entry = {k: v for k, v in rec.entry.fields.items() if not _OWN.match(k)}
        return _found(rec, entry, bib, wanted=rec.entry.key)
    if not online:
        return Found(
            "offline", rec.kind, rec.value, message="Looking this up needs the network, which this quilt has off."
        )
    get = http or http_get
    try:
        if rec.kind == "doi":
            raw = get(
                DOI_ORG + urllib.parse.quote(rec.value, safe="/"), {"Accept": "application/vnd.citationstyles.csl+json"}
            )
            entry = _from_csl(json.loads(raw.decode("utf-8")))
        elif rec.kind == "arxiv":
            raw = get(
                ARXIV_API + "?" + urllib.parse.urlencode({"id_list": rec.value}), {"Accept": "application/atom+xml"}
            )
            got = _from_atom(raw, rec.value)
            if got is None:
                return Found("missing", rec.kind, rec.value, message=f"arXiv has no paper {rec.value}.")
            entry = got
        else:
            params = {"search_string": f"an:{rec.value}", "page": "0", "results_per_page": "1"}
            raw = get(ZBMATH + "?" + urllib.parse.urlencode(params), {})
            got = _from_zbmath(json.loads(raw.decode("utf-8")), rec.value)
            if got is None:
                return Found("missing", rec.kind, rec.value, message=f"zbMATH Open has no document Zbl {rec.value}.")
            entry = got
    except NothingFound:
        where = {
            "doi": f"This DOI did not resolve: doi.org has no record of {rec.value}.",
            "arxiv": f"arXiv has no paper {rec.value}.",
        }
        return Found(
            "missing", rec.kind, rec.value, message=where.get(rec.kind, f"Nothing is recorded as {rec.value}.")
        )
    except (ResolveRefused, ValueError, ET.ParseError) as exc:
        return Found("unreachable", rec.kind, rec.value, message=str(exc))
    return _found(rec, entry, bib)


def _found(rec: Recognised, entry: dict[str, str], bib: Mapping[str, BibEntry], wanted: str = "") -> Found:
    fetchable = (
        rec.kind == "arxiv" or bool(entry.get("eprint")) or str(entry.get("doi", "")).lower().startswith("10.48550/")
    )
    return Found(
        "found",
        rec.kind,
        rec.value,
        entry,
        key_for(entry, set(bib), wanted),
        "source" if fetchable else "lookup",
        duplicates(entry, rec.work_id, bib),
    )
