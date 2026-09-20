"""Label insertion for `loom id` and `loom import` (book 6.2.4, 6.3): a `\\label{<prefix>-<local>}` on every theorem-like environment and sectioning command that has no id, allocated in document order."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

from loom.scan.labels import base36_decode, base36_encode
from loom.scan.scan import ScanResult
from loom.scan.tokenize import read_args

SECTION_LEVELS = {
    "part": -1,
    "chapter": 0,
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
    "paragraph": 4,
    "subparagraph": 5,
}


@dataclass(frozen=True)
class Insertion:
    file: str
    offset: int
    text: str
    key: str
    line: int


def plan_insertions(
    result: ScanResult, files: list[str], prefix: str, first_local: str, sections: bool = True, all_levels: bool = False
) -> list[Insertion]:
    """Insertions for `files` in order, allocating ids from `first_local` upward."""
    asm = result.assembly
    counter = base36_decode(first_local)
    out: list[Insertion] = []
    max_level = 5 if all_levels else 3
    for file in files:
        src = result.files[file]
        candidates: list[tuple[int, str, str]] = []  # (offset, key, kind)
        fe = asm.envs.get(file)
        if fe:
            for env in fe.theorem_envs:
                key = asm.key_of_env(file, env)
                node = asm.nodes.get(key or "")
                if node is None or node.id:
                    continue
                candidates.append((env.body_start, node.key, "env"))
        if sections:
            for node in asm.nodes.values():
                if node.kind != "section" or node.file != file or node.id or node.level is None:
                    continue
                m = re.match(
                    r"\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?\s*",
                    src.clean[node.start :],
                )
                if not m or SECTION_LEVELS[m.group(1)] > max_level:
                    continue
                _, _, after = read_args(src.clean, node.start + m.end(), "om")
                # directly after the heading's arguments, ahead of any existing label, so the id is the first label
                candidates.append((after, node.key, "section"))
        for offset, key, _kind in sorted(candidates):
            new_id = f"{prefix}-{base36_encode(counter)}"
            counter += 1
            out.append(Insertion(file, offset, f"\\label{{{new_id}}}", key, src.line_of(offset)))
    return out


def apply_insertions(text: str, insertions: list[Insertion]) -> str:
    out = text
    for ins in sorted(insertions, key=lambda i: i.offset, reverse=True):
        out = out[: ins.offset] + ins.text + out[ins.offset :]
    return out


def unified_diff(before: str, after: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile=path, tofile=path
        )
    )
