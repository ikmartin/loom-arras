"""Dataclasses shared by every scanner stage (book chapter 5 vocabulary).

Offsets are character offsets into a file's decoded text; comments are blanked, never removed, so offsets in `clean` equal offsets in `text`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, order=True)
class Span:
    """Half-open [start, end) character range in one quilt-relative file."""

    file: str
    start: int
    end: int

    def __len__(self) -> int:
        return self.end - self.start


@dataclass
class SourceFile:
    """One scanned file: `text` as decoded, `clean` with every comment replaced by spaces of equal length."""

    path: str
    abspath: Path
    text: str
    clean: str
    encoding: str
    ignored: bool
    line_starts: list[int] = field(default_factory=list)
    superseded: str | None = (
        None  # the ledger action whose output replaced this document, which then defines nothing (book 17.12)
    )

    def line_of(self, offset: int) -> int:
        """1-based line containing `offset`."""
        lo, hi = 0, len(self.line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.line_starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def col_of(self, offset: int) -> int:
        return offset - self.line_starts[self.line_of(offset) - 1] + 1

    def slice(self, span: Span) -> str:
        return self.text[span.start : span.end]


@dataclass(frozen=True)
class Location:
    file: str
    line: int
    column: int | None = None


@dataclass(frozen=True)
class Fix:
    """A command that would resolve a diagnostic, offered to be copied; nothing runs it (docs/specs/diagnostics.md §1)."""

    label: str
    command: str


@dataclass
class Diagnostic:
    severity: str
    code: str
    message: str
    locations: list[Location] = field(default_factory=list)
    keys: list[str] = field(default_factory=list)
    fixes: list[Fix] = field(default_factory=list)
    subject: str | None = None  # "source" (the default when absent) or "record": what the diagnostic is about

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "locations": [
                {"file": loc.file, "line": loc.line, **({"column": loc.column} if loc.column is not None else {})}
                for loc in self.locations
            ],
            "keys": list(self.keys),
        }
        if self.fixes:
            out["fixes"] = [{"label": f.label, "command": f.command} for f in self.fixes]
        if self.subject:
            out["subject"] = self.subject
        return out


@dataclass(frozen=True)
class Macro:
    """A macro definition from the preamble closure; `args` counts parameters, `default` is the optional first argument's default."""

    name: str
    args: int
    body: str
    default: str | None = None
    kind: str = "newcommand"


@dataclass(frozen=True)
class Taxon:
    """A theorem-like environment declared by \\newtheorem or \\declaretheorem: `env` is the author's name, `name` the display name."""

    env: str
    name: str
    style: str
    numbered: bool
    file: str
    offset: int
    counter: str | None = None
    within: str | None = None


@dataclass(frozen=True)
class Directive:
    key: str
    value: str
    file: str
    offset: int
    line: int
    form: str  # bare | kv | begin | end | tex


@dataclass
class Env:
    """One environment occurrence in a file's environment tree."""

    name: str
    start: int
    end: int
    body_start: int
    body_end: int
    optarg: str | None
    optarg_span: tuple[int, int] | None
    children: list[Env] = field(default_factory=list)
    parent: Env | None = field(default=None, repr=False)
    theorem_like: bool = False
    is_proof: bool = False

    def own_ranges(self) -> list[tuple[int, int]]:
        """[start, end) pieces of this environment's own text: its region minus its children's regions."""
        pieces: list[tuple[int, int]] = []
        pos = self.start
        for child in self.children:
            if child.start > pos:
                pieces.append((pos, child.start))
            pos = child.end
        if self.end > pos:
            pieces.append((pos, self.end))
        return pieces
