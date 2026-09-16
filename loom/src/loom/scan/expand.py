"""Master expansion with a span map (book 5.9.1, 5.9.2, 5.9.4).

\\input, \\include, and \\nest are resolved as TeX does: the path as written, then with .tex appended; a braceless \\input name is accepted; a name kpsewhich finds is a system file and ignored; a non-.tex file is an opaque inclusion whose text is never scanned. The expanded text keeps every reached file's text exactly once, each child spliced right after its inclusion command, so a section that starts in one file and continues in another is one unit. Cycles and second inclusions of a file in one master are reported and not expanded.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from loom.scan.model import Diagnostic, Location, SourceFile, Span
from loom.scan.tokenize import read_mandatory, tokenize

INCLUDE_CMDS = {"input", "include", "nest"}


@dataclass
class Segment:
    file: str
    file_start: int
    length: int
    exp_start: int
    shift: int

    @property
    def exp_end(self) -> int:
        return self.exp_start + self.length


@dataclass
class Inclusion:
    parent: str
    site_start: int
    site_end: int
    name: str
    kind: str
    child: str | None
    shift: int
    problem: str | None = None  # missing | cycle | double | system | opaque


@dataclass
class Expansion:
    master: str
    text: str = ""
    segments: list[Segment] = field(default_factory=list)
    inclusions: list[Inclusion] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    reached: dict[str, int] = field(default_factory=dict)

    def locate(self, exp_offset: int) -> tuple[str, int, int]:
        """(file, offset in file, level shift) for an expanded offset."""
        lo, hi = 0, len(self.segments) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.segments[mid].exp_start <= exp_offset:
                lo = mid
            else:
                hi = mid - 1
        seg = self.segments[lo]
        return seg.file, seg.file_start + (exp_offset - seg.exp_start), seg.shift

    def map_range(self, a: int, b: int) -> list[Span]:
        """File spans covering the expanded range [a, b), in order."""
        out: list[Span] = []
        for seg in self.segments:
            lo, hi = max(a, seg.exp_start), min(b, seg.exp_end)
            if lo < hi:
                out.append(Span(seg.file, seg.file_start + (lo - seg.exp_start), seg.file_start + (hi - seg.exp_start)))
        return out

    def exp_offset(self, file: str, offset: int) -> int | None:
        for seg in self.segments:
            if seg.file == file and seg.file_start <= offset < seg.file_start + seg.length:
                return seg.exp_start + (offset - seg.file_start)
        return None


@cache
def _kpsewhich(name: str) -> bool:
    """Whether the distribution resolves `name`. Memoised because it is a subprocess run once per unresolved inclusion, and a paper's unresolved names repeat: on the Manolache import it was 86 ms of a 166 ms scan, over half the total."""
    exe = shutil.which("kpsewhich")
    if not exe:
        return False
    try:
        proc = subprocess.run([exe, name], capture_output=True, text=True, errors="replace", timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0 and bool(proc.stdout.strip())


def resolve_inclusion(root: Path, name: str, known: frozenset[str] = frozenset()) -> tuple[str | None, str | None]:
    """(quilt-relative path, problem). Problems: 'system' for a kpsewhich-resolvable name, 'missing' otherwise.

    `known` holds paths that exist only in an editor's buffers, so a file an author has written but not yet saved resolves.
    """
    name = name.strip()
    if not name or name.startswith("/") or ".." in Path(name).parts:
        return None, "missing"
    for cand in (name, name + ".tex"):
        rel = Path(cand).as_posix()
        if rel in known or (root / cand).is_file():
            return rel, None
    probe = name if "." in Path(name).name else name + ".tex"
    if _kpsewhich(probe):
        return None, "system"
    return None, "missing"


def _read_include_arg(text: str, pos: int) -> tuple[str | None, int]:
    """The argument of \\input-like commands: a braced group, or a whitespace-delimited name (the primitive form)."""
    value, _, _, nxt = read_mandatory(text, pos)
    if value is None:
        return None, pos
    if nxt == pos + len(value) or text[pos:nxt].lstrip().startswith("{"):
        return value.strip(), nxt
    m = re.match(r"\s*([^\s{}\\]+)", text[pos:])
    if m:
        return m.group(1), pos + m.end()
    return value.strip(), nxt


def expand_master(master: SourceFile, root: Path, files: dict[str, SourceFile]) -> Expansion:
    """`files` is the scanner's whole file table, so a path that exists only in an editor's buffer resolves like one on disk."""
    exp = Expansion(master=master.path)
    parts: list[str] = []
    cursor = [0]

    def emit(file: str, file_start: int, length: int, shift: int) -> None:
        if length <= 0:
            return
        exp.segments.append(Segment(file, file_start, length, cursor[0], shift))
        cursor[0] += length

    def rec(src: SourceFile, shift: int, stack: tuple[str, ...]) -> None:
        exp.reached[src.path] = exp.reached.get(src.path, 0) + 1
        text = src.clean
        pos = 0
        for t in tokenize(text):
            if t.kind != "cmd" or t.value not in INCLUDE_CMDS:
                continue
            name, arg_end = _read_include_arg(text, t.end)
            if name is None:
                continue
            emit(src.path, pos, arg_end - pos, shift)
            parts.append(text[pos:arg_end])
            pos = arg_end
            child_shift = shift + 1 if t.value == "nest" else shift
            inc = Inclusion(src.path, t.start, arg_end, name, t.value, None, child_shift)
            exp.inclusions.append(inc)
            rel, problem = resolve_inclusion(root, name, frozenset(files))
            loc = [Location(src.path, src.line_of(t.start))]
            if rel is None:
                inc.problem = problem
                if problem == "missing":
                    exp.diagnostics.append(
                        Diagnostic("error", "missing-include", f"\\{t.value}{{{name}}} names no file", loc)
                    )
                continue
            inc.child = rel
            if not rel.endswith(".tex") or rel not in files:
                inc.problem = "opaque"
                continue
            if rel in stack or rel == src.path:
                inc.problem = "cycle"
                chain = " -> ".join([*stack, src.path, rel])
                exp.diagnostics.append(Diagnostic("error", "inclusion-cycle", f"inclusion cycle {chain}", loc))
                continue
            if rel in exp.reached:
                inc.problem = "double"
                exp.diagnostics.append(
                    Diagnostic("error", "double-inclusion", f"{rel} is included twice in {master.path}", loc, [rel])
                )
                continue
            child = files[rel]
            if child.ignored:
                inc.problem = "ignored"
                continue
            rec(child, child_shift, (*stack, src.path))
        emit(src.path, pos, len(text) - pos, shift)
        parts.append(text[pos:])

    rec(master, 0, ())
    exp.text = "".join(parts)
    return exp
