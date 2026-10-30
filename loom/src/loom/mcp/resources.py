"""The MCP resources: what a link names, read at the address `loom link` prints, each by the reading command it stands for.

`quilt:KEY` is `loom source KEY` and `cited:ID?page=N` is `loom library read ID N`; `reading` holds the whole table. A read runs its command, so it carries the command a person reruns, and a client that reads no resources loses nothing, since each is also a tool. The one exception is `quilt:state`, which no command prints alone: it is served as `loom ai orient` prints it. The list is read off a scan, and holds what a person would `@`-mention; the templates reach the rest. Nothing here imports the MCP SDK.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import parse_qs, unquote

from loom.links import ANNOTATION, SESSION
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult

TEX, MARKDOWN, TEXT = "text/x-tex", "text/markdown", "text/plain"
#: `quilt:state`, the research state.
STATE = "state"


class NotAResource(ValueError):
    """A URI that names no resource; the message says what it is and what reads it instead."""


@dataclass(frozen=True)
class ResourceSpec:
    """One listed resource, or a template when `uri` holds `{…}`.

    Parameters
    ----------
    uri : str
    name : str
        The short name a client lists and searches: the key, path or citekey.
    title : str
    description : str
    mime : str
    """

    uri: str
    name: str
    title: str
    description: str
    mime: str


@dataclass(frozen=True)
class Reading:
    """How a URI is read: the command after `loom`, or None for the research state, and the kind of text it prints."""

    argv: tuple[str, ...] | None
    mime: str


TEMPLATES = (
    ResourceSpec(
        "quilt:{+key}",
        "key",
        "A key, a document or a landmark",
        "A key's own text, a document flattened with every inclusion in place, or a landmark's text, as `loom source` or `loom history show` prints it.",
        TEX,
    ),
    ResourceSpec(
        "quilt:{+key}?closure",
        "closure",
        "A key and what it depends on",
        "Exactly the statements a key depends on, in dependency order, then the key: `loom source KEY --closure`.",
        TEX,
    ),
    ResourceSpec(
        "cited:{+work}",
        "work",
        "A cited work's overview",
        "A cited work, by identifier (doi:…, arXiv:…): its overview, a reading of the paper, or with none the digest's opening, the paper's own words; `loom library read WORK`.",
        MARKDOWN,
    ),
    ResourceSpec(
        "cited:{+work}?page={page}",
        "page",
        "A page of a cited work",
        "A cited work's text on one page, the text a quotation is checked against: `loom library read WORK PAGE`.",
        TEXT,
    ),
)


def _positional(*words: str) -> tuple[str, ...]:
    """`words` as positionals, after `--` when one looks like an option, so an address never sets a flag."""
    return ("--", *words) if any(w.startswith("-") for w in words) else words


def landmarks(quilt: Quilt) -> dict[str, str]:
    """Each landmark's name, by its quilt-relative path and by its name: a link names one either way (`links._quilt`)."""
    from loom.scan.scan import landmark_documents

    out: dict[str, str] = {}
    for path in landmark_documents(quilt):
        name = PurePosixPath(path).stem
        out[path] = out[name] = name
    return out


