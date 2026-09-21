"""The quilt's own bibliography (book 8.15): `digests/bibliography.bib`, gathered from the canon documents and only ever appended to.

A canon document cites through a `.bib` it names or through an inline `thebibliography`; both are read. An entry from a `.bib` is copied verbatim, so nothing the author wrote is lost. A `\\bibitem` is free text, so it becomes an entry holding that text in `loom-text`, the identifiers found in it, and a best-effort author, title and year, marked `loom-parsed = {heuristic}`. An entry already in the file is never rewritten or removed: the author corrects a heuristic entry by hand, and the next scan leaves the correction alone.
"""

from __future__ import annotations

import json
import re
import shutil
import string
from dataclasses import dataclass, field
from pathlib import Path

from loom.clock import stamp
from loom.refs.identity import WorkId, primary
from loom.refs.ingest import filename_title, identifiers_in, look_at
from loom.refs.pages import STORAGE, page_texts, sha256_of, storage_root, write_map
from loom.refs.unreadable import declarations
from loom.scan.bib import BIBLIOGRAPHY, BibEntry, parse_bib, raw_entries
from loom.scan.quilt import Quilt
from loom.scan.scan import canon_documents
from loom.scan.source import blank_comments
from loom.scan.tokenize import match_group, read_args, read_optional, tokenize

HEADER = (
    "% The quilt's bibliography, written by `loom refs scan` from the canon documents (book 8.15).\n"
    "% Loom only appends: an entry here is never rewritten or removed, so correct one by hand and it stays corrected.\n"
)

_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s{},]+[^\s{},.;])")
_ARXIV = re.compile(
    r"(?:arXiv[:\s]*|arxiv\.org/abs/)\s*(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)", re.I
)
_MR = re.compile(r"\bMR\s*:?\s*(\d{5,8})\b")
_ZBL = re.compile(r"\bZbl\s*:?\s*(\d{4}\.\d{5}|\d{3,4}\.\d{5})\b")
_YEAR = re.compile(r"\((?:[^()]*?\b)?((?:19|20)\d\d)\)")
_ANY_YEAR = re.compile(r"\b((?:19|20)\d\d)\b")
#: `K. Behrend, B. Fantechi,` -- initials and surnames, the opening of a hand-written entry that italicises nothing.
_AUTHOR = r"[A-Z]\.(?:\s*[~\-]?\s*[A-Z]\.)*\s*~?\s*(?:van |von |de |della )?[A-Z][A-Za-z'’\-]+"
_AUTHORS = re.compile(rf"^\s*{_AUTHOR}(?:\s*(?:,|and|,\s*and)\s+{_AUTHOR})*", re.S)
_TITLE_ARG = re.compile(r"\\(?:textit|emph|textsl)\s*\{")
_TITLE_GROUP = re.compile(r"\{\s*\\(?:it|em|sl|itshape)\b\s*")


@dataclass
class Candidate:
    key: str
    text: str  # BibTeX, ready to append
    source: str  # the canon document it came from
    compare: str = ""  # the text two sources are compared by


