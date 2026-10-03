"""The document workspace: a source-only Git repository, such as an Overleaf project, that coauthors edit.

Loom keeps its own clone of the workspace in `.loom/workspace/` and runs Git only there; the quilt's own files are read and written as files, and the quilt's version control, if it has any, is never touched. Publishing commits the selected documents' sources in the clone and stamps each document; incorporating a pull applies the reviewed patch to the quilt's files after stamping what it replaces. Neither accepts mathematics.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loom.clock import stamp
from loom.reshape.importer import closure_of
from loom.scan.quilt import Quilt
from loom.tex.runner import compile_tex

if TYPE_CHECKING:
    from loom.scan.scan import ScanResult

#: Loom's clone of the document workspace, under the quilt root.
WORKSPACE = ".loom/workspace"
#: The ref in the clone that holds the last prepared publication.
PUBLICATION_REF = "refs/loom/publication"


class SyncError(Exception):
    """A sync precondition failed without changing the quilt source."""


@dataclass
class SyncState:
    url: str
    branch: str
    master: str
    integrated: str
    incoming: str = ""
    observed: str = ""
    published_main: str = ""
    last_pull: dict[str, Any] = field(default_factory=dict)
    # Projections of the shared origin store (`loom.review_origins`), where they are persisted.
    review_origins: dict[str, str] = field(default_factory=dict)
    review_changed: dict[str, bool] = field(default_factory=dict)
    review_baselines: dict[str, str] = field(default_factory=dict)
    review_local_changed: dict[str, bool] = field(default_factory=dict)
    documents: list[str] = field(default_factory=list)
    prepared: str = ""
    prepared_landmarks: list[str] = field(default_factory=list)

    @classmethod
    def read(cls, root: Path) -> SyncState:
        path = root / ".loom" / "source-sync.json"
        if not path.is_file():
            raise SyncError("document workspace is not configured; run `loom sync init URL` first")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = cls(**data)
            from loom.review_origins import read

            state.review_origins = {}
            state.review_changed = {}
            state.review_baselines = {}
            state.review_local_changed = {}
            for key, row in read(root).items():
                if row["source"].startswith("pull:"):
                    state.review_origins[key] = row["source"].removeprefix("pull:")
                    state.review_changed[key] = row["changed"]
                    if row.get("baseline"):
                        state.review_baselines[key] = row["baseline"]
                    state.review_local_changed[key] = row["local_before"]
            if not state.documents:
                state.documents = [state.master]
            elif state.master not in state.documents:
                state.documents.insert(0, state.master)
            return state
        except (ValueError, TypeError) as exc:
            raise SyncError(f"{path} is not a valid source-sync record; pair again with `loom sync init URL`") from exc

    def write(self, root: Path) -> None:
        if self.master not in self.documents:
            self.documents.insert(0, self.master)
        path = root / ".loom" / "source-sync.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        from loom.review_origins import read, write

        origins = read(root)
        for key, commit in self.review_origins.items():
            # Adoption may have superseded a pull's origin since this transport object was read.
            if origins.get(key, {}).get("source", "").startswith("adopt:") and commit != self.incoming:
                continue
            origins[key] = {
                "source": "pull:" + commit,
                "changed": self.review_changed.get(key, False),
                "baseline": self.review_baselines.get(key),
                "local_before": self.review_local_changed.get(key, False),
                "label": f"Incoming from {source_label(self.url)}",
            }
        if origins or self.last_pull:
            write(root, origins)
        data = {key: value for key, value in vars(self).items() if not key.startswith("review_")}
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)


def git(cwd: Path, *args: str, env: dict[str, str] | None = None, input: bytes | None = None) -> bytes:
    """Run git in `cwd`, which is loom's clone or a scratch directory, never the quilt's own repository."""
    try:
        run = subprocess.run(["git", *args], cwd=cwd, env=env, input=input, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise SyncError("Git is required to reach a document workspace") from exc
    if run.returncode:
        detail = run.stderr.decode("utf-8", errors="replace").strip()
        if args and args[0] == "push":
            detail += "\n" + run.stdout.decode("utf-8", errors="replace").strip()
        raise SyncError(f"git {' '.join(args)}: {detail or f'exited {run.returncode}'}")
    return run.stdout


def workspace(root: Path) -> Path:
    """Loom's clone of the document workspace, refused by name when it is missing.

    Every Git call but `configure`'s clone runs here. The clone is loom's own: it holds the fetched revisions and the prepared publication, and nothing an author wrote.
    """
    clone = root / WORKSPACE
    if not (clone / ".git").is_dir():
        raise SyncError(
            f"loom's clone of the document workspace ({WORKSPACE}) is missing; pair again with `loom sync init URL`"
        )
    return clone


def source_label(url: str) -> str:
    """A readable name for a document workspace: Overleaf for its Git transport, otherwise the URL without its scheme or `.git`.

    Parameters
    ----------
    url : str
        The workspace URL or path `loom sync init` was given.

    Returns
    -------
    str
        The name Incoming and the review queue show.
    """
    if "git.overleaf.com/" in url:
        return "Overleaf"
    name = url.split("://", 1)[-1].rstrip("/")
    return name.removesuffix(".git") or url


def revision(cwd: Path, ref: str) -> str:
    return git(cwd, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()


def current_selection(state: SyncState, result: ScanResult) -> tuple[str, list[str]]:
    """The sync record's main and selected documents as they are now, main first.

    Each recorded path is followed across the history's moves (`ScanResult.current_document`), so a record written before a `linearize` publishes what the document became; the record itself is never rewritten. A path that leads nowhere is kept as written, so `selected_documents` refuses it by name.

    Parameters
    ----------
    state : SyncState
        The sync record as read.
    result : ScanResult
        A scan of the quilt, for its live documents and history.

    Returns
    -------
    tuple of (str, list of str)
        The local path Overleaf's main maps to, and every selected document without duplicates.
    """

    def now(path: str) -> str:
        return result.current_document(path) or path

    main = now(state.master)
    documents = list(dict.fromkeys(now(d) for d in (state.documents or [state.master])))
    if main not in documents:
        documents.insert(0, main)
    return main, documents


def local_main(quilt: Quilt, state: SyncState) -> str:
    """The local path Overleaf's main file maps to now: `current_selection`'s main, from a fresh scan."""
    from loom.scan.scan import scan

    return current_selection(state, scan(quilt))[0]


def _selection(quilt: Quilt, state: SyncState) -> tuple[str, list[str]]:
    """`current_selection` from a fresh scan, each document checked safe and live; both `selected_documents` and `source_projection` read it."""
    from loom.scan.scan import scan

    result = scan(quilt)
    main, documents = current_selection(state, result)
    for document in documents:
        path = Path(document)
        if path.is_absolute() or ".." in path.parts:
            raise SyncError(f"selected document has an unsafe path: {document}")
        if result.document_role(document) == "drafting-ai":
            raise SyncError(f"selected document is an agent's document, which is never published: {document}")
        if result.document_role(document) != "drafting":
            raise SyncError(f"selected document is not a live drafting document: {document}")
    return main, documents


def selected_documents(quilt: Quilt, state: SyncState) -> list[str]:
    """Validate and return the persistent source-projection document selection, each document where it is now (`current_selection`)."""
    return _selection(quilt, state)[1]


def source_projection(quilt: Quilt, state: SyncState) -> tuple[list[str], dict[str, str]]:
    """Selected masters and their union of local-to-remote source paths; the main document publishes as `published_main` wherever it has moved locally."""
    root = quilt.root
    main, documents = _selection(quilt, state)
    projected: dict[str, str] = {}
    remote_sources: dict[str, str] = {}
    for document in documents:
        found, outside = closure_of(root, root / document)
        if outside:
            raise SyncError(f"{document} reaches files outside the quilt: " + ", ".join(outside))
        for local in found:
            remote = state.published_main if local == main else local
            previous = remote_sources.get(remote)
            if previous is not None and previous != local:
                raise SyncError(f"two quilt files would publish as {remote}: {previous}, {local}")
            remote_sources[remote] = local
            projected[local] = remote
    return documents, projected


def source_paths(quilt: Quilt, state: SyncState) -> list[str]:
    """Every source path in the selected document projection."""
    return sorted(source_projection(quilt, state)[1])


def configure(quilt: Quilt, url: str, published_main: str = "") -> SyncState:
    """Clone the document workspace into `.loom/workspace/` and pair it with the quilt's main document.

    A clone already there is replaced, since it holds nothing that a fetch and a publish do not make again. The branch is the workspace's default branch.

    Parameters
    ----------
    quilt : Quilt
        The quilt to pair.
    url : str
        The workspace's Git URL or path, e.g. Overleaf's `https://git.overleaf.com/<project>`.
    published_main : str, default ''
        The main document's path in the workspace; '' keeps the quilt's path.

    Returns
    -------
    SyncState
        The written sync record, its `integrated` revision the workspace's tip.
    """
    root = quilt.root
    if published_main and (Path(published_main).is_absolute() or ".." in Path(published_main).parts):
        raise SyncError("the document workspace main path must stay within the project")
    target = root / WORKSPACE
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="workspace-", dir=target.parent) as temporary:
        clone = Path(temporary) / "clone"
        git(root, "clone", "--quiet", "--no-tags", url, str(clone))
        try:
            tip = revision(clone, "HEAD")
        except SyncError as exc:
            raise SyncError(f"{url} has no commits; create the project there first") from exc
        branch = git(clone, "symbolic-ref", "--short", "HEAD").decode().strip()
        if target.exists():
            shutil.rmtree(target)
        clone.rename(target)
    state = SyncState(
        url=url,
        branch=branch,
        master=quilt.config.main,
        integrated=tip,
        published_main=published_main or quilt.config.main,
        documents=[quilt.config.main],
    )
    state.write(root)
    return state


def fetch(quilt: Quilt, state: SyncState) -> SyncState:
    clone = workspace(quilt.root)
    git(clone, "fetch", "--quiet", "--no-tags", "origin", state.branch)
    new = revision(clone, "FETCH_HEAD")
    # Keep a ref to the reviewed object even when a later fetch moves FETCH_HEAD.
    git(clone, "update-ref", f"refs/loom/incoming/{new}", new)
    if state.prepared and new == state.prepared:
        _recognize_publication(state)
    if new != state.incoming:
        state.incoming = new
        state.observed = stamp()
    state.write(quilt.root)
    return state


def _recognize_publication(state: SyncState) -> None:
    """The same exact-revision recognition after push and fetch; review work stays intact."""
    state.integrated = state.prepared
    if state.incoming != state.prepared:
        state.incoming = state.prepared
        state.observed = stamp()


def push_publication(quilt: Quilt, state: SyncState, commit: str) -> None:
    """Send the prepared revision from loom's clone to the workspace, never forced."""
    if not commit or commit != state.prepared:
        raise SyncError("publication does not match the prepared revision")
    try:
        git(workspace(quilt.root), "push", "--porcelain", "origin", f"{commit}:refs/heads/{state.branch}")
    except SyncError as exc:
        outcome = (
            "Publication rejected"
            if "[rejected]" in str(exc) or "[remote rejected]" in str(exc)
            else "Publication was not confirmed"
        )
        raise SyncError(
            f"{outcome}: {exc}. The prepared revision is kept; "
            "run `loom sync fetch` to reconcile the workspace before publishing again, since a transport failure can leave the outcome uncertain."
        ) from exc
    _recognize_publication(state)
    try:
        state.write(quilt.root)
    except OSError as exc:
        raise SyncError(
            f"Published {commit[:12]} to {source_label(state.url)}, but recording local success failed: {exc}. "
            "Run `loom sync fetch` to reconcile the prepared revision."
        ) from exc


