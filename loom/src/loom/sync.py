"""The source-only Git bridge for an Overleaf-backed quilt.

The quilt branch owns Loom's records.  The remote branch owns only the files needed to compile the selected master.  Git transports both histories.  The one operation that writes author files is an explicit, locally served
``Incorporate pull`` action: it applies the exact reviewed patch and records
two local commits, without pushing or accepting mathematics.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loom.clock import stamp
from loom.reshape.importer import closure_of
from loom.scan.quilt import Quilt
from loom.tex.runner import compile_tex


class SyncError(Exception):
    """A sync precondition failed without changing the quilt source."""


@dataclass
class SyncState:
    remote: str
    branch: str
    master: str
    integrated: str
    incoming: str = ""
    observed: str = ""
    local_commit: str = ""
    published_main: str = ""
    last_pull: dict[str, Any] = field(default_factory=dict)
    review_origins: dict[str, str] = field(default_factory=dict)
    review_changed: dict[str, bool] = field(default_factory=dict)
    review_baselines: dict[str, str] = field(default_factory=dict)
    review_local_changed: dict[str, bool] = field(default_factory=dict)
    documents: list[str] = field(default_factory=list)
    prepared: str = ""
    prepared_from: str = ""
    publication_ref: str = "refs/loom/publication"

    @classmethod
    def read(cls, root: Path) -> SyncState:
        path = root / ".loom" / "source-sync.json"
        if not path.is_file():
            raise SyncError("document workspace is not configured; run `loom sync init` first")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = cls(**data)
            if not state.documents:
                state.documents = [state.master]
            elif state.master not in state.documents:
                state.documents.insert(0, state.master)
            return state
        except (ValueError, TypeError) as exc:
            raise SyncError(f"{path} is not a valid source-sync record") from exc

    def write(self, root: Path) -> None:
        if self.master not in self.documents:
            self.documents.insert(0, self.master)
        path = root / ".loom" / "source-sync.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(vars(self), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)


def git(root: Path, *args: str, env: dict[str, str] | None = None, input: bytes | None = None) -> bytes:
    try:
        run = subprocess.run(["git", *args], cwd=root, env=env, input=input, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise SyncError("Git is required for source sync") from exc
    if run.returncode:
        detail = run.stderr.decode("utf-8", errors="replace").strip()
        raise SyncError(f"git {' '.join(args)}: {detail or f'exited {run.returncode}'}")
    return run.stdout


def revision(root: Path, ref: str) -> str:
    return git(root, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()


def selected_documents(quilt: Quilt, state: SyncState) -> list[str]:
    """Validate and return the persistent source-projection document selection."""
    from loom.scan.scan import scan

    documents = list(dict.fromkeys(state.documents or [state.master]))
    if state.master not in documents:
        documents.insert(0, state.master)
    live = set(scan(quilt).masters)
    for document in documents:
        path = Path(document)
        if path.is_absolute() or ".." in path.parts:
            raise SyncError(f"selected document has an unsafe path: {document}")
        if document not in live:
            raise SyncError(f"selected document is not a live drafting document: {document}")
    return documents


def source_projection(quilt: Quilt, state: SyncState) -> tuple[list[str], dict[str, str]]:
    """Selected masters and their union of local-to-remote source paths."""
    root = quilt.root
    documents = selected_documents(quilt, state)
    projected: dict[str, str] = {}
    remote_sources: dict[str, str] = {}
    for document in documents:
        found, outside = closure_of(root, root / document)
        if outside:
            raise SyncError(f"{document} reaches files outside the quilt: " + ", ".join(outside))
        for local in found:
            remote = state.published_main if local == state.master else local
            previous = remote_sources.get(remote)
            if previous is not None and previous != local:
                raise SyncError(f"two quilt files would publish as {remote}: {previous}, {local}")
            remote_sources[remote] = local
            projected[local] = remote
    return documents, projected


def source_paths(quilt: Quilt, state: SyncState) -> list[str]:
    """Every committed source path in the selected document projection."""
    return sorted(source_projection(quilt, state)[1])


def configure(quilt: Quilt, remote: str, branch: str, published_main: str = "") -> SyncState:
    root = quilt.root
    top = Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != root.resolve():
        raise SyncError("the quilt must be at the root of its Git repository")
    git(root, "remote", "get-url", remote)
    upstream = revision(root, f"refs/remotes/{remote}/{branch}")
    if published_main and (Path(published_main).is_absolute() or ".." in Path(published_main).parts):
        raise SyncError("the document workspace main path must stay within the project")
    state = SyncState(
        remote=remote,
        branch=branch,
        master=quilt.config.main,
        integrated=upstream,
        published_main=published_main or quilt.config.main,
        documents=[quilt.config.main],
    )
    state.write(root)
    return state


def fetch(quilt: Quilt, state: SyncState) -> SyncState:
    root = quilt.root
    git(root, "fetch", "--no-tags", state.remote, state.branch)
    new = revision(root, "FETCH_HEAD")
    # Keep a ref to the reviewed object even when a later fetch moves FETCH_HEAD.
    git(root, "update-ref", f"refs/loom/incoming/{new}", new)
    if state.prepared and new == state.prepared:
        state.integrated = new
        state.local_commit = state.prepared_from
    if new != state.incoming:
        state.incoming = new
        state.observed = stamp()
    state.write(root)
    return state


def changed_files(root: Path, before: str, after: str) -> list[dict[str, str]]:
    if before == after:
        return []
    raw = git(root, "diff", "--name-status", "--no-renames", "-z", before, after)
    parts = raw.decode("utf-8", errors="replace").split("\0")
    return [{"status": parts[i], "path": parts[i + 1]} for i in range(0, len(parts) - 1, 2)]


def tree_files(root: Path, commit: str) -> dict[str, bytes]:
    names = git(root, "ls-tree", "-r", "--name-only", "-z", commit).split(b"\0")
    return {name.decode("utf-8"): git(root, "show", f"{commit}:{name.decode('utf-8')}") for name in names if name}


def incoming_patch(quilt: Quilt, state: SyncState) -> bytes:
    if not state.incoming or state.incoming == state.integrated:
        return b""
    # The remote is source-only, and collaborators may add a new input that
    # cannot yet be in the local master closure.
    patch = git(quilt.root, "diff", "--binary", "--no-renames", state.integrated, state.incoming)
    if state.published_main != state.master:
        old = state.published_main.encode()
        new = state.master.encode()
        rewritten = []
        for line in patch.splitlines(keepends=True):
            if line.startswith((b"diff --git ", b"--- ", b"+++ ")):
                line = line.replace(b"a/" + old, b"a/" + new).replace(b"b/" + old, b"b/" + new)
            rewritten.append(line)
        patch = b"".join(rewritten)
    return patch


def _incoming_paths(quilt: Quilt, state: SyncState) -> list[str]:
    paths = [
        state.master if row["path"] == state.published_main else row["path"]
        for row in changed_files(quilt.root, state.integrated, state.incoming)
    ]
    if len(paths) != len(set(paths)) or any(Path(p).is_absolute() or ".." in Path(p).parts for p in paths):
        raise SyncError("incoming source contains an unsafe or duplicate path")
    return paths


def _prepared_path(root: Path, incoming: str) -> Path:
    return root / "build" / "incoming" / f"{incoming}.json"


def prepare_incorporation(quilt: Quilt, state: SyncState) -> dict[str, Any]:
    """Preflight one pinned pull and save its exact checked transaction."""
    root = quilt.root
    if not state.incoming or state.incoming == state.integrated:
        raise SyncError("there is no incoming revision to incorporate")
    paths = _incoming_paths(quilt, state)
    if not paths:
        raise SyncError("the incoming revision changes no files")
    patch = incoming_patch(quilt, state)
    if not patch:
        raise SyncError("the incoming patch is empty")
    git(root, "diff", "--cached", "--quiet")
    git(root, "diff", "--quiet", "HEAD", "--", *paths)
    for row in changed_files(root, state.integrated, state.incoming):
        path = state.master if row["path"] == state.published_main else row["path"]
        if row["status"].startswith("A") and (root / path).exists():
            raise SyncError(f"{path} already exists locally; reconcile it before incorporation")
    git(root, "apply", "--check", "-", input=patch)
    git(root, "var", "GIT_AUTHOR_IDENT")
    git(root, "var", "GIT_COMMITTER_IDENT")
    head = revision(root, "HEAD")
    home = root / "build" / "incoming"
    home.mkdir(parents=True, exist_ok=True)
    patch_path = home / f"{state.incoming}.patch"
    patch_path.write_bytes(patch)
    prepared: dict[str, Any] = {
        "base": state.integrated,
        "incoming": state.incoming,
        "head": head,
        "patch_sha256": hashlib.sha256(patch).hexdigest(),
        "paths": paths,
    }
    from loom.render.build import build

    manifest = build(quilt).manifest
    incoming_review = manifest.get("incoming") or {}
    if incoming_review.get("commit") != state.incoming:
        raise SyncError("the incoming review changed; refresh and prepare again")
    prepared["changed_keys"] = [change["key"] for change in incoming_review.get("changes", [])]
    prepared["review_keys"] = sorted(
        set(prepared["changed_keys"])
        | {
            dependent["key"]
            for change in incoming_review.get("changes", [])
            for dependent in change.get("affected", [])
        }
    )
    from loom.review_queue import fingerprint
    from loom.scan.scan import scan

    current = scan(quilt)
    prepared["local_before"] = {
        key: state.review_local_changed.get(key, False)
        or (
            key in state.review_baselines
            and key in current.nodes
            and fingerprint(current, key) != state.review_baselines[key]
        )
        for key in prepared["review_keys"]
    }
    _prepared_path(root, state.incoming).write_text(json.dumps(prepared, indent=2) + "\n", encoding="utf-8")
    return {**prepared, "patch": str(patch_path), "root": str(root)}


def incorporate_pull(quilt: Quilt, state: SyncState) -> dict[str, Any]:
    """Apply one reviewed pull and record its two local commits.

    Preparation checks every condition before this function changes an author
    file.  A failed ``git apply --check`` therefore leaves the source alone.
    The saved transaction also makes a retry able to complete the private sync commit if the source commit was already made.
    """
    root = quilt.root
    requested = state.incoming
    if not requested:
        raise SyncError("there is no incoming revision to incorporate")
    if state.integrated == requested:
        return finish_incorporation(quilt, state)

    prepared = prepare_incorporation(quilt, state)
    patch_path = root / "build" / "incoming" / f"{requested}.patch"
    patch = patch_path.read_bytes()
    try:
        # prepare_incorporation has already run --check against the same pinned
        # bytes.  Do not request a three-way merge: a conflict must stop before
        # Git writes conflict markers into an author file.
        git(root, "apply", "-", input=patch)
        return finish_incorporation(quilt, state)
    except SyncError:
        # If no commit was made, every affected path was clean at preflight and
        # can be restored to the pinned HEAD.  Once the source commit exists,
        # keep it: finish_incorporation is deliberately resumable and will
        # complete the private sync-record commit on retry.
        if revision(root, "HEAD") == prepared["head"]:
            present = set(tree_files(root, prepared["head"]))
            existing = [path for path in prepared["paths"] if path in present]
            if existing:
                git(root, "restore", "--worktree", "--source", prepared["head"], "--", *existing)
            for path in set(prepared["paths"]) - present:
                candidate = root / path
                if candidate.exists() and candidate.is_file():
                    candidate.unlink()
        raise


def _expected_blobs(root: Path, head: str, patch: bytes, paths: list[str]) -> dict[str, str | None]:
    """Apply the reviewed patch to a temporary Git index, never to author files."""
    with tempfile.TemporaryDirectory(prefix="loom-incoming-index-") as temp:
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(Path(temp) / "index")
        git(root, "read-tree", head, env=env)
        git(root, "apply", "--cached", "-", env=env, input=patch)
        out: dict[str, str | None] = {}
        for path in paths:
            try:
                out[path] = git(root, "rev-parse", f":{path}", env=env).decode().strip()
            except SyncError:
                out[path] = None
        return out


def finish_incorporation(quilt: Quilt, state: SyncState) -> dict[str, Any]:
    """Verify the author's Git application, then commit source and private sync metadata."""
    root = quilt.root
    if not state.incoming:
        raise SyncError("there is no prepared incoming revision")
    record = _prepared_path(root, state.incoming)
    if not record.is_file():
        raise SyncError("prepare this incoming revision before finishing")
    prepared = json.loads(record.read_text(encoding="utf-8"))
    paths = prepared["paths"]
    patch_path = root / "build" / "incoming" / f"{state.incoming}.patch"
    patch = patch_path.read_bytes()
    if prepared["incoming"] != state.incoming or (
        prepared["base"] != state.integrated and state.integrated != state.incoming
    ):
        raise SyncError("the incoming revision changed; prepare it again")
    if hashlib.sha256(patch).hexdigest() != prepared["patch_sha256"]:
        raise SyncError("the prepared patch changed; prepare it again")
    expected = _expected_blobs(root, prepared["head"], patch, paths)
    for path, blob in expected.items():
        actual = root / path
        if blob is None:
            if actual.exists():
                raise SyncError(f"{path} should have been removed by the patch")
        elif (
            actual.is_symlink() or not actual.is_file() or git(root, "hash-object", "--", path).decode().strip() != blob
        ):
            raise SyncError(f"{path} does not match the reviewed pull; apply the prepared patch exactly")
    head = revision(root, "HEAD")
    if state.integrated == state.incoming and state.local_commit and head != state.local_commit:
        if revision(root, "HEAD^") == state.local_commit and git(
            root, "diff", "--name-only", "HEAD^", "HEAD"
        ).decode().splitlines() == [".loom/source-sync.json"]:
            return {
                "source_commit": state.local_commit,
                "sync_commit": head,
                "integrated": state.integrated,
                "paths": paths,
            }
    if head == prepared["head"]:
        git(root, "diff", "--cached", "--quiet")
        git(root, "add", "--", *paths)
        git(
            root,
            "commit",
            "-m",
            f"Incorporate source from {state.remote}/{state.branch} {state.incoming[:12]}",
            "--",
            *paths,
        )
        head = revision(root, "HEAD")
    else:
        if revision(root, "HEAD^") != prepared["head"]:
            raise SyncError("local Git history changed after preparation; reconcile before finishing")
        committed = sorted(git(root, "diff", "--name-only", "HEAD^", "HEAD").decode().splitlines())
        if committed != sorted(paths) or not git(root, "log", "-1", "--format=%s").decode().startswith(
            "Incorporate source from "
        ):
            raise SyncError("the commit after preparation is not Loom's source incorporation commit")
    if state.integrated != state.incoming:
        from loom.review_queue import fingerprint
        from loom.scan.scan import scan

        incorporated = scan(quilt)
        state.integrated = state.incoming
        state.local_commit = head
        state.last_pull = {
            "commit": state.incoming,
            "observed": state.observed,
            "keys": prepared["review_keys"],
            "changed": prepared["changed_keys"],
        }
        for key in prepared["review_keys"]:
            state.review_origins[key] = state.incoming
            state.review_changed[key] = key in prepared["changed_keys"]
            if key in incorporated.nodes:
                state.review_baselines[key] = fingerprint(incorporated, key)
            state.review_local_changed[key] = prepared.get("local_before", {}).get(key, False)
        state.write(root)
    if git(root, "status", "--porcelain", "--", ".loom/source-sync.json").strip():
        git(root, "add", "--", ".loom/source-sync.json")
        git(
            root,
            "commit",
            "-m",
            f"Record incorporated {state.remote}/{state.branch} revision {state.incoming[:12]}",
            "--",
            ".loom/source-sync.json",
        )
    return {
        "source_commit": head,
        "sync_commit": revision(root, "HEAD"),
        "integrated": state.integrated,
        "paths": paths,
    }


