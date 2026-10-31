"""`loom.paths` owns every path loom uses inside a quilt: no other module spells one out, and `[quilt] history` is honoured wherever the history is reached."""

from __future__ import annotations

import ast
import os
from pathlib import Path

import loom
from loom.ai.layout import agent_dirs
from loom.records.store import Records
from loom.scan.quilt import load_quilt
from tests.helpers import ok
from tests.unit._quilts import demo

SRC = Path(loom.__file__).parent
#: Directories loom names; a path built from one of these as a literal belongs in `loom.paths`.
DIRS = ("build", ".loom", "digests", "annotations", "ai", "nodes", "retired", "refs", "notes")
#: The prefixes a literal quilt path starts with.
PREFIXES = tuple(f"{d}/" for d in ("build", ".loom", "digests", "annotations", "ai"))
#: loom's record files, by name.
RECORDS = {
    "reference-notes.jsonl",
    "state.toml",
    "serve.json",
    "review-decisions.json",
    "review-origins.json",
    "review-observations.json",
    "adoption-decisions.json",
    "source-sync.json",
    "last-seen.json",
}
#: Literals that look like quilt paths and are not, each with its reason, by file and the stripped source line.
ALLOWED = {
    # an output directory inside a temporary stage, not the quilt's build output
    ("sync.py", 'stage / "build" / f"{index}-{Path(projected).stem}",'),
    ("section_drafts.py", 'stage, base, under(base, "paper.tex"), stage / "build", result.quilt.config.engine'),
    # text for a person: help naming a file, and init's summary of its ignore file, which changes when the layout moves (plan 0.22.5)
    ("cli/help.py", '"ai/rules.md lists what it may."'),
    ("cli/quilt.py", '"build/ (everything loom can rebuild)",'),
}


def _docstrings(tree: ast.AST) -> set[int]:
    """The ids of every docstring constant in `tree`, which are prose and never paths."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                out.add(id(first.value))
    return out


def _offences(path: Path) -> list[tuple[int, str]]:
    """(line, why) for each literal in one module that spells out a quilt path."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    prose = _docstrings(tree)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            right = node.right
            if isinstance(right, ast.Constant) and isinstance(right.value, str) and right.value.split("/")[0] in DIRS:
                found.append((node.lineno, f"joins {right.value!r}"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose:
            if node.value.startswith(PREFIXES) or node.value in RECORDS:
                found.append((node.lineno, f"spells {node.value!r}"))
    return found


def test_no_module_but_paths_spells_out_a_quilt_path() -> None:
    """Every path loom uses inside a quilt is named once, in `loom.paths`, so moving one is a change in one place."""
    bad = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        if rel == "paths.py":
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for lineno, why in _offences(path):
            if (rel, lines[lineno - 1].strip()) not in ALLOWED:
                bad.append(f"{rel}:{lineno}: {why}")
    assert not bad, "name these in loom/src/loom/paths.py:\n" + "\n".join(bad)


def test_the_history_setting_is_honoured_wherever_the_history_is_reached(tmp_path: Path) -> None:
    """A quilt whose `[quilt] history` names another directory has its agents' read-only list, its records' snapshots and `init`'s ledger there."""
    q = demo(tmp_path)
    config = q / "config.toml"
    config.write_text(config.read_text().replace("[quilt]\n", '[quilt]\nhistory = "hist"\n', 1))
    quilt = load_quilt(q)
    _, readonly = agent_dirs(quilt.config)
    assert "hist" in readonly and ".loom/history" not in readonly
    assert Records(q).history_dir == q / "hist"

    user = Path(os.environ["XDG_CONFIG_HOME"]) / "loom" / "config.toml"
    user.parent.mkdir(parents=True, exist_ok=True)
    user.write_text('[quilt]\nhistory = "hist"\n')
    ok("init", str(tmp_path / "fresh"), "--prefix", "zz", "--yes")
    assert (tmp_path / "fresh" / "hist" / "ledger.jsonl").is_file()
    assert not (tmp_path / "fresh" / ".loom" / "history").exists()
