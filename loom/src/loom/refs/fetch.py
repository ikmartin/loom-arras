"""`loom refs fetch`: sources and PDFs for the works a quilt cites (plan 0.12 §4.3).

Absorbs what `loom digest fetch` did, and adds the two things §4.3 needs. **A resolver candidate is enough to fetch with and never enough to be an identity**: DR-122 keeps identity with the author, but downloading an e-print on a strong candidate is reversible, costs one request, and is checkable on arrival -- so a work whose entry declares no identifier is still fetchable, which is what takes relloc's mechanically-extractable fraction from 2 works toward 15.

**The arrival check is the guard.** A fetched source's title is scored against the bibliography entry's, and a source that does not match is discarded rather than filed. This is what stops a plausible-but-wrong candidate attaching the wrong paper to the right entry, and it is why fetching on a candidate is safe when identifying on one is not.
"""

from __future__ import annotations

import difflib
import gzip
import io
import re
import shutil
import tarfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC
from pathlib import Path

from loom.refs.identity import primary
from loom.refs.resolve import Query, _fold, load, query_for
from loom.scan.bib import BibEntry
from loom.scan.quilt import Quilt
from loom.version import __version__

USER_AGENT = f"loom/{__version__} (+https://github.com/ikmartin/loom)"

# Below this similarity the fetched source is not the work the entry names, and is discarded (§4.3).
#
# This is a **title similarity**, 0 to 1, and not `resolve.score`. That function is `0.75 * ratio + 0.15 (author) +
# 0.10 (year)`, so when the authors and year are unknown -- which they are here, because all we have is the source's
# own `\title` -- it can never exceed 0.75, and a threshold expressed in its units means something other than it
# appears to. Measured on this corpus, a correct match scores 0.93 and the closest wrong one 0.71, so 0.8 separates
# them with room on both sides.
ARRIVAL = 0.8

_TITLE = re.compile(r"\\title\s*(?:\[[^\]]*\])?\s*\{", re.S)


class FetchRefused(Exception):
    """Fetching is off, or the entry has no identifier anyone will serve."""


@dataclass
class Fetched:
    """What one work's fetch did, whether or not it worked."""

    citekey: str
    files: list[Path] = field(default_factory=list)
    source: bool = False
    pdf: bool = False
    ident: str = ""
    # "declared" when the entry names the identifier, "candidate" when a lookup proposed it (§4.3)
    via: str = ""
    title_score: float | None = None
    refused: str = ""
    discarded: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.files) and not self.discarded


def arxiv_id(entry: BibEntry) -> str | None:
    """The arXiv identifier an entry declares: its `eprint` when `eprinttype`/`archiveprefix` is absent or arXiv, else None.

    The type check is load-bearing rather than defensive. Two of relloc's four `eprint` fields are JSTOR stable ids, so a reader that takes `eprint` at face value reports twice the arXiv coverage that exists.
    """
    e = entry.eprint
    if not e:
        return None
    kind = (entry.fields.get("eprinttype") or entry.fields.get("archiveprefix") or "arxiv").strip().lower()
    if kind != "arxiv":
        return None
    e = re.sub(r"^arxiv:", "", e.strip(), flags=re.I)
    return e or None


def candidate_arxiv(root: Path, entry: BibEntry) -> str | None:
    """The arXiv id of the entry's best recorded candidate, if a lookup found one; never touches the network."""
    for c in load(root, entry):
        for ident in [c.id, *c.also]:
            if ident.startswith("arxiv:"):
                return ident.split(":", 1)[1]
    return None


def identifier_for(root: Path, entry: BibEntry) -> tuple[str | None, str]:
    """(arXiv id, how we know it): what the entry declares, else what a recorded candidate proposes."""
    declared_id = arxiv_id(entry)
    if declared_id:
        return declared_id, "declared"
    found = candidate_arxiv(root, entry)
    return (found, "candidate") if found else (None, "")


def work_dir(root: Path, entry: BibEntry | None) -> Path:
    """The directory under `refs/` holding everything fetched for one work.

    Named by the work's primary global identifier, never by the citekey: two quilts citing one paper name one directory, which is what lets a shared cache be a hardlink rather than a mapping (DR-108).
    """
    wid = primary(entry)
    if wid is None:
        raise FetchRefused("the work has no bibliography entry, so it has no identity to file under")
    return root / "refs" / wid.path