def changed_files(cwd: Path, before: str, after: str) -> list[dict[str, str]]:
    if before == after:
        return []
    raw = git(cwd, "diff", "--name-status", "--no-renames", "-z", before, after)
    parts = raw.decode("utf-8", errors="replace").split("\0")
    return [{"status": parts[i], "path": parts[i + 1]} for i in range(0, len(parts) - 1, 2)]


def exact_renames(cwd: Path, before: str, after: str) -> list[tuple[str, str]]:
    """(deleted, added) remote path pairs between two commits whose blobs are identical: a rename Git would call exact.

    A blob deleted or added more than once in the diff pairs nothing, since which went where cannot be told. Paths are the remote's; `prepare_incorporation` maps Overleaf's main to its local path.
    """
    if before == after:
        return []
    raw = git(cwd, "diff", "--raw", "--no-renames", "--no-abbrev", "-z", before, after).decode(
        "utf-8", errors="replace"
    )
    parts = raw.split("\0")
    deleted: dict[str, list[str]] = {}
    added: dict[str, list[str]] = {}
    for i in range(0, len(parts) - 1, 2):
        meta = parts[i].split()
        if len(meta) < 5:
            continue
        old_blob, new_blob, status = meta[2], meta[3], meta[4]
        if status == "D":
            deleted.setdefault(old_blob, []).append(parts[i + 1])
        elif status == "A":
            added.setdefault(new_blob, []).append(parts[i + 1])
    return sorted(
        (gone[0], came[0]) for blob, gone in deleted.items() if len(gone) == 1 and len(came := added.get(blob, [])) == 1
    )


