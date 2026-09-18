#!/usr/bin/env python3
"""Write the fixture quilts by running loom's own commands (book 14.3, plan 0.9 §6).

`tests/quilts/sources/<name>/` holds what an author wrote; every record -- the acceptance ledger, the history, the runs and the comments -- is made here by the commands that make one, under a fixed clock, so nothing in a fixture is hand-written and `--check` proves the checked-in copy is this script's output.

    python scripts/gen_quilts.py [demo|synthetic|all] [--check]
"""

from __future__ import annotations

import argparse
import filecmp
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

from click.testing import CliRunner

REPO = Path(__file__).resolve().parents[1]
SOURCES = REPO / "tests" / "quilts" / "sources"
QUILTS = REPO / "tests" / "quilts"
ASSETS = REPO / "src" / "loom" / "assets"
AUTHOR = "The synthetic quilt"


class Gen:
    """A quilt under construction: `at` fixes the clock, `run` invokes loom in process, `apply_patch` plays the author.

    The author's name is fixed too, in a user config of this script's own: a record that carried whoever ran the generator would differ from machine to machine, and the check test could not run at all.
    """

    def __init__(self, root: Path, author: str) -> None:
        self.root = root
        self.author = author
        self.time = "2026-09-13T09:00:00Z"
        self.config = root.parent / "config-home"
        (self.config / "loom").mkdir(parents=True, exist_ok=True)
        (self.config / "loom" / "config.toml").write_text(f'[author]\nname = "{author}"\n', encoding="utf-8")

    def at(self, when: str) -> None:
        self.time = when

    def env(self) -> dict[str, str]:
        return {
            "LOOM_FIXED_TIME": self.time,
            "XDG_CONFIG_HOME": str(self.config),
            "GIT_CONFIG_GLOBAL": str(self.config / "gitconfig-none"),
            "GIT_CONFIG_NOSYSTEM": "1",
        }

    def run(self, *args: str, expect: int = 0) -> str:
        from loom.cli import main

        old = os.getcwd()
        try:
            os.chdir(self.root)
            res = CliRunner().invoke(main, list(args), env=self.env())
        finally:
            os.chdir(old)
        if res.exit_code != expect:
            raise SystemExit(f"loom {' '.join(args)} -> {res.exit_code} (wanted {expect})\n{res.output}")
        return res.output

    def edit(self, rel: str, old: str, new: str, count: int = 1) -> None:
        p = self.root / rel
        text = p.read_text(encoding="utf-8")
        if old not in text:
            raise SystemExit(f"{rel}: nothing to replace:\n{old!r}")
        p.write_text(text.replace(old, new, count), encoding="utf-8")

    def write(self, rel: str, text: str) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def apply_patch(self, diff: str) -> None:
        """Apply a unified diff loom printed, as the author's editor would."""
        for chunk in _split_diff(diff):
            rel, new = _apply(self.root, chunk)
            (self.root / rel).write_text(new, encoding="utf-8")


def _split_diff(diff: str) -> list[list[str]]:
    out: list[list[str]] = []
    cur: list[str] = []
    for line in diff.splitlines(keepends=True):
        if line.startswith("--- ") and cur:
            out.append(cur)
            cur = []
        cur.append(line)
    if cur:
        out.append(cur)
    return [c for c in out if any(x.startswith("@@") for x in c)]


def _apply(root: Path, lines: list[str]) -> tuple[str, str]:
    rel = lines[0][4:].strip()
    text = (root / rel).read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    pos = 0
    i = 2
    while i < len(lines):
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@", lines[i])
        if not m:
            i += 1
            continue
        start = int(m.group(1)) - 1
        out.extend(text[pos:start])
        pos = start
        i += 1
        while i < len(lines) and not lines[i].startswith("@@") and not lines[i].startswith("--- "):
            tag, body = lines[i][0], lines[i][1:]
            if tag == " ":
                out.append(text[pos])
                pos += 1
            elif tag == "-":
                pos += 1
            elif tag == "+":
                out.append(body)
            i += 1
    out.extend(text[pos:])
    return rel, "".join(out)


def _copy_sources(name: str, dest: Path) -> None:
    src = SOURCES / name
    if not src.is_dir():
        raise SystemExit(f"{src} is missing")
    shutil.copytree(src, dest)


