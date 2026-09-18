"""Bringing a quilt's records to the current layout (book 17.16, DR-132): `.loom/snapshots/` becomes `<history>/texts/`, and `[quilt] drafts` is renamed `drafting` in `config.toml`. Idempotent; called by `loom upgrade`."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from loom.history.ledger import TEXTS

_DRAFTS_KEY = re.compile(r"^(\s*)drafts(\s*=)", re.M)


@dataclass
class HistoryMigration:
    moved: list[str] = field(default_factory=list)  # snapshot files moved into texts/
    renamed: bool = False  # `drafts` -> `drafting` in config.toml

    @property
    def done(self) -> bool:
        return bool(self.moved or self.renamed)


def migrate_history(root: Path, history_dir: Path) -> HistoryMigration:
    rep = HistoryMigration()
    old = root / ".loom" / "snapshots"
    if old.is_dir():
        texts = history_dir / TEXTS
        texts.mkdir(parents=True, exist_ok=True)
        for p in sorted(old.glob("*.tex")):
            target = texts / p.name
            if target.exists():
                p.unlink()  # content-addressed: the same bytes are already there
            else:
                shutil.move(str(p), str(target))
            rep.moved.append(p.name)
        try:
            old.rmdir()
        except OSError:
            pass
    cfg = root / "config.toml"
    if cfg.is_file():
        text = cfg.read_text(encoding="utf-8")
        if _DRAFTS_KEY.search(text) and not re.search(r"^\s*drafting\s*=", text, re.M):
            cfg.write_text(_DRAFTS_KEY.sub(r"\1drafting\2", text, count=1), encoding="utf-8")
            rep.renamed = True
    return rep