def mark_incorporated(quilt: Quilt, state: SyncState) -> SyncState:
    if not state.incoming or state.incoming == state.integrated:
        raise SyncError("there is no incoming revision to mark incorporated")
    # This is an author assertion about source incorporation, never a mathematical acceptance.
    git(quilt.root, "diff", "--quiet", "HEAD", "--", *source_paths(quilt, state))
    state.integrated = state.incoming
    state.local_commit = revision(quilt.root, "HEAD")
    state.write(quilt.root)
    return state


def publish(quilt: Quilt, state: SyncState) -> tuple[str, list[str]]:
    """Prepare a validated document workspace revision at a stable local ref.

    A temporary Git index builds the source tree from committed blobs. It never stages quilt source or modifies the current index or author files; only the local publication ref and sync record are updated.
    """
    root = quilt.root
    if state.incoming and state.incoming != state.integrated:
        raise SyncError("an incoming revision is still awaiting incorporation")
    remote_tip = revision(root, f"refs/remotes/{state.remote}/{state.branch}")
    if remote_tip != state.integrated:
        raise SyncError("Document workspace advanced; fetch and review the new revision before publishing")
    quilt_commit = revision(root, "HEAD")
    # Discover the closure from committed content, so a deleted or edited input cannot hide a required file.
    with tempfile.TemporaryDirectory(prefix="loom-committed-source-") as temporary:
        snapshot = Path(temporary)
        for path, content in tree_files(root, quilt_commit).items():
            dest = snapshot / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        documents, projection = source_projection(Quilt(snapshot, quilt.config), state)
    for path in ["config.toml", *projection]:
        committed = git(root, "show", f"{quilt_commit}:{path}")
        if not (root / path).is_file() or (root / path).read_bytes() != committed:
            raise SyncError(f"{path} has uncommitted edits; commit them before publishing")
        if git(root, "diff", "--cached", "--name-only", quilt_commit, "--", path).strip():
            raise SyncError(f"{path} has uncommitted staged edits; commit them before publishing")
    # An untracked input may shadow an installed TeX package; it must not silently disappear from the projection.
    _, live_projection = source_projection(quilt, state)
    for path in live_projection.keys() - projection.keys():
        raise SyncError(f"{path} is not committed; commit it before publishing")
    blobs: dict[str, str] = {}
    for path, projected in projection.items():
        try:
            blob = git(root, "rev-parse", "--verify", f"{quilt_commit}:{path}").decode().strip()
        except SyncError as exc:
            raise SyncError(f"{path} is not committed; commit it before publishing") from exc
        if (root / path).read_bytes() != git(root, "show", f"{quilt_commit}:{path}"):
            raise SyncError(f"{path} has uncommitted edits; commit them before publishing")
        if projected in blobs:
            raise SyncError(f"two quilt files would publish as {projected}")
        blobs[projected] = blob
    with tempfile.TemporaryDirectory(prefix="loom-source-sync-") as temporary:
        stage = Path(temporary)
        for path, blob in blobs.items():
            dest = stage / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(git(root, "cat-file", "blob", blob))
        for index, document in enumerate(documents):
            projected = projection[document]
            out = compile_tex(
                stage,
                projected,
                stage / "build" / f"{index}-{Path(projected).stem}",
                quilt.config.engine,
            )
            if not out.ok:
                raise SyncError(f"the source-only document {document} does not compile: {out.first_error}")
        env = dict(os.environ)
        env["GIT_INDEX_FILE"] = str(stage / "source.index")
        git(root, "read-tree", "--empty", env=env)
        for path, blob in blobs.items():
            git(root, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git(root, "write-tree", env=env).decode().strip()
        source_commit = (
            git(
                root,
                "commit-tree",
                tree,
                "-p",
                remote_tip,
                "-m",
                f"Publish Loom source from {quilt_commit}",
            )
            .decode()
            .strip()
        )
    git(root, "update-ref", state.publication_ref, source_commit)
    state.prepared = source_commit
    state.prepared_from = quilt_commit
    state.write(root)
    return source_commit, sorted(blobs)


def update_documents(quilt: Quilt, state: SyncState, action: str, document: str) -> SyncState:
    """Persist one additional live master in the source projection; never commit or publish it."""
    from loom.scan.scan import scan

    path = Path(document)
    if path.is_absolute() or ".." in path.parts:
        raise SyncError(f"document has an unsafe path: {document}")
    current = list(dict.fromkeys(state.documents or [state.master]))
    if state.master not in current:
        current.insert(0, state.master)
    if action == "add":
        live = set(scan(quilt).masters)
        if document not in live:
            raise SyncError(f"{document} is not a live drafting document")
        if document not in current:
            current.append(document)
    elif action == "remove":
        if document == state.master:
            raise SyncError("the primary document workspace document cannot be removed")
        current = [item for item in current if item != document]
    else:
        raise SyncError(f"unknown document action: {action}")
    state.documents = current
    state.write(quilt.root)
    return state


def summary(quilt: Quilt, state: SyncState) -> dict[str, Any]:
    target = state.incoming or state.integrated
    return {
        "prepared": state.prepared,
        "prepared_from": state.prepared_from,
        "publication_ref": state.publication_ref,
        "documents": state.documents or [state.master],
        "remote": state.remote,
        "branch": state.branch,
        "integrated": state.integrated,
        "incoming": target,
        "observed": state.observed,
        "files": changed_files(quilt.root, state.integrated, target),
    }
