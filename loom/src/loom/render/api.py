"""The write API: the HTTP form of loom's record-writing commands (specs/write-api.md, plan 0.11 Part G).

Served by the publisher, never by the viewer, and it writes only to loom's own record locations -- never to a source file. Every endpoint wraps the same library function the CLI calls, so there is one implementation of what a comment is and the two surfaces cannot drift.

Nothing here wakes an agent. An agent pulls: it reads open findings with `loom status` and `loom ai findings` and answers with `loom comment --reply`. A person writing in the viewer and an agent answering in its own session are the same log seen from two ends.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loom.clock import stamp

#: What this publisher serves. A viewer reads this rather than assuming the specification's table, so an endpoint that
#: is not here answers 404 and a viewer that hides the affordance is right to.
CAPABILITIES = [
    "comment",
    "reply",
    "resolve",
    "edit",
    "discard",
    "refs-note",
    "digest-verify",
    "digest-discard",
    "locate",
]

WRITE_API_VERSION = 1


class ApiError(Exception):
    """A request loom refused, with the code a viewer shows and the status it gets."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def discovery() -> dict[str, Any]:
    """The answer to `GET /_api`."""
    return {"write_api": WRITE_API_VERSION, "capabilities": list(CAPABILITIES)}


def _str(body: dict[str, Any], name: str, *, required: bool = False) -> str | None:
    value = body.get(name)
    if value is None or value == "":
        if required:
            raise ApiError("missing-field", f"{name} is required")
        return None
    if not isinstance(value, str):
        raise ApiError("bad-field", f"{name} must be a string")
    return value