def _get(url: str, attempts: int = 3) -> bytes:
    """GET with loom's User-Agent; arXiv answers a burst of requests with 406, so a failed attempt is retried after a pause."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    last: Exception | None = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(3.0 * attempt)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                return bytes(resp.read())
        except urllib.error.HTTPError as exc:
            last = FetchRefused(f"{url}: HTTP {exc.code} {exc.reason}")
            if exc.code not in (406, 429, 500, 502, 503):
                break
        except urllib.error.URLError as exc:
            last = FetchRefused(f"{url}: {exc.reason}")
    assert last is not None
    raise last


def _unpack(data: bytes, dest: Path) -> list[Path]:
    """Unpack an arXiv e-print (a gzipped tar, a gzipped single file, or a PDF) under `dest`, refusing paths that escape it."""
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if data[:4] == b"%PDF":
        p = dest / "paper.pdf"
        p.write_bytes(data)
        return [p]
    try:
        raw = gzip.decompress(data)
    except OSError:
        raw = data
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tar:
            for member in tar.getmembers():
                target = (dest / member.name).resolve()
                if not str(target).startswith(str(dest.resolve())) or member.issym() or member.islnk():
                    continue
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    f = tar.extractfile(member)
                    if f is not None:
                        target.write_bytes(f.read())
                        written.append(target)
        return written
    except tarfile.TarError:
        pass
    p = dest / "main.tex"
    p.write_bytes(raw)
    return [p]


def _balanced(text: str, start: int) -> str:
    """The contents of the brace group beginning at `start` (which indexes the `{`), or '' if it never closes."""
    depth = 0
    out: list[str] = []
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
            if depth == 1:
                continue
        elif c == "}":
            depth -= 1
            if depth == 0:
                return "".join(out)
        out.append(c)
    return ""


def source_title(src: Path) -> str:
    """The `\\title{...}` of an unpacked source, from whichever file declares one; '' when none does.

    Reads at most 40 `.tex` files and only the first 200 KB of each -- a title is in a preamble, and an e-print can unpack to a hundred figures.
    """
    for path in sorted(src.rglob("*.tex"))[:40]:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
        except OSError:
            continue
        m = _TITLE.search(text)
        if m:
            found = _balanced(text, m.end() - 1)
            if found.strip():
                return found.strip()
    return ""


def title_ratio(a: str, b: str) -> float:
    """How similar two titles are, 0 to 1, folded to ASCII words.

    A subtitle one side omits does not sink the other -- but only when what is omitted is short. An unconditional prefix rule scored "The Intrinsic Normal Cone" against "The Intrinsic Normal Cone for Artin Stacks" as a perfect match, so a 1997 paper was confidently filed as a different 2024 one. Two papers in this corpus are exactly that pair.
    """
    x, y = _fold(a), _fold(b)
    if not x or not y:
        return 0.0
    if (x.startswith(y) or y.startswith(x)) and min(len(x), len(y)) >= 0.8 * max(len(x), len(y)):
        return 1.0
    return difflib.SequenceMatcher(None, x, y).ratio()


def arrival_score(q: Query, src: Path) -> float | None:
    """How well an unpacked source's own title matches the entry we fetched it for; None when it declares no title.

    None is not a failure. A source with no `\\title` (a paper whose title is set by a class option, a stripped submission) cannot be checked this way and is kept: the check rejects a mismatch, it does not demand a match.
    """
    title = source_title(src)
    if not title:
        return None
    return title_ratio(q.title, title)


def fetch_work(
    quilt: Quilt,
    citekey: str,
    entry: BibEntry | None,
    *,
    pdf: bool = True,
    allow_candidate: bool = True,
) -> Fetched:
    """Fetch one work's source and PDF, checking on arrival that what came back is the work the entry names.

    Parameters
    ----------
    quilt : Quilt
        The quilt; `config.fetch` must be true or nothing touches the network.
    citekey : str
        The entry's key, for the report only.
    entry : BibEntry or None
        The bibliography entry; None is refused, since a work with no entry has no identity to file under.
    pdf : bool, default True
        Also fetch the PDF. Eager by default: the page is what an anchor points into, and it is one spaced request.
    allow_candidate : bool, default True
        Fetch on a recorded resolver candidate where the entry declares no identifier (§4.3).

    Returns
    -------
    Fetched
        What happened, including a refusal or a discard. Never raises for an ordinary miss.

    See Also
    --------
    identifier_for : which identifier this will use, and how it is known.
    arrival_score : the check a candidate-fetched source must pass.
    """
    out = Fetched(citekey=citekey)
    if not quilt.config.fetch:
        out.refused = "fetching is off: set fetch = true under [refs] in config.toml to allow it"
        return out
    if entry is None:
        out.refused = f"{citekey} is not in the bibliography"
        return out
    ident, via = identifier_for(quilt.root, entry)
    if ident is None:
        url = pdf_url(entry)
        if url and pdf:
            return _fetch_url(quilt, citekey, entry, url, out)
        out.refused = f"{citekey} names no arXiv identifier or PDF link, and no lookup has proposed one"
        return out
    if via == "candidate" and not allow_candidate:
        out.refused = f"{citekey} declares no identifier (a candidate exists; pass --candidates to use it)"
        return out
    out.ident, out.via = ident, via
    home = work_dir(quilt.root, entry)
    src = home / "src"
    try:
        out.files = _unpack(_get(f"https://export.arxiv.org/e-print/{ident}"), src)
        out.source = True
    except FetchRefused as exc:
        out.refused = str(exc)
    if out.source:
        # The check runs whatever the identifier's provenance: a declared `eprint` can be a typo, and the cost is a
        # title comparison against a file already on disk.
        out.title_score = arrival_score(query_for(entry), src)
        if out.title_score is not None and out.title_score < ARRIVAL:
            got = source_title(src)
            _discard(src)
            out.files, out.source = [], False
            out.discarded = f'fetched source is titled "{got}", which does not match this entry ({out.title_score:.2f})'
            return out
        record_source(home, f"arxiv:{ident}", via)
    if pdf and not (home / "paper.pdf").is_file():
        try:
            p = home / "paper.pdf"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(_get(f"https://export.arxiv.org/pdf/{ident}"))
            out.files.append(p)
            out.pdf = True
        except FetchRefused as exc:
            if not out.source:
                out.refused = str(exc)
    if out.files:
        out.refused = ""
    return out


def record_source(home: Path, identifier: str, via: str) -> None:
    """Write `src.json` beside a fetched source: which artifact it is, and how the identifier was known.

    The directory is named for the WORK, and a source fetched on a candidate preprint id is not the published version the work's DOI names. Without this record the digest extracted from it claimed `extracted-from: doi:…`, DR-109's version warning could not fire, and Chang, Kiem and Li's digest carried the preprint's numbering and a conclusion the published paper states differently.
    """
    import json as _json
    from datetime import date

    (home / "src.json").write_text(
        _json.dumps({"identifier": identifier, "via": via, "fetched": date.today().isoformat()}, indent=2) + "\n",
        encoding="utf-8",
    )


def recorded_source(home: Path) -> str:
    """The identifier `src.json` names for the source under `home`, or '' when none was recorded."""
    import json as _json

    try:
        return str(_json.loads((home / "src.json").read_text(encoding="utf-8")).get("identifier", ""))
    except (OSError, ValueError, AttributeError):
        return ""


def _discard(src: Path) -> None:
    """Remove a source tree that failed the arrival check; a wrong paper on disk is worse than none."""
    shutil.rmtree(src, ignore_errors=True)


def pdf_url(entry: BibEntry) -> str:
    """The entry's `url` when it points straight at a PDF; '' otherwise.

    Lecture notes and drafts live at an author's own address with no DOI and no arXiv id -- Alper's "Stacks and Moduli" is one in the study corpus -- and an agent asked for exactly this: numbering drifts between revisions of such a document, so a dated local copy is worth more there than anywhere.
    """
    url = (entry.fields.get("url") or "").strip()
    return url if url.lower().split("?")[0].endswith(".pdf") and url.startswith(("https://", "http://")) else ""


def _fetch_url(quilt: Quilt, citekey: str, entry: BibEntry, url: str, out: Fetched) -> Fetched:
    """Download a PDF the entry links to, keep it only if its first page carries the entry's title, and date it."""
    import json as _json
    from datetime import datetime

    from loom.refs.ingest import TITLE_MATCH, title_lines
    from loom.refs.pages import page_texts, sha256_of

    home = work_dir(quilt.root, entry)
    home.mkdir(parents=True, exist_ok=True)
    dest = home / "paper.pdf"
    if dest.is_file():
        out.pdf, out.files = True, [dest]
        return out
    try:
        data = _get(url)
    except FetchRefused as exc:
        out.refused = str(exc)
        return out
    if data[:4] != b"%PDF":
        out.refused = f"{url} did not return a PDF"
        return out
    dest.write_bytes(data)
    want = str(entry.fields.get("title") or "")
    try:
        first = page_texts(dest)[0] if want else ""
    except Exception:  # noqa: BLE001 -- an unreadable PDF is reported below as unchecked, not as a crash
        first = ""
    best = max((title_ratio(want, line) for line in title_lines(first)), default=0.0) if first else 0.0
    out.title_score = best
    if want and first and best < TITLE_MATCH:
        dest.unlink(missing_ok=True)
        out.discarded = f"the PDF at {url} does not carry this entry's title on its first page ({best:.2f})"
        return out
    # the date is the point: a draft's numbering is only meaningful against the revision it was read from
    (home / "fetched.json").write_text(
        _json.dumps(
            {
                "url": url,
                "fetched": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sha256": sha256_of(dest),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    out.pdf, out.files, out.via, out.ident = True, [dest], "url", url
    return out