def tree_files(cwd: Path, commit: str) -> dict[str, bytes]:
    names = git(cwd, "ls-tree", "-r", "--name-only", "-z", commit).split(b"\0")
    return {name.decode("utf-8"): git(cwd, "show", f"{commit}:{name.decode('utf-8')}") for name in names if name}


def incoming_patch(quilt: Quilt, state: SyncState, main: str | None = None) -> bytes:
    """The pinned pull as a Git patch against local paths: Overleaf's main is rewritten to `main`, default `local_main`."""
    if not state.incoming or state.incoming == state.integrated:
        return b""
    # The remote is source-only, and collaborators may add a new input that
    # cannot yet be in the local master closure.
    patch = git(workspace(quilt.root), "diff", "--binary", "--no-renames", state.integrated, state.incoming)
    main = main or local_main(quilt, state)
    if state.published_main != main:
        old = state.published_main.encode()
        new = main.encode()
        rewritten = []
        for line in patch.splitlines(keepends=True):
            if line.startswith((b"diff --git ", b"--- ", b"+++ ")):
                line = line.replace(b"a/" + old, b"a/" + new).replace(b"b/" + old, b"b/" + new)
            rewritten.append(line)
        patch = b"".join(rewritten)
    return patch


def _incoming_paths(quilt: Quilt, state: SyncState, main: str) -> list[str]:
    paths = [
        main if row["path"] == state.published_main else row["path"]
        for row in changed_files(workspace(quilt.root), state.integrated, state.incoming)
    ]
    if len(paths) != len(set(paths)) or any(Path(p).is_absolute() or ".." in Path(p).parts for p in paths):
        raise SyncError("incoming source contains an unsafe or duplicate path")
    return paths


