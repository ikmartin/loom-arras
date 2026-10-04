"""The quilt's own bibliography (book 8.15): `digests/bibliography.bib`, gathered from the landmarks and only ever appended to.

A landmark cites through a `.bib` it names or through an inline `thebibliography`; both are read. An entry from a `.bib` is copied verbatim, so nothing the author wrote is lost. A `\\bibitem` is free text, so it becomes an entry holding that text in `loom-text`, the identifiers found in it, and a best-effort author, title and year, marked `loom-parsed = {heuristic}`. An entry already in the file is never rewritten or removed: the author corrects a heuristic entry by hand, and the next scan leaves the correction alone.
"""

from __future__ import annotations

import json
import re
import shutil
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from loom.clock import stamp
from loom.refs.fetch import FetchRefused, work_dir
from loom.refs.identity import WorkId, declared, primary
from loom.refs.ingest import TOP_LINES, _title_span, filename_title, identifiers_in, identify_document
from loom.refs.pages import STORAGE, page_texts, sha256_of, storage_root, write_map
from loom.refs.unreadable import declarations
from loom.scan.bib import BIBLIOGRAPHY, BibEntry, parse_bib, raw_entries
from loom.scan.quilt import Quilt
from loom.scan.scan import landmark_documents
from loom.scan.source import blank_comments
from loom.scan.tokenize import match_group, read_args, read_optional, tokenize

if TYPE_CHECKING:
    from loom.cli.report import Report

