"""Filing one PDF a person dropped in the viewer (plan 0.24.2), with the pieces `loom library add` files with: identified by what its first pages show, filed under the work it is, beside any document the work already holds, or recorded as a copy.

A PDF that shows no work in the library is offered an entry from its own account, as gathering offers one to a stored document no entry names: the identifier on its first pages, and a title only where a reference manager wrote it into the filename.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.scan.scan import ScanResult


class FilingRefused(Exception):
    """A document that will not be filed under the work asked for, and why."""


@dataclass
class Seen:
    """What a dropped PDF shows: the works it matches strongly, the one to file it under when one is best, and, matching none, the entry its first pages offer."""

    matches: list[dict[str, Any]] = field(default_factory=list)
    best: str = ""
    offer: dict[str, str] = field(default_factory=dict)
    weak: str = ""

    def to_json(self) -> dict[str, Any]:
        return {"matches": list(self.matches), "best": self.best, "offer": dict(self.offer), "weak": self.weak}


def identify(result: ScanResult, pdf: Path) -> Seen:
    """What `pdf` shows itself to be, against the library's entries, as `loom library add` reads it."""
    from loom.refs.ingest import identify_document
    from loom.refs.scan import _own_account, one_work_of

    bib = result.bib
    identity = identify_document(pdf, bib)
    seen = Seen(matches=[{"citekey": m.citekey, "strength": m.strength, "how": m.how} for m in identity.strong])
    best = identity.best()
    if len(best) > 1 and (top := one_work_of([m.citekey for m in best], bib)):
        best = [m for m in best if m.citekey == top] or best[:1]
    if len(best) == 1:
        seen.best = best[0].citekey
        return seen
    seen.weak = identity.weak if not best else f"it names {' and '.join(m.citekey for m in best)} equally"
    if not best:
        wid, fields = _own_account(pdf)
        fields = dict(fields)
        # a reference manager's `Author - 2019 - Title.pdf` gives the first author too, which the key is made from
        named = re.match(r"^(?P<who>[^-]+?)(?:\s+et\s+al\.?)?\s+-\s+(?:19|20)\d\d\s+-\s+", pdf.stem)
        if named and fields.get("title") and "author" not in fields:
            fields["author"] = re.split(r"\s+and\s+|,\s*", named.group("who").strip())[0]
        if wid is not None:
            if wid.scheme == "arxiv":
                fields.update(eprint=wid.value, archiveprefix="arXiv")
            else:
                fields[wid.scheme] = wid.value
        seen.offer = fields
    return seen


def file_under(result: ScanResult, pdf: Path, citekey: str, by: str, *, came_from: str) -> dict[str, Any]:
    """File `pdf` under the work `citekey`, as `loom library add PDF --for CITEKEY` files it, and say where it went.

    Parameters
    ----------
    result : ScanResult
        A scan of the quilt whose bibliography holds `citekey`.
    pdf : Path
        The document, anywhere on disk; it is copied into the store.
    citekey : str
        The work it is filed under.
    by : str
        Who filed it, for the copy ledger.
    came_from : str
        Where it came from, as the ledger and a sibling entry's `loom-source` record it: the dropped file's name.

    Returns
    -------
    dict
        `{citekey, filed, sibling, already, copy_of}`: whether it was filed, under a sibling entry beside the work's first document, held already, or a copy of one of the work's documents.

    Raises
    ------
    FilingRefused
        The document does not show it is that work, or shows it is another.
    """
    from loom.refs.ingest import identify_document
    from loom.refs.pages import sha256_of
    from loom.refs.scan import Filing, append_entries, file_document, plan_filing, record_copy_of

    bib = result.bib
    if citekey not in bib:
        raise FilingRefused(f"the library has no work {citekey}")
    why = identify_document(pdf, bib).refusal_for(citekey, bib[citekey])
    if why:
        raise FilingRefused(why)
    f = Filing(pdf, citekey, "pdf", sha256_of(pdf), came_from)
    sibling = plan_filing(result.quilt, bib, f, set(bib), {})
    if not f.already:
        file_document(result.quilt, f, by=by)
    if f.copy_of:
        record_copy_of(result.quilt, bib, f)
    append_entries(result.quilt, [sibling] if sibling is not None else [])
    return {
        "citekey": citekey,
        "filed": not f.already,
        "sibling": f.sibling,
        "already": f.already,
        "copy_of": f.copy_of,
    }
