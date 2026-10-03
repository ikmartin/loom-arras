"""The write API: the HTTP form of loom's record-writing commands (specs/write-api.md, plan 0.11 Part G).

Served by the publisher, never by the viewer. Most endpoints write only Loom's private records. Explicit pull and AI incorporation apply exactly a reviewed patch to author files. Every endpoint wraps a library function shared with CLI and test surfaces.

Nothing here wakes an agent. An agent pulls: it reads open annotations with `loom status` and `loom ai annotations` and answers with `loom annotate --reply`. A person writing in the viewer and an agent answering in its own session are the same log seen from two ends.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loom.clock import stamp

#: What this publisher serves. A viewer reads this rather than assuming the specification's table, so an endpoint that
#: is not here answers 404 and a viewer that hides the affordance is right to.
CAPABILITIES = [
    "annotate",
    "reply",
    "resolve",
    "edit",
    "discard",
    "refs-cite",
    "digest-verify",
    "digest-discard",
    "locate",
    "compare",
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
    "sync-preview",
    "adopt-close",
    "adopt-reopen",
    "adopt-refresh",
    "adopt-paper",
    "adopt-decision",
    "adopt-preview",
    "adopt-finish",
    "review-decision",
    "review-finish",
    "reviewer-settings",
]

WRITE_API_VERSION = 1

#: Endpoints that answer and change nothing the manifest shows, so the publisher does not rebuild after them.
READS = ("compare", "adopt-preview", "sync-preview", "adopt-paper")

#: Decision writes publish queue metadata themselves, without rendering documents.
NO_REBUILD = (*READS, "review-decision", "adopt-decision")


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
    if endpoint == "refs-cite":
        return {"ok": True, "result": _refs_cite(root, body)}
    if endpoint in ("digest-verify", "digest-discard"):
        return {"ok": True, "result": _digest(root, endpoint, body)}
    if endpoint == "locate":
        return _locate(root, body)
    if endpoint == "compare":
        return _compare(root, body)
    if endpoint == "message":
        return _message(root, body)
    if endpoint in ("sync-incorporate", "sync-preview"):
        from loom.incorporation_review import finish, preview, validate
        from loom.scan.quilt import load_quilt, reviewer_identity
        from loom.scan.scan import scan
        from loom.sync import SyncError, SyncState, _expected_blobs, git, incorporate_pull, prepare_incorporation

        try:
            quilt = load_quilt(root)
            state = SyncState.read(root)
            incoming = _str(body, "incoming", required=True)
            base = _str(body, "base", required=True)
            if incoming != state.incoming:
                raise ApiError("revision-changed", "the fetched revision changed; reload Incoming")
            if base != state.integrated and state.integrated != state.incoming:
                raise ApiError("revision-changed", "the incorporated base changed; reload Incoming")
            binding = {"kind": "sync", "incoming": incoming or "", "base": base or ""}
            reviewer, _ = reviewer_identity(root)
            if endpoint == "sync-preview" or body.get("review_token") or body.get("accept"):
                if not reviewer or _str(body, "reviewer") != reviewer:
                    raise ApiError("reviewer-changed", "Choose your reviewer name and reload Incoming", status=409)
                before = scan(quilt)
                if endpoint == "sync-preview":
                    prepared = prepare_incorporation(quilt, state)
                    blobs = _expected_blobs(
                        root, prepared["head"], Path(prepared["patch"]).read_bytes(), prepared["paths"]
                    )
                    overlay = {
                        p: git(root, "cat-file", "blob", b).decode("utf-8") if b else ""
                        for p, b in blobs.items()
                        if p.endswith((".tex", ".sty", ".cls", ".bib"))
                    }
                    return {"ok": True, "result": preview(before, overlay, binding, reviewer)}
                accepted = _accept_keys(body)
                saved = validate(before, _str(body, "review_token", required=True) or "", binding, reviewer, accepted)
            else:
                saved = None
            sync_result = incorporate_pull(quilt, state)
            if saved is not None:
                sync_result.update(finish(scan(load_quilt(root)), saved, accepted, reviewer or ""))
        except SyncError as exc:
            raise ApiError("sync-refused", str(exc), status=409) from exc
        return {"ok": True, "result": sync_result}
    if endpoint in (
        "adopt-decision",
        "adopt-preview",
        "adopt-finish",
        "adopt-close",
        "adopt-reopen",
        "adopt-refresh",
        "adopt-paper",
    ):
        from loom.adopt import comparison, decisions, incorporate, prepare
        from loom.adopt import decide as adopt_decide
        from loom.cli._common import is_agent
        from loom.scan.quilt import load_quilt, reviewer_identity
        from loom.scan.scan import scan
        from loom.sync import SyncError

        reviewer, _ = reviewer_identity(root)
        if not reviewer or _str(body, "reviewer") != reviewer:
            raise ApiError("reviewer-changed", "Choose your reviewer name and reload Incoming", status=409)
        if is_agent(_str(body, "author") or reviewer):
            raise ApiError("author-only", "An agent proposes; only the author incorporates", status=403)
        copy = _str(body, "copy", required=True) or ""
        try:
            result = scan(load_quilt(root))
            if endpoint in ("adopt-close", "adopt-reopen"):
                from loom.draft_lifecycle import close_draft, reopen_draft

                answer = (
                    close_draft(result, copy, reviewer, confirmed=body.get("confirmed") is True)
                    if endpoint == "adopt-close"
                    else reopen_draft(result, copy, reviewer)
                )
            elif endpoint == "adopt-refresh":
                from loom.adopt import refresh

                answer = refresh(result, copy)
            elif endpoint == "adopt-paper":
                from loom.section_drafts import preview_in_paper

                answer = preview_in_paper(result, copy)
            elif endpoint == "adopt-finish":
                from loom.incorporation_review import finish, validate

                token = _str(body, "token", required=True) or ""
                accepted = _accept_keys(body)
                saved = (
                    validate(
                        result,
                        _str(body, "review_token", required=True) or "",
                        {"kind": "adopt", "token": token},
                        reviewer,
                        accepted,
                    )
                    if body.get("review_token") or accepted
                    else None
                )
                answer = incorporate(result, copy, token, reviewer)
                if saved is not None:
                    answer.update(finish(scan(load_quilt(root)), saved, accepted, reviewer))
            elif endpoint == "adopt-decision":
                keys = body.get("keys")
                document = body.get("document")
                kept = body.get("kept", [])
                if (
                    not isinstance(keys, list)
                    or not all(isinstance(k, str) for k in keys)
                    or not isinstance(document, bool)
                    or not isinstance(body.get("preamble", False), bool)
                    or not isinstance(kept, list)
                    or not all(isinstance(k, str) for k in kept)
                ):
                    raise ApiError("bad-field", "keys must be a list of strings and document must be a boolean")
                revision = body.get("revision", 0)
                if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
                    raise ApiError("bad-field", "revision must be a nonnegative integer")
                data = comparison(result, copy)
                answer = adopt_decide(
                    result,
                    copy,
                    keys,
                    document,
                    _str(body, "fingerprint", required=True) or "",
                    reviewer,
                    kept,
                    revision=revision,
                    data=data,
                    preamble=bool(body.get("preamble", False)),
                )
                import json

                from loom.render.publish import publish

                manifest_path = root / "build/manifest.json"
                if manifest_path.is_file():
                    manifest = json.loads(manifest_path.read_text())
                    if manifest.get("reviewer", {}).get("name") == reviewer:
                        for contribution in manifest.get("contributions", []):
                            if (
                                contribution.get("copy") == data["copy"]
                                and contribution.get("fingerprint") == data["fingerprint"]
                            ):
                                contribution["choices"] = answer
                        publish(root / "build", {}, manifest)
            else:
                data = comparison(result, copy)
                chosen = decisions(result, copy, reviewer, data=data)
                if _str(body, "fingerprint", required=True) != chosen["fingerprint"]:
                    raise SyncError("Contribution changed; reload Incoming")
                answer = prepare(
                    result,
                    copy,
                    chosen["keys"],
                    chosen["document"],
                    reviewer,
                    data=data,
                    preamble=chosen.get("preamble", False),
                )
                from loom.incorporation_review import preview

                answer["review"] = preview(
                    result, answer["overlay"], {"kind": "adopt", "token": answer["token"]}, reviewer
                )
            return {"ok": True, "result": answer}
        except (SyncError, ValueError, OSError) as exc:
            raise ApiError("adoption-refused", str(exc), status=409) from exc
    if endpoint == "reviewer-settings":
        from loom.scan.quilt import reviewer_identity, save_author

        if "name" in body:
            try:
                save_author(_str(body, "name", required=True) or "")
            except (ValueError, OSError) as exc:
                raise ApiError("settings-refused", str(exc), status=409) from exc
        name, source = reviewer_identity(root)
        return {"ok": True, "result": "reviewer settings", "reviewer": {"name": name, "source": source}}
    if endpoint in ("review-decision", "review-finish"):
        from loom.cli._quilt import open_scan
        from loom.cli.review import _acceptance_master, _master_compiles, write_acceptance
        from loom.review_queue import clear_accepted, decide, pending, rows_for
        from loom.scan.quilt import reviewer_identity

        reviewer, _ = reviewer_identity(root)
        if not reviewer:
            raise ApiError("no-reviewer", "Choose your reviewer name in Settings", status=409)
        if _str(body, "reviewer") != reviewer:
            raise ApiError("reviewer-changed", "Reviewer changed; reload Review before continuing", status=409)
        result = open_scan(str(root))
        if endpoint == "review-decision":
            key = _str(body, "key", required=True) or ""
            status = _str(body, "status", required=True) or ""
            import json

            manifest_path = root / "build" / "manifest.json"
            if not manifest_path.is_file():
                raise ApiError("review-unavailable", "build the quilt before reviewing", status=409)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("reviewer", {}).get("name") != reviewer:
                raise ApiError("reviewer-changed", "Rebuild and reload Review before continuing", status=409)
            if key not in {row["key"] for row in rows_for(result, manifest)}:
                raise ApiError("not-unresolved", f"{key} is not awaiting review", status=409)
            try:
                decide(result, key, status, reviewer)
            except ValueError as exc:
                raise ApiError("review-refused", str(exc), status=409) from exc
            from loom.render.publish import publish

            manifest["unresolved"] = rows_for(result, manifest)
            publish(root / "build", {}, manifest)
            return {"ok": True, "result": f"{key}: {status}"}
        try:
            keys = pending(result, reviewer)
        except ValueError as exc:
            raise ApiError("review-changed", str(exc), status=409) from exc
        if not keys:
            raise ApiError("nothing-pending", "there are no pending OK decisions", status=409)
        for key in keys:
            node = result.nodes[key]
            if (
                node.external
                or node.derived_of
                or node.incomplete
                or (node.kind == "environment" and node.basis in ("open-claim", "unclassified"))
            ):
                raise ApiError("not-acceptable", f"{key} is not eligible for acceptance", status=409)
        from loom.records.store import Records

        states = Records(root, result.quilt.history_dir, reviewer=reviewer).key_states(result)
        for key in keys:
            for dep in result.dependencies.review_targets(key):
                dependency = states.get(dep)
                if dependency and dependency.row and not dependency.fresh and dep not in keys:
                    raise ApiError("dependency-pending", f"review {dep} before finishing {key}", status=409)
        remaining = [key for key in keys if not (states[key].row and states[key].fresh)]
        if not remaining:
            clear_accepted(root, keys, reviewer)
            return {"ok": True, "result": "pending decisions were already accepted"}
        contexts = {key: _acceptance_master(result, key) for key in remaining}
        for master in dict.fromkeys(contexts.values()):
            ok, why = _master_compiles(result, master)
            if not ok:
                raise ApiError("compile-failed", f"{master} does not compile: {why}", status=409)
        rows, _, _ = write_acceptance(result, remaining, reviewer, contexts)
        clear_accepted(root, keys, reviewer)
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


def _compare(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """The differing pairs of two items, rendered with their changed words (book 15.2.6).

    Body: `left` and `right`, each a live document's path or a landmark (`DOC@STEP`, a name or a step). Writes nothing a record holds: its renderings go to `build/compare/`, named by their inputs.
    """
    from loom.cli._quilt import open_scan
    from loom.render.compare import CompareError, compare

    left = _str(body, "left", required=True) or ""
    right = _str(body, "right", required=True) or ""
    try:
        return {"ok": True, **compare(open_scan(str(root)), left, right)}
    except CompareError as exc:
        raise ApiError("unknown-item", str(exc), status=404) from exc


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
    from loom.cli._common import ContentError, EnvError, NotFoundError
    from loom.cli._quilt import open_scan
    from loom.cli.review import _one_comment, _writer, discard_annotation, edit_annotation

    # Validate the request before touching the quilt: a missing field is the caller's mistake and should be named as
    # one, not reported as whatever the first function to be handed nothing happens to complain about.
    needs = {"annotate": ("target", "message"), "reply": ("annotation", "message")}.get(endpoint, ("annotation",))
    for field in needs:
        _str(body, field, required=True)

    # **A write over the API names its session** (plan 0.13.1). The session travels with the write from the writer's own context -- the author's from the viewer's selection, an agent's from the session it is attached to -- so nothing here reads `.loom/active`, which narrows to `loom annotate`'s terminal default. A request naming none is malformed rather than something to paper over: falling back would file work wherever the pointer happened to point, which is the failure this replaced.
    which = _str(body, "session")
    if not which:
        raise ApiError("no-session", "a write must name the session it belongs to")

    try:
        # Who is at the browser, not what shell the server was started in: with `loom serve` running in an agent's
        # terminal every note the author wrote in their own browser was recorded `author: "agent"` until this stopped
        # sniffing. An agent posting here declares itself, and `is_agent` still guards the author's verbs by that name.
        writer = _writer(root, which, _str(body, "author"), sniff=False)
    except NotFoundError as exc:
        raise ApiError(f"no-such-{exc.what}", str(exc), status=404) from exc
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
        if endpoint == "annotate":
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
                in_doc=_str(body, "in"),
            )
        annotation = _str(body, "annotation", required=True)
        if endpoint == "reply":
            return _one_comment(
                result, writer, None, _str(body, "message", required=True), None, None, annotation, None
            )
        return _one_comment(result, writer, None, _str(body, "message"), None, None, None, annotation, undo=undo)
    except NotFoundError as exc:
        raise ApiError(f"no-such-{exc.what}", str(exc), status=404) from exc
    except ContentError as exc:
        raise ApiError("refused", str(exc)) from exc
    except EnvError as exc:
        raise ApiError("bad-request", str(exc)) from exc


def _refs_cite(root: Path, body: dict[str, Any]) -> str:
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
            "from": {"session": record.rel, "annotation": ann_id},
        },
    )
    return f"accepted {ann_id}; {resolved}"


def _accept_keys(body: dict[str, Any]) -> list[str]:
    keys = body.get("accept", [])
    if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
        raise ApiError("bad-field", "accept must be a list of mathematical block keys")
    return keys