HEADER = (
    "% The quilt's bibliography, gathered by `loom library update` from the landmarks (book 8.15).\n"
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
    source: str  # the landmark it came from
    compare: str = ""  # the text two sources are compared by


@dataclass
class ScanReport:
    canon: int = 0  # landmarks read
    added: list[Candidate] = field(default_factory=list)
    present: int = 0  # entries the file already had
    conflicts: list[tuple[str, str, str]] = field(default_factory=list)  # (key, kept source, other source)
    missing_bib: list[tuple[str, str]] = field(default_factory=list)  # (landmark, .bib it names that is absent)
    copied: list[tuple[str, str]] = field(default_factory=list)  # (seed file, where it was filed)
    already: int = 0  # documents the ledger had seen before
    derived: list[str] = field(default_factory=list)  # entries offered for a document that stated an identifier
    unnamed: list[str] = field(default_factory=list)  # entries offered for a document that stated none
    #: (seed file, why) for a document that resembles an entry without showing plainly that it is that entry's.
    unmatched: list[tuple[str, str]] = field(default_factory=list)
    siblings: list[tuple[str, str]] = field(default_factory=list)  # (new key, the work it is a second document of)
    #: (seed file, the version it is a copy of, why): recorded in the ledger and not filed.
    copies: list[tuple[str, str, str]] = field(default_factory=list)
    unmapped: list[tuple[str, str]] = field(default_factory=list)  # (file, why no page text was written)
    adopted: list[tuple[str, str]] = field(default_factory=list)  # (new key, the store directory nothing named)
    forgotten: int = 0  # stored documents a tombstone says not to offer again
    duplicates: list[tuple[str, list[str]]] = field(
        default_factory=list
    )  # (where the document came from, the entries naming it)

    #: True when the scan wrote nothing: a dry run, or `library update` asking what gathering would add.
    dry_run: bool = False

    def problems(self) -> int:
        """How many findings need the author: conflicts, `.bib` files named and absent, and entries naming one document."""
        return len(self.conflicts) + len(self.missing_bib) + len(self.duplicates)

    def report(self) -> Report:
        """The scan as a report: what the bibliography holds and gained, what came in from `refs/`, and each finding that needs the author.

        Store paths stay in the JSON; the text names the citekey and the file the author dropped.
        """
        from loom.cli.report import Group, Item, Report, counted

        # A `\bibitem` and a document dropped in `refs/` both carry `loom-parsed`; counting them together said "from \bibitem text" about a PDF that came from no bibliography at all.
        from_seed = {c.key for c in self.added if c.text and "loom-source" in c.text}
        heuristic = {c.key for c in self.added if "loom-parsed" in c.text and c.key not in from_seed}
        total = self.present + len(self.added)
        new = f"{len(self.added)} new" if self.added else "none new"
        verdict = (
            f"{BIBLIOGRAPHY} {'would hold' if self.dry_run else 'holds'} {counted(total, 'entry', 'entries')}, {new}"
        )
        if self.problems():
            verdict += f"; {counted(self.problems(), 'finding')} for you"
        lines: list[str] = []
        if self.copied or self.already:
            copied = f"{len(self.copied)} new" if self.copied else "none new"
            offered = len(self.derived) + len(self.unnamed)
            lines.append(
                f"{SEED}/: {counted(len(self.copied) + self.already, 'document')} in loom's store, {copied}"
                + (f", {counted(offered, 'new entry', 'new entries')} offered" if offered else "")
            )
        if self.forgotten:
            lines.append(
                f"{counted(self.forgotten, 'stored document')} not offered: forgotten; "
                "loom library ignore WORK --undo --why '…' offers one again"
            )
        if not self.canon:
            lines.append(
                "no landmarks to gather from: the bibliography grows when you `loom stamp DOCUMENT -m NAME` a document"
            )

        def origin(c: Candidate) -> str:
            if c.key in from_seed:
                return f"read from {_shown(c.source)} itself"
            return f"from {_shown(c.source)}" + (
                ", parsed heuristically from \\bibitem text" if c.key in heuristic else ""
            )

        groups = [
            Group(
                "conflicts: the landmarks disagree, and the first is kept",
                [Item(f"{kept} (kept) and {other}", key=key) for key, kept, other in sorted(self.conflicts)],
                problem=True,
            ),
            Group(
                "missing .bib files: a landmark names one that does not exist",
                [Item(f"{doc} names {name}.bib", key=f"{name}.bib") for doc, name in sorted(self.missing_bib)],
                problem=True,
            ),
            Group(
                f"entries naming one document: keep one and delete the others from {BIBLIOGRAPHY}",
                [Item(_shown(came), key=", ".join(keys)) for came, keys in self.duplicates],
                problem=True,
            ),
            Group("new entries", [Item(origin(c), key=c.key) for c in sorted(self.added, key=lambda c: c.key.lower())]),
            Group(
                "second documents, filed beside the first",
                [Item(f"a second document for {old}", key=new_key) for new_key, old in sorted(self.siblings)],
            ),
            Group(
                "copies of a filed document, recorded and not filed again",
                [Item(f"{name}: {why}", key=of) for name, of, why in sorted(self.copies)],
            ),
            Group(
                "entries for stored documents",
                [
                    Item("a document in loom's store, which the bibliography no longer named", key=key)
                    for key, _ in sorted(self.adopted)
                ],
            ),
            Group("no page text", [Item(why, key=name) for name, why in sorted(self.unmapped)]),
            Group(
                "not filed against an entry, so offered one of their own",
                [Item(f"{name}: {why}") for name, why in sorted(self.unmatched)],
                limit=None,
                next="loom library add FILE --for WORK files one you know is that work",
            ),
        ]
        return Report(
            verdict,
            ok=not self.problems(),
            groups=[g for g in groups if g.items],
            lines=lines,
            dry_run=self.dry_run,
            data={
                "landmarks": self.canon,
                "entries": total,
                "present": self.present,
                "added": [{"key": c.key, "source": c.source} for c in self.added],
                "conflicts": [{"key": k, "kept": a, "other": b} for k, a, b in self.conflicts],
                "missing_bib": [{"landmark": d, "bib": f"{n}.bib"} for d, n in self.missing_bib],
                "copied": [{"from": a, "to": b} for a, b in self.copied],
                "already": self.already,
                "derived": list(self.derived),
                "unnamed": list(self.unnamed),
                "siblings": [{"key": a, "of": b} for a, b in self.siblings],
                "copies": [{"file": a, "of": b, "why": c} for a, b, c in self.copies],
                "unmapped": [{"file": a, "why": b} for a, b in self.unmapped],
                "unmatched": [{"file": a, "why": b} for a, b in self.unmatched],
                "adopted": [{"key": a, "home": b} for a, b in self.adopted],
                "forgotten": self.forgotten,
                "duplicates": [{"from": a, "keys": b} for a, b in self.duplicates],
            },
        )

    def lines(self) -> list[str]:
        """The report's text, line by line, for a command that passes the scan on as notes."""
        return self.report().render().split("\n")


def _shown(path: str) -> str:
    """A path as the author knows it: one inside loom's store is `a document in loom's store`, since the store is not theirs to navigate."""
    return "a document in loom's store" if path.startswith(STORAGE + "/") else path


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
        "loom-file",
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
    """Every entry the landmarks carry, first source winning; a second source disagreeing is a conflict."""
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

    docs = landmark_documents(quilt)
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
    """Append every entry a landmark carries that the quilt's bibliography does not have yet.

    Parameters
    ----------
    quilt : Quilt
        The quilt to scan.
    write : bool, default True
        Append to `digests/bibliography.bib`; False reports what would be added.

    Returns
    -------
    ScanReport
        What was added, how many entries were already there, conflicts between landmarks, and named `.bib` files that do not exist.
    """
    report = ScanReport(dry_run=not write)
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
    from_seed = [c for c in copy_documents(quilt, existing, report, write=write) if c.key not in existing]
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
    report.duplicates = _duplicates(existing)
    return report


def versions_of(bib: dict[str, BibEntry]) -> dict[str, list[str]]:
    """Each work with versions: its primary citekey and the sibling entries filed as other documents of it, by `loom-copy-of` (book 8.16).

    A version of a version belongs to the first one's primary; a sibling whose primary is no longer in the bibliography, or a cycle, stands alone.
    """
    out: dict[str, list[str]] = {}
    for key in sorted(bib):
        top, seen = key, {key}
        while (up := str(bib[top].fields.get("loom-copy-of") or "").strip()) in bib and up not in seen:
            top = up
            seen.add(up)
        if top != key and str(bib[top].fields.get("loom-copy-of") or "").strip() not in bib:
            out.setdefault(top, []).append(key)
    return out


def primary_of(bib: dict[str, BibEntry]) -> dict[str, str]:
    """Each version's primary citekey, the inverse of `versions_of`; a key absent is its own work's primary."""
    return {v: top for top, vs in versions_of(bib).items() for v in vs}


def other_versions(bib: dict[str, BibEntry]) -> dict[str, list[str]]:
    """Each key of a work with versions, mapped to the work's other keys, primary first: where a citation of one finds what the others hold."""
    out: dict[str, list[str]] = {}
    for top, vs in versions_of(bib).items():
        work = [top, *vs]
        for k in work:
            out[k] = [o for o in work if o != k]
    return out


def one_work_of(keys: list[str], bib: dict[str, BibEntry]) -> str:
    """The primary of the one work `keys` all belong to, or '' when they name more than one; how a document naming a work and its versions equally is filed."""
    tops = {primary_of(bib).get(k, k) for k in keys}
    return tops.pop() if len(tops) == 1 else ""


def _held(pdf: Path, title: str) -> tuple[str, int] | None:
    """(byline, page count) of a PDF whose first page sets `title` whole; None when it does not, or cannot be read."""
    from loom.refs.resolve import _fold

    try:
        pages = page_texts(pdf)
    except Exception:  # noqa: BLE001 -- an unreadable document matches nothing
        return None
    lines = [_fold(" ".join(x.split())) for x in (pages[0] if pages else "").splitlines()[:TOP_LINES] if x.strip()]
    span = _title_span(lines, title) if title else None
    if span is None:
        return None
    return (lines[span[1]] if span[1] < len(lines) else ""), len(pages)


def same_document(pdf: Path, wid: WorkId | None, stored: list[tuple[BibEntry, Path]]) -> tuple[str, str]:
    """(citekey, why) when `pdf` is a copy of a version's document, else ('', ''): the filing rule of book 8.16.

    A copy states a version's own identifier, or sets the same title over the same byline on as many pages as that version's stored PDF. `stored` is each version of one work with where its PDF is, primary first; `wid` is what `pdf` states (`_own_account`).
    """
    from loom.refs.resolve import _fold

    if wid is not None:
        for entry, _ in stored:
            if any(w.scheme == wid.scheme and w.value.lower() == wid.value.lower() for w in declared(entry)):
                return entry.key, f"it states {wid}, {entry.key}'s own identifier"
    for entry, path in stored:
        title = _fold(str(entry.fields.get("title") or ""))
        theirs = _held(path, title) if path.is_file() else None
        if theirs is not None and _held(pdf, title) == theirs:
            n = theirs[1]
            return entry.key, f"same title, authors and {n} page{'' if n == 1 else 's'}"
    return "", ""


def stored_versions(root: Path, bib: dict[str, BibEntry], top: str) -> list[tuple[BibEntry, Path]]:
    """Every version of the work `top` with where its PDF is stored, primary first; a version with no home is left out."""
    out = []
    for key in [top, *versions_of(bib).get(top, [])]:
        try:
            out.append((bib[key], work_dir(root, bib[key]) / "paper.pdf"))
        except FetchRefused:
            continue
    return out


def _duplicates(bib: dict[str, BibEntry]) -> list[tuple[str, list[str]]]:
    """Entries that name one stored document, which earlier scans offered again and again; reported, never removed, since the file is the author's to edit."""
    by_home: dict[str, list[str]] = {}
    came: dict[str, str] = {}
    for key, entry in bib.items():
        filed = str(entry.fields.get("loom-file") or "").strip()
        if filed:
            by_home.setdefault(filed, []).append(key)
            came.setdefault(filed, str(entry.fields.get("loom-source") or filed))
    return sorted((came[home], sorted(keys)) for home, keys in by_home.items() if len(keys) > 1)


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


def record_copy(root: Path, sha: str, source: str, dest: str, extra: dict[str, str] | None = None) -> None:
    """Append one copy to the ledger, with `extra` fields such as an override `library add --force` made. Nothing is ever removed from it."""
    path = storage_root(root) / LEDGER
    ledger = load_ledger(root)
    ledger[sha] = {"from": source, "to": dest, "when": stamp(), **(extra or {})}
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


def _entry_for(
    pdf: Path, wid: WorkId | None, fields: dict[str, str], key: str, source: str = "", filed: str = ""
) -> str:
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
    # where the document went, when that is not derivable from an identifier it does not state
    if filed:
        out["loom-file"] = filed
    out["loom-parsed"] = "heuristic"
    return _bibtex(key, out)


def _sibling(pdf: Path, wid: WorkId | None, entry: BibEntry, key: str, *, source: str, home: Path) -> Candidate:
    """The entry for a second document of `entry`'s work, filed beside the first at `home` (store-relative).

    It always names its home in `loom-file`: one stating no identifier is otherwise looked for under the synthetic home its author, title and year hash to, which is the original's, and shows the original's PDF or none (audit §3).
    """
    fields = {k: v for k, v in entry.fields.items() if k in ("author", "title", "year")}
    fields["loom-copy-of"] = entry.key
    return Candidate(key, _entry_for(pdf, wid, fields, key, source=source, filed=home.as_posix()), source, source)


def _derived_key(pdf: Path, sha: str, taken: set[str]) -> str:
    """A citekey for a document nothing in the bibliography claims: its filename, or its hash when the name says nothing."""
    stem = re.sub(r"[^A-Za-z0-9]", "", pdf.stem)[:24]
    key = stem or f"pdf{sha[:8]}"
    return key if key not in taken else _free_key(key, taken)


def _spaced(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


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
    # compared with whitespace collapsed, as the bibliography reader collapses it: a file named with two spaces was otherwise never found again, and every scan adopted it under a new key
    sources = {_spaced(str(e.fields["loom-source"])) for e in bib.values() if e.fields.get("loom-source")}
    for entry in bib.values():
        filed = str(entry.fields.get("loom-file") or "").strip()
        if filed:
            claimed.add(filed)  # an entry that says where its document went names that home
        wid = primary(entry)
        if wid is not None:
            claimed.add(wid.path)
    ledger = {rec.get("to", ""): rec for rec in load_ledger(quilt.root).values() if not rec.get("duplicate-of")}
    # What the author has deliberately deleted the entry for. Without this the offer is loom undoing their decision on every scan, which is the whole reason `loom library ignore` sets a document aside.
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
        if _spaced(came) in sources:
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
        offers.append(
            Candidate(
                key,
                _entry_for(pdf, wid, said, key, source=came, filed="" if wid else f"{home.parent.name}/{home.name}"),
                rel,
                rel,
            )
        )
        report.adopted.append((key, rel))
    return offers


def copy_documents(
    quilt: Quilt, bib: dict[str, BibEntry], report: ScanReport, *, write: bool = True
) -> list[Candidate]:
    """Copy every document in the seed space the store has not seen before, and offer an entry for one the bibliography does not have.

    Copy-once is by content hash and by the ledger, never by what is on disk: a document the author has since deleted from `refs/` is not copied again, and neither is one they renamed. Where it goes is decided by what it says about itself -- its own identifier, the entry it shows plainly it is (`identify_document`, the rule `library add` files on), or its hash. A second document for a work that already has one is a copy when `same_document` says so, recorded in the ledger and not filed; otherwise it is another version, filed beside the first under a sibling key rather than over it, because a preprint often carries results the published version drops (DR-192).
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
        ledger[sha] = {"from": rel}  # the same bytes dropped twice in one gathering are one document, offered once
        wid, said = _own_account(pdf)
        # filed against an entry only on the rule `library add` files on; anything weaker is its own document
        identity = identify_document(pdf, bib)
        best = identity.best()
        citekey = best[0].citekey if len(best) == 1 else one_work_of([m.citekey for m in best], bib) if best else ""
        if not citekey:
            why = f"it names {' and '.join(m.citekey for m in best)} equally" if best else identity.weak
            if why and not why.startswith("nothing in the bibliography"):
                report.unmatched.append((rel, why))
        entry = bib.get(citekey)
        # where the entry's document lives, `loom-file` first, as every reader looks (`work_dir`)
        try:
            claimed = work_dir(root, entry) if entry is not None else None
        except FetchRefused:
            claimed = None
        own = storage_root(root) / (wid.path if wid else f"file/{sha[:16]}")
        if claimed is not None and own == claimed and (claimed / "paper.pdf").is_file():
            own = (
                storage_root(root) / f"file/{sha[:16]}"
            )  # a second document stating the work's own identifier is filed by its content, never over the first
        if claimed is not None and not (claimed / "paper.pdf").is_file():
            home = claimed  # the work the bibliography already names, with nothing filed for it yet
        elif claimed is not None and entry is not None:
            top = primary_of(bib).get(citekey, citekey)
            same, why = same_document(pdf, wid, stored_versions(root, bib, top))
            if same:
                report.copies.append((rel, same, why))
                if write:
                    to = work_dir(root, bib[same]).relative_to(root).as_posix()
                    record_copy(root, sha, rel, to, {"duplicate-of": same})
                continue
            home = own  # another version of that work: beside the first, under a sibling key
            sibling = _free_key(top, taken)
            taken.add(sibling)
            offers.append(_sibling(pdf, wid, bib[top], sibling, source=rel, home=own.relative_to(storage_root(root))))
            report.siblings.append((sibling, top))
        else:
            home = own  # nothing in the bibliography claims it
            key = _derived_key(pdf, sha, taken)
            taken.add(key)
            here = own.relative_to(storage_root(root)).as_posix()
            offers.append(
                Candidate(key, _entry_for(pdf, wid, said, key, source=rel, filed="" if wid else here), rel, rel)
            )
            (report.derived if wid else report.unnamed).append(key)
        report.copied.append((rel, home.relative_to(root).as_posix()))
        if not write:
            continue  # a dry run says what it would copy and copies, maps and records nothing
        home.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf, home / "paper.pdf")
        try:
            write_map(home, home / "paper.pdf")
        except Exception as exc:  # noqa: BLE001 -- no poppler, or a PDF with no text layer: the copy stands either way
            report.unmapped.append((rel, str(exc)))
        record_copy(root, sha, rel, home.relative_to(root).as_posix())
    return offers


def tree_sha(path: Path) -> str:
    """A content hash for a LaTeX source, a file or a whole tree: what the ledger keys a source by, as it keys a PDF by its bytes."""
    import hashlib

    h = hashlib.sha256()
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    for f in files:
        h.update((f.relative_to(path).as_posix() if path.is_dir() else f.name).encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


@dataclass
class Filing:
    """One document `loom library add` files, or would: the work, where it lands, and whether it goes beside the work's first document."""

    path: Path
    citekey: str
    kind: str  # "pdf" or "source"
    sha: str
    source: str  # where it came from, as the ledger and `loom-source` record it
    home: Path | None = None
    #: The sibling entry's key when the work already holds a document, so this one is filed beside it (book 8.16).
    sibling: str = ""
    #: Why nothing is filed: the same document is in the store already; '' when it is filed.
    already: str = ""
    #: The version this document is a copy of (`same_document`), which the ledger records; '' otherwise.
    copy_of: str = ""
    #: The refusal `--force` overrode, recorded in the ledger with who forced it.
    forced: str = ""
    #: Why no page text was written for a filed PDF.
    unmapped: str = ""


def plan_filing(
    quilt: Quilt, bib: dict[str, BibEntry], f: Filing, taken: set[str], seen: dict[str, str]
) -> Candidate | None:
    """Decide where `f` lands, filling in its home, sibling or `already`; returns the sibling entry to append, or None.

    Never over a document: a copy of a version's document (`same_document`) is not filed and `record_copy_of` records it, another version goes beside the first under `<key>A`, and the same bytes already in the store, or given twice in one run, are filed once. Reads only; `file_document` writes.
    """
    root = quilt.root
    store = storage_root(root)
    if f.sha in seen:
        f.already = f"the same document as {seen[f.sha]}"
        return None
    seen[f.sha] = f.path.name
    ledger = load_ledger(root)
    if f.kind == "pdf" and f.sha in ledger:
        rec = ledger[f.sha]
        f.already = (
            f"already recorded as a copy of {rec['duplicate-of']}'s document, from {rec.get('from', 'elsewhere')}"
            if rec.get("duplicate-of")
            else f"already in loom's store, filed from {rec.get('from', 'elsewhere')}"
        )
        return None
    entry = bib[f.citekey]
    claimed = work_dir(root, entry)
    first = claimed / "paper.pdf" if f.kind == "pdf" else claimed / "src"
    held = first.is_file() if f.kind == "pdf" else first.is_dir() and any(first.rglob("*.tex"))
    if not held:
        f.home = claimed
        return None
    if f.kind == "pdf" and sha256_of(first) == f.sha:
        f.already = f"already filed for {f.citekey}"
        return None
    top = primary_of(bib).get(f.citekey, f.citekey)
    wid = _own_account(f.path)[0] if f.kind == "pdf" else None
    if f.kind == "pdf":
        same, why = same_document(f.path, wid, stored_versions(root, bib, top))
        if same:
            f.already, f.copy_of = f"the same document as {same}'s: {why}", same
            return None
    own = store / "file" / f.sha[:16]
    f.home = own
    f.sibling = _free_key(top, taken)
    taken.add(f.sibling)
    return _sibling(f.path, wid, bib[top], f.sibling, source=f.source, home=own.relative_to(store))


def record_copy_of(quilt: Quilt, bib: dict[str, BibEntry], f: Filing) -> None:
    """Record in the copy ledger that `f` is a copy of `f.copy_of`'s document, so it is never offered again and nothing is filed."""
    to = work_dir(quilt.root, bib[f.copy_of]).relative_to(quilt.root).as_posix()
    record_copy(quilt.root, f.sha, f.source, to, {"duplicate-of": f.copy_of})


def file_document(quilt: Quilt, f: Filing, *, by: str = "") -> None:
    """Copy a planned filing into the store, write a PDF's page text, and record it in the copy ledger, with the override and who made it when `--force` did."""
    assert f.home is not None and not f.already
    root = quilt.root
    f.home.mkdir(parents=True, exist_ok=True)
    if f.kind == "pdf":
        shutil.copy(f.path, f.home / "paper.pdf")
        try:
            write_map(f.home, f.home / "paper.pdf")
        except Exception as exc:  # noqa: BLE001 -- no poppler, or no text layer: the PDF stands either way
            f.unmapped = str(exc)
    else:
        dest = f.home / "src"
        dest.mkdir(parents=True, exist_ok=True)
        if f.path.is_dir():
            shutil.copytree(f.path, dest, dirs_exist_ok=True)
        else:
            shutil.copy(f.path, dest / f.path.name)
    extra = {"forced": f.forced, "by": by} if f.forced else None
    record_copy(root, f.sha, f.source, f.home.relative_to(root).as_posix(), extra)


def append_entries(quilt: Quilt, entries: list[Candidate]) -> None:
    """Append entries to the quilt's bibliography, as gathering does: only ever appended, so a correction by hand outlives them."""
    _append(quilt.root / BIBLIOGRAPHY, entries)
