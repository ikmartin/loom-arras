"""The write API: the HTTP form of loom's record-writing commands (specs/write-api.md, plan 0.11 Part G).

Served by the publisher, never by the viewer. Most endpoints write only Loom's private records. Explicit pull and AI incorporation apply exactly a reviewed patch to author files. Every endpoint wraps a library function shared with CLI and test surfaces.

Nothing here wakes an agent. An agent pulls: it reads open annotations with `loom status` and `loom ai annotations` and answers with `loom annotate --reply`. A person writing in the viewer and an agent answering in its own session are the same log seen from two ends.
"""

from __future__ import annotations

import base64
import re
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
    "delete",
    "restore",
    "annotations-take",
    "suggestion-apply",
    "library-verify",
    "library-discard",
    "library-update",
    "library-recognise",
    "library-lookup",
    "library-add",
    "library-upload",
    "library-file",
    "library-delete",
    "library-ignore",
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
    "review-accept",
    "reviewer-settings",
    "settings-save",
    "agents-update",
    "here",
    "changes-keep",
    "changes-undo",
    "file-tick",
    "history-record",
    "history-restore",
    "pdf-save",
]

WRITE_API_VERSION = 1

#: Endpoints that answer and change nothing the manifest shows, so the publisher does not rebuild after them.
READS = (
    "locate",
    "compare",
    "adopt-preview",
    "sync-preview",
    "adopt-paper",
    "here",
    "open",
    "library-recognise",
    "library-lookup",
)

#: The largest request body the publisher reads: a 256 MB PDF in base64, the largest a person drops in the viewer, which is about what a browser can encode; `loom library add` takes any size.
MAX_BODY = 344 * 1024 * 1024

#: Decision writes publish queue metadata themselves, without rendering documents.
NO_REBUILD = (*READS, "adopt-decision", "library-update", "library-upload")
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
    """`library-update`: queue a library run on the publisher's runner and answer with its job at once; the author's, refused to a declared agent, so an agent never grants itself the network this way. No works is every work, its bibliography gathered first; `steps` runs only those (a digest made again is `extract` alone, with `redo`)."""
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
    allowed = WORK_STEPS if works else STEPS
    steps = body.get("steps")
    if steps is not None and (not isinstance(steps, list) or not steps or not all(x in allowed for x in steps)):
        raise ApiError("bad-field", f"steps must be some of {', '.join(allowed)}")
    job = jobs.submit(
        works,
        tuple(x for x in allowed if x in steps) if steps else allowed,
        who=who,
        online=body.get("online") is True,
        redo=body.get("redo") is True,
    )
    what = ", ".join(works) if works else "every work"
    return {"ok": True, "result": f"started a library run on {what}", "job": job.to_json()}


