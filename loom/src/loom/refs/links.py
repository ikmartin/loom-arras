"""Typed links between results, and the only thing in this layer nobody verifies (plan 0.12 §7).

A digest of twenty papers that cannot point between them is twenty documents in a directory. A link is a **typed relation between two identified results, with a reason**: a closed vocabulary because an open one becomes prose with extra steps and because a viewer can only draw what it can name, two endpoints because a record with one is a summary and summaries are the thing this layer does not store, and a sentence because an untyped unexplained edge is noise and the sentence is what an author reads six months later.

**Written freely, not proposed.** An assertion about a relation has no page span to check it against, so a verification step would be theatre. Links are tier 3: never citable, never in a closure, never in a digest's `.tex`. They are navigation, not mathematics, and every surface that shows one says so.

They live in one file at `digests/links.jsonl` rather than per work, because a link's two ends are usually in two different digests and a record that lives in one of them is misfiled half the time.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from loom.clock import stamp

#: The vocabulary, closed. Each is read "<from> <kind> <to>".
KINDS: dict[str, str] = {
    "same-notion": "defines the same notion as",
    "generalises": "generalises",
    "specialises": "is a special case of",
    "depends-on": "depends on",
    "contradicts": "contradicts",
}


@dataclass
class Link:
    """One asserted relation between two results."""

    id: str
    frm: str
    to: str
    kind: str
    why: str
    by: str = ""
    when: str = ""

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["from"] = d.pop("frm")
        return d

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> Link:
        return cls(
            id=str(d["id"]),
            frm=str(d.get("from", "")),
            to=str(d.get("to", "")),
            kind=str(d.get("kind", "")),
            why=str(d.get("why", "")),
            by=str(d.get("by", "")),
            when=str(d.get("when", "")),
        )


def links_path(root: Path) -> Path:
    return root / "digests" / "links.jsonl"


def read_links(root: Path) -> list[Link]:
    """Every link, oldest first; an unlinked one is gone from the file, so this is the live set."""
    path = links_path(root)
    if not path.is_file():
        return []
    out: list[Link] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Link.from_json(json.loads(line)))
        except (ValueError, KeyError, TypeError):
            continue
    return out


def write_links(root: Path, links: list[Link]) -> None:
    """Rewrite the file. Links are edited by hand often enough that an append-only log would mostly be tombstones."""
    path = links_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(x.to_json()) + "\n" for x in links), encoding="utf-8")


def next_id(links: list[Link]) -> str:
    taken = {x.id for x in links}
    n = 1
    while f"link-{n:04d}" in taken:
        n += 1
    return f"link-{n:04d}"


def add_link(root: Path, frm: str, to: str, kind: str, why: str, by: str) -> Link:
    """Record one link, refusing a kind outside the vocabulary and a link to itself.

    Parameters
    ----------
    root : Path
        The quilt root.
    frm, to : str
        Result ids, in either digest. Both must exist; a link to something that is not there is a typo, not a claim.
    kind : str
        One of `KINDS`.
    why : str
        One or two sentences. Not optional: an untyped, unexplained edge is noise.
    by : str
        Who asserted it.

    Returns
    -------
    Link
        The stored record.
    """
    if kind not in KINDS:
        raise ValueError(f"{kind} is not a link kind; use one of {', '.join(sorted(KINDS))}")
    if frm == to:
        raise ValueError("a link needs two different results")
    if not why.strip():
        raise ValueError("say why in a sentence: an unexplained edge is noise, and the sentence is what you read later")
    links = read_links(root)
    for x in links:
        if x.frm == frm and x.to == to and x.kind == kind:
            raise ValueError(f"{x.id} already says that; loom refs unlink {x.id} to replace it")
    made = Link(id=next_id(links), frm=frm, to=to, kind=kind, why=why.strip(), by=by, when=stamp())
    links.append(made)
    write_links(root, links)
    return made


def remove_link(root: Path, link_id: str) -> Link:
    """Remove one link, returning what was removed."""
    links = read_links(root)
    keep = [x for x in links if x.id != link_id]
    if len(keep) == len(links):
        raise LookupError(f"no link {link_id}")
    gone = next(x for x in links if x.id == link_id)
    write_links(root, keep)
    return gone


def touching(root: Path, key: str) -> list[Link]:
    """Every link with `key` at either end, which is what a result's page shows."""
    return [x for x in read_links(root) if key in (x.frm, x.to)]