@dataclass
class ScanReport:
    canon: int = 0  # canon documents read
    added: list[Candidate] = field(default_factory=list)
    present: int = 0  # entries the file already had
    conflicts: list[tuple[str, str, str]] = field(default_factory=list)  # (key, kept source, other source)
    missing_bib: list[tuple[str, str]] = field(default_factory=list)  # (canon document, .bib it names that is absent)
    copied: list[tuple[str, str]] = field(default_factory=list)  # (seed file, where it was filed)
    already: int = 0  # documents the ledger had seen before
    derived: list[str] = field(default_factory=list)  # entries offered for a document that stated an identifier
    unnamed: list[str] = field(default_factory=list)  # entries offered for a document that stated none
    siblings: list[tuple[str, str]] = field(default_factory=list)  # (new key, the work it is a second document of)
    unmapped: list[tuple[str, str]] = field(default_factory=list)  # (file, why no page text was written)
    adopted: list[tuple[str, str]] = field(default_factory=list)  # (new key, the store directory nothing named)
    forgotten: int = 0  # stored documents a tombstone says not to offer again

    def lines(self) -> list[str]:
        """What a person reads: one line of counts, then each conflict and each missing `.bib`."""
        heuristic = sum(1 for c in self.added if "loom-parsed" in c.text)
        out = [
            f"{BIBLIOGRAPHY}: {len(self.added)} added"
            + (f" ({heuristic} from \\bibitem text, parsed heuristically)" if heuristic else "")
            + f", {self.present} already there"
        ]
        out += [f"conflict: {key} differs between {kept} (kept) and {other}" for key, kept, other in self.conflicts]
        if self.copied or self.already:
            out.append(
                f"{SEED}/: {len(self.copied)} copied into {STORAGE}"
                + (f", {self.already} already copied before" if self.already else "")
                + (
                    f", {len(self.derived) + len(self.unnamed)} new entries offered"
                    if self.derived or self.unnamed
                    else ""
                )
            )
        out += [f"{new} is a second document for {old}, filed beside it" for new, old in self.siblings]
        out += [f"{key} adopts {where}, which the bibliography no longer named" for key, where in self.adopted]
        if self.forgotten:
            out.append(f"{self.forgotten} stored document(s) not offered: forgotten (loom refs forget --undo restores)")
        out += [f"{name}: no page text ({why})" for name, why in self.unmapped]
        out += [f"{doc} names {name}.bib, which does not exist" for doc, name in self.missing_bib]
        if not self.canon:
            out.append("no canon documents to gather from: the bibliography grows when you `loom canonize` a document")
        return out


def _unbrace(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("{", "").replace("}", "")).strip()


def _title_of(text: str) -> tuple[str, int, int] | None:
    """The first italic group, `\\textit{...}` or `{\\it ...}` and kin, with its span: amsplain, amsalpha and most hand-written lists set the title that way."""
    hits = [(m.start(), m.end() - 1, m.end()) for m in _TITLE_ARG.finditer(text)]
    hits += [(m.start(), m.start(), m.end()) for m in _TITLE_GROUP.finditer(text)]
    for start, brace, inner in sorted(hits):
        end = match_group(text, brace)
        if end > 0:
            return text[inner : end - 1], start, end
    return None


def bibitem_fields(text: str) -> dict[str, str]:
    """Best-effort fields from one `\\bibitem`'s free text: identifiers by pattern, then title, author and year."""
    fields: dict[str, str] = {"loom-text": re.sub(r"\s+", " ", text).strip(), "loom-parsed": "heuristic"}
    flat = re.sub(
        r"\\url\s*\{([^}]*)\}|\\href\s*\{([^}]*)\}\{[^}]*\}", lambda m: " " + (m.group(1) or m.group(2)) + " ", text
    )
    if m := _ARXIV.search(flat):
        fields["eprint"] = m.group(1)
        fields["archiveprefix"] = "arXiv"
    if m := _DOI.search(flat):
        fields["doi"] = m.group(1)
    if m := _MR.search(flat):
        fields["mrnumber"] = m.group(1)
    if m := _ZBL.search(flat):
        fields["zbl"] = m.group(1)
    title = _title_of(text)
    if title:
        head, title_text, rest = text[: title[1]], title[0], text[title[2] :]
    else:
        # No italics: an entry reads `K. Behrend, Gromov-Witten invariants in algebraic geometry. Invent. Math. ...`, so the authors end where the initials stop and the title ends at the first sentence break.
        m = _AUTHORS.match(text)
        head = m.group(0) if m else ""
        after = text[len(head) :].lstrip(" ,")
        stop = re.search(r"\.(?=\s|$)", after)
        title_text, rest = (after[: stop.start()], after[stop.end() :]) if stop else ("", after)
    cleaned = _unbrace(title_text).rstrip(",. ")
    if cleaned:
        fields["title"] = cleaned
    author = _unbrace(head).rstrip(",:; ")
    if author and len(author) < 300:
        fields["author"] = author
    year = _YEAR.search(rest) or _ANY_YEAR.search(rest)
    if year:
        fields["year"] = year.group(1)
    return fields