def pull_files(quilt: Quilt, state: SyncState) -> dict[str, bytes | None]:
    """The pinned pull applied to the quilt's current files in a scratch directory: each path it touches and what that path would then hold, None for a removal.

    Every check incorporation makes is made here and nothing in the quilt is written; `incorporate` writes exactly this, and the write API's `sync-preview` reads it. The patch applies hunk by hunk, so an author's edit elsewhere in a file the pull touches survives.

    Parameters
    ----------
    quilt : Quilt
        The paired quilt.
    state : SyncState
        The sync record, with a fetched revision not yet incorporated.

    Returns
    -------
    dict of str to bytes or None
        Quilt-relative path to its content after the pull.
    """
    root = quilt.root
    if not state.incoming or state.incoming == state.integrated:
        raise SyncError("there is no incoming revision to incorporate")
    main = local_main(quilt, state)
    paths = _incoming_paths(quilt, state, main)
    if not paths:
        raise SyncError("the incoming revision changes no files")
    for row in changed_files(workspace(root), state.integrated, state.incoming):
        path = main if row["path"] == state.published_main else row["path"]
        if row["status"].startswith("A") and (root / path).exists():
            raise SyncError(f"{path} already exists locally; rename or remove it, then incorporate again")
    for path in paths:
        target = root / path
        if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
            raise SyncError(f"unsafe source path: {path}")
    patch = incoming_patch(quilt, state, main)
    with tempfile.TemporaryDirectory(prefix="loom-pull-") as temporary:
        stage = Path(temporary) / "quilt"
        stage.mkdir()
        for path in paths:
            if (root / path).is_file():
                (stage / path).parent.mkdir(parents=True, exist_ok=True)
                (stage / path).write_bytes((root / path).read_bytes())
        # outside any repository, so `git apply` patches these files and nothing else
        env = {**os.environ, "GIT_CEILING_DIRECTORIES": temporary}
        try:
            git(stage, "apply", "--whitespace=nowarn", "-", env=env, input=patch)
        except SyncError as exc:
            raise SyncError(
                f"the pull does not apply to your current files: {exc}. "
                "Read it with `loom sync patch`, bring those files in line in your editor, then incorporate again"
            ) from exc
        return {path: (stage / path).read_bytes() if (stage / path).is_file() else None for path in paths}