def build_synthetic(dest: Path) -> None:
    """The synthetic quilt: the author's paper, then a year of landmarks, stamps, a fork, a revert, a review, and the two faults a quilt can be left in."""
    _copy_sources("synthetic", dest)
    g = Gen(dest, AUTHOR)

    # The first landmark, with every node as the author first wrote it.
    g.at("2026-09-13T09:00:00Z")
    g.run("canonize", "drafting/main.tex", "--to", "canon/widgets-v1.tex", "-m", "First landmark", "--no-check")

    # Acceptance, on that same text. --force skips the compile: the rows it writes do not depend on it, and the generator must produce the same bytes with or without a TeX distribution.
    g.at("2026-09-14T09:00:00Z")
    g.run("accept", "sy-0001", "--author", AUTHOR, "--force")
    g.run("accept", "sy-0002", "--proofs", "--author", AUTHOR, "--force")
    g.run("accept", "sy-0003", "--proofs", "--author", AUTHOR, "--force")
    g.run("accept", "sy-000F", "--proofs", "--author", AUTHOR, "--force")

    # A first pass that was discarded; its one annotation is written with the rest, below.
    g.at("2026-09-15T10:00:00Z")
    (dest / "ai" / "runs").mkdir(parents=True)
    quick = g.run("ai", "start", "quick").strip().splitlines()[-1].strip()

    # The author rewrites the definition, so everything that depends on it goes stale.
    g.edit(
        "drafting/main.tex",
        "A \\emph{widget} is a pair $(X,\\sigma)$ with $\\sigma\\colon X\\to X$ satisfying \\eqref{eq:prose}.",
        "A \\emph{widget} is a pair $(X,\\sigma)$ of a set and an involution $\\sigma$ of $X$, so that \\eqref{eq:prose} holds.",
    )
    g.at("2026-09-15T11:00:00Z")
    g.run("stamp", "-m", "Referee points")

    # The talk needs its own version of the two-proof lemma.
    g.at("2026-09-15T12:00:00Z")
    out = g.run("fork", "sy-0006", "--in", "drafting/talk.tex")
    g.apply_patch(out[out.index("--- drafting/talk.tex") :])
    forked = re.search(r"Wrote nodes/(sy-[0-9A-Z]{4})\.tex", out)
    assert forked, out
    fork_id = forked.group(1)

    g.at("2026-09-15T13:00:00Z")
    g.run("canonize", "drafting/main.tex", "--to", "canon/widgets-v2.tex", "-m", "After the referee", "--no-check")

    # An edit the author thinks better of: revert puts the recorded text back, and the head is then the text of @1.
    g.edit("nodes/sy-0002.tex", "one or two points", "at most two points")
    g.at("2026-09-15T14:00:00Z")
    out = g.run("revert", "sy-0002@1")
    g.apply_patch(out[out.index("--- nodes/sy-0002.tex") :])

    # The talk's own copy is shortened for the slide; a stamp narrowed to the talk records that and nothing else.
    g.edit(
        f"nodes/{fork_id}.tex",
        "A widget with $|X| = 1$ has a fixed point.",
        "A widget with one point has a fixed point.",
    )
    g.at("2026-09-15T15:00:00Z")
    g.run("stamp", "-m", "Talk prepared", "--in", "drafting/talk.tex")

    # The retired lemma: accepted, then dropped, so its ledger rows retire and its id is never allocated again.
    g.edit(
        "drafting/main.tex",
        "\n\\begin{lemma}[Retired]\\label{sy-000F}\n"
        "This lemma is accepted and then deleted, so its ledger rows retire.\n"
        "\\end{lemma}\n"
        "\\begin{proof}\nTrivial.\n\\end{proof}\n",
        "",
    )
    g.at("2026-09-15T16:00:00Z")
    g.run("canonize", "drafting/main.tex", "--to", "canon/widgets-v3.tex", "-m", "Third landmark", "--no-check")

    # The review that stands: a run with two annotations, the author's own comments, one reply, one resolution.
    g.at("2026-09-16T00:00:00Z")
    referee = g.run("ai", "start", "referee").strip().splitlines()[-1].strip()
    g.run(
        "comment",
        "sy-0003",
        "The hypothesis 'finite' is essential for the parity count; say so in the statement.",
        "--kind",
        "objection",
        "--severity",
        "major",
        "--quote",
        "finite widget",
        "--run",
        referee,
    )
    g.run(
        "comment",
        "sy-0004",
        "Cite the orbit lemma by number here.",
        "--kind",
        "suggestion",
        "--severity",
        "minor",
        "--quote",
        "disjoint union of orbits",
        "--payload",
        "By Lemma~\\ref{sy-0002}, $X$ is the disjoint union of orbits.",
        "--placement",
        "replace",
        "--run",
        referee,
    )
    g.run(
        "comment",
        "drafting/main.tex",
        "The paper never says which conventions it inherits from the setup section; one sentence at the top would fix it.",
        "--kind",
        "suggestion",
        "--severity",
        "moderate",
        "--run",
        referee,
    )
    # Two citation suggestions: one the author accepts, which leaves a breadcrumb in reference-notes.jsonl, and one
    # left open, so the viewer has both a decided suggestion and an undecided one to show.
    g.run(
        "comment",
        "sy-0003",
        "Kreschmer's cycle-group paper proves this for permutations; cite it rather than reproving the parity count.",
        "--kind",
        "citation",
        "--run",
        referee,
    )
    g.run(
        "comment",
        "sy-0002",
        "The orbit decomposition is standard; a textbook reference would do.",
        "--kind",
        "citation",
        "--run",
        referee,
    )
    g.write(
        f"{referee}/thread.md",
        "# Thread: referee sy-0003\n\n## 2026-09-16 00:00 referee of sy-0003\n\n"
        "Asked: hostile review of the parity theorem. Did: read the statement and its closure, left one objection on "
        "the statement, one suggestion on the first proof, and one point about the document as a whole. Decided: "
        "nothing; the author decides. Remains: the second proof was not reviewed.\n",
    )
    g.run(
        "comment",
        "sy-0002",
        "Is the orbit of a fixed point counted as one point or two?",
        "--kind",
        "question",
        "--quote",
        "one or two points",
        "--author",
        AUTHOR,
    )
    objection, suggestion, document, cited, _open = _annotation_ids(dest, referee)[:5]
    g.at("2026-09-16T09:00:00Z")
    g.run("refs", "note", "--from", referee, "--accept", cited, "--reason", "worth citing", "--author", AUTHOR)
    g.at("2026-09-16T00:00:00Z")
    g.write(f"{referee}/referee-sy-0003.notes.md", _synthetic_report(objection, suggestion, document))
    g.run("comment", "--reply", objection, "Agreed; I will add the hypothesis to the statement.", "--author", AUTHOR)
    g.run("comment", "--reply", suggestion, "Done in the next revision.", "--author", AUTHOR)
    g.run("comment", "--resolve", suggestion, "--author", AUTHOR)
    g.run(
        "comment",
        "sy-0001",
        "Is the involution required to be a bijection, or does that follow?",
        "--kind",
        "question",
        "--quote",
        "an involution $\\sigma$ of $X$",
        "--author",
        AUTHOR,
    )
    g.run("comment", "sy-000A", "Gadgets of odd order cannot exist.", "--kind", "ok", "--run", quick)
    g.run("ai", "discard", quick)

    # The definition is revised once more, and the question that quoted the old wording no longer matches it: an annotation loom cannot place is said to be detached, never quietly moved.
    g.edit(
        "drafting/main.tex",
        "a pair $(X,\\sigma)$ of a set and an involution $\\sigma$ of $X$, so that",
        "a pair of a set and an involution of it, so that",
    )

    # The two faults a quilt can be left in, last: canonize refuses a document that reaches a conflicted id.
    twice = g.run("id", "--next").strip()
    body = (
        f"\\begin{{lemma}}[Doubly defined]\\label{{{twice}}}\n"
        "This lemma is defined twice, so it has no text and loom says so rather than choosing.\n"
        "\\end{lemma}\n"
    )
    g.write(f"nodes/{twice}.tex", body)
    g.edit("drafting/main.tex", "\\input{nodes/sy-000B}\n", f"\\input{{nodes/sy-000B}}\n\n\\input{{nodes/{twice}}}\n")
    g.edit(
        "drafting/talk.tex",
        "\\begin{frame}{Two arguments}",
        "\\begin{frame}{The doubly defined lemma}\n" + body + "\\end{frame}\n\n\\begin{frame}{Two arguments}",
    )
    with (dest / "canon" / "widgets-v1.tex").open("a", encoding="utf-8") as fh:
        fh.write("% A landmark edited after the fact, so loom:canon-edited has something to report.\n")

    _write_expected_lint(g)


