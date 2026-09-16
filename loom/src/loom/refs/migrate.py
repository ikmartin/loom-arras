"""Bring a quilt's reference layout to the current one (plan 0.5, DR-108, DR-109).

Digests move from `refs/<citekey>.tex` to `digests/<citekey>.tex`; fetched artifacts move from `refs/src/<citekey>/` and `refs/pdf/<citekey>.pdf` into the work's own directory under `refs/`, named by its global identifier; and a digest header's single `source:` splits into `extracted-from:` and `published-as:`.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from loom.refs.identity import identify, parse, primary
from loom.scan.bib import BibEntry, parse_bib

_DIGEST = re.compile(r"^%\s*!LOOM\s+digest:\s*(\S+)\s*$", re.M)
_SOURCE = re.compile(r"^%\s*!LOOM\s+source:\s*(.*)$", re.M)
_PREFIX = re.compile(r"^%\s*!LOOM\s+prefix:\s*\S+\s*$", re.M)


@dataclass
class Migration:
    moved: list[str] = field(default_factory=list)
    rewrote: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)  # a digest whose provenance could not be split

    @property
    def done(self) -> bool:
        return bool(self.moved or self.rewrote)


def _bib(root: Path) -> dict[str, BibEntry]:
    out: dict[str, BibEntry] = {}
    for p in sorted(root.glob("*.bib")) + sorted(root.glob("**/*.bib")):
        try:
            out.update(parse_bib(p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return out


def _split_header(text: str, entry: BibEntry | None) -> tuple[str, bool]:
    """Turn a single `source:` into the pair that replaced it; returns the text and whether the split is certain.

    A DOI names the published work and an eprint names the preprint, so the field it came from decides which key it becomes. Nothing can infer the *other* one, and that is the point: on a digest extracted from arXiv while the bibliography cites a DOI, the migration leaves `published-as:` to be filled in and `loom:unverified-locators` says so.
    """
    m = _SOURCE.search(text)
    if m is None:
        return text, True
    wid = parse(m.group(1).strip())
    if wid is None:
        return _SOURCE.sub(f"% !LOOM extracted-from: {m.group(1).strip()}", text, count=1), False
    if wid.published:
        # a DOI is not something statements can be extracted from, so recording it as `extracted-from` would assert
        # something false. Say only what is known -- the work the bibliography cites -- and leave the artifact blank;
        # loom:unverified-locators then asks for it rather than the quilt quietly claiming a provenance it lacks.
        return _SOURCE.sub(f"% !LOOM published-as: {wid}", text, count=1), False
    lines = [f"% !LOOM extracted-from: {wid}"]
    for other in identify(entry):
        if other.published:
            lines.append(f"% !LOOM published-as: {other}")
            break
    return _SOURCE.sub("\n".join(lines), text, count=1), True


def migrate(root: Path) -> Migration:
    """Move a quilt's references into the current layout and split its digest headers. Idempotent."""
    rep = Migration()
    bib = _bib(root)
    refs = root / "refs"

    for old in sorted(refs.glob("*.tex")) if refs.is_dir() else []:
        text = old.read_text(encoding="utf-8", errors="replace")
        m = _DIGEST.search(text)
        if m is None:
            continue
        citekey = m.group(1)
        new = root / "digests" / old.name
        new.parent.mkdir(parents=True, exist_ok=True)
        if not _PREFIX.search(text):
            declared_line = f"% !LOOM prefix: {_slug(citekey)}"
            text = _DIGEST.sub(lambda mm, line=declared_line: mm.group(0) + "\n" + line, text, count=1)  # type: ignore[misc]
        text, certain = _split_header(text, bib.get(citekey))
        new.write_text(text, encoding="utf-8")
        old.unlink()
        rep.moved.append(f"refs/{old.name} -> digests/{old.name}")
        rep.rewrote.append(f"digests/{old.name}")
        if not certain:
            rep.unknown.append(citekey)

    for kind, pattern in (("src", "*"), ("pdf", "*.pdf")):
        home = refs / kind
        if not home.is_dir():
            continue
        for old in sorted(home.glob(pattern)):
            citekey = old.name[:-4] if kind == "pdf" and old.name.endswith(".pdf") else old.name
            wid = primary(bib.get(citekey))
            if wid is None:
                continue
            dest = refs / wid.path / ("paper.pdf" if kind == "pdf" else "src")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                continue
            shutil.move(str(old), str(dest))
            rep.moved.append(f"refs/{kind}/{old.name} -> refs/{wid.path}/{dest.name}")
        if home.is_dir() and not any(home.iterdir()):
            home.rmdir()
    return rep


def _slug(citekey: str) -> str:
    from loom.scan.bib import citekey_slug

    return citekey_slug(citekey)
