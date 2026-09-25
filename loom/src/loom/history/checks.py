"""What the record says against what the files say (book 17.14, 17.15): reported with the commands that would resolve it, repaired never.

`quick_checks` runs on every scan and costs one hash per canon document; `verify` walks every step directory and runs only from `loom lint` and `loom history verify`.
"""

from __future__ import annotations

from pathlib import Path

from loom.history.ledger import History
from loom.history.steps import file_hash
from loom.history.versions import version_filename
from loom.render.manifest import key_hash
from loom.scan.hashing import hash_text
from loom.scan.model import Diagnostic, Fix, Location
from loom.scan.scan import ScanResult


def quick_checks(result: ScanResult, history: History) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    for p in history.problems:
        out.append(
            Diagnostic(
                "error", "loom:history-corrupt", f"the history ledger cannot be read in full: {p}", [], subject="record"
            )
        )
    if not history.exists:
        return out
    root = result.quilt.root
    hist_rel = history.dir.relative_to(root).as_posix() if history.dir.is_relative_to(root) else str(history.dir)
    seen: set[str] = set()
    for e in reversed(history.steps()):
        to = e.get("to") or {}
        path, recorded = (to.get("path"), to.get("hash")) if isinstance(to, dict) else (None, None)
        if not path or not recorded or path in seen:
            continue
        seen.add(str(path))
        f = root / str(path)
        if not f.is_file():
            continue  # deletion is absence; the step keeps its copy
        if file_hash(f) != recorded:
            stem = Path(str(path)).stem
            drafting = result.quilt.config.drafting
            out.append(
                Diagnostic(
                    "warning",
                    "loom:canon-edited",
                    f"{path} is not the text step {e.step:04d} recorded; the landmark's copy is {hist_rel}/{e.dir}/{Path(str(path)).name}",
                    [Location(str(path), 1)],
                    subject="record",
                    fixes=[
                        Fix("restore the landmark", f"cp {hist_rel}/{e.dir}/{Path(str(path)).name} {path}"),
                        Fix("work on it as a draft instead", f"loom draft {path} --to {drafting}/{stem}.tex"),
                    ],
                )
            )
    removed = history.removed_ids()
    for key, step in sorted(removed.items()):
        n = result.nodes.get(key)
        if n is None or n.kind not in ("environment", "proof") or "#" in key:
            continue
        current = key_hash(result, key)
        recorded = {v.hash for v in history.versions_of(key)}
        loc = [Location(n.file, result.files[n.file].line_of(n.start))]
        if current in recorded:
            out.append(
                Diagnostic(
                    "info",
                    "loom:node-recovered",
                    f"{key} was removed at step {step:04d} and is back with a text the history knows; the next step records it as restored",
                    loc,
                    [key],
                )
            )
        else:
            out.append(
                Diagnostic(
                    "error",
                    "loom:id-reused",
                    f"{key} was removed at step {step:04d} and is defined again with a text the history never recorded; an id names one node forever",
                    loc,
                    [key],
                    fixes=[
                        Fix("it is a new node: give it a fresh id", "loom id --next"),
                        Fix("it is the old node revised: record it", f'loom stamp -m "{key} revised"'),
                    ],
                )
            )
    return out


def verify(result: ScanResult, history: History) -> list[Diagnostic]:
    """The full walk: every step directory, version file, preamble and document copy against its recorded hash; every ancestry line against the steps it names."""
    out: list[Diagnostic] = list(quick_checks(result, history))
    root = result.quilt.root
    hist_rel = history.dir.relative_to(root).as_posix() if history.dir.is_relative_to(root) else str(history.dir)

    def missing(what: str, e_step: int) -> Diagnostic:
        return Diagnostic(
            "error",
            "loom:history-missing",
            f"{what} of step {e_step:04d} is missing from {hist_rel}",
            [],
            subject="record",
            fixes=[Fix("see what git has", f"git -C {root} log --oneline -- {hist_rel}")],
        )

    def edited(what: str, e_step: int) -> Diagnostic:
        return Diagnostic(
            "error",
            "loom:history-edited",
            f"{what} of step {e_step:04d} does not hash to what the ledger recorded; the record was edited by hand",
            [],
            subject="record",
            fixes=[Fix("see what git has", f"git -C {root} log --oneline -- {hist_rel}")],
        )

    for e in history.steps():
        n = e.step or 0
        d = history.dir / (e.dir or "")
        if not e.dir or not d.is_dir():
            out.append(missing(f"the directory {e.dir}", n))
            continue
        for key, h in (e.get("froze") or {}).items():
            p = d / version_filename(key)
            if not p.is_file():
                out.append(missing(f"the version file for {key}", n))
            elif hash_text(p.read_text(encoding="utf-8", errors="replace")) != h:
                out.append(edited(f"the version file for {key}", n))
        pre = e.get("preamble")
        if pre:
            p = d / "preamble.tex"
            if not p.is_file():
                out.append(missing("the preamble", n))
            elif hash_text(p.read_text(encoding="utf-8", errors="replace")) != pre:
                out.append(edited("the preamble", n))
        to = e.get("to") or {}
        if isinstance(to, dict) and to.get("path") and to.get("hash"):
            p = d / Path(str(to["path"])).name
            if not p.is_file():
                out.append(missing(f"the copy of {to['path']}", n))
            elif file_hash(p) != to["hash"]:
                out.append(edited(f"the copy of {to['path']}", n))
    for e in history.entries:
        if e.action == "fork":
            frm = e.get("from") or {}
            if isinstance(frm, dict) and isinstance(frm.get("step"), int):
                st = history.step(frm["step"])
                key = str(frm.get("id", ""))
                if st is None or key not in history.state_at(frm["step"]):
                    out.append(
                        Diagnostic(
                            "warning",
                            "loom:dangling-ancestry",
                            f"{e.get('new')} was forked from {key}@{frm['step']}, which the history no longer resolves",
                            [],
                            [str(e.get("new", ""))],
                            subject="record",
                        )
                    )
        elif e.action == "revert":
            step = e.get("step")
            key = str(e.get("key", ""))
            if isinstance(step, int) and (history.step(step) is None or key not in history.state_at(step)):
                out.append(
                    Diagnostic(
                        "warning",
                        "loom:dangling-ancestry",
                        f"{key} was reverted to @{step}, which the history no longer resolves",
                        [],
                        [key],
                        subject="record",
                    )
                )
        elif e.action == "draft":
            frm = e.get("from") or {}
            if isinstance(frm, dict) and isinstance(frm.get("step"), int) and history.step(frm["step"]) is None:
                to = e.get("to") or {}
                drafted = to.get("path") if isinstance(to, dict) else to
                out.append(
                    Diagnostic(
                        "warning",
                        "loom:dangling-ancestry",
                        f"{drafted} was drafted from step {frm['step']:04d}, which the history no longer has",
                        [],
                        subject="record",
                    )
                )
    return out