def _synthetic_report(objection: str, suggestion: str, document: str) -> str:
    """The conformance fixture's referee report: several named blocks, findings that resolve to real annotations, math in the prose, and one symbol declared twice with different meanings, so the report pane and the notation panel both have something real to work on."""
    return f"""## [summary]
The parity theorem is correct as stated but leans on finiteness without saying so. One citation is missing a number. The document as a whole does not say which conventions it inherits.

## [notation]
- $\\Fix(\\sigma)$ is the fixed locus of the involution.
- $k$ is the number of two-element orbits.
- $\\Fix(\\sigma)$ is also used below for the fixed locus of the induced map on orbits.

## [referee-review] Major and minor issues

### Major Issues
- The count $|X| = |\\Fix(\\sigma)| + 2k$ needs $X$ finite, and the statement does not say it. Everything after it is fine. ({objection})

### Minor Issues
- The orbit decomposition is used by name rather than by number; a replacement sentence is attached. ({suggestion})

### Clarity/Exposition
- The paper inherits conventions from the setup section without saying so. ({document})

## [decision]
Minor Revision.
"""


def _demo_report(*, suggestion: str, objection: str, document: str) -> str:
    """The demo's referee report, written the way `ai/rules.md` says to write one: named blocks, and every finding ending in its annotation's id.

    It exists so the fixture has something the report pane can actually render -- several blocks, findings that resolve to real annotations, math in the prose, and a notation block for the panel that reads one.
    """
    return f"""## [summary]
The statement mixes a finiteness claim with a closedness claim; the proof leaves one continuity step unsaid. One suggestion carries a proposed replacement for the statement. The author must decide whether to split the theorem.

## [notation]
- $\\Fix(\\sigma)$ is the fixed locus, written $X^\\sigma$ in the cited literature.
- $(X,\\sigma)$ is a widget; the paper's $\\iota$ is this quilt's $\\sigma$.

## [referee-review] Major and minor issues

### Major Issues
- The proof takes continuity of $(\\mathrm{{id}},\\sigma)\\colon X \\to X \\times X$ for granted. It does follow from continuity of $\\sigma$ and the universal property of the product, but the step is load-bearing for the closedness claim and is never stated. ({objection})

### Minor Issues
- The statement binds a parity claim, which needs $|X|$ finite, to a closedness claim, which does not. Splitting them would let the second be cited on its own. A replacement statement is attached. ({suggestion})

### Clarity/Exposition
- $\\Fix$ is introduced twice in the setup, once in prose and once as a definition. ({document})

## [decision]
Minor Revision. Nothing here is wrong; the proof is missing one sentence and the statement is doing two jobs.
"""