def bibitems(text: str) -> dict[str, str]:
    """Every `\\bibitem[label]{key} text` in `text`'s `thebibliography` environments, key -> raw text."""
    clean = blank_comments(text)
    out: dict[str, str] = {}
    for env in re.finditer(r"\\begin\s*\{thebibliography\}(.*?)\\end\s*\{thebibliography\}", clean, re.S):
        body_start = env.start(1)
        items = [t for t in tokenize(env.group(1)) if t.kind == "cmd" and t.value == "bibitem"]
        for i, t in enumerate(items):
            _, _, _, pos = read_optional(env.group(1), t.end)
            (key,), _, after = read_args(env.group(1), pos, "m")
            if key is None:
                continue
            stop = items[i + 1].start if i + 1 < len(items) else len(env.group(1))
            raw = text[body_start + after : body_start + stop]
            out.setdefault(key.strip(), raw.strip())
    return out


def _bibtex(key: str, fields: dict[str, str]) -> str:
    etype = "article" if "title" in fields else "misc"
    lines = [f"@{etype}{{{key},"]
    for name in (
        "author",
        "title",
        "year",
        "eprint",
        "archiveprefix",
        "doi",
        "mrnumber",
        "zbl",
        "loom-text",
        "loom-source",
        "loom-copy-of",
        "loom-parsed",
    ):
        if name in fields:
            lines.append(f"  {name} = {{{fields[name]}}},")
    return "\n".join(lines) + "\n}\n"


def _named_bibs(root: Path, text: str) -> tuple[list[Path], list[str]]:
    """The `.bib` files a document names through `\\bibliography` or `\\addbibresource`, resolved against the quilt root; the names that resolve to nothing."""
    clean = blank_comments(text)
    found: list[Path] = []
    absent: list[str] = []
    for t in tokenize(clean):
        if t.kind != "cmd" or t.value not in ("bibliography", "addbibresource"):
            continue
        spec = "m" if t.value == "bibliography" else "om"
        values, _, _ = read_args(clean, t.end, spec)
        names = values[-1]
        for name in (names or "").split(","):
            name = name.strip()
            if not name:
                continue
            p = root / (name if name.endswith(".bib") else name + ".bib")
            if p.is_file():
                found.append(p)
            else:
                absent.append(name)
    return found, absent


def candidates(quilt: Quilt, report: ScanReport) -> dict[str, Candidate]:
    """Every entry the canon documents carry, first source winning; a second source disagreeing is a conflict."""
    root = quilt.root
    out: dict[str, Candidate] = {}

    def offer(c: Candidate) -> None:
        kept = out.setdefault(c.key, c)
        if (
            kept is not c
            and kept.source != c.source
            and re.sub(r"\s+", "", kept.compare) != re.sub(r"\s+", "", c.compare)
        ):
            report.conflicts.append((c.key, kept.source, c.source))

    docs = canon_documents(quilt)
    report.canon = len(docs)
    for bib in sorted((root / SEED).glob("*.bib")) if (root / SEED).is_dir() else []:
        raw = bib.read_text(encoding="utf-8", errors="replace")
        source = bib.relative_to(root).as_posix()
        for key, entry_text in raw_entries(raw).items():
            offer(Candidate(key, entry_text.rstrip() + "\n", source, entry_text))
    for rel in docs:
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        bibs, absent = _named_bibs(root, text)
        report.missing_bib.extend((rel, name) for name in absent)
        for bib in bibs:
            raw = bib.read_text(encoding="utf-8", errors="replace")
            source = bib.relative_to(root).as_posix()
            for key, entry_text in raw_entries(raw).items():
                offer(Candidate(key, entry_text.rstrip() + "\n", f"{rel} via {source}", entry_text))
        for key, item in bibitems(text).items():
            offer(Candidate(key, _bibtex(key, bibitem_fields(item)), rel, item))
    return out


