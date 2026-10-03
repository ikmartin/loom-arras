"""Atomic publish (book 9.2.2): fragments and assets first, each by write-then-rename, the manifest last by rename, so a viewer never reads a half-written state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def write_atomic(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if isinstance(data, str):
        tmp.write_text(data, encoding="utf-8")
    else:
        tmp.write_bytes(data)
    os.replace(tmp, path)


#: The paths each build directory's last publication in this process kept, and the prefixes it pruned.
_PATHS: dict[Path, tuple[frozenset[str], tuple[str, ...]]] = {}

#: What each build directory was last given, by relative path, in this process: a served quilt republishes every few seconds, and comparing with what is in memory spares reading back thousands of files that have not changed.
_WRITTEN: dict[Path, dict[str, str | bytes]] = {}


def _unchanged(path: Path, data: str | bytes, before: str | bytes | None = None) -> bool:
    """True when `path` already holds exactly `data`, so publishing it again would rewrite identical bytes.

    Most of a warm build's files are the same as last time (every source/ file, every re-rendered fragment whose text came out the same); comparing costs a read, rewriting costs a write and a rename. `before` is what this process last wrote there; when it matches, a file still present is taken as unchanged without reading it.
    """
    if before is not None and before == data and path.exists():
        return True
    try:
        return path.read_bytes() == (data.encode("utf-8") if isinstance(data, str) else data)
    except OSError:
        return False


def publish(
    build_dir: Path,
    files: dict[str, str | bytes],
    manifest: dict[str, Any],
    prune_prefixes: tuple[str, ...] = (),
    keep: set[str] | frozenset[str] = frozenset(),
) -> None:
    """Write every file in `files` (paths relative to build/) whose bytes differ from what is there, remove stale files under `prune_prefixes` that are in neither `files` nor `keep`, then the manifest.

    Parameters
    ----------
    build_dir : Path
        The build directory every path is relative to.
    files : dict[str, str | bytes]
        Relative path to content; str is written as UTF-8.
    manifest : dict[str, Any]
        Written last, always, as `manifest.json`.
    prune_prefixes : tuple[str, ...], default ()
        Directories whose files not named in `files` or `keep` are removed; () prunes nothing.
    keep : set[str], default empty
        Relative paths already on disk as they should be: neither written nor pruned.
    """
    written = _WRITTEN.setdefault(build_dir.resolve(), {})
    for rel, data in files.items():
        path = build_dir / rel
        if not _unchanged(path, data, written.get(rel)):
            write_atomic(path, data)
        written[rel] = data
    # the same paths as this process's last publication here: nothing it did not write can be under the prefixes, so there is nothing to walk for
    published = (frozenset((*files, *keep)), prune_prefixes)
    last = _PATHS.get(build_dir.resolve())
    _PATHS[build_dir.resolve()] = published
    if last == published:
        prune_prefixes = ()
    for prefix in prune_prefixes:
        base = build_dir / prefix
        if base.is_dir():
            kept = {rel for rel in (*files, *keep) if rel.startswith(prefix)}
            for p in base.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(build_dir).as_posix()
                    if rel not in kept and not rel.endswith(".tmp"):
                        p.unlink()
    write_atomic(build_dir / "manifest.json", json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False))
