"""The ledger `.loom/state.toml`: acceptance rows, appended only, written only by `loom accept` (book 7.2).

The writer emits the book's exact `[[accept]]` block so git merges of concurrent appends to different keys are clean; the reader uses tomllib. Nothing here edits or removes a row.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

HEADER = "# .loom/state.toml -- written by `loom accept`. Do not edit.\nschema = 1\n"


@dataclass
class AcceptRow:
    key: str
    author: str
    date: str  # ISO 8601 UTC, e.g. 2026-09-16T14:02:11Z
    text: str
    preamble: str
    master: str
    closure: dict[str, str] = field(default_factory=dict)

    def to_toml(self) -> str:
        lines = [
            "[[accept]]",
            f"key = {_q(self.key)}",
            f"author = {_q(self.author)}",
            f"date = {self.date}",
            f"text = {_q(self.text)}",
            f"preamble = {_q(self.preamble)}",
            f"master = {_q(self.master)}",
            "[accept.closure]",
        ]
        for k, v in self.closure.items():
            lines.append(f"{_q(k)} = {_q(v)}")
        return "\n".join(lines) + "\n"


def _q(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def ledger_path(root: Path) -> Path:
    return root / ".loom" / "state.toml"


def read_ledger(root: Path) -> list[AcceptRow]:
    p = ledger_path(root)
    if not p.is_file():
        return []
    data = tomllib.loads(p.read_text(encoding="utf-8"))
    rows: list[AcceptRow] = []
    for r in data.get("accept", []):
        date = r.get("date")
        if hasattr(date, "strftime"):
            date = date.strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append(
            AcceptRow(
                key=str(r.get("key", "")),
                author=str(r.get("author", "")),
                date=str(date or ""),
                text=str(r.get("text", "")),
                preamble=str(r.get("preamble", "")),
                master=str(r.get("master", "")),
                closure={str(k): str(v) for k, v in dict(r.get("closure", {})).items()},
            )
        )
    return rows


def append_rows(root: Path, rows: list[AcceptRow]) -> None:
    p = ledger_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = p.read_text(encoding="utf-8") if p.is_file() else ""
    with p.open("a", encoding="utf-8") as fh:
        if not existing:
            fh.write(HEADER)
        for row in rows:
            fh.write("\n" + row.to_toml())


def latest_rows(rows: list[AcceptRow]) -> dict[str, AcceptRow]:
    """The last row per key; earlier rows are history."""
    out: dict[str, AcceptRow] = {}
    for r in rows:
        out[r.key] = r
    return out
