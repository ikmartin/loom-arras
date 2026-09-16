"""`loom digest fetch CITEKEY [--pdf]` (book 8.9): the arXiv e-print source and, with `--pdf`, the PDF, into the work's own directory under `refs/`. Nothing is fetched unless `[refs] fetch = true`; no other command touches the network."""

from __future__ import annotations

import gzip
import io
import re
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from loom.refs.identity import primary
from loom.scan.bib import BibEntry
from loom.scan.quilt import Quilt
from loom.version import __version__

USER_AGENT = f"loom/{__version__} (+https://github.com/ikmartin/loom)"


class FetchRefused(Exception):
    """Fetching is off, or the entry has no arXiv identifier."""


def arxiv_id(entry: BibEntry) -> str | None:
    """The arXiv identifier of an entry: its `eprint` when `eprinttype`/`archiveprefix` is absent or arXiv, else None."""
    e = entry.eprint
    if not e:
        return None
    kind = (entry.fields.get("eprinttype") or entry.fields.get("archiveprefix") or "arxiv").strip().lower()
    if kind != "arxiv":
        return None
    e = re.sub(r"^arxiv:", "", e.strip(), flags=re.I)
    return e or None


def work_dir(root: Path, entry: BibEntry | None) -> Path:
    """The directory under `refs/` holding everything fetched for one work.

    Named by the work's primary global identifier, never by the citekey: at depth 1 a citekey exists, and past it a work reached through someone else's bibliography has none at all. Two quilts citing one paper therefore name one directory, which is what lets a shared cache be a hardlink rather than a mapping (DR-108).
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


def fetch(quilt: Quilt, citekey: str, entry: BibEntry | None, pdf: bool = False) -> list[Path]:
    """Fetch the e-print (and the PDF) for `citekey`; returns the files written."""
    if not quilt.config.fetch:
        raise FetchRefused("fetching is off: set fetch = true under [refs] in config.toml to allow it")
    if entry is None:
        raise FetchRefused(f"{citekey} is not in the bibliography")
    ident = arxiv_id(entry)
    if ident is None:
        raise FetchRefused(f"{citekey} has no eprint field naming an arXiv identifier")
    home = work_dir(quilt.root, entry)
    written: list[Path] = []
    source_error: FetchRefused | None = None
    try:
        written = _unpack(_get(f"https://arxiv.org/e-print/{ident}"), home / "src")
    except FetchRefused as exc:
        source_error = exc
    if pdf:
        p = home / "paper.pdf"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(_get(f"https://arxiv.org/pdf/{ident}"))
        written.append(p)
    if source_error is not None and not written:
        raise source_error
    if source_error is not None:
        raise FetchRefused(f"{source_error} (the PDF was fetched: {written[-1].relative_to(quilt.root)})")
    return written