def reading(uri: str, quilt: Quilt) -> Reading:
    """The command that reads `uri`, or NotAResource.

    quilt:KEY              loom source KEY
    quilt:KEY?closure      loom source --closure KEY
    quilt:DOC.tex#PLACE    loom source PLACE
    quilt:KEY#PLACE        loom source KEY, the node the place is in
    quilt:LANDMARK         loom history show NAME
    quilt:state            no command: `research_state`, as `loom ai orient` prints it
    cited:ID               loom library read ID
    cited:ID?page=N        loom library read ID N

    Only the syntax is read here: a key that names nothing is the command's own refusal.
    """
    if uri.startswith("cited:"):
        body, _, query = uri[len("cited:") :].partition("?")
        work = unquote(body.split("#", 1)[0])
        if not work:
            raise NotAResource(f"{uri}: names no work; `loom link CITEKEY` prints a work's address")
        page = (parse_qs(query.replace("#", "&")).get("page") or [""])[0]
        if page and not (page.isdigit() and int(page) > 0):
            raise NotAResource(f"{uri}: page must be a number from 1")
        if page:
            return Reading(("library", "read", *_positional(work, page)), TEXT)
        return Reading(("library", "read", *_positional(work)), MARKDOWN)
    if not uri.startswith("quilt:"):
        raise NotAResource(
            f"{uri}: loom's resources are quilt:KEY and cited:SCHEME:VALUE, the addresses `loom link` prints"
        )
    body, _, place = uri[len("quilt:") :].partition("#")
    raw, _, query = body.partition("?")
    key, place = unquote(raw), unquote(place)
    asked = parse_qs(query, keep_blank_values=True)
    if set(asked) - {"closure"}:
        raise NotAResource(f"{uri}: a quilt: address takes only ?closure")
    closure = ("--closure",) if "closure" in asked else ()
    if not key:
        raise NotAResource(f"{uri}: names no key")
    if ANNOTATION.match(key):
        raise NotAResource(f"{uri}: an annotation, which loom_ai_annotations reads with its thread")
    if SESSION.match(key):
        raise NotAResource(f"{uri}: a session, which loom_session_list lists and loom_ai_orient reads")
    if key == STATE:
        if closure or place:
            raise NotAResource(f"{uri}: the research state is read whole")
        return Reading(None, MARKDOWN)
    marks = landmarks(quilt)
    if key in marks:
        if closure or place:
            raise NotAResource(f"{uri}: a landmark is read whole")
        return Reading(("history", "show", *_positional(marks[key])), TEX)
    if key.endswith(".tex") and place:
        return Reading(("source", *closure, *_positional(place)), TEX)
    return Reading(("source", *closure, *_positional(key)), TEX)


def listed(result: ScanResult) -> list[ResourceSpec]:
    """What a person would `@`-mention: the research state, each document and landmark, each statement and section of the quilt's own, and each cited work with an identifier.

    A digest's results and every proof are left out, to keep the list to the quilt's own results; `quilt:{+key}` reads them.
    """
    from loom.pages import read, state_page
    from loom.refs.identity import primary

    quilt = result.quilt
    out: list[ResourceSpec] = []
    if read(quilt.root, state_page(quilt.config)) is not None:
        out.append(
            ResourceSpec(
                "quilt:state",
                "state",
                "Research state",
                "The quilt's goals, open problems, conventions and decisions, with the hash `loom write state --base` needs.",
                MARKDOWN,
            )
        )
    for path in sorted(result.masters):
        out.append(
            ResourceSpec(
                f"quilt:{path}",
                path,
                PurePosixPath(path).name,
                "A document, flattened with every inclusion in place.",
                TEX,
            )
        )
    for path in result.canon_files:
        name = PurePosixPath(path).stem
        out.append(
            ResourceSpec(f"quilt:{path}", name, f"Landmark {name}", "A landmark's text, as its step kept it.", TEX)
        )
    for key, n in result.nodes.items():
        if n.kind not in ("environment", "section") or n.external or n.conflict_of:
            continue
        title = " · ".join(x for x in (n.taxon, n.title) if x) or key
        out.append(
            ResourceSpec(
                f"quilt:{key}",
                key,
                title,
                f"Its own text, in {n.file}; quilt:{key}?closure adds what it depends on.",
                TEX,
            )
        )
    for ck, entry in sorted(result.bib.items()):
        wid = primary(entry)
        if wid is None:
            continue
        said = entry.fields.get("title", "").strip("{} ")
        out.append(
            ResourceSpec(
                f"cited:{wid.scheme}:{wid.value}",
                ck,
                f"{ck} · {said}" if said else ck,
                "Its overview, or the digest's opening; ?page=N reads one page of its text.",
                MARKDOWN,
            )
        )
    return out
