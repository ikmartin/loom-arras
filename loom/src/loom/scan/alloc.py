"""Id allocation (book 5.3.2): the set of local parts anything can point at, recomputed on every call; nothing is stored."""

from __future__ import annotations

import re
import subprocess

from loom.scan.labels import LOOMLOCAL
from loom.scan.scan import ScanResult


def visible_locals(result: ScanResult, prefix: str) -> set[str]:
    """Every local part under `prefix` that anything can point at: ids in source, the acceptance ledger's keys, the history ledger's keys and every file name under its steps (an id the history has recorded is never allocated again, book 17.14), annotation targets, references anywhere (dangling included), and git history."""
    pat = re.compile(r"\b" + re.escape(prefix) + r"-([0-9A-Z]{4})\b")
    found: set[str] = set()
    for src in result.files.values():
        found.update(pat.findall(src.text))
    root = result.quilt.root
    ledger = root / ".loom" / "state.toml"
    if ledger.is_file():
        found.update(pat.findall(ledger.read_text(encoding="utf-8", errors="replace")))
    history = result.quilt.history_dir
    if (history / "ledger.jsonl").is_file():
        found.update(pat.findall((history / "ledger.jsonl").read_text(encoding="utf-8", errors="replace")))
        for step in history.iterdir():
            if step.is_dir() and step.name != "texts":
                found.update(pat.findall(" ".join(p.name for p in step.iterdir())))
    log = root / "annotations" / "log.jsonl"
    if log.is_file():
        found.update(pat.findall(log.read_text(encoding="utf-8", errors="replace")))
    try:
        revs = subprocess.run(
            ["git", "-C", str(root), "rev-list", "--all", "--max-count=500"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=20,
            check=False,
        )
        if revs.returncode == 0 and revs.stdout.strip():
            out = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "grep",
                    "-h",
                    "-o",
                    "-E",
                    rf"\b{re.escape(prefix)}-[0-9A-Z]{{4}}\b",
                    *revs.stdout.split(),
                ],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
                check=False,
            )
            found.update(pat.findall(out.stdout))
    except (OSError, subprocess.SubprocessError):
        pass
    return {x for x in found if LOOMLOCAL.match(x)}