def _annotation_ids(root: Path, run: str) -> list[str]:
    """The ids a run created, read back out of the log so the generator can reply to and resolve them."""
    import json

    log = root / "annotations" / "log.jsonl"
    out: list[str] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("event") == "created" and e.get("run") == run:
            out.append(e["id"])
    return out


def build_demo(dest: Path) -> None:
    """The packaged demo: what `loom init --demo` writes, with its AI layer, one person's comment, one finished run, and one landmark."""
    _copy_sources("demo", dest)
    g = Gen(dest, "The loom demo")
    g.at("2026-09-16T00:00:00Z")
    g.run("ai", "init", "--skills", "--permissions")
    g.run(
        "comment",
        "dm-0003/proof",
        "Closedness only needs that the diagonal is closed; say where Hausdorff is used.",
        "--kind",
        "suggestion",
        "--quote",
        "diagonal is closed",
        "--author",
        "The loom demo",
    )
    g.run("accept", "dm-0002", "--proofs", "--author", "The loom demo", "--force")
    g.run(
        "canonize",
        "drafting/main.tex",
        "--to",
        "canon/widgets-v1.tex",
        "-m",
        "The demo's first landmark",
        "--no-check",
    )

    g.at("2026-09-16T14:02:00Z")
    run_dir = g.run("ai", "start", "referee-dm-0003").strip().splitlines()[-1].strip()
    g.at("2026-09-16T14:31:00Z")
    g.run(
        "comment",
        "dm-0003",
        "The theorem assumes $X$ finite for the parity claim, but the closedness claim needs no finiteness; consider splitting the statement.",
        "--kind",
        "suggestion",
        "--severity",
        "moderate",
        "--quote",
        "with $X$ a finite set",
        "--payload",
        "Let $(X,\\sigma)$ be a widget. Then $\\Fix(\\sigma)$ is closed in every topology on $X$ for which $\\sigma$ is continuous and $X$ is Hausdorff; if moreover $X$ is finite, $\\Fix(\\sigma)$ is nonempty if and only if $|X|$ is odd.",
        "--placement",
        "replace",
        "--run",
        run_dir,
    )
    g.run(
        "comment",
        "dm-0003/proof",
        "Continuity of $(\\mathrm{id},\\sigma)$ into the product is used without being said; it follows from $\\sigma$ continuous, but say so.",
        "--kind",
        "objection",
        "--severity",
        "major",
        "--quote",
        "the preimage of the diagonal",
        "--run",
        run_dir,
    )
    # A whole-document annotation: its target is the master's path, which loom has written since 0.6 and nothing showed.
    g.run(
        "comment",
        "drafting/main.tex",
        "The setup section introduces $\\Fix$ twice, once in prose and once in the definition; keep the definition.",
        "--kind",
        "suggestion",
        "--severity",
        "minor",
        "--run",
        run_dir,
    )
    g.write(
        f"{run_dir}/thread.md",
        "# Thread: referee dm-0003\n\n## 2026-09-16 14:31 referee\n\n"
        "Refereed dm-0003. One major objection in the proof, one moderate suggestion on the statement "
        "with a proposed replacement, and one minor point about the document as a whole.\n",
    )
    # in creation order: the statement suggestion, the proof objection, the whole-document point
    suggestion, objection, document = _annotation_ids(dest, run_dir)[:3]
    g.write(
        f"{run_dir}/referee-dm-0003.notes.md",
        _demo_report(suggestion=suggestion, objection=objection, document=document),
    )
    # the edit that leaves an accepted key stale, so a fresh demo shows a state worth looking at
    g.edit("nodes/dm-0001.tex", "a pair $(X,\\sigma)$ of a finite set", "a pair $(X,\\sigma)$ of a set")
    _write_expected_lint(g)


