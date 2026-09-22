"""The source-only Git bridge for an Overleaf-backed quilt.

The quilt branch owns Loom's records.  The remote branch owns only the files
needed to compile the selected master.  Git transports both histories; Loom
never merges into, or writes, an author's drafting files.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
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

    @classmethod
    def read(cls, root: Path) -> SyncState:
        path = root / ".loom" / "source-sync.json"
        if not path.is_file():
            raise SyncError("source sync is not configured; run `loom sync init` first")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(**data)
        except (ValueError, TypeError) as exc:
            raise SyncError(f"{path} is not a valid source-sync record") from exc

    def write(self, root: Path) -> None:
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


def source_paths(quilt: Quilt) -> list[str]:
    """The master closure, not a broad extension-based copy of the quilt."""
    root = quilt.root
    master = quilt.config.main
    if not master or not (root / master).is_file():
        raise SyncError("the configured main drafting document is missing")
    found, outside = closure_of(root, root / master)
    if outside:
        raise SyncError("the document reaches files outside the quilt: " + ", ".join(outside))
    return sorted(found)


def configure(quilt: Quilt, remote: str, branch: str, published_main: str = "") -> SyncState:
    root = quilt.root
    top = Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != root.resolve():
        raise SyncError("the quilt must be at the root of its Git repository")
    git(root, "remote", "get-url", remote)
    upstream = revision(root, f"refs/remotes/{remote}/{branch}")
    if published_main and (Path(published_main).is_absolute() or ".." in Path(published_main).parts):
        raise SyncError("the Overleaf main path must stay within the project")
    state = SyncState(
        remote=remote,
        branch=branch,
        master=quilt.config.main,
        integrated=upstream,
        published_main=published_main or quilt.config.main,
    )
    state.write(root)
    return state


def fetch(quilt: Quilt, state: SyncState) -> SyncState:
    root = quilt.root
    git(root, "fetch", "--no-tags", state.remote, state.branch)
    new = revision(root, "FETCH_HEAD")
    # Keep a ref to the reviewed object even when a later fetch moves FETCH_HEAD.
    git(root, "update-ref", f"refs/loom/incoming/{new}", new)
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


def mark_incorporated(quilt: Quilt, state: SyncState) -> SyncState:
    if not state.incoming or state.incoming == state.integrated:
        raise SyncError("there is no incoming revision to mark incorporated")
    # This is an author assertion about source incorporation, never a mathematical acceptance.
    git(quilt.root, "diff", "--quiet", "HEAD", "--", *source_paths(quilt))
    state.integrated = state.incoming
    state.local_commit = revision(quilt.root, "HEAD")
    state.write(quilt.root)
    return state


def publish(quilt: Quilt, state: SyncState, *, push: bool) -> tuple[str, list[str]]:
    """Commit a clean source projection on the remote lineage and optionally push it.

    A temporary Git index builds the source tree from HEAD blobs.  It never
    stages a quilt file or modifies the current index or working directory.
    """
    root = quilt.root
    if state.incoming and state.incoming != state.integrated:
        raise SyncError("an incoming revision is still awaiting incorporation")
    remote_tip = revision(root, f"refs/remotes/{state.remote}/{state.branch}")
    if remote_tip != state.integrated:
        raise SyncError("Overleaf advanced; fetch and review the new revision before publishing")
    paths = source_paths(quilt)
    blobs: dict[str, str] = {}
    for path in paths:
        blob = git(root, "rev-parse", "--verify", f"HEAD:{path}").decode().strip()
        if (root / path).read_bytes() != git(root, "show", f"HEAD:{path}"):
            raise SyncError(f"{path} has uncommitted edits; commit them before publishing")
        projected = state.published_main if path == state.master else path
        if projected in blobs:
            raise SyncError(f"two quilt files would publish as {projected}")
        blobs[projected] = blob
    with tempfile.TemporaryDirectory(prefix="loom-source-sync-") as temporary:
        stage = Path(temporary)
        for path, blob in blobs.items():
            dest = stage / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(git(root, "cat-file", "blob", blob))
        out = compile_tex(stage, state.published_main, stage / "build", quilt.config.engine)
        if not out.ok:
            raise SyncError(f"the source-only document does not compile: {out.first_error}")
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
                f"Publish Loom source from {revision(root, 'HEAD')[:12]}",
            )
            .decode()
            .strip()
        )
    if push:
        git(root, "push", state.remote, f"{source_commit}:refs/heads/{state.branch}")
        git(root, "update-ref", f"refs/remotes/{state.remote}/{state.branch}", source_commit)
        state.integrated = source_commit
        state.incoming = source_commit
        state.observed = stamp()
        state.local_commit = revision(root, "HEAD")
        state.write(root)
    return source_commit, sorted(blobs)


def summary(quilt: Quilt, state: SyncState) -> dict[str, Any]:
    target = state.incoming or state.integrated
    return {
        "remote": state.remote,
        "branch": state.branch,
        "integrated": state.integrated,
        "incoming": target,
        "observed": state.observed,
        "files": changed_files(quilt.root, state.integrated, target),
    }