def handle(root: Path, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """Perform one write and describe it, or raise `ApiError`.

    Parameters
    ----------
    root : Path
        The quilt.
    endpoint : str
        The path after `/_api/`, one of `CAPABILITIES`.
    body : dict
        The decoded JSON request.

    Returns
    -------
    dict
        `{"ok": True, "result": <what the CLI would have printed>}`.
    """
    if endpoint not in CAPABILITIES:
        raise ApiError("unknown-endpoint", f"no endpoint {endpoint}", status=404)
    if endpoint == "refs-note":
        return {"ok": True, "result": _refs_note(root, body)}
    if endpoint in ("digest-verify", "digest-discard"):
        return {"ok": True, "result": _digest(root, endpoint, body)}
    if endpoint == "locate":
        return _locate(root, body)
    return {"ok": True, "result": _review(root, endpoint, body)}


def _locate(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """Turn a reader's selection on a page into the anchor loom would record (plan 0.13 item 2).

    Body: `citekey`, `page`, and either `text` -- what the reader selected -- or `rects`, the rectangles they drew when there was no text worth selecting. The answer carries the anchor and, beside it, the line a person would read.

    **Mapping happens here and not in the viewer.** The client's text layer is a third extraction of the page, after the committed page text and the word boxes; only loom holds the other two, and only loom can say what the committed text says, which is what an anchor is checked against. The client never decides what the anchor is.

    This endpoint **writes nothing**: it answers, and whether an annotation is made is a separate act.
    """
    from loom.cli._quilt import open_scan
    from loom.refs.fetch import work_dir
    from loom.refs.pages import page_box, read_map, read_page, token_boxes
    from loom.refs.proposals import Anchor
    from loom.refs.search import locate_offsets, locate_span, words_in_boxes

    citekey = _str(body, "citekey", required=True) or ""
    page = body.get("page")
    if not isinstance(page, int) or page < 1:
        raise ApiError("bad-field", "page must be a positive integer")
    rects = [[float(v) for v in r] for r in body.get("rects") or []]
    text = _str(body, "text")
    if not text and not rects:
        raise ApiError("missing-field", "one of text or rects is required")

    result = open_scan(str(root))
    if citekey not in result.bib:
        raise ApiError("no-such-work", f"{citekey} is not in the bibliography", status=404)
    home = work_dir(root, result.bib[citekey])
    pdf = home / "paper.pdf"
    m = read_map(home)
    if m is None or not pdf.is_file():
        raise ApiError("not-readable", f"{citekey} has no copy on this machine", status=404)
    xml = token_boxes(pdf, page, home)

    anchor = Anchor(kind="pdf", sha256=m.sha256, page=page)
    span = locate_span(xml, text, page) if text else None
    if span is not None:
        offsets = locate_offsets(read_page(home, page) or "", text or "")
        anchor.quads = [list(q) for q in span.lines]
        if offsets:
            anchor.basis, anchor.start, anchor.end = "text", offsets[0], offsets[1]
        else:
            # found on the page's boxes and not in its committed text: geometry is what can honestly be recorded
            anchor.basis = "box"
    else:
        # a formula, a figure, a scan: what the reader drew is the record, and whatever words it covers are a hint
        anchor.basis, anchor.quads = "box", rects
        text = words_in_boxes(xml, rects) or text
    box = page_box(xml)
    said = "text" if anchor.basis == "text" else "box"
    return {
        "ok": True,
        "result": f"{citekey} p.{page} anchored by {said}, {len(anchor.quads or [])} line(s)",
        "anchor": _anchor_json(anchor),
        "text": text or "",
        "page_box": {"width": box[0], "height": box[1]} if box else None,
    }


def _anchor_json(anchor: Any) -> dict[str, Any]:
    """An anchor in the shape a result record carries it, so the endpoint and the record cannot spell one differently."""
    from loom.refs.proposals import Result

    out: dict[str, Any] = Result(id="", local="", anchor=anchor).to_json()["anchor"]
    return out


def _digest(root: Path, endpoint: str, body: dict[str, Any]) -> str:
    """Verify or discard a proposed digest node, through the same functions `loom refs verify|discard` call.

    `digest-verify` with a `statement` is edit-then-verify: the author's own rendering replaces the proposed one and both parties are recorded. It never touches `source_text`, so the anchor survives and the node stays re-checkable (plan 0.12 §5.4).
    """
    from loom.cli._quilt import open_scan
    from loom.refs.proposals import discard_result, verify_result
    from loom.scan.quilt import resolve_author

    node = _str(body, "node", required=True) or ""
    result = open_scan(str(root))
    who = resolve_author(_str(body, "author"), root)[0]
    try:
        if endpoint == "digest-discard":
            return discard_result(result, node, _str(body, "reason", required=True) or "", who)
        return verify_result(
            result, node, _str(body, "statement"), who, local=_str(body, "local"), taxon=_str(body, "taxon")
        )[0]
    except LookupError as exc:
        raise ApiError("no-such-node", str(exc), status=404) from exc


def _review(root: Path, endpoint: str, body: dict[str, Any]) -> str:
    # Imported here rather than at module scope: the CLI package pulls in click and the whole command tree, and a
    # server that is only ever asked for files should not pay for it at startup.
    from loom.cli._common import ContentError, EnvError
    from loom.cli._quilt import open_scan
    from loom.cli.review import _one_comment, _writer, discard_annotation, edit_annotation

    # Validate the request before touching the quilt: a missing field is the caller's mistake and should be named as
    # one, not reported as whatever the first function to be handed nothing happens to complain about.
    needs = {"comment": ("target", "message"), "reply": ("annotation", "message")}.get(endpoint, ("annotation",))
    for field in needs:
        _str(body, field, required=True)

    try:
        writer = _writer(root, _str(body, "run"), _str(body, "author"))
    except (EnvError, ContentError) as exc:
        raise ApiError("no-such-run", str(exc)) from exc

    try:
        # `undo` puts a withdrawn or resolved finding back by appending another event; the viewer offers it in place
        # of the verb that fired, so a wrong click is one click back (DR-174).
        undo = bool(body.get("undo"))
        if endpoint == "discard":
            return discard_annotation(
                root, _str(body, "annotation", required=True) or "", writer, _str(body, "reason"), undo
            )
        if endpoint == "edit":
            fields = {k: _str(body, k) for k in ("message", "severity", "payload", "placement")}
            return edit_annotation(root, _str(body, "annotation", required=True) or "", writer, **fields)
        result = open_scan(str(root))
        if endpoint == "comment":
            return _one_comment(
                result,
                writer,
                _str(body, "target", required=True),
                _str(body, "message", required=True),
                _str(body, "quote"),
                _str(body, "kind"),
                None,
                None,
                _str(body, "severity"),
                _str(body, "payload"),
                _str(body, "placement"),
            )
        annotation = _str(body, "annotation", required=True)
        if endpoint == "reply":
            return _one_comment(
                result, writer, None, _str(body, "message", required=True), None, None, annotation, None
            )
        return _one_comment(result, writer, None, _str(body, "message"), None, None, None, annotation, undo=undo)
    except ContentError as exc:
        raise ApiError("refused", str(exc)) from exc
    except EnvError as exc:
        raise ApiError("bad-request", str(exc)) from exc


def _refs_note(root: Path, body: dict[str, Any]) -> str:
    """Accept or reject a citation an agent suggested: the log records the decision, the breadcrumb records the work."""
    from loom.ai.runs import thread_id
    from loom.records.annotations import find_annotation
    from loom.records.store import Records
    from loom.refs.notes import append_note

    decision = _str(body, "decision", required=True)
    if decision not in ("accept", "reject"):
        raise ApiError("bad-field", "decision must be accept or reject")
    ann_id = _str(body, "annotation", required=True) or ""
    records = Records(root).records
    found = find_annotation(records, ann_id)
    if found is None:
        raise ApiError("no-such-annotation", f"no annotation {ann_id}", status=404)
    record, annotation = found

    reason = _str(body, "reason")
    try:
        resolved = _review(root, "resolve", {**body, "message": reason or f"{decision}ed"})
    except ApiError:
        raise
    if decision == "reject":
        return f"rejected {ann_id}; {resolved}"
    append_note(
        root,
        {
            "work": annotation.body,
            "for": [annotation.target_key],
            "claim": annotation.selector.exact if annotation.selector else None,
            "identifier": {"verified": False},
            "accepted": {"when": stamp(), "who": _str(body, "author") or "viewer"},
            "from": {"run": thread_id(record.rel), "annotation": ann_id},
        },
    )
    return f"accepted {ann_id}; {resolved}"