def _append(path: Path, entries: list[Candidate]) -> None:
    """Add entries to the bibliography. Only ever appends, so a correction made by hand outlives every later scan."""
    if not entries:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    prior = path.read_text(encoding="utf-8") if path.is_file() else HEADER
    chunks = [prior if prior.endswith("\n") else prior + "\n"]
    for c in entries:
        chunks.append(f"\n% from {c.source}\n{c.text}")
    path.write_text("".join(chunks), encoding="utf-8")


def scan_bibliography(quilt: Quilt, *, write: bool = True) -> ScanReport:
    """Append every canon entry the quilt's bibliography does not have yet.

    Parameters
    ----------
    quilt : Quilt
        The quilt to scan.
    write : bool, default True
        Append to `digests/bibliography.bib`; False reports what would be added.

    Returns
    -------
    ScanReport
        What was added, how many entries were already there, conflicts between canon documents, and named `.bib` files that do not exist.
    """
    report = ScanReport()
    path = quilt.root / BIBLIOGRAPHY
    existing = parse_bib(path.read_text(encoding="utf-8", errors="replace")) if path.is_file() else {}
    from_canon = [c for key, c in candidates(quilt, report).items() if key not in existing]
    report.present = len(existing)
    report.added += from_canon
    if write:
        _append(path, from_canon)
        existing = parse_bib(path.read_text(encoding="utf-8", errors="replace")) if path.is_file() else existing
    else:
        existing = {**existing, **parse_bib("".join(c.text for c in from_canon))}
    # the documents the author dropped, after the entries, so a PDF is matched against everything the bibliography now knows
    from_seed = [c for c in copy_documents(quilt, existing, report) if c.key not in existing]
    report.added += from_seed
    if write:
        _append(path, from_seed)
        existing = parse_bib(path.read_text(encoding="utf-8", errors="replace")) if path.is_file() else existing
    else:
        existing = {**existing, **parse_bib("".join(c.text for c in from_seed))}
    # last, and against everything the bibliography now knows: a document the store holds and no entry names
    orphans = [c for c in adopt_orphans(quilt, existing, report) if c.key not in existing]
    report.added += orphans
    if write:
        _append(path, orphans)
    return report


#: The author's seed space: where they drop reference PDFs and `.bib` files. Loom reads it and never writes it (book 8.16).
SEED = "refs"
#: Every document ever copied into the store, by content hash, so a file is copied once and never again -- not when it is renamed, not when it is deleted from the seed space and not when it is dropped a second time.
LEDGER = "copied.json"


