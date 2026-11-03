"""The write API: the HTTP form of loom's record-writing commands (specs/write-api.md, plan 0.11 Part G).

Served by the publisher, never by the viewer. Most endpoints write only Loom's private records. Explicit pull and AI incorporation apply exactly a reviewed patch to author files. Every endpoint wraps a library function shared with CLI and test surfaces.

Nothing here wakes an agent. An agent pulls: it reads open annotations with `loom status` and `loom ai annotations` and answers with `loom annotate --reply`. A person writing in the viewer and an agent answering in its own session are the same log seen from two ends.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loom.paths import BUILD, MANIFEST

if TYPE_CHECKING:
    from loom.scan.scan import ScanResult

#: What this publisher serves. A viewer reads this rather than assuming the specification's table, so an endpoint that
#: is not here answers 404 and a viewer that hides the affordance is right to.
CAPABILITIES = [
    "annotate",
    "reply",
    "resolve",
    "edit",
    "discard",
    "library-cite",
    "library-verify",
    "library-discard",
    "library-update",
    "locate",
    "compare",
    "session-use",
    "session-rename",
    "session-delete",
    "session-new",
    "session-close",
    "session-reopen",
    "session-purpose",
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
    "settings-save",
    "agents-update",
    "here",
    "changes-keep",
    "changes-undo",
    "note",
    "note-keep",
]

WRITE_API_VERSION = 1

#: Endpoints that answer and change nothing the manifest shows, so the publisher does not rebuild after them.
READS = ("locate", "compare", "adopt-preview", "sync-preview", "adopt-paper", "here", "open")

#: Decision writes publish queue metadata themselves, without rendering documents.
NO_REBUILD = (*READS, "review-decision", "adopt-decision", "library-update")
#: A publisher's own scan, offered to its handlers by `offer_scan`: `loom serve` answers with the scan its last publication made while no scan input has changed since, and None otherwise.
_SCANS: dict[Path, Callable[[], ScanResult | None]] = {}


def offer_scan(root: Path, provider: Callable[[], ScanResult | None]) -> None:
    """Let the handlers for `root` read `provider`'s scan instead of scanning again; `loom serve` offers its own."""
    _SCANS[root.resolve()] = provider


#: The publisher's library runs (`loom.jobs.Jobs`), offered by `offer_jobs`: `loom serve` offers its own, and nothing else runs them.
_JOBS: dict[Path, Any] = {}


def offer_jobs(root: Path, jobs: Any) -> None:
    """Let `library-update` for `root` queue its runs on `jobs`; `loom serve` offers its own."""
    _JOBS[root.resolve()] = jobs


def _busy(root: Path, citekey: str) -> None:
    """Refuse a write to the work `citekey` while a library run acts on it: the run writes its digest too, and the two would cross."""
    jobs = _JOBS.get(root.resolve())
    if citekey and jobs is not None and jobs.touching(citekey):
        raise ApiError(
            "library-busy", f"a library run is acting on {citekey}; write this when it has finished", status=409
        )


