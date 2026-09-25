"""Links an agent or a person writes into what the viewer shows (plan 0.14 phase 3, specs/dialect.md §2.13).

Two schemes and one grammar. `quilt:KEY[#PLACE]` names something this quilt owns by its fixed key -- a node, a document, an annotation, a session -- and `cited:SCHEME:VALUE[?page=N&quote=…]` names a place in a cited work by its global identifier. **Only what the viewer can show is linkable**: an included file that is no document, a session's drafts, a deleted session are refused, because a link to something the viewer does not display is a link to nothing.

A link is checked when it is posted (`loom session say`, `loom annotate`) and printed correctly by `loom link`, so an agent never composes one by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote

#: A markdown link whose destination is one of the two schemes.
LINK = re.compile(r"\]\(((?:quilt|cited):[^)\s]+)\)")
ANNOTATION = re.compile(r"^a-\d{4}-\d{2}-\d{2}-\d+$")
SESSION = re.compile(r"^s-\d{4}-\d{2}-\d{2}-\d{4}$")


class LinkError(ValueError):
    """A link that names nothing the viewer shows; the message says what and why."""


@dataclass(frozen=True)
class Target:
    """What a link names: its kind, the key it is addressed by, and the place in it, if any."""

    kind: str  # node | document | annotation | session | work
    key: str
    place: str = ""
    href: str = ""


def resolve(result: Any, root: Path, href: str, records: list[Any] | None = None) -> Target:
    """The thing `href` names, or LinkError.

    Parameters
    ----------
    result : ScanResult
        The quilt as scanned: its nodes, documents and bibliography.
    root : Path
        The quilt root, for its sessions and its annotation log.
    href : str
        A `quilt:` or `cited:` link.
    records : list, optional
        The annotation records; read from the log when not given.

    Returns
    -------
    Target

    Raises
    ------
    LinkError
        When the link names nothing the viewer shows.
    """
    if href.startswith("quilt:"):
        return _quilt(result, root, href, records)
    if href.startswith("cited:"):
        return _cited(result, href)
    raise LinkError(f"{href}: a link is quilt:KEY or cited:SCHEME:VALUE")


def _quilt(result: Any, root: Path, href: str, records: list[Any] | None) -> Target:
    from loom.cli._common import EnvError
    from loom.cli._quilt import resolve_key

    body = href[len("quilt:") :]
    key, _, place = body.partition("#")
    if not key:
        raise LinkError(f"{href}: names no key")
    if ANNOTATION.match(key):
        from loom.records.annotations import find_annotation, load_records

        if records is None:
            records, _ = load_records(root)
        if find_annotation(records, key) is None:
            raise LinkError(f"{href}: no annotation {key}")
        return Target("annotation", key, href=href)
    if SESSION.match(key):
        from loom.sessions import sessions

        if key not in sessions(root):
            raise LinkError(f"{href}: no session {key}")
        return Target("session", key, href=href)
    if key in result.canon_files:
        if place:
            raise LinkError(f"{href}: a landmark is linked whole")
        return Target("document", key, href=href)
    try:
        canonical = resolve_key(result, key)
    except EnvError:
        raise LinkError(f"{href}: no key {key} in this quilt") from None
    node = result.nodes.get(canonical)
    if node is not None and node.kind == "master":
        if place:
            _reached(result, href, place, canonical)
        return Target("document", canonical, place, href)
    if node is not None and node.kind == "file":
        raise LinkError(f"{href}: {key} is a file the documents include, and the viewer shows no file on its own")
    if place:
        owner = _owner(result, _key(result, href, place))
        if owner != _owner(result, canonical):
            raise LinkError(f"{href}: {place} is not in {key}")
    return Target("node", canonical, place, href)


def _key(result: Any, href: str, key: str) -> str:
    from loom.cli._common import EnvError
    from loom.cli._quilt import resolve_key

    try:
        return resolve_key(result, key)
    except EnvError:
        raise LinkError(f"{href}: no key {key} in this quilt") from None


def _owner(result: Any, key: str) -> str:
    """The node a key is shown in: a region's container, a proof's statement, else the key itself."""
    region = result.assembly.regions.get(key)
    if region is not None:
        key = region.container
    return key.split("/proof", 1)[0]


def _reached(result: Any, href: str, place: str, master: str) -> None:
    """Refuse a place a document does not reach."""
    owner = _owner(result, _key(result, href, place))
    node = result.nodes.get(owner)
    if node is None or master not in node.reached_by:
        raise LinkError(f"{href}: {master} does not include {place}")


def _cited(result: Any, href: str) -> Target:
    from loom.refs.identity import identify, parse

    m = re.match(r"([^?#]*)(?:[?#](.*))?$", href[len("cited:") :], re.S)
    target, rest = (m.group(1), m.group(2) or "") if m else ("", "")
    wid = parse(target)
    if wid is None:
        raise LinkError(f"{href}: cited: takes a work's identifier, doi:…, arXiv:…, MR…, zbMATH…")
    for citekey, entry in result.bib.items():
        if any((w.scheme, w.value.lower()) == (wid.scheme, wid.value.lower()) for w in identify(entry)):
            keys = parse_qs(rest.replace("#", "&"))
            page = (keys.get("page") or [""])[0]
            if page and not (page.isdigit() and int(page) > 0):
                raise LinkError(f"{href}: page must be a number from 1")
            return Target("work", citekey, f"page={page}" if page else "", href)
    raise LinkError(f"{href}: no entry in the bibliography states {target}")


def check(result: Any, root: Path, text: str) -> list[str]:
    """One sentence per link in `text` that names nothing the viewer shows; empty when every link resolves."""
    from loom.records.annotations import load_records

    hrefs = LINK.findall(text)
    if not hrefs:
        return []
    records, _ = load_records(root)
    out: list[str] = []
    for href in hrefs:
        try:
            resolve(result, root, href, records)
        except LinkError as exc:
            out.append(str(exc))
    return out


def refuse_bad_links(result: Any, root: Path, text: str) -> None:
    """Raise ContentError naming every bad link in `text`, with the command that prints a good one."""
    from loom.cli._common import ContentError

    bad = check(result, root, text)
    if bad:
        raise ContentError(
            "links that name nothing the viewer shows:\n  "
            + "\n  ".join(bad)
            + "\n`loom link THING` prints a correct one"
        )


def quilt_link(key: str, place: str = "") -> str:
    """`[](quilt:KEY#PLACE)`, the empty text the viewer fills with its own name for the thing."""
    return f"[](quilt:{key}{'#' + place if place else ''})"


def cited_link(scheme: str, value: str, page: int | None = None, text: str | None = None) -> str:
    """`[](cited:SCHEME:VALUE?page=N&quote=…)`."""
    keys = []
    if page:
        keys.append(f"page={page}")
    if text:
        keys.append("quote=" + quote(text, safe=""))
    return f"[](cited:{scheme}:{value}{'?' + '&'.join(keys) if keys else ''})"