def _library_add(root: Path, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """Adding works by hand (plan 0.24.2): what a pasted text is (`library-recognise`), what it names (`library-lookup`), writing it into loom's bibliography (`library-add`), a dropped PDF kept and identified (`library-upload`) then filed under a work or as its own (`library-file`), and a work added by hand taken out again (`library-delete`).

    A dropped PDF is filed whatever is known about it: lookups only add what they can. Every act but recognising is the author's, refused to a declared agent; a lookup that asks for the network is too, so an agent never grants itself it. `online` is the person's allowance of the network for that one act, as `--online` is.
    """
    import base64
    import hashlib

    from loom.cli._common import is_agent
    from loom.refs.add import file_new, file_under, identify
    from loom.refs.added import NotDeletable, add_entry, delete_work
    from loom.refs.build import WORK_STEPS
    from loom.refs.identity import recognise
    from loom.refs.lookup import key_for, look_up
    from loom.scan.quilt import load_quilt, reviewer_identity
    from loom.scan.scan import scan

    if endpoint == "library-recognise":
        rec = recognise(_str(body, "text", required=True) or "")
        said: dict[str, Any] = {
            "ok": True,
            "result": rec.label,
            "kind": rec.kind,
            "label": rec.label,
            "value": rec.value,
        }
        if rec.entry is not None:
            said["entry"] = {k: v for k, v in rec.entry.fields.items() if not k.startswith("loom-")}
        return said
    who = reviewer_identity(root)[0]
    asks = body.get("online") is True
    if (endpoint != "library-lookup" or asks) and is_agent(_str(body, "author") or who):
        raise ApiError(
            "author-only", "An agent reads and annotates; only the author adds works to the library", status=403
        )
    quilt = load_quilt(root)
    online = quilt.config.online or asks
    uploads = root / BUILD / "uploads"

    def run(citekey: str, *, pages: bool = False) -> dict[str, Any] | None:
        """The run on the work just added or filed: what a `fetch` asks for, carrying the act's allowance of the network; else, with `pages`, reading its text, which needs none."""
        jobs = _JOBS.get(root.resolve())
        if jobs is None or not (body.get("fetch") or pages):
            return None
        steps = WORK_STEPS if body.get("fetch") else ("map",)
        return jobs.submit([citekey], steps, who=who, online=asks).to_json()  # type: ignore[no-any-return]

    if endpoint == "library-lookup":
        found = look_up(_str(body, "text", required=True) or "", _scan(root).bib, online=online)
        return {"ok": True, "result": found.state, "found": found.to_json()}
    if endpoint == "library-add":
        text = _str(body, "text", required=True) or ""
        result = _scan(root)
        found = look_up(text, result.bib, online=online)
        if found.state != "found":
            raise ApiError(f"lookup-{found.state}", found.message or f"nothing was found for {text}", status=409)
        wanted = _str(body, "key")
        key = key_for(found.entry, set(result.bib), wanted or found.key)
        if wanted and key != wanted:
            raise ApiError("key-taken", f"the library already has a work filed as {wanted}", status=409)
        rec = recognise(text)
        try:
            add_entry(quilt, found.entry, key, who, rec.entry.type if rec.entry is not None else "")
        except ValueError as exc:
            raise ApiError("not-added", str(exc), status=409) from exc
        return {"ok": True, "result": f"added {key} to the library", "citekey": key, "job": run(key)}
    if endpoint == "library-upload":
        name = Path(_str(body, "name", required=True) or "").name
        raw = _str(body, "data", required=True) or ""
        try:
            data = base64.b64decode(raw, validate=True)
        except ValueError as exc:
            raise ApiError("bad-field", "data must be the PDF in base64") from exc
        if not data.startswith(b"%PDF-"):
            raise ApiError("not-a-pdf", f"{name} is not a PDF")
        sha = hashlib.sha256(data).hexdigest()
        # kept under its own name, which is what a reference manager writes a title into
        stem = re.sub(r"[^\w .,()+-]", "_", Path(name).stem).strip() or "upload"
        path = uploads / sha / f"{stem}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        result = _scan(root)
        seen = identify(root, result.bib, path, online=online)
        return {"ok": True, "result": f"kept {name}", "upload": sha, "name": name, **seen.to_json()}
    if endpoint == "library-file":
        sha = _str(body, "upload", required=True) or ""
        kept = sorted((uploads / sha).glob("*.pdf")) if re.fullmatch(r"[0-9a-f]{64}", sha) else []
        if not kept:
            raise ApiError("no-such-upload", f"no PDF was dropped as {sha[:12]}", status=404)
        path = kept[0]
        name = path.name
        result = _scan(root)
        # where a run can read its text, filing answers at once and the run says how far through its pages it is
        later = _JOBS.get(root.resolve()) is not None
        if body.get("new"):
            typed = body.get("entry")
            edits = {k: v for k, v in typed.items() if isinstance(v, str)} if isinstance(typed, dict) else None
            filed = file_new(
                quilt, result.bib, path, who, came_from=name, online=online, edits=edits, read_pages=not later
            )
        else:
            citekey = _str(body, "citekey", required=True) or ""
            if citekey not in result.bib:
                raise ApiError("no-such-work", f"the library has no work {citekey}", status=404)
            _busy(root, citekey)
            filed = file_under(quilt, result.bib, path, citekey, who, came_from=name, read_pages=not later)
        citekey = filed["citekey"]
        return {
            "ok": True,
            "result": f"filed {name} under {citekey}",
            **filed,
            "job": run(citekey, pages=filed["filed"]),
        }
    citekey = _str(body, "citekey", required=True) or ""
    _busy(root, citekey)
    try:
        return {"ok": True, "result": delete_work(scan(quilt), citekey, who)}
    except NotDeletable as exc:
        raise ApiError(exc.code, exc.message, status=404 if exc.code == "no-such-work" else 409) from exc


def _library_ignore(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """`library-ignore` (plan 0.24.4): stop loom asking for a work's paper, or offering its stored document an entry, or withdraw that, as `loom library ignore` does; the author's, since whether a work can be had is a claim about the world."""
    from loom.cli._common import is_agent
    from loom.refs.unreadable import NotIgnorable, ignore
    from loom.scan.quilt import reviewer_identity

    who = reviewer_identity(root)[0]
    if is_agent(_str(body, "author") or who):
        raise ApiError(
            "author-only",
            "Whether a work can be obtained is the author's claim; an agent reports what it could not find",
            status=403,
        )
    citekey = _str(body, "citekey", required=True) or ""
    why = _str(body, "why", required=True) or ""
    result = _scan(root)
    if citekey not in result.bib:
        raise ApiError("no-such-work", f"the library has no work {citekey}", status=404)
    _busy(root, citekey)
    try:
        return {"ok": True, "result": ignore(result, citekey, why, who, undo=body.get("undo") is True)[1]}
    except NotIgnorable as exc:
        raise ApiError(exc.code, exc.message, status=409) from exc


def _scan(root: Path) -> ScanResult:
    """The quilt's scan: the publisher's own while it is current, else a fresh one."""
    from loom.cli._quilt import open_scan

    provider = _SCANS.get(root.resolve())
    kept = provider() if provider is not None else None
    return kept if kept is not None else open_scan(str(root))


#: Writes that change records alone, which the scan never reads, or keep a version, whose landmark the build reads again (`build(reuse=…)`); their publication builds from the last scan (`ServeSession.rebuild`).
RECORD_WRITES = (
    "annotate",
    "file-tick",
    "annotations-take",
    "changes-keep",
    "history-record",
    "reply",
    "resolve",
    "edit",
    "delete",
    "restore",
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


def _pdf_save(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """Write a PDF the viewer made as a new file of the project, at a path the person names (P7).

    Refuses a path that exists, leaves the quilt, is hidden from the viewer or is not a `.pdf`, bytes that are not a PDF, and an agent: page edits are the person's act at the viewer.
    """
    from loom.cli._common import is_agent
    from loom.files import Shown
    from loom.scan.quilt import load_quilt, reviewer_identity

    name = (_str(body, "path", required=True) or "").strip()
    data = _str(body, "data", required=True) or ""
    if is_agent(_str(body, "author") or reviewer_identity(root)[0]):
        raise ApiError("author-only", "An agent reads and annotates; only the author saves a PDF", status=403)
    if not name.lower().endswith(".pdf"):
        raise ApiError("bad-field", "a saved PDF's name ends in .pdf")
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or name.startswith("/"):
        raise ApiError("bad-field", f"{name} is outside the quilt")
    rel = path.relative_to(root.resolve()).as_posix()
    if not Shown.of(load_quilt(root)).is_shown(rel):
        raise ApiError("hidden", f"{rel} would be hidden from the viewer: name a place it shows", status=403)
    if path.exists():
        raise ApiError("exists", f"{rel} already exists; a saved PDF never replaces a file", status=409)
    try:
        raw = base64.b64decode(data, validate=True)
    except ValueError as exc:
        raise ApiError("bad-field", "data is not base64") from exc
    if not raw.startswith(b"%PDF-"):
        raise ApiError("bad-field", "data is not a PDF")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as fh:
        fh.write(raw)
    return {"ok": True, "result": f"saved {rel}", "path": rel, "bytes": len(raw)}


def _changes(root: Path, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """`changes-keep` and `changes-undo`: the reviewer keeps a change to an open file, some hunks of it, or every change (no `path`), or puts one back as it was at their look, a new file removed; the author's acts, refused to a declared agent.

    `seen` is the file's hash as the page drew it (`changes[].hash`); an act on a file that has moved on since is `stale`, so a hunk's number never names another change.
    """
    from loom.cli._common import is_agent
    from loom.looks import LookRefused, changes, keep, undo
    from loom.scan.quilt import load_quilt, reviewer_identity

    who = reviewer_identity(root)[0]
    if not who:
        raise ApiError("no-reviewer", "Choose your reviewer name in Settings", status=409)
    if is_agent(_str(body, "author") or who):
        raise ApiError(
            "author-only", "An agent reads and annotates; only the author keeps or undoes a change", status=403
        )
    quilt = load_quilt(root)
    hunks = body.get("hunks")
    if hunks is not None and (
        not isinstance(hunks, list)
        or not hunks
        or any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in hunks)
    ):
        raise ApiError("bad-field", "hunks must be a list of whole numbers from 0")
    path = _str(body, "path", required=endpoint == "changes-undo" or hunks is not None)
    seen = _str(body, "seen")
    what = (f"a change to {path}" if len(hunks) == 1 else f"{len(hunks)} changes to {path}") if hunks else path
    from loom.history.acts import Kept, keep_versions

    try:
        if endpoint == "changes-undo":
            # the text being set aside is a version of each document it is part of, kept before it goes
            kept: list[Kept] = []
            first = lambda: kept.append(keep_versions(_scan(root), [path or ""], "undo", "Before an undo", who))  # noqa: E731
            back = undo(quilt, who, path or "", hunks=hunks, seen=seen, before=first)
            said = (
                f"removed {path}; its text is kept"
                if back is None
                else f"put back {what}; the text it replaced is kept"
            )
            return {"ok": True, "result": "; ".join(filter(None, [said, *(k.said() for k in kept)]))}
        # a whole keep keeps a version of the documents whose files moved since the look, and none at a first look
        moved = [path] if path else [c.path for c in changes(quilt, who)]
        keep(quilt, who, path, hunks=hunks, seen=seen)
    except LookRefused as exc:
        raise ApiError(
            exc.code, exc.message, status=404 if exc.code in ("no-such-change", "no-such-hunk") else 409
        ) from exc
    versions = keep_versions(_scan(root), moved, "keep", "Kept an edit", who)
    return {
        "ok": True,
        "result": "; ".join(filter(None, [f"kept {what}" if path else "kept everything", versions.said()])),
    }


def _file_tick(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """`file-tick`: the person sets one box of a Markdown file (`loom.tasks`), `task` being the id the published body gives it; refused to a declared agent, which edits a file as it edits any other."""
    from loom.cli._common import is_agent
    from loom.scan.quilt import load_quilt, reviewer_identity
    from loom.tasks import TickRefused, tick

    who = reviewer_identity(root)[0]
    if is_agent(_str(body, "author") or who):
        raise ApiError("author-only", "An agent edits the file; a tick in the viewer is the person's", status=403)
    path = _str(body, "path", required=True) or ""
    task = _str(body, "task", required=True) or ""
    done = body.get("done")
    if not isinstance(done, bool):
        raise ApiError("bad-field", "done must be true or false")
    try:
        changed = tick(load_quilt(root), who, path, task, done)
    except TickRefused as exc:
        raise ApiError(exc.code, exc.message, status=404 if exc.code == "no-such-file" else 409) from exc
    verb = "ticked" if done else "unticked"
    return {"ok": True, "result": f"{verb} a box in {path}" if changed else f"that box in {path} is already {verb}"}


def _history(root: Path, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """`history-record` keeps a version of a document under the author's name for it, as `loom stamp DOC -m NAME`; `history-restore` puts a version back into its document (`document`, `version`), or the text an undo set aside back into its file (`path`, `text`), keeping what it replaces first. The author's acts, refused to a declared agent."""
    from loom.cli._common import is_agent
    from loom.history.acts import RestoreRefused, put_back, restore
    from loom.history.ledger import actor_for, load_history
    from loom.history.steps import slug, stamp_document
    from loom.looks import open_texts
    from loom.scan.quilt import load_quilt, reviewer_identity

    who = reviewer_identity(root)[0] or actor_for(root)
    if is_agent(_str(body, "author") or who or ""):
        raise ApiError(
            "author-only", "An agent reads and annotates; only the author records or restores a version", status=403
        )
    quilt = load_quilt(root)
    if endpoint == "history-restore" and body.get("path") is not None:
        path = _str(body, "path", required=True) or ""
        digest = _str(body, "text", required=True) or ""
        try:
            put_back(root, quilt.history_dir, path, digest, who, open_texts(quilt))
        except RestoreRefused as exc:
            raise ApiError(exc.code, exc.message, status=409) from exc
        return {"ok": True, "result": f"put {path} back as the undo found it; its text before is kept"}
    result = _scan(root)
    doc = _str(body, "document", required=True) or ""
    if result.document_role(doc) != "person":
        raise ApiError("bad-field", f"{doc} is not one of your documents")
    if endpoint == "history-record":
        name = (_str(body, "name", required=True) or "").strip()
        if not name:
            raise ApiError("bad-field", "a version needs a name", fields={"name": "Give the version a name."})
        history = load_history(quilt.history_dir)
        landmark = slug(f"{Path(doc).stem} {name}", limit=120)
        if history.landmark(landmark) is not None:
            raise ApiError(
                "name-in-use",
                f"a version named {name} is kept already",
                status=409,
                fields={"name": "That name is in use."},
            )
        try:
            stamp_document(result, history, doc, landmark, name, who)
        except ValueError as exc:
            raise ApiError("cannot-record", str(exc).split(";")[0], status=409) from exc
        return {"ok": True, "result": f"kept this version of {Path(doc).name} as “{name}”"}
    version = _str(body, "version", required=True) or ""
    try:
        done = restore(result, doc, version, who)
    except RestoreRefused as exc:
        raise ApiError(exc.code, exc.message, status=404 if exc.code == "unknown-version" else 409) from exc
    if not done["paths"]:
        return {"ok": True, "result": f"{Path(doc).name} is already as “{done['label']}” holds it"}
    return {
        "ok": True,
        "result": f"put {Path(doc).name} back as “{done['label']}” holds it; its text before is the version “{done['before']}”",
    }


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
    if endpoint == "file-tick":
        return _file_tick(root, body)
    if endpoint in ("history-record", "history-restore"):
        return _history(root, endpoint, body)
    if endpoint == "annotations-take":
        return _take(root, body)
    if endpoint == "pdf-save":
        return _pdf_save(root, body)
    if endpoint in ("library-verify", "library-discard"):
        return {"ok": True, "result": _library(root, endpoint, body)}
    if endpoint == "library-update":
        return _library_update(root, body)
    if endpoint in (
        "library-recognise",
        "library-lookup",
        "library-add",
        "library-upload",
        "library-file",
        "library-delete",
    ):
        return _library_add(root, endpoint, body)
    if endpoint == "library-ignore":
        return _library_ignore(root, body)
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
                raise ApiError("revision-changed", "the fetched revision changed; reload Review")
            if base != state.integrated and state.integrated != state.incoming:
                raise ApiError("revision-changed", "the incorporated base changed; reload Review")
            binding = {"kind": "sync", "incoming": incoming or "", "base": base or ""}
            reviewer, _ = reviewer_identity(root)
            if endpoint == "sync-preview" or body.get("review_token") or body.get("accept"):
                if not reviewer or _str(body, "reviewer") != reviewer:
                    raise ApiError("reviewer-changed", "Choose your reviewer name and reload Review", status=409)
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
            raise ApiError("reviewer-changed", "Choose your reviewer name and reload Review", status=409)
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
                    raise SyncError("Contribution changed; reload Review")
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
    if endpoint == "review-accept":
        import json

        from loom.cli._common import is_agent
        from loom.review_queue import accept
        from loom.scan.quilt import reviewer_identity

        reviewer, _ = reviewer_identity(root)
        if not reviewer:
            raise ApiError("no-reviewer", "Choose your reviewer name in Settings", status=409)
        if _str(body, "reviewer") != reviewer:
            raise ApiError("reviewer-changed", "Reviewer changed; reload Review before continuing", status=409)
        if is_agent(_str(body, "author") or reviewer):
            raise ApiError("author-only", "An agent reads and annotates; only the author accepts", status=403)
        keys = body.get("keys")
        if not isinstance(keys, list) or not keys or not all(isinstance(k, str) and k for k in keys):
            raise ApiError("bad-field", "keys must be a nonempty list of block keys")
        manifest_path = root / MANIFEST
        if not manifest_path.is_file():
            raise ApiError("review-unavailable", "build the quilt before reviewing", status=409)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("reviewer", {}).get("name") != reviewer:
            raise ApiError("reviewer-changed", "Rebuild and reload Review before continuing", status=409)
        try:
            answer = accept(_scan(root), manifest, keys, reviewer)
        except KeyError as exc:
            raise ApiError(
                "not-unresolved", f"{exc.args[0]} is not awaiting review; reload Review", status=409
            ) from exc
        except ValueError as exc:
            raise ApiError("compile-failed", str(exc), status=409) from exc
        if answer["accepted"]:
            # what the page showed with its Accept: an edit touching only blocks just accepted has been seen
            from loom.history.acts import keep_versions
            from loom.looks import keep_accepted

            after = _scan(root)
            moved = keep_accepted(after, reviewer, answer["accepted"])
            if moved:
                keep_versions(after, moved, "keep", "Kept an edit", reviewer)
        return {
            "ok": True,
            "result": f"accepted {len(answer['accepted'])} of {len(answer['accepted']) + len(answer['refused'])}",
            **answer,
        }
    if endpoint.startswith("session-"):
        return {"ok": True, "result": _session(root, endpoint, body)}
    if endpoint in ("delete", "restore"):
        return _delete(root, endpoint, body)
    return {"ok": True, "result": _review(root, endpoint, body)}


def _delete(root: Path, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
    """Delete an annotation, answering with the events removed, or put back events a delete removed: the viewer's undo of a delete is the second."""
    from loom.cli._common import ContentError, EnvError, NotFoundError
    from loom.cli.review import _annotator, delete_annotation
    from loom.records.log import EVENTS, restore

    try:
        writer = _annotator(root, _str(body, "author"), sniff=False)
        if endpoint == "delete":
            said, removed = delete_annotation(root, _str(body, "annotation", required=True) or "", writer)
            return {"ok": True, "result": said, "removed": removed}
        events = body.get("events")
        if (
            not isinstance(events, list)
            or not events
            or not all(isinstance(e, dict) and e.get("event") in EVENTS and e.get("id") for e in events)
        ):
            raise ApiError("bad-field", "events must be the events a delete answered with")
        put = restore(root, events)
        return {"ok": True, "result": f"restored {', '.join(put)}"}
    except NotFoundError as exc:
        raise ApiError(f"no-such-{exc.what}", str(exc), status=404) from exc
    except (EnvError, ContentError, ValueError) as exc:
        raise ApiError("refused", str(exc)) from exc


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
    from loom.cli.review import _annotator, _one_comment, edit_annotation

    # Validate the request before touching the quilt: a missing field is the caller's mistake and should be named as
    # one, not reported as whatever the first function to be handed nothing happens to complain about.
    needs = {"annotate": ("target",), "reply": ("annotation", "message")}.get(endpoint, ("annotation",))
    for field in needs:
        _str(body, field, required=True)

    # An annotation belongs to no session, so a `session` sent with one is ignored.
    try:
        # Who is at the browser, not what shell the server was started in: with `loom serve` running in an agent's terminal every annotation the author wrote in their own browser was recorded `author: "agent"` until this stopped sniffing. An agent posting here declares itself, and `is_agent` still guards the author's verbs by that name.
        writer = _annotator(root, _str(body, "author"), sniff=False)
    except NotFoundError as exc:
        raise ApiError(f"no-such-{exc.what}", str(exc), status=404) from exc
    except (EnvError, ContentError) as exc:
        raise ApiError("refused", str(exc)) from exc

    try:
        # `undo` opens a resolved annotation again by appending another event; the viewer offers it in place of the verb that fired, so a wrong click is one click back (DR-174).
        undo = bool(body.get("undo"))
        result = _scan(root)
        if endpoint == "suggestion-apply":
            return _apply(root, result, _str(body, "annotation", required=True) or "", writer)
        if endpoint == "edit":
            # the viewer sends the new text as `message`, as every other endpoint names it; the log's field is `body`
            fields = {"body": _str(body, "message"), **{k: _str(body, k) for k in ("payload", "placement")}}
            # a type of "" or null takes the type off; absent leaves it as it is
            type_given = ("" if body["type"] is None else _str(body, "type")) if "type" in body else None
            return edit_annotation(
                result,
                _str(body, "annotation", required=True) or "",
                writer,
                False,
                type_given,
                _look(body),
                _geometry(body, "rects"),
                _geometry(body, "strokes"),
                **fields,
            )
        if endpoint == "annotate":
            # an annotation on a PDF page carries the page and its rectangles or strokes (plan 0.13 item 2)
            page = body.get("page")
            if page is not None and (not isinstance(page, int) or page < 1):
                raise ApiError("bad-field", "page must be a positive integer")
            rects = _geometry(body, "rects")
            return _one_comment(
                result,
                writer,
                _str(body, "target", required=True),
                _str(body, "message"),
                _str(body, "quote"),
                _str(body, "type"),
                None,
                None,
                _str(body, "payload"),
                _str(body, "placement"),
                page=page,
                rects=rects,
                in_doc=_str(body, "in"),
                look=_look(body),
                strokes=_geometry(body, "strokes"),
                mark=_str(body, "mark"),
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


def _apply(root: Path, result: ScanResult, annotation: str, writer: tuple[str, str]) -> str:
    """`suggestion-apply`: write a suggestion's text into its file, as `loom suggestion apply ID`, then resolve it as applied against the file as written. The author's act, refused to a declared agent."""
    from loom.cli._common import ContentError, EnvError, NotFoundError
    from loom.cli.review import _one_comment
    from loom.records.annotations import find_annotation, load_records
    from loom.records.suggestions import ApplyRefused, apply

    if writer[0] == "agent":
        raise ApiError("author-only", "An agent suggests; only the author puts a suggestion into the text", status=403)
    found = find_annotation(load_records(root)[0], annotation)
    if found is None:
        raise NotFoundError("annotation", f"no annotation {annotation}")
    try:
        documents, kept = apply(result, found[1], writer[1])
    except ApplyRefused as exc:
        raise ApiError(exc.code, exc.message, status=409) from exc
    said = f"applied the suggestion in {' and '.join(Path(d).name for d in documents) or found[1].target_key}"
    try:
        _one_comment(_scan(root), writer, None, None, None, None, None, annotation, applied=True)
    except (ContentError, EnvError) as exc:  # the text is in; only the record of it failed, and the person is told so
        return f"{said}, but it could not be resolved as applied: {exc}"
    return "; ".join(x for x in (said, kept.said()) if x)


def _geometry(body: dict[str, Any], name: str) -> list[list[float]] | None:
    """`rects` or `strokes` as a write gives them, each a list of numbers; refused when it is not."""
    from loom.records.marks import MarkRefused, clean_rects, clean_strokes

    try:
        return (clean_rects if name == "rects" else clean_strokes)(body.get(name))
    except MarkRefused as exc:
        raise ApiError(exc.code, exc.message, status=exc.status) from exc


def _take(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    """`annotations-take`: a PDF's own annotations written as annotations on it, what is here already left alone (`marks.take_in`)."""
    from loom.cli._common import ContentError, EnvError
    from loom.cli.review import _annotator
    from loom.records.marks import MarkRefused, take_in

    items = body.get("items")
    if not isinstance(items, list):
        raise ApiError("missing-field", "items is the list of annotations to take in")
    try:
        writer = _annotator(root, _str(body, "author"), sniff=False)
        took = take_in(_scan(root), _str(body, "target", required=True) or "", items, writer)
    except MarkRefused as exc:
        raise ApiError(exc.code, exc.message, status=exc.status) from exc
    except (EnvError, ContentError) as exc:
        raise ApiError("refused", str(exc)) from exc
    return {"ok": True, "result": f"took in {took['taken']}", **took}


def _look(body: dict[str, Any]) -> dict[str, Any]:
    """The look a write sets, as `look: {color, style, weight, opacity}` with any field left out; refused when it is not a table."""
    look = body.get("look")
    if look is None:
        return {}
    if not isinstance(look, dict):
        raise ApiError("bad-field", "look must be an object of color, style, weight and opacity")
    return {k: look[k] for k in ("color", "style", "weight", "opacity") if k in look}


def _accept_keys(body: dict[str, Any]) -> list[str]:
    keys = body.get("accept", [])
    if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
        raise ApiError("bad-field", "accept must be a list of mathematical block keys")
    return keys
