"""`loom here`: where the person is looking in the viewer, from the tab they touched last, as `loom serve` holds it."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from loom.cli._common import EnvError
from loom.cli._quilt import open_quilt, open_scan, quilt_option
from loom.cli.report import Report
from loom.scan.scan import ScanResult


@click.command(name="here")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Print the report as one JSON object, the place as the viewer sent it beside it.",
)
@quilt_option
def here_command(as_json: bool, quilt_path: str | None) -> None:
    """Say where the person is looking in the viewer: the document, result, paper or session in front of them, the block at the top of the pane, the words they selected or the region of a page, and the session their annotations land in.

    The viewer tab they touched last reports it to `loom serve`, which keeps it in memory only. With nothing serving the quilt, or no tab open, it says so. Each thing is named with the link `loom link` prints.
    """
    root = open_quilt(quilt_path).root
    from loom.render.serve import open_url, read_serve_json

    url = open_url(root)
    if not url:
        Report(
            "nothing serves this quilt, so loom cannot say where the person is looking",
            lines=["`loom serve` starts the viewer; the person opens it, and what they look at is reported here."],
            data={"serving": False, "place": None},
        ).emit(as_json)
        return
    got = _fetch(url, str(read_serve_json(root).get("token") or ""))
    if got.get("place") is None:
        Report(
            f"loom serve is running, but no viewer tab has reported where it is; the person opens {url}",
            data={"serving": True, "url": url, "place": None},
        ).emit(as_json)
        return
    result = open_scan(quilt_path)
    place: dict[str, Any] = got["place"]
    looking = _resolve(result, place)
    Report(
        _verdict(looking),
        lines=_lines(looking) + [f"(reported {_ago(got.get('age'))} by the viewer tab touched last)"],
        data={
            "serving": True,
            "url": url,
            "when": got.get("when"),
            "age": got.get("age"),
            "place": place,
            "looking": looking,
        },
    ).emit(as_json)


def _fetch(url: str, token: str) -> dict[str, Any]:
    """`GET /_api/here` with the server's token; a server that does not answer is an environment problem."""
    import json
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url + "_api/here", headers={"X-Loom-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=2) as answer:
            got = json.loads(answer.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise EnvError(f"loom serve did not answer at {url}: {exc}") from None
    return got if isinstance(got, dict) else {}


def _href(link: str) -> str:
    return link.removeprefix("[](").removesuffix(")")


def _key(result: ScanResult, key: str) -> dict[str, Any]:
    """A key as the reader knows it, its taxon and title, with its link; `gone` when the quilt no longer has it."""
    from loom.links import quilt_link

    n = result.nodes.get(key)
    if n is None:
        return {"key": key, "name": key, "link": None, "gone": True}
    name = " · ".join(x for x in (n.taxon, n.title) if x) or key
    return {"key": key, "name": name, "link": _href(quilt_link(key))}


def _work(result: ScanResult, citekey: str, page: Any = None) -> dict[str, Any]:
    """A cited work, and a page of it, at the `cited:` address `loom link` prints."""
    from loom.cli.review import _work_target
    from loom.links import cited_link

    page = page if isinstance(page, int) and page > 0 else None
    found = _work_target(result, citekey)
    entry = result.bib.get(citekey)
    title = entry.fields.get("title", "").strip("{} ") if entry is not None else ""
    out: dict[str, Any] = {"work": citekey, "name": f"{citekey} · {title}" if title else citekey, "page": page}
    out["link"] = _href(cited_link(found[1].scheme, found[1].value, page)) if found else None
    return out


def _item(result: ScanResult, item: Any, page: Any = None) -> dict[str, Any] | None:
    """One pane's item resolved: what it is, its name, and its link."""
    from loom.sessions import sessions

    if not isinstance(item, dict):
        return None
    kind, ident = str(item.get("kind", "")), str(item.get("id", ""))
    if kind == "document":
        return {"kind": kind, "path": ident, "name": ident, "link": f"quilt:{ident}"}
    if kind in ("node", "context"):
        return {"kind": kind, **_key(result, ident)}
    if kind == "work":
        place = item.get("place")
        return {"kind": kind, **_work(result, ident, page or (place.get("page") if isinstance(place, dict) else None))}
    if kind == "session":
        found = sessions(Path(result.quilt.root)).get(ident)
        return {"kind": kind, "session": ident, "name": found.title if found else ident, "link": f"quilt:{ident}"}
    if kind == "page" and ident == "state":
        return {"kind": kind, "name": "the research state", "link": "quilt:state"}
    return {"kind": kind, "name": ident, "link": None}


def _resolve(result: ScanResult, place: dict[str, Any]) -> dict[str, Any]:
    """The reported place against the quilt as it stands: each thing named and linked, a key it no longer has marked `gone`."""
    out: dict[str, Any] = {"route": place.get("route")}
    if place.get("route") == "review":
        review = place.get("review")
        if isinstance(review, dict) and review.get("key"):
            out["review"] = {**_key(result, str(review["key"])), "cause": review.get("cause") or None}
    elif place.get("route") == "elsewhere":
        out["path"] = str(place.get("path") or "")
    else:
        out["item"] = _item(result, place.get("item"), place.get("page"))
        block = place.get("block")
        if isinstance(block, dict) and block.get("key"):
            out["block"] = _key(result, str(block["key"]))
        sel = place.get("selection")
        if isinstance(sel, dict):
            if sel.get("key"):
                out["selection"] = {**_key(result, str(sel["key"])), "text": str(sel.get("text") or "")}
            elif isinstance(sel.get("page"), int) and out["item"] and out["item"].get("work"):
                at = _work(result, out["item"]["work"], sel["page"])
                out["selection"] = {**at, "text": str(sel.get("text") or ""), "rects": sel.get("rects") or []}
        out["beside"] = _item(result, place.get("beside"))
    sid = place.get("session")
    if isinstance(sid, str) and sid:
        out["session"] = _item(result, {"kind": "session", "id": sid})
    return out


def _named(thing: dict[str, Any] | None) -> str:
    if not thing:
        return ""
    name = str(thing.get("name") or "")
    if thing.get("key") and thing["key"] != name:
        name = f"{thing['key']} ({name})"
    if thing.get("page"):
        name += f", page {thing['page']}"
    return name


def _verdict(looking: dict[str, Any]) -> str:
    if looking.get("route") == "review":
        return (
            f"the person is in Review, on {_named(looking['review'])}"
            if "review" in looking
            else "the person is in Review"
        )
    if looking.get("route") == "elsewhere":
        return f"the person is on {looking.get('path') or 'a page'} in the viewer, reading nothing"
    said = f"the person is looking at {_named(looking.get('item')) or 'nothing the viewer names'}"
    block = looking.get("block")
    if block and block.get("key") != (looking.get("item") or {}).get("key"):
        said += f", at {_named(block)}"
    return said


def _lines(looking: dict[str, Any]) -> list[str]:
    """One line per thing in front of the person, each with its link."""

    def line(label: str, thing: dict[str, Any] | None, extra: str = "") -> list[str]:
        if not thing:
            return []
        link = f"  []({thing['link']})" if thing.get("link") else ""
        gone = "  (no longer in the quilt)" if thing.get("gone") else ""
        return [f"  {label:<9} {_named(thing)}{extra}{link}{gone}"]

    out: list[str] = [""]
    if "review" in looking:
        cause = looking["review"].get("cause")
        out += line("reviewing", looking["review"], f", which needs review: {cause}" if cause else "")
    else:
        out += line("open", looking.get("item"))
        out += line("at", looking.get("block"))
        sel = looking.get("selection")
        if sel:
            if sel.get("text"):
                out += line("selected", sel)
                out.append(f'            "{sel["text"]}"')
            else:
                box = "; ".join(_box(r) for r in sel.get("rects") or [])
                out += line("region", sel, f" at {box} (points from the page's top left)" if box else "")
        out += line("beside", looking.get("beside"))
    session = looking.get("session")
    if session:
        out += line("session", session, " (annotations land here)")
    return out


def _box(rect: Any) -> str:
    """A region's corners as the viewer sent them, in PDF points: `x0,y0,x1,y1`."""
    try:
        return ",".join(f"{float(v):g}" for v in rect)
    except (TypeError, ValueError):
        return str(rect)


def _ago(age: Any) -> str:
    if not isinstance(age, int | float):
        return "just now"
    if age < 60:
        return f"{int(age)} s ago"
    return f"{int(age // 60)} min ago"
