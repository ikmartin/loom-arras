"""A crawled work's record, `refs/<scheme>/<id>/work.json` (book 8.13.4).

One record per work, beside whatever was downloaded for it: what the work is, the identifiers it is known by, its subjects, its references, and how the crawl reached it. Several sources describe one work, so a record is built by merging, and identifiers are compared in one normal form.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loom.refs.identity import WorkId
from loom.render.publish import write_atomic

RECORD = 1
RANK = {"doi": 0, "arxiv": 1, "mr": 2, "zbl": 3, "work": 4}
_ARXIV_VERSION = re.compile(r"v\d+$")


def norm(ident: str) -> str:
    """One spelling per identifier: the scheme lowercased, a DOI's value lowercased (DOIs are case-insensitive), an arXiv number without its version (every version is the same work)."""
    scheme, _, value = ident.strip().partition(":")
    scheme = scheme.lower()
    value = value.strip()
    if scheme == "doi":
        value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value, flags=re.I).lower()
        m = re.match(r"^10\.48550/arxiv\.(.+)$", value)
        if m:
            return "arxiv:" + _ARXIV_VERSION.sub("", m.group(1))
    if scheme == "arxiv":
        value = _ARXIV_VERSION.sub("", value)
    return f"{scheme}:{value}"


def ranked(ids: list[str]) -> list[str]:
    """Identifiers without duplicates, most useful first: DOI, arXiv, MR, Zbl."""
    seen: dict[str, str] = {}
    for i in ids:
        seen.setdefault(norm(i), i)
    return sorted(seen.values(), key=lambda i: RANK.get(i.partition(":")[0].lower(), 9))


@dataclass
class Reference:
    """One entry of a work's reference list: an identifier where a source resolved it, the display text otherwise.

    `zbmath` is zbMATH's own document number when zbMATH matched the entry without a DOI, which identifies the work exactly by one request rather than by a lookup; `msc` is what zbMATH says about its subject, which lets the subject filter run without asking at all.
    """

    id: str | None = None
    text: str | None = None
    zbmath: int | None = None
    msc: list[str] = field(default_factory=list)


@dataclass
class Work:
    """Everything the crawl knows about one work.

    `home` is the directory it is filed under, relative to the quilt: `refs/` and its primary identifier's path. A depth-1 work keeps the identifier its bibliography entry declares, version included, so its record sits beside what `loom digest fetch` and `loom refs add` put there.
    """

    ids: list[str]
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    msc: list[str] = field(default_factory=list)
    arxiv_category: str = ""
    references: list[Reference] = field(default_factory=list)
    references_known: bool = False
    depth: int = 0
    reached_from: list[str] = field(default_factory=list)
    reached_by: str = ""
    citekeys: list[str] = field(default_factory=list)
    open_pdf: str = ""
    download: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, Any] = field(default_factory=dict)
    home: str = ""

    @property
    def key(self) -> str:
        return norm(self.ids[0])

    @property
    def arxiv(self) -> str | None:
        return next((i.partition(":")[2] for i in self.ids if i.lower().startswith("arxiv:")), None)

    @property
    def doi(self) -> str | None:
        return next((i.partition(":")[2] for i in self.ids if i.lower().startswith("doi:")), None)

    @property
    def downloadable(self) -> str:
        """`source` from arXiv, `pdf` from an open copy, or '' when only metadata is to be had."""
        return "source" if self.arxiv else "pdf" if self.open_pdf else ""

    def add_ids(self, more: list[str]) -> None:
        self.ids = ranked([*self.ids, *more])

    def add_references(self, more: list[Reference]) -> None:
        """Merge a source's reference list: one entry per identifier, and text entries only where no source resolved anything."""
        known = {norm(r.id) for r in self.references if r.id}
        for r in more:
            if r.id and norm(r.id) not in known:
                known.add(norm(r.id))
                self.references.append(r)
            elif not r.id and r.text and not any(x.text == r.text for x in self.references):
                self.references.append(r)
        if more:
            self.references_known = True

    def merge(self, other: Work) -> None:
        """Take in a record found to name this same work under another identifier."""
        self.add_ids(other.ids)
        self.fill(other.title, other.authors, other.year, other.msc)
        self.arxiv_category = self.arxiv_category or other.arxiv_category
        self.add_references(other.references)
        self.references_known = self.references_known or other.references_known
        self.depth = min(d for d in (self.depth, other.depth) if d) if self.depth or other.depth else 0
        self.reached_from += [k for k in other.reached_from if k not in self.reached_from]
        self.citekeys += [k for k in other.citekeys if k not in self.citekeys]
        self.open_pdf = self.open_pdf or other.open_pdf
        self.download = self.download or other.download
        for k, v in other.sources.items():
            self.sources.setdefault(k, v)
        self.home = self.home or other.home

    def fill(
        self, title: str = "", authors: list[str] | None = None, year: int | None = None, msc: list[str] | None = None
    ) -> None:
        """Take what a source knows that the record does not."""
        self.title = self.title or title
        self.authors = self.authors or list(authors or [])
        self.year = self.year or year
        for code in msc or []:
            if code not in self.msc:
                self.msc.append(code)


def home_of(ident: str) -> str:
    """The directory an identifier's work is filed under, relative to the quilt."""
    scheme, _, value = ident.partition(":")
    return "refs/" + WorkId(scheme.lower(), value).path


def save(root: Path, work: Work) -> Path:
    """Write a work's record into its home; returns the file."""
    work.home = work.home or home_of(work.ids[0])
    path = root / work.home / "work.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"record": RECORD, **asdict(work)}
    # whole or not at all: a fetch killed mid-write must not leave a record that no longer loads
    write_atomic(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    return path


def load(path: Path) -> Work | None:
    """A work's record, or None when the file is not one loom can read."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("record", None)
        data["references"] = [Reference(**r) for r in data.get("references", [])]
        return Work(**data)
    except (OSError, ValueError, TypeError):
        return None


def load_all(root: Path) -> dict[str, Work]:
    """Every work record under `refs/`, by normal key."""
    out: dict[str, Work] = {}
    for path in sorted((root / "refs").glob("*/*/work.json")):
        w = load(path)
        if w and w.ids:
            out[w.key] = w
    return out