def _review(quilt: Quilt, state: SyncState, result: ScanResult) -> dict[str, Any]:
    """What the pull asks to be reviewed, read from the Incoming review a build publishes: changed and affected keys, collaborator renames, and which keys the author had edited since the last pull."""
    from loom.render.build import build
    from loom.review_queue import fingerprint

    main = current_selection(state, result)[0]
    incoming_review = build(quilt).manifest.get("incoming") or {}
    if incoming_review.get("commit") != state.incoming:
        raise SyncError("the incoming review changed; run `loom sync fetch` and review it again")
    changed_keys = [c["key"] for c in incoming_review.get("changes", []) if c.get("category") != "prose"]
    review_keys = sorted(
        set(changed_keys)
        | set(incoming_review.get("affected", []))
        | {d["key"] for c in incoming_review.get("changes", []) for d in c.get("affected", [])}
    )
    # a live document deleted and an identical drafting document added is a collaborator's rename, recorded only once the pull is incorporated (book 4.6)
    moves = [
        {"from": main if gone == state.published_main else gone, "to": came, "main": gone == state.published_main}
        for gone, came in exact_renames(workspace(quilt.root), state.integrated, state.incoming)
        if (main if gone == state.published_main else gone) in result.masters
        and came.endswith(".tex")
        and Path(came).parent.as_posix() == quilt.config.drafting
    ]
    local_before = {
        key: state.review_local_changed.get(key, False)
        or (
            key in state.review_baselines
            and key in result.nodes
            and fingerprint(result, key) != state.review_baselines[key]
        )
        for key in review_keys
    }
    return {"changed_keys": changed_keys, "review_keys": review_keys, "moves": moves, "local_before": local_before}


def _reaching(root: Path, documents: list[str], paths: set[str]) -> list[str]:
    """The documents among `documents` whose source closure includes one of `paths`: the ones a publish or a pull stamps."""
    out = []
    for document in documents:
        if (root / document).is_file() and set(closure_of(root, root / document)[0]) & paths:
            out.append(document)
    return out


def _stamp(
    quilt: Quilt, result: ScanResult, documents: list[str], name: str, message: str, actor: str | None
) -> list[str]:
    """Stamp each document as a landmark named `<stem> <name>`, refusing before any is written when one reaches a conflicted key."""
    from loom.history.ledger import load_history
    from loom.history.steps import slug, stamp_document

    for document in documents:
        conflicted = sorted(k for k, n in result.nodes.items() if n.kind == "conflict" and document in n.reached_by)
        if conflicted:
            raise SyncError(
                f"{document} reaches {', '.join(conflicted)}, defined by two files each, so it has no one text to stamp; `loom lint --nodes` shows them"
            )
    landmarks = []
    for document in documents:
        history = load_history(quilt.history_dir)
        landmark = base = slug(f"{Path(document).stem} {name}", limit=120)
        suffix = 2
        while history.landmark(landmark) is not None:
            landmark, suffix = f"{base}-{suffix}", suffix + 1
        stamp_document(result, history, document, landmark, message.format(document=document), actor)
        landmarks.append(landmark)
    return landmarks


