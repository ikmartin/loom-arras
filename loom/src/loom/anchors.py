"""One anchor type, shared by results, digest nodes and annotations (plan 0.13 item 2).

Where something was read from. A **PDF anchor** names a page of an artifact by the artifact's hash, and says which of its two descriptions is of record: `basis: text` when `start`/`end` locate the quotation in the committed page text -- searchable, listable, re-findable in another copy of the work -- and `basis: box` when they cannot, which is what a display formula does, whose text layer is control bytes. A **LaTeX anchor** names a file under the quilt by its path and hash, and `bytes` the range the quotation occupies.

`quads` is one rectangle per line, in points with the origin at the top left. For a text anchor it is derived at build time from the offsets and never recorded; for a box it *is* the anchor, and is recorded. Recording never fails: what cannot be found in the text is recorded as geometry.

A result's anchor lives in `digests/<citekey>.results.json`; an annotation's lives in the `anchor` field of its `created` event, beside the `exact`/`prefix`/`suffix` triple annotations have always carried (`records/selectors.py`), and is told from a plain text selector by carrying `kind`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, TypeGuard

#: The keys a PDF anchor does not carry, and the keys a LaTeX anchor does not. Each kind carries only its own, so a
#: field added to `Anchor` and not named here lands in both kinds and means nothing in one of them.
_NOT_PDF = ("path", "bytes")
_NOT_TEX = ("page", "quads", "last", "basis", "start", "end")
#: Optional either way: dropped when empty, so a record says only what it knows.
_OPTIONAL = ("quads", "last", "path", "bytes", "basis", "start", "end")


@dataclass
class Anchor:
    kind: str = "pdf"
    sha256: str = ""
    page: int = 0
    quads: list[list[float]] | None = None
    last: int = 0
    path: str = ""
    bytes: list[int] | None = None
    basis: str = ""  # pdf only: `text` | `box`
    start: int = 0  # pdf, basis text: offsets into the committed page text of `page`
    end: int = 0

    @property
    def pages(self) -> range:
        return range(self.page, max(self.page, self.last) + 1)

    def to_dict(self) -> dict[str, Any]:
        """The anchor as a record carries it: its own kind's keys, and none that are empty (contract §9.2, §9.3)."""
        a = asdict(self)
        for key in _NOT_PDF if a["kind"] == "pdf" else _NOT_TEX:
            a.pop(key)
        for key in _OPTIONAL:
            if key in a and not a[key]:
                a.pop(key)
        return a

    @classmethod
    def from_dict(cls, a: dict[str, Any]) -> Anchor:
        """An anchor from a record, every field coerced and defaulted, so a hand-edited file cannot raise here."""
        return cls(
            kind=str(a.get("kind", "pdf")),
            sha256=str(a.get("sha256", "")),
            page=int(a.get("page", 0) or 0),
            quads=[[float(v) for v in q] for q in a["quads"]] if a.get("quads") else None,
            last=int(a.get("last", 0) or 0),
            path=str(a.get("path", "")),
            bytes=[int(x) for x in a["bytes"]] if a.get("bytes") else None,
            basis=str(a.get("basis", "")),
            start=int(a.get("start", 0) or 0),
            end=int(a.get("end", 0) or 0),
        )


def is_page_anchor(d: Any) -> TypeGuard[dict[str, Any]]:
    """Whether a record's `anchor` value is a PDF anchor rather than a plain text selector: it carries `kind`."""
    return isinstance(d, dict) and d.get("kind") == "pdf"