def _library_update(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """`library-update`: queue a library run on the publisher's runner and answer with its job at once; the author's, refused to a declared agent, so an agent never grants itself the network this way. No works is every work, its bibliography gathered first."""
    from loom.cli._common import NotFoundError, is_agent
    from loom.refs.build import STEPS, WORK_STEPS
    from loom.refs.update import named
    from loom.scan.quilt import load_quilt, reviewer_identity

    who = reviewer_identity(root)[0]
    if is_agent(_str(body, "author") or who):
        raise ApiError("author-only", "An agent reads and annotates; only the author starts a library run", status=403)
    jobs = _JOBS.get(root.resolve())
    if jobs is None:
        raise ApiError("no-runner", "a library run needs loom serve, which runs it beside the viewer", status=409)
    asked = body.get("works") or []
    if not isinstance(asked, list) or not all(isinstance(w, str) and w for w in asked):
        raise ApiError("bad-field", "works must be a list of works")
    works: list[str] = []
    if asked:
        try:
            works = named(load_quilt(root), _scan(root), tuple(asked))
        except NotFoundError as exc:
            raise ApiError("no-such-work", str(exc), status=404) from exc
    job = jobs.submit(
        works,
        WORK_STEPS if works else STEPS,
        who=who,
        online=body.get("online") is True,
        redo=body.get("redo") is True,
    )
    what = ", ".join(works) if works else "every work"
    return {"ok": True, "result": f"started a library run on {what}", "job": job.to_json()}


def _scan(root: Path) -> ScanResult:
    """The quilt's scan: the publisher's own while it is current, else a fresh one."""
    from loom.cli._quilt import open_scan

    provider = _SCANS.get(root.resolve())
    kept = provider() if provider is not None else None
    return kept if kept is not None else open_scan(str(root))


#: Writes that change records alone, which the scan never reads; their publication builds from the last scan (`ServeSession.rebuild`).
RECORD_WRITES = (
    "annotate",
    "note",
    "note-keep",
    "changes-keep",
    "reply",
    "resolve",
    "edit",
    "discard",
    "library-cite",
    "session-new",
    "session-use",
    "session-rename",
    "session-delete",
    "session-close",
    "session-reopen",
    "session-purpose",
    "adopt-decision",
    "reviewer-settings",
)


class ApiError(Exception):
    """A request loom refused, with the code a viewer shows, the status it gets, and for a form the reason for each field it refused."""

    def __init__(self, code: str, message: str, status: int = 400, fields: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.fields = fields or {}

    def answer(self) -> dict[str, Any]:
        """The JSON body a refusal is served as."""
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.fields:
            error["fields"] = self.fields
        return {"error": error}


def discovery() -> dict[str, Any]:
    """The answer to `GET /_api`; `open` is offered only on a machine that can open an application."""
    from loom.files import can_open

    return {"write_api": WRITE_API_VERSION, "capabilities": [*CAPABILITIES, *(["open"] if can_open() else [])]}


def _str(body: dict[str, Any], name: str, *, required: bool = False) -> str | None:
    value = body.get(name)
    if value is None or value == "":
        if required:
            raise ApiError("missing-field", f"{name} is required")
        return None
    if not isinstance(value, str):
        raise ApiError("bad-field", f"{name} must be a string")
    return value


def _note(root: Path, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """`note` writes a note, a quote among them, on `target` in the session the write names; `note-keep` keeps one so it never fades."""
    from loom.cli._common import ContentError, EnvError, NotFoundError
    from loom.cli.review import _writer
    from loom.notes import NoteRefused, keep, write

    which = _str(body, "session")
    if not which:
        raise ApiError("no-session", "a write must name the session it belongs to")
    try:
        sid, kind, name = _writer(root, which, _str(body, "author"), sniff=False)
    except NotFoundError as exc:
        raise ApiError(f"no-such-{exc.what}", str(exc), status=404) from exc
    except (EnvError, ContentError) as exc:
        raise ApiError("refused", str(exc)) from exc
    try:
        if endpoint == "note-keep":
            note = keep(root, _str(body, "note", required=True) or "", name)
            return {"ok": True, "result": f"kept {note.id}", "note": note.id}
        page = body.get("page")
        if page is not None and (not isinstance(page, int) or page < 1):
            raise ApiError("bad-field", "page must be a positive integer")
        rects = [[float(v) for v in r] for r in body.get("rects") or []] or None
        note = write(
            _scan(root),
            _str(body, "target", required=True) or "",
            author=name,
            author_kind="agent" if kind == "agent" else "person",
            session=sid,
            body=_str(body, "body") or "",
            quote=_str(body, "quote"),
            page=page,
            rects=rects,
        )
    except NoteRefused as exc:
        raise ApiError(exc.code, exc.message, status=exc.status) from exc
    return {"ok": True, "result": f"noted {note.id}", "note": note.id}


def _changes(root: Path, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """`changes-keep` and `changes-undo`: the reviewer keeps a change to an open file, or every change (no `path`), or puts one back as it was at their look; the author's acts, refused to a declared agent."""
    from loom.cli._common import is_agent
    from loom.looks import LookRefused, keep, undo
    from loom.scan.quilt import load_quilt, reviewer_identity

    who = reviewer_identity(root)[0]
    if not who:
        raise ApiError("no-reviewer", "Choose your reviewer name in Settings", status=409)
    if is_agent(_str(body, "author") or who):
        raise ApiError(
            "author-only", "An agent reads and annotates; only the author keeps or undoes a change", status=403
        )
    quilt = load_quilt(root)
    path = _str(body, "path", required=endpoint == "changes-undo")
    try:
        if endpoint == "changes-undo":
            undo(quilt, who, path or "")
            return {"ok": True, "result": f"{path} is back as it was at your look"}
        keep(quilt, who, path)
    except LookRefused as exc:
        raise ApiError(exc.code, exc.message, status=404 if exc.code == "no-such-change" else 409) from exc
    return {"ok": True, "result": f"kept {path}" if path else "kept everything"}


def _settings(root: Path, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """`settings-save` writes the viewer's Settings into `config.toml`, all of them or none; `agents-update` rewrites the permission files to match it, as `loom upgrade` does. The author's acts, refused to a declared agent: the config is the person's, and an agent never moves its own boundary."""
    from loom.cli._common import is_agent
    from loom.scan.quilt import load_quilt, reviewer_identity

    if is_agent(_str(body, "author") or reviewer_identity(root)[0]):
        raise ApiError(
            "author-only", "An agent reads and annotates; only the author changes the quilt's settings", status=403
        )
    quilt = load_quilt(root)
    if endpoint == "agents-update":
        from loom.ai.layout import SHELL, variant, write_permissions
        from loom.paths import AI

        if not (root / AI).is_dir():
            raise ApiError(
                "no-agent-layer", "this quilt has no agent layer; run `loom ai init` to write one", status=409
            )
        written, _ = write_permissions(root, quilt.config, shell=variant(root) == SHELL)
        return {
            "ok": True,
            "result": f"rewrote {', '.join(written)}" if written else "the permission files were current",
        }
    from loom.config_edit import ConfigRefused, save
    from loom.files import Shown

    changes = body.get("changes")
    if not isinstance(changes, dict) or not changes:
        raise ApiError("missing-field", "changes must name at least one setting")
    result = _scan(root)
    shown = Shown.of(quilt)
    own = {m for m in result.masters if result.document_role(m) == "person"}
    try:
        save(quilt, changes, masters=own, shown=lambda rel: (root / rel).is_file() and shown.is_shown(rel))
    except ConfigRefused as exc:
        raise ApiError("bad-value", str(exc), status=409, fields=exc.refused) from exc
    except OSError as exc:
        raise ApiError("settings-refused", str(exc), status=409) from exc
    return {"ok": True, "result": f"saved {', '.join(changes)} to config.toml"}


def _open(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """`open`: the application `app`, or the shown file `file` in its application, started for the person on their click; nothing in the quilt changes (`loom.files.open_command` says what it refuses)."""
    from loom.files import OpenRefused, Shown, launch, open_command
    from loom.scan.quilt import load_quilt

    app, file = _str(body, "app"), _str(body, "file")
    if (app is None) == (file is None):
        raise ApiError("bad-request", "name an app or a file, not both")
    try:
        argv = open_command(Shown.of(load_quilt(root)), app=app, file=file)
    except OpenRefused as exc:
        raise ApiError(exc.code, exc.message, status=404 if exc.code == "no-such-file" else 400) from exc
    launch(argv)
    return {"ok": True, "result": "opened", "opened": app or file}


#: Where the reader is, by quilt: the last place a viewer tab reported (`here`), the stamp it came at, and when by this process's clock. Held in memory only, never written: it is where a person is, not a record.
_HERE: dict[Path, tuple[str, float, dict[str, Any]]] = {}
#: The largest place a tab may report, in bytes of JSON: a selection is words, not a document.
HERE_LIMIT = 64_000


def reading_place(root: Path) -> dict[str, Any]:
    """`GET /_api/here`'s answer: the last place a tab reported, when, and how many seconds ago; `place` is None before any has."""
    import time

    kept = _HERE.get(root.resolve())
    if kept is None:
        return {"place": None, "when": None, "age": None}
    when, at, place = kept
    return {"place": place, "when": when, "age": round(time.monotonic() - at, 1)}


def forget_place(root: Path) -> None:
    """Drop the reader's place, as a server does when it stops: nobody is reading through it any more."""
    _HERE.pop(root.resolve(), None)


def _here(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """Keep the place a viewer tab reports, in place of the last one: the tab touched last wins."""
    import json
    import time

    from loom.clock import stamp

    if body.get("route") not in ("reading", "review", "elsewhere"):
        raise ApiError("bad-field", "route must be reading, review or elsewhere")
    if len(json.dumps(body)) > HERE_LIMIT:
        raise ApiError("bad-field", f"a place is at most {HERE_LIMIT:,} bytes")
    _HERE[root.resolve()] = (stamp(), time.monotonic(), body)
    return {"ok": True}


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
    if endpoint not in discovery()["capabilities"]:
        raise ApiError("unknown-endpoint", f"no endpoint {endpoint}", status=404)
    if endpoint == "here":
        return _here(root, body)
    if endpoint == "open":
        return _open(root, body)
    if endpoint in ("changes-keep", "changes-undo"):
        return _changes(root, endpoint, body)
    if endpoint in ("note", "note-keep"):
        return _note(root, endpoint, body)
    if endpoint == "library-cite":
        return {"ok": True, "result": _library_cite(root, body)}
    if endpoint in ("library-verify", "library-discard"):
        return {"ok": True, "result": _library(root, endpoint, body)}
    if endpoint == "library-update":
        return _library_update(root, body)
    if endpoint == "locate":
        return _locate(root, body)
    if endpoint == "compare":
        return _compare(root, body)
    if endpoint in ("sync-incorporate", "sync-preview"):
        from loom.cli._common import is_agent
        from loom.incorporation_review import finish, preview, validate

        if endpoint == "sync-incorporate" and is_agent(_str(body, "author") or ""):
            raise ApiError("author-only", "Incorporating a collaborator's changes is the author's", status=403)
        from loom.scan.quilt import load_quilt, reviewer_identity
        from loom.scan.scan import scan
        from loom.sync import SyncError, SyncState, pull_files
        from loom.sync import incorporate as incorporate_pull

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
                    overlay = {
                        p: data.decode("utf-8") if data is not None else ""
                        for p, data in pull_files(quilt, state).items()
                        if p.endswith((".tex", ".sty", ".cls", ".bib"))
                    }
                    return {"ok": True, "result": preview(before, overlay, binding, reviewer)}
                accepted = _accept_keys(body)
                saved = validate(before, _str(body, "review_token", required=True) or "", binding, reviewer, accepted)
            else:
                saved = None
            sync_result = incorporate_pull(quilt, state, reviewer or None)
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

                manifest_path = root / MANIFEST
                if manifest_path.is_file():
                    manifest = json.loads(manifest_path.read_text())
                    if manifest.get("reviewer", {}).get("name") == reviewer:
                        for contribution in manifest.get("contributions", []):
                            if (
                                contribution.get("copy") == data["copy"]
                                and contribution.get("fingerprint") == data["fingerprint"]
                            ):
                                contribution["choices"] = answer
                        publish(root / BUILD, {}, manifest)
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
    if endpoint in ("settings-save", "agents-update"):
        return _settings(root, endpoint, body)
    if endpoint == "reviewer-settings":
        from loom.cli._common import is_agent
        from loom.scan.quilt import reviewer_identity, save_author

        if is_agent(_str(body, "author") or reviewer_identity(root)[0]):
            raise ApiError(
                "author-only", "An agent reads and annotates; only the author names the reviewer", status=403
            )
        if "name" in body:
            try:
                save_author(_str(body, "name", required=True) or "")
            except (ValueError, OSError) as exc:
                raise ApiError("settings-refused", str(exc), status=409) from exc
        name, source = reviewer_identity(root)
        return {"ok": True, "result": "reviewer settings", "reviewer": {"name": name, "source": source}}
    if endpoint in ("review-decision", "review-finish"):
        from loom.cli._common import is_agent
        from loom.cli.review import _acceptance_master, _master_compiles, write_acceptance
        from loom.review_queue import clear_accepted, decide, pending, rows_for
        from loom.scan.quilt import reviewer_identity

        reviewer, _ = reviewer_identity(root)
        if not reviewer:
            raise ApiError("no-reviewer", "Choose your reviewer name in Settings", status=409)
        if _str(body, "reviewer") != reviewer:
            raise ApiError("reviewer-changed", "Reviewer changed; reload Review before continuing", status=409)
        if is_agent(_str(body, "author") or reviewer):
            raise ApiError("author-only", "An agent reads and annotates; only the author reviews", status=403)
        result = _scan(root)
        if endpoint == "review-decision":
            key = _str(body, "key", required=True) or ""
            status = _str(body, "status", required=True) or ""
            import json

            manifest_path = root / MANIFEST
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
            publish(root / BUILD, {}, manifest)
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

    Body: `citekey`, `page`, and either `text` -- what the reader selected -- or `rects`, the rectangles they drew when there was no text worth selecting. `page` may be left out with `text`, for a link that quotes without a page: the first page whose committed text holds the quote is used. The answer carries the anchor, the page, and beside them the line a person would read.

    **Mapping happens here and not in the viewer.** The client's text layer is a third extraction of the page, after the committed page text and the word boxes; only loom holds the other two, and only loom can say what the committed text says, which is what an anchor is checked against. The client never decides what the anchor is.

    This endpoint **writes nothing**: it answers, and whether an annotation is made is a separate act.
    """
    from loom.refs.anchoring import anchor_on_page
    from loom.refs.fetch import work_dir
    from loom.refs.pages import read_map
    from loom.refs.search import grep_work

    citekey = _str(body, "citekey", required=True) or ""
    page = body.get("page")
    rects = [[float(v) for v in r] for r in body.get("rects") or []]
    text = _str(body, "text")
    if not (page is None and text) and (not isinstance(page, int) or page < 1):
        raise ApiError("bad-field", "page must be a positive integer")
    raw_span = body.get("span")
    span = (int(raw_span[0]), int(raw_span[1])) if isinstance(raw_span, list) and len(raw_span) == 2 else None
    if not text and not rects and not span:
        raise ApiError("missing-field", "one of text, rects or span is required")

    result = _scan(root)
    if citekey not in result.bib:
        raise ApiError("no-such-work", f"{citekey} is not in the bibliography", status=404)
    home = work_dir(root, result.bib[citekey])
    if read_map(home) is None or not (home / "paper.pdf").is_file():
        raise ApiError("not-readable", f"{citekey} has no copy on this machine", status=404)
    if page is None:
        hits = grep_work(home, citekey, text or "")
        if not hits:
            raise ApiError("not-found", f"no page of {citekey} holds that text", status=404)
        page = min(h.page for h in hits)
    placed = anchor_on_page(home, page, text, rects, span)
    box = placed.page_box
    return {
        "ok": True,
        "result": f"{citekey} p.{page} anchored by {placed.said}, {len(placed.anchor.quads or [])} line(s)",
        "page": page,
        "anchor": _anchor_json(placed.anchor),
        "text": placed.selector.exact,
        "page_box": {"width": box[0], "height": box[1]} if box else None,
    }


def _compare(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """The differing pairs of two items, rendered with their changed words.

    Body: `left` and `right`, each a live document's path or a landmark (`DOC@STEP`, a name or a step). Writes nothing a record holds: its renderings go to `.loom/build/compare/`, named by their inputs.
    """
    from loom.render.compare import CompareError, compare

    left = _str(body, "left", required=True) or ""
    right = _str(body, "right", required=True) or ""
    try:
        return {"ok": True, **compare(_scan(root), left, right)}
    except CompareError as exc:
        raise ApiError("unknown-item", str(exc), status=404) from exc


def _resolve_session(root: Path, which: str, *, deleted: bool = False) -> Any:
    """The session `which` names, live unless `deleted`: 404 when none does, 409 naming them when several do."""
    from loom.sessions import SessionNotFound, resolve

    try:
        return resolve(root, which, deleted=deleted)
    except SessionNotFound as exc:
        if exc.matches:
            raise ApiError("ambiguous-session", str(exc), status=409) from None
        raise ApiError("no-such-session", str(exc), status=404) from None


def _session(root: Path, endpoint: str, body: dict[str, Any]) -> str:
    """Change which session is active, retitle one, or tombstone one (plan 0.13 §5).

    Through the same functions `loom session` calls, so the two surfaces cannot spell a session event differently. **Purging is not here and never will be**: it rewrites the annotation log, and the one place that should be reachable from is a terminal where the author typed the word.
    """
    from loom.cli._common import whoever
    from loom.sessions import active, close, create, delete, purpose, rename, resume, sessions, set_active

    who = _str(body, "author") or whoever(root, sniff=False)
    if endpoint == "session-new":
        # named by the author on the spot, and made the one writing lands in: what §16's example does from the page
        title = _str(body, "title", required=True) or ""
        made = create(root, title, who, purpose=_str(body, "purpose") or "")
        set_active(root, made.id)
        return f"{made.id}  {title}  (active)"
    which = _str(body, "session", required=True) or ""
    # resuming and deleting name a tombstone to refuse it with its reason, and deleting one again is harmless
    found = _resolve_session(root, which, deleted=endpoint in ("session-use", "session-delete"))
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


def _library(root: Path, endpoint: str, body: dict[str, Any]) -> str:
    """Verify or discard a proposed digest node, through the same functions `loom library verify|discard` call.

    `library-verify` with a `statement` is edit-then-verify: the author's own rendering replaces the proposed one and both parties are recorded. It never touches `source_text`, so the anchor survives and the node stays re-checkable (plan 0.12 §5.4).

    **Both are the author's verbs, and the guard is on the declared identity** (plan 0.13 §8). The server's own environment says nothing here -- loom may be serving from the terminal an agent is working in -- so the marker is not consulted; what is refused is a writer who names itself an agent. A post with no author is the author's own click in their own browser, which is what this endpoint is for.
    """
    from loom.cli._common import is_agent
    from loom.refs.proposals import discard_result, verify_result
    from loom.scan.quilt import resolve_author

    node = _str(body, "node", required=True) or ""
    named = _str(body, "author")
    if named and is_agent(named):
        verb = "loom library discard" if endpoint == "library-discard" else "loom library verify"
        raise ApiError(
            "author-only",
            f"{verb} is the author's, and {named} is an agent. An agent proposes; it does not vouch for its own "
            "reading. To ask for one, write a suggestion on the result.",
            status=403,
        )
    result = _scan(root)
    found = result.nodes.get(node)
    _busy(root, getattr(found, "digest", None) or "")
    who = resolve_author(named, root)[0]
    try:
        if endpoint == "library-discard":
            return discard_result(result, node, _str(body, "why", required=True) or "", who)
        return verify_result(
            result, node, _str(body, "statement"), who, local=_str(body, "local"), taxon=_str(body, "taxon")
        )[0]
    except LookupError as exc:
        raise ApiError("no-such-node", str(exc), status=404) from exc


def _review(root: Path, endpoint: str, body: dict[str, Any]) -> str:
    # Imported here rather than at module scope: the CLI package pulls in click and the whole command tree, and a
    # server that is only ever asked for files should not pay for it at startup.
    from loom.cli._common import ContentError, EnvError, NotFoundError
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
        result = _scan(root)
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
        applied = body.get("applied") is True
        if applied and (endpoint != "resolve" or undo):
            raise ApiError(
                "bad-field", "applied says how a suggestion was resolved, so it goes with resolve and not undo"
            )
        return _one_comment(
            result, writer, None, _str(body, "message"), None, None, None, annotation, undo=undo, applied=applied
        )
    except NotFoundError as exc:
        raise ApiError(f"no-such-{exc.what}", str(exc), status=404) from exc
    except ContentError as exc:
        raise ApiError("refused", str(exc)) from exc
    except EnvError as exc:
        raise ApiError("bad-request", str(exc)) from exc


def _library_cite(root: Path, body: dict[str, Any]) -> str:
    """Accept or reject a citation an agent suggested, through `decide_citation` as `loom library verify|discard` do."""
    from loom.cli._common import ContentError, EnvError, NotFoundError, is_agent
    from loom.cli.review import _writer
    from loom.refs.notes import DECISIONS, decide_citation, find_citation

    if is_agent(_str(body, "author") or ""):
        raise ApiError(
            "author-only", "An agent suggests a citation; only the author accepts or rejects one", status=403
        )
    decision = _str(body, "decision", required=True)
    if decision not in DECISIONS:
        raise ApiError("bad-field", "decision must be accept or reject")
    ann_id = _str(body, "annotation", required=True) or ""
    which = _str(body, "session")
    if not which:
        raise ApiError("no-session", "a write must name the session it belongs to")
    try:
        # the suggestion first: one that names nothing is the caller's mistake whoever is asking
        find_citation(root, ann_id, decision)
        session, _kind, who = _writer(root, which, _str(body, "author"), sniff=False)
        decide_citation(root, ann_id, decision, _str(body, "why"), who, session)
    except LookupError as exc:
        raise ApiError("no-such-annotation", str(exc), status=404) from exc
    except NotFoundError as exc:
        raise ApiError(f"no-such-{exc.what}", str(exc), status=404) from exc
    except (EnvError, ContentError, ValueError) as exc:
        raise ApiError("refused", str(exc)) from exc
    return f"{decision}ed {ann_id}; resolved {ann_id}"


def _accept_keys(body: dict[str, Any]) -> list[str]:
    keys = body.get("accept", [])
    if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
        raise ApiError("bad-field", "accept must be a list of mathematical block keys")
    return keys
