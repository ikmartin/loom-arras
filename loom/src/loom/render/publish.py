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


def publish(
    build_dir: Path, files: dict[str, str | bytes], manifest: dict[str, Any], prune_prefixes: tuple[str, ...] = ()
) -> None:
    """Write every file in `files` (paths relative to build/), remove stale files under `prune_prefixes` not in `files`, then the manifest."""
    for rel, data in files.items():
        write_atomic(build_dir / rel, data)
    for prefix in prune_prefixes:
        base = build_dir / prefix
        if base.is_dir():
            keep = {rel for rel in files if rel.startswith(prefix)}
            for p in base.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(build_dir).as_posix()
                    if rel not in keep and not rel.endswith(".tmp"):
                        p.unlink()
    write_atomic(build_dir / "manifest.json", json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False))
