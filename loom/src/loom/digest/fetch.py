"""`loom digest fetch CITEKEY [--pdf]` (book 8.9): the arXiv e-print source into `refs/src/<citekey>/`, and with `--pdf` the PDF into `refs/pdf/`. Nothing is fetched unless `[refs] fetch = true`; no other command touches the network."""

from __future__ import annotations

import gzip
import io
import re
import tarfile
import urllib.request
from pathlib import Path

from loom.scan.bib import BibEntry
from loom.scan.quilt import Quilt
from loom.version import __version__

USER_AGENT = f"loom/{__version__} (+https://github.com/ikmartin/loom)"


class FetchRefused(Exception):
    """Fetching is off, or the entry has no arXiv identifier."""


def arxiv_id(entry: BibEntry) -> str | None:
    e = entry.eprint
    if not e:
        return None
    e = re.sub(r"^arxiv:", "", e.strip(), flags=re.I)
    return e or None


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return bytes(resp.read())


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
    written = _unpack(_get(f"https://arxiv.org/e-print/{ident}"), quilt.root / "refs" / "src" / citekey)
    if pdf:
        p = quilt.root / "refs" / "pdf" / f"{citekey}.pdf"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(_get(f"https://arxiv.org/pdf/{ident}"))
        written.append(p)
    return written