def incorporate(quilt: Quilt, state: SyncState, actor: str | None = None) -> dict[str, Any]:
    """Apply the fetched pull to the quilt's files, stamping first each selected document it reaches.

    The landmark keeps each document as it was, uncommitted edits included, so nothing here needs a clean tree and nothing is committed. Mathematics is left for review; acceptance is a separate act.

    Parameters
    ----------
    quilt : Quilt
        The paired quilt.
    state : SyncState
        The sync record, with a fetched revision not yet incorporated; updated and written.
    actor : str, optional
        Who the stamps are recorded as; default the quilt's author.

    Returns
    -------
    dict
        `integrated` (the revision now incorporated), `paths` (the files written) and `landmarks` (one per stamped document).

    See Also
    --------
    pull_files : The same checks and result, writing nothing.
    """
    from loom.history.ledger import actor_for
    from loom.review_queue import fingerprint
    from loom.scan.scan import scan

    root = quilt.root
    after = pull_files(quilt, state)
    result = scan(quilt)
    review = _review(quilt, state, result)
    who = actor if actor is not None else actor_for(root)
    documents = _reaching(root, current_selection(state, result)[1], set(after))
    history_dir = quilt.history_dir
    touched = [
        root / ".loom/review-origins.json",
        root / ".loom/source-sync.json",
        root / "config.toml",
        history_dir / "ledger.jsonl",
        *(root / path for path in after),
    ]
    snapshots = {p: p.read_bytes() if p.is_file() else None for p in touched}
    kept = {e.name for e in history_dir.iterdir()} if history_dir.is_dir() else set()
    label = source_label(state.url)
    try:
        landmarks = _stamp(
            quilt,
            result,
            documents,
            f"before pull {state.incoming[:12]}",
            f"{{document}} before incorporating {label} {state.incoming[:12]}",
            who,
        )
        for path, data in after.items():
            target = root / path
            if data is None:
                target.unlink(missing_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        incorporated = scan(quilt)
        _record_moves(quilt, state, review["moves"], incorporated)
        state.last_pull = {
            "commit": state.incoming,
            "observed": state.observed,
            "keys": review["review_keys"],
            "changed": review["changed_keys"],
        }
        for key in review["review_keys"]:
            state.review_origins[key] = state.incoming
            state.review_changed[key] = key in review["changed_keys"]
            if key in incorporated.nodes:
                state.review_baselines[key] = fingerprint(incorporated, key)
            state.review_local_changed[key] = review["local_before"].get(key, False)
        state.integrated = state.incoming
        state.write(root)
    except Exception as exc:
        for file, content in snapshots.items():
            if content is None:
                file.unlink(missing_ok=True)
            else:
                file.write_bytes(content)
        if history_dir.is_dir():
            for made in (e for e in history_dir.iterdir() if e.name not in kept and e.is_dir()):
                shutil.rmtree(made)
        if isinstance(exc, ValueError):
            raise SyncError(str(exc)) from exc
        raise
    return {"integrated": state.integrated, "paths": sorted(after), "landmarks": landmarks}


@dataclass
class Publication:
    """What `publish` prepared: the workspace revision, the files it holds, and the landmarks stamped for it; `unchanged` when the workspace already holds exactly these files, `reused` when an earlier publish prepared and stamped them."""

    commit: str
    paths: list[str]
    landmarks: list[str]
    unchanged: bool = False
    reused: bool = False


def _identity(clone: Path, env: dict[str, str], actor: str | None) -> dict[str, str]:
    """`env` with a committer for loom's clone: the one Git is configured with, else the author's name."""
    try:
        git(clone, "var", "GIT_COMMITTER_IDENT", env=env)
        return env
    except SyncError:
        name = actor or "loom"
        return {
            **env,
            "GIT_AUTHOR_NAME": name,
            "GIT_COMMITTER_NAME": name,
            "GIT_AUTHOR_EMAIL": "loom@localhost",
            "GIT_COMMITTER_EMAIL": "loom@localhost",
        }


def publish(quilt: Quilt, state: SyncState, actor: str | None = None) -> Publication:
    """Prepare the selected documents' sources as one revision in loom's clone, and stamp each document as published.

    The files are the quilt's as they are on disk; every selected document must compile from them alone. The revision sits on the workspace's tip at `PUBLICATION_REF` until `push_publication` sends it. Preparing the same files again returns the revision already prepared and stamps nothing.

    Parameters
    ----------
    quilt : Quilt
        The paired quilt.
    state : SyncState
        The sync record; updated and written.
    actor : str, optional
        Who the stamps are recorded as; default the quilt's author.

    Returns
    -------
    Publication
        The prepared revision, or the workspace's tip with `unchanged` set when there is nothing to publish.
    """
    from loom.history.ledger import actor_for
    from loom.scan.scan import scan

    root = quilt.root
    clone = workspace(root)
    if state.incoming and state.incoming != state.integrated:
        raise SyncError(
            "an incoming revision is still awaiting incorporation; incorporate it in Incoming or with `loom sync incorporate` first"
        )
    remote_tip = revision(clone, f"refs/remotes/origin/{state.branch}")
    if remote_tip != state.integrated:
        raise SyncError(
            "the document workspace advanced; run `loom sync fetch` and review the new revision before publishing"
        )
    documents, projection = source_projection(quilt, state)
    files = {remote: (root / local).read_bytes() for local, remote in projection.items()}
    with tempfile.TemporaryDirectory(prefix="loom-source-sync-") as temporary:
        stage = Path(temporary)
        for path, data in files.items():
            dest = stage / "source" / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        for index, document in enumerate(documents):
            projected = projection[document]
            out = compile_tex(
                stage / "source",
                projected,
                stage / "build" / f"{index}-{Path(projected).stem}",
                quilt.config.engine,
            )
            if not out.ok:
                raise SyncError(f"the source-only document {document} does not compile: {out.first_error}")
        env = {**os.environ, "GIT_INDEX_FILE": str(stage / "source.index")}
        git(clone, "read-tree", "--empty", env=env)
        for path, data in files.items():
            blob = git(clone, "hash-object", "-w", "--stdin", input=data).decode().strip()
            git(clone, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git(clone, "write-tree", env=env).decode().strip()
        if tree == git(clone, "rev-parse", f"{remote_tip}^{{tree}}").decode().strip():
            return Publication(remote_tip, sorted(files), [], unchanged=True)
        if state.prepared:
            try:
                same = git(clone, "rev-parse", f"{state.prepared}^{{tree}}", f"{state.prepared}^").decode().split()
            except SyncError:
                same = []
            if same == [tree, remote_tip]:
                return Publication(state.prepared, sorted(files), state.prepared_landmarks, reused=True)
        who = actor if actor is not None else actor_for(root)
        commit = (
            git(
                clone,
                "commit-tree",
                tree,
                "-p",
                remote_tip,
                "-m",
                f"Publish {', '.join(documents)} from loom",
                env=_identity(clone, env, who),
            )
            .decode()
            .strip()
        )
    landmarks = _stamp(
        quilt,
        scan(quilt),
        documents,
        f"published {commit[:12]}",
        f"{{document}} as published to {source_label(state.url)} in {commit[:12]}",
        who,
    )
    git(clone, "update-ref", PUBLICATION_REF, commit)
    state.prepared = commit
    state.prepared_landmarks = landmarks
    state.write(root)
    return Publication(commit, sorted(files), landmarks)


def _record_moves(quilt: Quilt, state: SyncState, moves: list[dict[str, Any]], incorporated: ScanResult) -> None:
    """Append a `move` line (`via: "sync"`) for each exact rename the prepared pull carries whose new path is now a live document.

    Called once, when `finish_incorporation` first records the pull. Overleaf's main renamed takes `published_main` with it, so a publish keeps the collaborator's name, and moving the default document moves `[quilt] main`, as `loom mv` does.
    """
    from loom.history.ledger import actor_for, append_entry
    from loom.reshape.importer import set_main_forced

    for move in moves:
        if move["to"] not in incorporated.masters:
            continue
        append_entry(
            quilt.history_dir,
            "move",
            {"from": move["from"], "to": move["to"], "moved": False, "via": "sync"},
            actor_for(quilt.root),
        )
        if move["main"]:
            state.published_main = move["to"]
        if move["from"] == quilt.config.main:
            set_main_forced(quilt, move["to"])


def update_documents(quilt: Quilt, state: SyncState, action: str, document: str) -> SyncState:
    """Persist one additional live master in the source projection; never publish it."""
    from loom.scan.scan import scan

    path = Path(document)
    if path.is_absolute() or ".." in path.parts:
        raise SyncError(f"document has an unsafe path: {document}")
    current = list(dict.fromkeys(state.documents or [state.master]))
    if state.master not in current:
        current.insert(0, state.master)
    # the record keeps the paths it was written with; what each names now is what an author adds or removes
    result = scan(quilt)
    main, now = current_selection(state, result)
    if action == "add":
        if result.document_role(document) == "drafting-ai":
            raise SyncError(f"{document} is an agent's document, which is never published")
        if result.document_role(document) != "drafting":
            raise SyncError(f"{document} is not a live drafting document")
        if document not in now:
            current.append(document)
    elif action == "remove":
        if document == main:
            raise SyncError("the primary document workspace document cannot be removed")
        current = [item for item in current if item != document and result.current_document(item) != document]
    else:
        raise SyncError(f"unknown document action: {action}")
    state.documents = current
    state.write(quilt.root)
    return state


def summary(quilt: Quilt, state: SyncState) -> dict[str, Any]:
    target = state.incoming or state.integrated
    return {
        "url": state.url,
        "branch": state.branch,
        "prepared": state.prepared,
        "prepared_landmarks": state.prepared_landmarks,
        "documents": state.documents or [state.master],
        "integrated": state.integrated,
        "incoming": target,
        "observed": state.observed,
        "files": changed_files(workspace(quilt.root), state.integrated, target),
    }