def load_ledger(root: Path) -> dict[str, dict[str, str]]:
    """The copy ledger, by sha256; an unreadable or absent ledger reads as empty, which costs a re-copy and never a loss."""
    path = storage_root(root) / LEDGER
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def record_copy(root: Path, sha: str, source: str, dest: str) -> None:
    """Append one copy to the ledger. Nothing is ever removed from it."""
    path = storage_root(root) / LEDGER
    ledger = load_ledger(root)
    ledger[sha] = {"from": source, "to": dest, "when": stamp()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _free_key(key: str, taken: set[str]) -> str:
    """`Man12`, then `Man12A`, `Man12B`: the sibling entry a second document for one work gets (DR-192)."""
    for letter in string.ascii_uppercase:
        if f"{key}{letter}" not in taken:
            return f"{key}{letter}"
    n = 2
    while f"{key}{n}" in taken:
        n += 1
    return f"{key}{n}"


def _own_account(pdf: Path) -> tuple[WorkId | None, dict[str, str]]:
    """What the document says about itself: the identifier on its first pages, and a heuristic title and year.

    Only the filename is read for a title, and only when a reference manager wrote it (`Author - 2019 - The Title.pdf`), because that came from a catalogue. A title guessed from page one is not: the longest early line on a real paper is a sentence of the abstract, which is the mistake `title_lines` exists to record.
    """
    fields: dict[str, str] = {}
    named = filename_title(pdf.stem)
    if named and named != pdf.stem:
        fields["title"] = named
        stem_year = re.search(r"\b((?:19|20)\d\d)\b", pdf.stem)
        if stem_year:
            fields["year"] = stem_year.group(1)
    try:
        pages = page_texts(pdf)
    except Exception:  # noqa: BLE001 -- an unreadable PDF is reported, never fatal
        return None, fields
    head = "\n".join(pages[:2])
    dois, arxivs = identifiers_in(head)
    if arxivs:
        return WorkId("arxiv", sorted(arxivs)[0], "candidate"), fields
    if dois:
        return WorkId("doi", sorted(dois)[0], "candidate"), fields
    return None, fields


def _entry_for(pdf: Path, wid: WorkId | None, fields: dict[str, str], key: str, source: str = "") -> str:
    """A bibliography entry for a document that had none, carrying where it came from.

    `source` overrides the seed path for a document that did not come from the seed space; it is what a later scan reads to know this entry already names that document.
    """
    out = dict(fields)
    if wid is not None:
        if wid.scheme == "arxiv":
            out["eprint"], out["archiveprefix"] = wid.value, "arXiv"
        else:
            out[wid.scheme] = wid.value
    out["loom-source"] = source or f"{SEED}/{pdf.name}"
    out["loom-parsed"] = "heuristic"
    return _bibtex(key, out)


def _derived_key(pdf: Path, sha: str, taken: set[str]) -> str:
    """A citekey for a document nothing in the bibliography claims: its filename, or its hash when the name says nothing."""
    stem = re.sub(r"[^A-Za-z0-9]", "", pdf.stem)[:24]
    key = stem or f"pdf{sha[:8]}"
    return key if key not in taken else _free_key(key, taken)


def adopt_orphans(quilt: Quilt, bib: dict[str, BibEntry], report: ScanReport) -> list[Candidate]:
    """Offer an entry for every document in the store that no bibliography entry names.

    The store outlives the bibliography. An entry deleted by hand, a citekey renamed, an import that filed a paper and then failed -- each leaves a directory holding a PDF, its page text and possibly a whole digest, which nothing can now reach: the viewer lists works by entry, and the copy ledger will not offer the file again because it remembers copying it. The document is not lost, only unnamed, and an entry is what names it.

    Parameters
    ----------
    quilt : Quilt
        The quilt whose store to walk.
    bib : dict of str to BibEntry
        The bibliography as it stands, including anything this scan has just added.
    report : ScanReport
        Filled in with one `adopted` row per orphan.

    Returns
    -------
    list of Candidate
        Entries to append, each carrying the store path it adopts and what the document says about itself.

    Notes
    -----
    What the entry says comes from the document and from the ledger's record of where it was dropped, never from a lookup: this runs offline, like the rest of the scan. A directory with no `paper.pdf` is skipped -- a work whose LaTeX alone is filed is a source-only work, which the invariant's relaxation allows (DR-198) and which nothing has lost.

    See Also
    --------
    copy_documents : The seed space's side of the same job, which files a document the store has not seen.
    """
    store = storage_root(quilt.root)
    if not store.is_dir():
        return []
    claimed = set()
    # An entry with an identifier names its home outright. One without -- a document the author dropped that says nothing about itself -- is filed under its hash, which the entry does not carry; what it does carry is `loom-source`, where the document came from, and the ledger knows which home that file became. Without this second check every scan would adopt the same hash-named directory again under a new key.
    sources = {str(e.fields["loom-source"]) for e in bib.values() if e.fields.get("loom-source")}
    for entry in bib.values():
        wid = primary(entry)
        if wid is not None:
            claimed.add(wid.path)
    ledger = {rec.get("to", ""): rec for rec in load_ledger(quilt.root).values()}
    # What the author has deliberately deleted the entry for. Without this the offer is loom undoing their decision on
    # every scan, which is the whole reason `loom refs forget` exists.
    forgotten = declarations(quilt.root, "forget")
    taken = set(bib)
    offers: list[Candidate] = []
    for pdf in sorted(store.glob("*/*/paper.pdf")):
        home = pdf.parent
        if f"{home.parent.name}/{home.name}" in claimed:
            continue
        rel = home.relative_to(quilt.root).as_posix()
        # where it was dropped, when the ledger remembers: the stored copy is always called `paper.pdf`, so the name a reference manager gave it -- which is the only title worth trusting (DR-191) -- survives only there
        came = str(ledger.get(rel, {}).get("from", "")) or rel
        if came in sources:
            continue  # an entry already names this document by where it came from
        sha = sha256_of(pdf)
        if f"sha256:{sha}" in forgotten:
            report.forgotten += 1
            continue
        wid, said = _own_account(pdf)  # the real file, for what the document says about itself
        stem = Path(came).stem
        named = filename_title(stem)
        if named and named != stem:
            said.setdefault("title", named)
            year = re.search(r"\b((?:19|20)\d\d)\b", stem)
            if year:
                said.setdefault("year", year.group(1))
        key = _derived_key(Path(came), sha, taken)
        # A tombstone on the citekey, which is what the author types after deleting the entry the last scan offered
        if key in forgotten:
            report.forgotten += 1
            continue
        taken.add(key)
        offers.append(Candidate(key, _entry_for(pdf, wid, said, key, source=came), rel, rel))
        report.adopted.append((key, rel))
    return offers


def copy_documents(quilt: Quilt, bib: dict[str, BibEntry], report: ScanReport) -> list[Candidate]:
    """Copy every document in the seed space the store has not seen before, and offer an entry for one the bibliography does not have.

    Copy-once is by content hash and by the ledger, never by what is on disk: a document the author has since deleted from `refs/` is not copied again, and neither is one they renamed. Where it goes is decided by what it says about itself -- its own identifier, the entry two signals agree it is, or its hash -- and a second document for a work that already has one is filed beside it under a sibling key rather than over it, because a preprint often carries results the published version drops (DR-192).
    """
    root = quilt.root
    seed = root / SEED
    if not seed.is_dir():
        return []
    ledger = load_ledger(root)
    taken = set(bib)
    offers: list[Candidate] = []
    for pdf in sorted(seed.rglob("*.pdf")):
        sha = sha256_of(pdf)
        rel = pdf.relative_to(root).as_posix()
        if sha in ledger:
            report.already += 1
            continue
        wid, said = _own_account(pdf)
        found = look_at(pdf, bib)
        citekey = found.best()[0] if found.attachable else ""
        entry = bib.get(citekey)
        named = primary(entry) if entry is not None else None
        claimed = storage_root(root) / named.path if named is not None else None
        own = storage_root(root) / (wid.path if wid else f"file/{sha[:16]}")
        if claimed is not None and not (claimed / "paper.pdf").is_file():
            home = claimed  # the work the bibliography already names, with nothing filed for it yet
        elif claimed is not None:
            home = own  # a second document for that work: beside the first, under a sibling key
            sibling = _free_key(citekey, taken)
            taken.add(sibling)
            fields = {k: v for k, v in entry.fields.items() if k in ("author", "title", "year")}  # type: ignore[union-attr]
            fields["loom-copy-of"] = citekey
            offers.append(Candidate(sibling, _entry_for(pdf, wid, fields, sibling), rel, rel))
            report.siblings.append((sibling, citekey))
        else:
            home = own  # nothing in the bibliography claims it
            key = _derived_key(pdf, sha, taken)
            taken.add(key)
            offers.append(Candidate(key, _entry_for(pdf, wid, said, key), rel, rel))
            (report.derived if wid else report.unnamed).append(key)
        home.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf, home / "paper.pdf")
        try:
            write_map(home, home / "paper.pdf")
        except Exception as exc:  # noqa: BLE001 -- no poppler, or a PDF with no text layer: the copy stands either way
            report.unmapped.append((rel, str(exc)))
        record_copy(root, sha, rel, home.relative_to(root).as_posix())
        report.copied.append((rel, home.relative_to(root).as_posix()))
    return offers