def _write_expected_lint(g: Gen) -> None:
    """The diagnostics the quilt is meant to report, as `loom lint` reports them: the fixture's own expectation, never typed by hand."""
    import json

    from loom.cli import main

    old = os.getcwd()
    try:
        os.chdir(g.root)
        res = CliRunner().invoke(main, ["lint", "--json"], env=g.env())
    finally:
        os.chdir(old)
    diags = json.loads(res.output)
    lines = sorted(f"{d['severity']} {d['code']}" for d in diags)
    (g.root / "EXPECTED-LINT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


BUILDERS = {"synthetic": build_synthetic, "demo": build_demo}


def _sync(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("build", "__pycache__", ".git"))


def _differences(a: Path, b: Path) -> list[str]:
    out: list[str] = []
    files = {p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file()}
    other = {p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file()}
    for rel in sorted(files - other):
        out.append(f"only generated: {rel}")
    for rel in sorted(other - files):
        out.append(f"only checked in: {rel}")
    for rel in sorted(files & other):
        if not filecmp.cmp(a / rel, b / rel, shallow=False):
            out.append(f"differs: {rel}")
    return out


def generate(names: Iterable[str], check: bool) -> int:
    problems: list[str] = []
    for name in names:
        with tempfile.TemporaryDirectory(prefix=f"loom-gen-{name}-") as tmp:
            built = Path(tmp) / name
            BUILDERS[name](built)
            target = QUILTS / name
            if check:
                diffs = _differences(built, target)
                if diffs:
                    problems.append(f"{name}:\n  " + "\n  ".join(diffs))
                else:
                    print(f"{name} is current")
            else:
                _sync(built, target)
                print(f"wrote {target.relative_to(REPO)}")
                if name == "demo":
                    _sync(built, ASSETS / "demo")
                    (ASSETS / "demo" / "EXPECTED-LINT.txt").unlink(missing_ok=True)
                    print(f"wrote {(ASSETS / 'demo').relative_to(REPO)}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        print("run: python scripts/gen_quilts.py " + " ".join(names), file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("which", nargs="?", default="all", choices=["all", *BUILDERS])
    ap.add_argument("--check", action="store_true", help="Compare with the checked-in quilts instead of writing them.")
    args = ap.parse_args()
    names = list(BUILDERS) if args.which == "all" else [args.which]
    return generate(names, args.check)


if __name__ == "__main__":
    raise SystemExit(main())
