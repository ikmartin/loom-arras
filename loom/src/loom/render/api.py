"""The write API: the HTTP form of loom's record-writing commands (specs/write-api.md, plan 0.11 Part G).

Served by the publisher, never by the viewer. Most endpoints write only Loom's private records. The explicit ``sync-incorporate`` endpoint is the narrow
exception: it applies the already displayed pull to author files and records
two local commits. Every endpoint wraps a library function so its behavior is shared with recovery and test surfaces.

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
    "session-use",
    "session-rename",
    "session-delete",
    "session-new",
    "session-close",
    "session-reopen",
    "session-purpose",
    "message",
    "agent-stop",
    "sync-incorporate",
    "review-decision",
    "review-finish",
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
    if endpoint == "message":
        return _message(root, body)
    if endpoint == "sync-incorporate":
        from loom.scan.quilt import load_quilt
        from loom.sync import SyncError, SyncState, incorporate_pull

        try:
            quilt = load_quilt(root)
            state = SyncState.read(root)
            incoming = _str(body, "incoming", required=True)
            base = _str(body, "base", required=True)
            if incoming != state.incoming:
                raise ApiError("revision-changed", "the fetched revision changed; reload Incoming")
            if base != state.integrated and state.integrated != state.incoming:
                raise ApiError("revision-changed", "the incorporated base changed; reload Incoming")
            sync_result = incorporate_pull(quilt, state)
        except SyncError as exc:
            raise ApiError("sync-refused", str(exc), status=409) from exc
        return {"ok": True, "result": sync_result}
    if endpoint in ("review-decision", "review-finish"):
        from loom.cli._quilt import open_scan
        from loom.cli.review import _author, _master_compiles, write_acceptance
        from loom.review_queue import clear_accepted, decide, pending, rows_for

        result = open_scan(str(root))
        if endpoint == "review-decision":
            key = _str(body, "key", required=True) or ""
            status = _str(body, "status", required=True) or ""
            import json

            manifest_path = root / "build" / "manifest.json"
            if not manifest_path.is_file():
                raise ApiError("review-unavailable", "build the quilt before reviewing", status=409)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if key not in {row["key"] for row in rows_for(result, manifest)}:
                raise ApiError("not-unresolved", f"{key} is not awaiting review", status=409)
            try:
                decide(result, key, status)
            except ValueError as exc:
                raise ApiError("review-refused", str(exc), status=409) from exc
            return {"ok": True, "result": f"{key}: {status}"}
        try:
            keys = pending(result)
        except ValueError as exc:
            raise ApiError("review-changed", str(exc), status=409) from exc
        if not keys:
            raise ApiError("nothing-pending", "there are no pending OK decisions", status=409)
        for key in keys:
            node = result.nodes[key]
            if (
                node.external
                or node.incomplete
                or (node.kind == "environment" and node.basis in ("open-claim", "unclassified"))
            ):
                raise ApiError("not-acceptable", f"{key} is not eligible for acceptance", status=409)
        from loom.records.store import Records

        states = Records(root, result.quilt.history_dir).key_states(result)
        for key in keys:
            for dep in Records.direct_keys(result, key):
                dependency = states.get(dep)
                if dependency and dependency.row and not dependency.fresh and dep not in keys:
                    raise ApiError("dependency-pending", f"review {dep} before finishing {key}", status=409)
        remaining = [key for key in keys if not (states[key].row and states[key].fresh)]
        if not remaining:
            clear_accepted(root, keys)
            return {"ok": True, "result": "pending decisions were already accepted"}
        ok, why = _master_compiles(result)
        if not ok:
            raise ApiError("compile-failed", f"the document does not compile: {why}", status=409)
        rows, _, _ = write_acceptance(result, remaining, _author(None, root))
        clear_accepted(root, keys)
        return {"ok": True, "result": f"accepted {len(rows)} keys"}
    if endpoint.startswith("session-"):
        return {"ok": True, "result": _session(root, endpoint, body)}
    return {"ok": True, "result": _review(root, endpoint, body)}


def _locate(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """Turn a reader's selection on a page into the anchor loom would record (plan 0.13 item 2).

    Body: `citekey`, `page`, and either `text` -- what the reader selected -- or `rects`, the rectangles they drew when there was no text worth selecting. The answer carries the anchor and, beside it, the line a person would read.

    **Mapping happens here and not in the viewer.** The client's text layer is a third extraction of the page, after the committed page text and the word boxes; only loom holds the other two, and only loom can say what the committed text says, which is what an anchor is checked against. The client never decides what the anchor is.

    This endpoint **writes nothing**: it answers, and whether an annotation is made is a separate act.
    """
    from loom.cli._quilt import open_scan
    from loom.refs.anchoring import anchor_on_page
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map

    citekey = _str(body, "citekey", required=True) or ""
    page = body.get("page")
    if not isinstance(page, int) or page < 1:
        raise ApiError("bad-field", "page must be a positive integer")
    rects = [[float(v) for v in r] for r in body.get("rects") or []]
    text = _str(body, "text")
    raw_span = body.get("span")
    span = (int(raw_span[0]), int(raw_span[1])) if isinstance(raw_span, list) and len(raw_span) == 2 else None
    if not text and not rects and not span:
        raise ApiError("missing-field", "one of text, rects or span is required")

    result = open_scan(str(root))
    if citekey not in result.bib:
        raise ApiError("no-such-work", f"{citekey} is not in the bibliography", status=404)
    home = work_dir(root, result.bib[citekey])
    if read_map(home) is None or not (home / "paper.pdf").is_file():
        raise ApiError("not-readable", f"{citekey} has no copy on this machine", status=404)
    placed = anchor_on_page(home, page, text, rects, span)
    box = placed.page_box
    return {
        "ok": True,
        "result": f"{citekey} p.{page} anchored by {placed.said}, {len(placed.anchor.quads or [])} line(s)",
        "anchor": _anchor_json(placed.anchor),
        "text": placed.selector.exact,
        "page_box": {"width": box[0], "height": box[1]} if box else None,
    }


def _message(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """Post a message into a session, and say whether anybody was listening (plan 0.13 §8, DR-195).

    **Loom appends.** A parked reader wakes because a file grew; where the quilt lets it, `loom serve` starts the author's own agent command for the turn (`loom.agent`). Loom holds no credentials, calls no model, and hands the message to nobody -- this is the mailbox the agent reads.

    **The message lands whether or not anybody is attached**, and the answer says which. Refusing would lose what the author typed, for a reason the browser cannot fix; saying nothing would let them believe it was delivered.
    """
    from loom.cli._common import whoever, writer
    from loom.mailbox import attached, pending, post, waiting_on
    from loom.sessions import resolve

    # the words may be left out: a message may be what the person marked, and nothing else (plan 0.14)
    text = (_str(body, "text") or "").strip()
    said = _str(body, "as")
    # A declared identity is taken as declared; with none, this is the author at their own keyboard, which is what the
    # viewer's composer is. `writer` is what refuses an agent that has not named itself.
    name, kind = writer(root, said) if said else (_str(body, "author") or whoever(root, sniff=False), "person")
    # A message names its session like every other write (plan 0.13.1): it is addressed to whoever is attached there,
    # and a message posted to "whatever was last active" would reach the wrong reader.
    which = _str(body, "session", required=True) or ""
    found = resolve(root, which)
    if found is None:
        raise ApiError("no-such-session", f"no session matches {which}", status=404)
    packet = pending(root, found, name)
    if not text and not packet:
        raise ApiError("nothing-to-send", "nothing to send: no words, and nothing marked since the last message")
    event = post(root, found.id, text, name, kind="message", changed=packet)
    here = [r for r in attached(root, found.id) if r.get("who") != name]
    return {
        "ok": True,
        "result": f"posted to {found.id}",
        "session": found.id,
        "seq": event.seq,
        "attached": here,
        "waiting": waiting_on(root, found.id, name),
    }


def _session(root: Path, endpoint: str, body: dict[str, Any]) -> str:
    """Change which session is active, retitle one, or tombstone one (plan 0.13 §5).

    Through the same functions `loom session` calls, so the two surfaces cannot spell a session event differently. **Purging is not here and never will be**: it rewrites the annotation log, and the one place that should be reachable from is a terminal where the author typed the word.
    """
    from loom.cli._common import whoever
    from loom.sessions import active, close, create, delete, purpose, rename, resolve, resume, sessions, set_active

    who = _str(body, "author") or whoever(root, sniff=False)
    if endpoint == "session-new":
        # named by the author on the spot, and made the one writing lands in: what §16's example does from the page
        title = _str(body, "title", required=True) or ""
        made = create(root, title, who, purpose=_str(body, "purpose") or "")
        set_active(root, made.id)
        return f"{made.id}  {title}  (active)"
    which = _str(body, "session", required=True) or ""
    found = resolve(root, which)
    if found is None:
        raise ApiError("no-such-session", f"no session matches {which}", status=404)
    if endpoint == "session-close":
        if found.state != "open":
            raise ApiError("refused", f"{found.id} is {found.state}")
        close(root, found.id, who)
        if active(root) == found.id:
            set_active(root, None)
        return f"closed {found.id}; its annotations are hidden until it is shown or resumed"
    if endpoint == "session-reopen":
        if found.state == "open":
            raise ApiError("refused", f"{found.id} is already open")
        resume(root, found.id, who)
        return f"reopened {found.id}"
    if endpoint == "session-purpose":
        purpose(root, found.id, _str(body, "purpose") or "", who)
        return f"{found.id} is for {_str(body, 'purpose') or '(nothing stated)'}"
    if endpoint == "session-rename":
        title = _str(body, "title", required=True) or ""
        rename(root, found.id, title, who)
        return f"{found.id} is now {title}"
    if endpoint == "session-delete":
        delete(root, found.id, who, _str(body, "reason") or "")
        if active(root) == found.id:
            set_active(root, None)
        return f"deleted {found.id}; its annotations stay in the log"
    if found.state == "deleted":
        raise ApiError("refused", f"{found.id} was deleted; nothing new can be written to it")
    if found.state == "closed":
        resume(root, found.id, who)
    set_active(root, found.id)
    return f"writing to {sessions(root)[found.id].title}"


def _anchor_json(anchor: Any) -> dict[str, Any]:
    """An anchor in the shape a result record carries it, so the endpoint and the record cannot spell one differently."""
    from loom.refs.proposals import Result

    out: dict[str, Any] = Result(id="", local="", anchor=anchor).to_json()["anchor"]
    return out


def _digest(root: Path, endpoint: str, body: dict[str, Any]) -> str:
    """Verify or discard a proposed digest node, through the same functions `loom refs verify|discard` call.

    `digest-verify` with a `statement` is edit-then-verify: the author's own rendering replaces the proposed one and both parties are recorded. It never touches `source_text`, so the anchor survives and the node stays re-checkable (plan 0.12 §5.4).

    **Both are the author's verbs, and the guard is on the declared identity** (plan 0.13 §8). The server's own environment says nothing here -- loom may be serving from the terminal an agent is working in -- so the marker is not consulted; what is refused is a writer who names itself an agent. A post with no author is the author's own click in their own browser, which is what this endpoint is for.
    """
    from loom.cli._common import is_agent
    from loom.cli._quilt import open_scan
    from loom.refs.proposals import discard_result, verify_result
    from loom.scan.quilt import resolve_author

    node = _str(body, "node", required=True) or ""
    named = _str(body, "author")
    if named and is_agent(named):
        verb = "loom refs discard" if endpoint == "digest-discard" else "loom refs verify"
        raise ApiError(
            "author-only",
            f"{verb} is the author's, and {named} is an agent. An agent proposes; it does not vouch for its own "
            "reading. To ask for one, write a suggestion on the result.",
            status=403,
        )
    result = open_scan(str(root))
    who = resolve_author(named, root)[0]
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

    # **A write over the API names its session** (plan 0.13.1). The session travels with the write from the writer's
    # own context -- the author's from the viewer's selection, an agent's from the session it is attached to -- so
    # nothing here reads `.loom/active`, which narrows to `loom comment`'s terminal default. A request naming none is
    # malformed rather than something to paper over: falling back would file work wherever the pointer happened to
    # point, which is the failure this replaced.
    which = _str(body, "session")
    if not which:
        raise ApiError("no-session", "a write must name the session it belongs to")

    try:
        # Who is at the browser, not what shell the server was started in: with `loom serve` running in an agent's
        # terminal every note the author wrote in their own browser was recorded `author: "agent"` until this stopped
        # sniffing. An agent posting here declares itself, and `is_agent` still guards the author's verbs by that name.
        writer = _writer(root, which, _str(body, "author"), sniff=False)
    except (EnvError, ContentError) as exc:
        raise ApiError("refused", str(exc)) from exc

    try:
        # `undo` puts a withdrawn or resolved finding back by appending another event; the viewer offers it in place
        # of the verb that fired, so a wrong click is one click back (DR-174).
        undo = bool(body.get("undo"))
        if endpoint == "discard":
            return discard_annotation(
                root, _str(body, "annotation", required=True) or "", writer, _str(body, "reason"), undo
            )
        result = open_scan(str(root))
        if endpoint == "edit":
            # the viewer sends the new text as `message`, as every other endpoint names it; the log's field is `body`
            fields = {"body": _str(body, "message"), **{k: _str(body, k) for k in ("severity", "payload", "placement")}}
            return edit_annotation(result, _str(body, "annotation", required=True) or "", writer, **fields)
        if endpoint == "comment":
            # a note on a page of a cited work carries the page and, for a box, the rectangles (plan 0.13 item 2)
            page = body.get("page")
            if page is not None and (not isinstance(page, int) or page < 1):
                raise ApiError("bad-field", "page must be a positive integer")
            rects = [[float(v) for v in r] for r in body.get("rects") or []] or None
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
                page=page,
                rects=rects,
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
            "from": {"run": record.rel, "annotation": ann_id},
        },
    )
    return f"accepted {ann_id}; {resolved}"
