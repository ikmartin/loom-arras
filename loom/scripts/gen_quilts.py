#!/usr/bin/env python3
"""Write the fixture quilts by running loom's own commands (book 14.3, plan 0.9 §6).

`tests/quilts/sources/<name>/` holds what an author wrote; every record -- the acceptance ledger, the history, the runs and the comments -- is made here by the commands that make one, under a fixed clock, so nothing in a fixture is hand-written and `--check` proves the checked-in copy is this script's output.

    python scripts/gen_quilts.py [demo|synthetic|showcase|all] [--check]
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

    def env(self, agent: bool = False) -> dict[str, str | None]:
        from loom.cli._common import AGENT_MARKERS

        # The generator plays both parties. As the author -- it accepts, verifies and discards to build the history --
        # an agent running it must not make loom refuse the author's verbs, so the markers are unset (None unsets the
        # variable for the call). As the agent, `agent=True` sets one, because since plan 0.13 §5 that is what makes a
        # record say an agent wrote it rather than crediting whoever's git identity the shell carries.
        return {
            "LOOM_FIXED_TIME": self.time,
            "XDG_CONFIG_HOME": str(self.config),
            "GIT_CONFIG_GLOBAL": str(self.config / "gitconfig-none"),
            "GIT_CONFIG_NOSYSTEM": "1",
            **{marker: ("1" if agent and marker == "AI_AGENT" else None) for marker in AGENT_MARKERS},
        }

    def run(self, *args: str, expect: int = 0, agent: bool = False) -> str:
        from loom.cli import main

        old = os.getcwd()
        try:
            os.chdir(self.root)
            res = CliRunner().invoke(main, list(args), env=self.env(agent))
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


def _later(name: str, rel: str, dest: Path) -> None:
    """Copy one file from `sources/<name>-later/` into the quilt: an author file written partway through the story, after the command that makes its targets exist."""
    src = SOURCES / f"{name}-later" / rel
    if not src.is_file():
        raise SystemExit(f"{src} is missing")
    (dest / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dest / rel)


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
        "--session",
        referee,
        agent=True,
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
        "--session",
        referee,
        agent=True,
    )
    g.run(
        "comment",
        "drafting/main.tex",
        "The paper never says which conventions it inherits from the setup section; one sentence at the top would fix it.",
        "--kind",
        "suggestion",
        "--severity",
        "moderate",
        "--session",
        referee,
        agent=True,
    )
    # Two citation suggestions: one the author accepts, which leaves a breadcrumb in reference-notes.jsonl, and one
    # left open, so the viewer has both a decided suggestion and an undecided one to show.
    g.run(
        "comment",
        "sy-0003",
        "Kreschmer's cycle-group paper proves this for permutations; cite it rather than reproving the parity count.",
        "--kind",
        "citation",
        "--payload",  # the work the suggestion names; the message argues for it
        "Kreschmer, Cycle groups of finite permutation actions, J. Alg. 1999",
        "--session",
        referee,
        agent=True,
    )
    g.run(
        "comment",
        "sy-0002",
        "The orbit decomposition is standard; a textbook reference would do.",
        "--kind",
        "citation",
        "--payload",
        "any standard text on group actions",
        "--session",
        referee,
        agent=True,
    )
    # The agent's account of the run, said in the chat (plan 0.14).
    g.run(
        "session",
        "say",
        "Asked: hostile review of the parity theorem. Did: read the statement and its closure, left one objection on "
        "the statement, one suggestion on the first proof, and one point about the document as a whole. Decided: "
        "nothing; the author decides. Remains: the second proof was not reviewed.",
        "--session",
        referee,
        "--as",
        "Referee Agent",
        agent=True,
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
    g.write(f".loom/sessions/{referee}/referee-sy-0003.notes.md", _synthetic_report(objection, suggestion, document))
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
    g.run(
        "comment",
        "sy-000A",
        "Gadgets of odd order cannot exist.",
        "--kind",
        "confirmation",
        "--session",
        quick,
        agent=True,
    )
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


def _annotation_ids(root: Path, session: str) -> list[str]:
    """The ids a session created, read back out of the log so the generator can reply to and resolve them."""
    import json

    log = root / "annotations" / "log.jsonl"
    out: list[str] = []
    for line in log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("event") == "created" and e.get("session") == session:
            out.append(e["id"])
    return out


def build_demo(dest: Path) -> None:
    """The packaged demo: what `loom init --demo` writes, with its AI layer, one person's comment, one finished run, and one landmark."""
    _copy_sources("demo", dest)
    g = Gen(dest, "The loom demo")
    g.at("2026-09-16T00:00:00Z")
    g.run("ai", "init", "--skills")
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

    # The cited work, the showcase's way: an invented paper this repository compiles, so the demo has a real document
    # behind its digest rather than prose about a paper nobody holds. The author drops the PDF into the seed space and
    # `refs scan` files it under the identifier it prints; the source is added beside it, and the digest is extracted by
    # the command that extracts one.
    (dest / "refs").mkdir(exist_ok=True)
    shutil.copy(DEMO_WORKS / "calloway-fixed-loci.pdf", dest / "refs" / "calloway-fixed-loci.pdf")
    g.run("refs", "scan")
    g.run("refs", "add", "Calloway14", str(DEMO_WORKS / "calloway-fixed-loci.tex"))
    g.run("refs", "map", "Calloway14")
    g.run("digest", "extract", "Calloway14", "--no-compile")

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
        "--session",
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
        "--session",
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
        "--session",
        run_dir,
        agent=True,
    )
    # The agent's account of the run, said in the chat (plan 0.14).
    g.run(
        "session",
        "say",
        "Refereed dm-0003. One major objection in the proof, one moderate suggestion on the statement "
        "with a proposed replacement, and one minor point about the document as a whole.",
        "--session",
        run_dir,
        "--as",
        "Referee Agent",
        agent=True,
    )
    # in creation order: the statement suggestion, the proof objection, the whole-document point
    suggestion, objection, document = _annotation_ids(dest, run_dir)[:3]
    g.write(
        f".loom/sessions/{run_dir}/referee-dm-0003.notes.md",
        _demo_report(suggestion=suggestion, objection=objection, document=document),
    )
    # the edit that leaves an accepted key stale, so a fresh demo shows a state worth looking at
    g.edit("nodes/dm-0001.tex", "a pair $(X,\\sigma)$ of a finite set", "a pair $(X,\\sigma)$ of a set")
    _write_expected_lint(g)


SHOWCASE = "The loom showcase"


def _tiny_pdf(path: Path, text: str = "Notes on balanced quivers, for a reader in a hurry.") -> None:
    """A one-page PDF with a text layer, written by hand: the orphan needs a document nothing else in the showcase names, and generating one needs no TeX."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    start = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


#: The invented cited works, compiled by `sources/showcase-works/build.sh` and committed beside their LaTeX. They are copied into the quilt's seed space and filed by `loom refs scan`, so that generating the showcase needs no TeX distribution and writes the same bytes on every machine.
WORKS = SOURCES / "showcase-works"
DEMO_WORKS = SOURCES / "demo-works"


def build_showcase(dest: Path) -> None:
    """The showcase quilt: one invented paper, two invented cited works, and every record loom writes, so that a fresh clone opens the viewer on a quilt that has been lived in.

    Read it as a tour rather than a fixture: the synthetic quilt exercises the source contract and this one exercises the *records* -- the reference layer, annotations of every kind, severity and state, a run, a landmark history, and the three faults a quilt can be left in. It is regenerated after a feature lands, so what it shows is what loom does today.
    """
    _copy_sources("showcase", dest)
    g = Gen(dest, SHOWCASE)

    # ---- The paper arrives, is atomized, and becomes the first landmark. --------------------------------
    g.at("2026-09-14T09:00:00Z")
    g.run("atomize", "drafting/main.tex", "drafting/main-atomic.tex", "--sections")
    g.at("2026-09-14T09:05:00Z")
    g.run(
        "canonize",
        "drafting/main-atomic.tex",
        "--to",
        "canon/flows-v1.tex",
        "-m",
        "The paper as it arrived",
        "--no-check",
    )

    # ---- The seed space, and loom's store. --------------------------------------------------------------
    # The author drops the two PDFs they hold into `refs/`; `refs scan` reads the canon document's
    # bibliography and files each document under the identifier it states on its own first page.
    (dest / "refs").mkdir(exist_ok=True)
    for pdf in sorted(WORKS.glob("*.pdf")):
        shutil.copy(pdf, dest / "refs" / pdf.name)
    g.at("2026-09-14T09:10:00Z")
    g.run("refs", "scan")
    g.at("2026-09-14T09:15:00Z")
    # The source goes into the store before the digest is made: a digest extracted from a file only this machine
    # holds cites pages nobody else can open, which is the invariant `digest extract` now enforces (plan 0.13 §4).
    g.run("refs", "add", "Arden24", str(WORKS / "arden-cycle-spaces.tex"))
    g.run("digest", "extract", "Arden24", "--no-compile")
    g.at("2026-09-14T09:20:00Z")
    g.run("ai", "init", "--skills")

    # ---- A run reads the work loom could not extract, and proposes its results. -------------------------
    # Bellamy19 is a PDF and nothing else, so every result is read off a page and anchored to it. The run
    # proposes; only the author may verify, which is the whole of DR-177 in two commands.
    g.at("2026-09-15T10:00:00Z")
    survey = g.run("ai", "start", "survey-bellamy").strip().splitlines()[-1].strip()
    g.run(
        "refs",
        "propose",
        "Bellamy19",
        "--local",
        "thm-2.3",
        "--page",
        "2",
        "--level",
        "1",
        "--session",
        survey,
        "--source-text",
        "The median orders of a weighted digraph are in bijection with the vertices of a rational polytope M (D) "
        "⊆ RA cut out by the exchange inequalities of Lemma 2.2, and M (D) is bounded.",
        "--statement",
        "The median orders of a weighted digraph are in bijection with the vertices of a rational polytope "
        "$M(D) \\subseteq \\mathbb{R}^{A}$ cut out by the exchange inequalities of Lemma~2.2, and $M(D)$ is bounded.",
    )
    g.run(
        "refs",
        "propose",
        "Bellamy19",
        "--local",
        "thm-3.2",
        "--page",
        "2",
        "--level",
        "1",
        "--session",
        survey,
        "--source-text",
        "Let D be a weighted digraph whose weight function is balanced at every vertex. Then the counting function "
        "of the median polytope of D agrees with a polynomial of degree equal to the dimension of that polytope for "
        "every nonnegative integer dilation factor, and the leading coefficient of that polynomial is the relative "
        "volume of the polytope.",
        "--statement",
        "Let $D$ be a weighted digraph whose weight function is balanced at every vertex. Then the counting function "
        "of the median polytope of $D$ agrees with a polynomial of degree equal to the dimension of that polytope, "
        "and the leading coefficient of that polynomial is the relative volume.",
        agent=True,
    )
    g.run(
        "refs",
        "propose",
        "Bellamy19",
        "--local",
        "prop-3.1",
        "--page",
        "2",
        "--session",
        survey,
        "--source-text",
        "The function L is a quasi-polynomial in k of degree equal to the dimension of M (D), with a period dividing "
        "the least common multiple of the denominators of the vertices of M (D).",
        "--statement",
        "The function $L$ is a quasi-polynomial in $k$ of degree equal to the dimension of $M(D)$, with a period "
        "dividing the least common multiple of the denominators of the vertices of $M(D)$.",
    )
    g.run(
        "refs",
        "propose",
        "Bellamy19",
        "--local",
        "def-4.1",
        "--page",
        "2",
        "--session",
        survey,
        "--source-text",
        "The defect of a weighted digraph is the least common multiple of the denominators of the vertices of its "
        "median polytope.",
        "--statement",
        "The \\emph{defect} of a weighted digraph is the least common multiple of the denominators of the vertices "
        "of its median polytope.",
        agent=True,
    )
    g.run(
        "refs",
        "link",
        "--from",
        "Bellamy19-thm-3.2",
        "--to",
        "Arden24-thm-3.1",
        "--kind",
        "depends-on",
        "--why",
        "Bellamy's counting theorem needs the polytope to be full-dimensional, and its dimension is Arden's rank.",
        "--session",
        survey,
        agent=True,
    )
    g.run(
        "refs",
        "link",
        "--from",
        "Bellamy19-thm-2.3",
        "--to",
        "Bellamy19-thm-3.2",
        "--kind",
        "specialises",
        "--why",
        "2.3 is the polytope; 3.2 counts its lattice points. The second is the one this quilt cites.",
        "--session",
        survey,
        agent=True,
    )
    # The agent's account of the run, said in the chat (plan 0.14).
    g.run(
        "session",
        "say",
        "Asked: find in Bellamy19 whatever the counting argument of Section 3 could rest on. Did: read pages 1 to 3, "
        "proposed four results, and asserted two links. Decided: nothing; the four proposals wait for the author. "
        "Remains: the examples of Section 4 are not proposed, since the paper states no result there beyond the "
        "definition of the defect.",
        "--session",
        survey,
        "--as",
        "Survey Agent",
        agent=True,
    )
    g.write(
        f".loom/sessions/{survey}/survey-bellamy.notes.md",
        _showcase_survey_report(),
    )

    # ---- The author decides on each proposal. ------------------------------------------------------------
    # Verified, verified with the rendering corrected, left pending, and discarded with a reason: the four
    # states 8.14 gives a proposal, all four visible in the digest view at once.
    g.at("2026-09-16T09:00:00Z")
    g.run("refs", "verify", "Bellamy19-thm-2.3", "--yes")
    g.run(
        "refs",
        "verify",
        "Bellamy19-thm-3.2",
        "--yes",
        "--statement",
        "Let $D$ be a weighted digraph whose weight function is balanced at every vertex. Then the counting "
        "function of the median polytope of $D$ agrees with a polynomial $L_{D}$ of degree $\\dim M(D)$ for every "
        "$k \\geq 0$, and the leading coefficient of $L_{D}$ is the relative volume of $M(D)$.",
    )
    g.run(
        "refs",
        "discard",
        "Bellamy19-def-4.1",
        "--reason",
        "The defect is defined in the sequel, not here; this paper only names it. Nothing in the quilt uses it.",
    )

    # ---- The author accepts what they are satisfied with. ------------------------------------------------
    # --force skips the compile check: the rows it writes do not depend on it, and the generator must write
    # the same bytes with or without a TeX distribution.
    g.at("2026-09-16T10:00:00Z")
    for key in ("sh-0001", "sh-0002", "sh-0003", "sh-0004", "sh-0005"):
        g.run("accept", key, "--force")
    for key in ("sh-0006", "sh-0007", "sh-0009"):
        g.run("accept", key, "--proofs", "--force")

    # ---- A referee run: one annotation of every kind, severity and state the model has. ------------------
    g.at("2026-09-16T11:00:00Z")
    referee = g.run("ai", "start", "referee-sh-0009").strip().splitlines()[-1].strip()
    g.run(
        "comment",
        "sh-0009",
        "The rank formula is stated for the underlying graph's component count, but nothing in the statement says "
        "that a loop counts as an arrow and contributes to the rank. Arden is explicit about it on "
        "[page 2](cited:arxiv:2504.01234v1?page=2); say so here too.",
        "--kind",
        "objection",
        "--severity",
        "major",
        "--quote",
        "underlying graph has $c$ connected components",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-0009/proof",
        "The kernel--image count is right but compressed into one clause. A reader checking it has to supply the "
        "rank--nullity step and the saturation step themselves. A replacement is attached.",
        "--kind",
        "suggestion",
        "--severity",
        "moderate",
        "--quote",
        "the rank of the kernel is the rank of the source less the rank of the image",
        "--payload",
        "the sequence $0 \\to \\Zcyc(\\quiv) \\to W(\\quiv) \\to \\operatorname{im} \\bd \\to 0$ is exact and "
        "$\\operatorname{im} \\bd$ is free, so it splits and the ranks add",
        "--placement",
        "replace",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-000C/proof",
        "Integrality of the vertices of $\\Pi$ does not follow from saturation of the cycle lattice: saturation is "
        "about the lattice, integrality is about the polytope's vertices, and Bellamy assumes the second "
        "([the balancing hypothesis](cited:doi:10.4171/showcase/19-2?quote=balanced%20at%20every%20vertex)). This is "
        "the gap Lemma~sh-000E is meant to close, and it is not closed.",
        "--kind",
        "objection",
        "--severity",
        "major",
        "--quote",
        "since $\\Pi$ has integral vertices by the saturation of Proposition~\\ref{sh-0007}",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-0006/proof",
        "Is the walk required to be a walk in the quiver, or only in the support? The two differ when an arrow of "
        "weight zero joins two arrows of the support.",
        "--kind",
        "question",
        "--quote",
        "we obtain an infinite walk inside $\\supp(w)$",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-0004",
        "Worth naming the quotient here: it is the group the divergence map lands in, and it is used twice later.",
        "--kind",
        "suggestion",
        "--severity",
        "minor",
        "--payload",
        "The quotient $W(\\quiv)/\\Zcyc(\\quiv)$ is the \\emph{boundary lattice} of $\\quiv$.",
        "--placement",
        "after",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "drafting/main-atomic.tex",
        "The paper never says whether quivers are assumed connected. Convention~sh-0001 says finite and says nothing "
        "about connectedness, and the rank formula is the only place it would matter.",
        "--kind",
        "suggestion",
        "--severity",
        "moderate",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-0200",
        "This section introduces the divergence map twice, once in prose and once as Definition sh-0003. Keep the "
        "definition.",
        "--kind",
        "suggestion",
        "--severity",
        "minor",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-0009#eq:rank",
        "The formula is right, and it is the one place the component count $c$ appears without being defined in the "
        "same breath.",
        "--kind",
        "objection",
        "--severity",
        "minor",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "Arden24-prop-2.1",
        "The transcription drops Arden's hypothesis that the quiver is finite, which is in his standing assumptions "
        "and not in the proposition. It is harmless here and would not be in a quilt that cited him for an infinite "
        "quiver.",
        "--kind",
        "objection",
        "--severity",
        "moderate",
        "--quote",
        "whose underlying graph has $c$ connected components",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-0005",
        "Both examples check out, and the second is the smallest quiver with trivial cycle lattice.",
        "--kind",
        "confirmation",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-000F",
        "The infinite case has a standard reference; cite it rather than pointing at a survey.",
        "--kind",
        "citation",
        "--payload",
        "Cortez, Flows on infinite quivers: a survey, Bull. Imag. Soc. 2007, Section 5",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-0008",
        "The remark asserts that no index creeps in, which is what Proposition sh-0007 says; the remark is redundant.",
        "--kind",
        "objection",
        "--severity",
        "minor",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-000B",
        "Height is defined for every weighting but only used for balanced ones.",
        "--kind",
        "suggestion",
        "--severity",
        "minor",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "sh-0007/proof",
        "This proof uses that the target of the divergence map is torsion-free, which is true of $\\ZZ^{V}$ and is "
        "never said. One clause fixes it.",
        "--kind",
        "objection",
        "--severity",
        "major",
        "--quote",
        "a homomorphism into a torsion-free group",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    (
        formula,
        expand,
        integrality,
        walk,
        boundary,
        document,
        section,
        equation,
        transcription,
        clean,
        citation,
        redundant,
        height,
        torsion,
    ) = _annotation_ids(dest, referee)[:14]
    # The agent's account of the run, said in the chat (plan 0.14).
    g.run(
        "session",
        "say",
        "Asked: referee the rank theorem and everything its proof reaches. Did: read the closure of sh-0009 and of "
        "sh-000C, and left fourteen findings -- three major, four moderate, five minor, one question and one clean "
        "read. Decided: nothing; every one of them is the author's to answer. Remains: the appendix (sh-0400) was "
        "not read, and Lemma sh-000E is marked incomplete, so there was nothing there to referee.",
        "--session",
        referee,
        "--as",
        "Referee (Agent)",
        agent=True,
    )
    g.write(
        f".loom/sessions/{referee}/referee-sh-0009.notes.md",
        _showcase_referee_report(formula=formula, expand=expand, integrality=integrality, document=document),
    )
    # The run withdraws one finding of its own and restates another: a discard is not a resolution, and an
    # edit is not a reply (DR-171, DR-174).
    g.at("2026-09-16T11:40:00Z")
    g.run(
        "comment",
        "--discard",
        redundant,
        "Proposition sh-0007 is a proposition and the remark is a remark; they are allowed to say the same thing.",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "--edit",
        height,
        "Height is defined for every weighting but only used for balanced ones, and $N_{\\quiv}(k)$ silently "
        "restricts to them. Say so in the definition rather than in the theorem that uses it.",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )

    # ---- The author answers. ------------------------------------------------------------------------------
    g.at("2026-09-16T15:00:00Z")
    g.run(
        "comment",
        "--reply",
        formula,
        "A loop contributes an arrow and no divergence, so it adds one to the rank. I will say it in Convention sh-0001 rather than in the theorem.",
    )
    g.at("2026-09-16T15:05:00Z")
    g.run(
        "comment",
        "--reply",
        formula,
        "Then the convention is the right place, and this finding can stand until it is there.",
        "--session",
        referee,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.at("2026-09-16T15:10:00Z")
    g.run("comment", "--resolve", expand, "Taken, with the exact sequence written out.")
    g.run("comment", "--resolve", walk, "The walk is a walk in the support, which is a subquiver.")
    g.run("comment", "--resolve", walk, "--undo")
    g.run(
        "refs",
        "note",
        "--from",
        referee,
        "--accept",
        citation,
        "--reason",
        "worth citing when the infinite case is written up",
    )
    g.run(
        "comment",
        "sh-000A",
        "Does this need the quiver to be connected, or does the component count handle it?",
        "--kind",
        "question",
        "--quote",
        "A quiver whose underlying graph is a forest",
    )
    g.run(
        "comment", "sh-0003", "Read against the definition in Arden24-def-1.2; the two agree.", "--kind", "confirmation"
    )

    # A second person, so the viewer has two comment sessions and not one.
    g.at("2026-09-17T09:00:00Z")
    g.run(
        "comment",
        "sh-000C",
        "I would split this: the polynomiality and the degree are two claims and only the first needs Bellamy.",
        "--kind",
        "suggestion",
        "--severity",
        "moderate",
        "--author",
        "Wren Halloway",
    )
    g.run(
        "comment",
        "--reply",
        integrality,
        "Agreed that this is the gap. I will not accept sh-000C until sh-000E is proved.",
        "--author",
        "Wren Halloway",
    )

    # ---- A run the author threw away. ---------------------------------------------------------------------
    g.at("2026-09-17T09:30:00Z")
    quick = g.run("ai", "start", "quick-pass").strip().splitlines()[-1].strip()
    g.run(
        "comment",
        "sh-0002",
        "A quiver should be required to be connected.",
        "--kind",
        "objection",
        "--severity",
        "major",
        "--session",
        quick,
        agent=True,
    )
    g.run(
        "comment",
        "sh-0005",
        "The bouquet is not a quiver.",
        "--kind",
        "objection",
        "--severity",
        "major",
        "--session",
        quick,
        agent=True,
    )
    g.run("ai", "discard", quick)

    # ---- A reading session: the author reads Bellamy, anchors to the page, and talks to an agent. ---------
    # Plan 0.13's reading layer, shown rather than described: an anchor into a filed PDF, a session shared with
    # an agent, and a message that waited in the inbox because nobody was attached.
    g.at("2026-09-17T11:00:00Z")
    reading = g.run("session", "new", "reading Bellamy 19").strip().splitlines()[0].split()[0]
    g.run(
        "comment",
        "Bellamy19-prop-3.1",
        "This is the form we use; the balanced case is the one that matters here.",
        "--kind",
        "note",
        "--session",
        reading,
    )
    g.run(
        "comment",
        "Bellamy19-thm-3.2",
        "Does this need the weights to be integral, or only bounded?",
        "--kind",
        "question",
        "--session",
        reading,
    )
    # Notes on the page itself (plan 0.13 item 2): one anchored to text the reader selected, one to a box drawn
    # around the display, both recorded against the work by its identifier.
    g.run(
        "comment",
        "Bellamy19",
        "Is total unimodularity really needed here, or only that the vertices are integral?",
        "--page",
        "2",
        "--quote",
        "totally unimodular",
        "--kind",
        "question",
        "--session",
        reading,
    )
    g.run(
        "comment",
        "Bellamy19",
        "This is the display we cite; the balanced case is the one that matters.",
        "--page",
        "2",
        "--box",
        "82,278,529,316",
        "--kind",
        "note",
        "--session",
        reading,
    )
    # The message carries what changed since the last one -- the notes above -- in the same text `session next`
    # prints, so a parked agent needs no second call to learn what it is being asked about.
    g.run(
        "session",
        "send",
        "Have a look at Bellamy's Theorem 3.2 and tell me whether integrality is used.",
        "--session",
        reading,
    )
    # The agent, attached, answers: a reply in the inbox, an edit of its own earlier objection in place, and a
    # suggestion asking the author for a verification it cannot make itself (DR-185's route).
    g.at("2026-09-17T11:10:00Z")
    g.run(
        "session",
        "send",
        "Integrality is used once, in the proof of Theorem 2.3: the vertex is integral because the matrix is totally unimodular. Theorem 3.2 only needs bounded weights.",
        "--session",
        reading,
        "--as",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "Bellamy19",
        "Answered on the page: unimodularity is the mechanism, integrality of the vertices is what is used downstream.",
        "--page",
        "2",
        "--quote",
        "the constraint matrix is an incidence matrix",
        "--kind",
        "note",
        "--session",
        reading,
        "--author",
        "Referee (Agent)",
        agent=True,
    )
    g.run(
        "comment",
        "Bellamy19-thm-3.2",
        "Please verify the transcription of 3.2 against p.2: the digest says 'integral' where the page says 'bounded'.",
        "--kind",
        "suggestion",
        "--severity",
        "moderate",
        "--session",
        reading,
        "--author",
        "Referee (Agent)",
        agent=True,
    )

    # ---- An orphan document, healed by the store. -----------------------------------------------------------
    # A document dropped into `refs/` is filed and offered an entry; the author deletes the entry; the store
    # outlives the bibliography, and the next scan offers it back (plan 0.13 item 6, `refs scan`'s adoption).
    g.at("2026-09-17T11:15:00Z")
    _tiny_pdf(g.root / "refs" / "Halloway - 2026 - Notes on balanced quivers.pdf")
    g.run("refs", "scan")
    bib = g.root / "digests" / "bibliography.bib"
    kept = [block for block in bib.read_text(encoding="utf-8").split("\n@") if "Notes on balanced quivers" not in block]
    bib.write_text("@".join(kept) if kept[0].startswith("@") else kept[0] + "@".join(kept[1:]), encoding="utf-8")
    g.run("refs", "scan")  # adopted: the entry is back, from the ledger's record of how the document arrived

    # ---- A work with no document to hold, declared rather than inferred. ----------------------------------
    g.at("2026-09-17T11:20:00Z")
    g.run(
        "refs",
        "unreadable",
        "Stacks",
        "--why",
        "a living work with no fixed version; there is no document to file",
    )

    # ---- A session closed when its work was done; its annotations stop being shown. -----------------------
    g.at("2026-09-17T11:30:00Z")
    g.run("session", "close", reading)

    # ---- The author edits, which is what makes states move. -----------------------------------------------
    # Editing the convention makes its dependents stale; editing the first proof of sh-0007 detaches the
    # annotation that quoted it. Neither is corrected and neither is hidden.
    g.at("2026-09-17T10:00:00Z")
    g.edit(
        "nodes/sh-0001.tex",
        "Every quiver in this paper is finite: both $V(\\quiv)$ and $A(\\quiv)$ are finite sets, and loops and parallel arrows are allowed.",
        "Every quiver in this paper is finite: both $V(\\quiv)$ and $A(\\quiv)$ are finite sets, and loops and parallel arrows are allowed, a loop counting as one arrow and contributing no divergence.",
    )
    g.edit(
        "nodes/sh-0007.tex",
        "The divergence map is a homomorphism into a torsion-free group, so $\\bd(n w) = n \\, \\bd w = 0$ forces $\\bd w = 0$.",
        "The divergence map is a homomorphism into $\\ZZ^{V}$, which is torsion-free, so $\\bd(n w) = n \\, \\bd w = 0$ forces $\\bd w = 0$.",
    )
    g.at("2026-09-17T10:05:00Z")
    g.run("stamp", "-m", "Referee points answered")
    g.at("2026-09-17T10:10:00Z")
    g.run("canonize", "drafting/main-atomic.tex", "--to", "canon/flows-v2.tex", "-m", "After the referee", "--no-check")

    # An edit the author thinks better of: revert puts the recorded text back.
    g.at("2026-09-17T11:00:00Z")
    g.edit("nodes/sh-0008.tex", "an honest dimension count", "a dimension count one can trust")
    g.at("2026-09-17T11:05:00Z")
    out = g.run("revert", "sh-0008@1")
    g.apply_patch(out[out.index("--- nodes/sh-0008.tex") :])

    # ---- A second master, and a node forked for it. -------------------------------------------------------
    _later("showcase", "drafting/talk.tex", dest)
    g.at("2026-09-17T12:00:00Z")
    out = g.run("fork", "sh-0006", "--in", "drafting/talk.tex")
    g.apply_patch(out[out.index("--- drafting/talk.tex") :])
    forked = re.search(r"Wrote nodes/(sh-[0-9A-Z]{4})\.tex", out)
    assert forked, out
    # The talk's copy is shortened for the slide, and loses the reference the slide cannot show.
    g.edit(
        f"nodes/{forked.group(1)}.tex",
        "Then the support $\\supp(w)$ contains a directed cycle of $\\quiv$.",
        "Then $\\supp(w)$ contains a directed cycle.",
    )
    g.edit(f"nodes/{forked.group(1)}.tex", "\\uses{sh-0001}\n", "")
    g.edit(
        f"nodes/{forked.group(1)}.tex",
        "which is a finite set by Convention~\\ref{sh-0001}, so some vertex repeats",
        "which is finite, so some vertex repeats",
    )
    g.at("2026-09-17T12:05:00Z")
    g.run("stamp", "-m", "Talk prepared", "--in", "drafting/talk.tex")

    # ---- A lemma the author started and has not placed. ---------------------------------------------------
    g.at("2026-09-18T09:00:00Z")
    out = g.run("new", "lemma", "Integral vertices of the flow polytope")
    fresh = re.search(r"nodes/(sh-[0-9A-Z]{4})\.tex", out)
    assert fresh, out
    g.write(
        f"nodes/{fresh.group(1)}.tex",
        f"% !LOOM created: 2026-09-18\n"
        f"% !LOOM tags: outlook\n"
        f"% !LOOM see: sh-000E\n\n"
        f"\\begin{{lemma}}[Integral vertices of the flow polytope]\\label{{{fresh.group(1)}}}\n"
        "Every vertex of $\\Pi$ is the indicator weighting of a directed cycle of $\\quiv$, up to sign.\n"
        "\\end{lemma}\n",
    )

    # ---- The last fault: one id defined twice. ------------------------------------------------------------
    # The author atomized a sketch, changed their mind, and made the original live again without removing the
    # node file the conversion wrote. Both files now define sh-0020, so it is conflicted: no text, no winner.
    _later("showcase", "drafting/sketch.tex", dest)
    g.at("2026-09-18T10:00:00Z")
    g.run("atomize", "drafting/sketch.tex", "drafting/sketch-atomic.tex")
    g.at("2026-09-18T10:05:00Z")
    g.run("live", "drafting/sketch.tex")

    _write_expected_lint(g)
    # The seed space is the author's and is not in version control (8.16), so the committed quilt is what a
    # coauthor's clone looks like: loom's store, and no `refs/`. The copy ledger keeps a second `refs scan`
    # from filing the same documents again.
    shutil.rmtree(dest / "refs")


def _showcase_referee_report(*, formula: str, expand: str, integrality: str, document: str) -> str:
    """The referee run's report, in the shape `ai/rules.md` asks for: named blocks, findings ending in the id of the annotation that carries them, and a notation block for the panel."""
    return f"""## [summary]
The rank theorem is correct and its proof is complete. The counting theorem is not: it takes integrality of the polytope's vertices from a saturation statement that does not give it, and the lemma meant to close that gap is marked incomplete. Everything else here is exposition.

## [notation]
- $\\Zcyc(\\quiv)$ is the cycle lattice, written $\\mathcal{{Z}}(Q)$ in Arden24.
- $\\Pi$ is the flow polytope of sh-000C; Bellamy's $M(D)$ is a different polytope over the same arc set.
- $c$ is the number of connected components of the underlying graph.

## [referee-review] Major and minor issues

### Major Issues
- Integrality of the vertices of $\\Pi$ is asserted from saturation of $\\Zcyc(\\quiv)$, and saturation is a statement about the lattice rather than about the polytope. Bellamy's theorem assumes the second. ({integrality})
- The rank formula does not say how a loop is counted, and the answer changes the rank. ({formula})

### Minor Issues
- The kernel--image step of the rank proof is one clause doing three things; a replacement is attached. ({expand})

### Clarity/Exposition
- Connectedness is never assumed and never excluded, and the rank formula is the one statement where it would matter. ({document})

## [decision]
Minor Revision for the rank theorem; the counting theorem needs the integrality lemma before it can be accepted.
"""


def _showcase_survey_report() -> str:
    """The survey run's report, written the way `ai/rules.md` asks: named blocks, and a notation block the panel can read."""
    return """## [summary]
Bellamy19 is a PDF with no source, so every result here was read off a page and anchored to it. Four results proposed: the polytope theorem (2.3), the counting theorem (3.2), the quasi-polynomial proposition (3.1) and the definition of the defect (4.1). The two theorems are the paper's main results and are proposed at level 1.

## [notation]
- $M(D)$ is the median polytope of the weighted digraph $D$; the paper writes it $M (D)$, which is the PDF's spacing and not a product.
- $L(k)$ counts lattice points of the dilate $kM(D)$.

## [findings]
- Theorem 3.2 is the one this quilt should cite. Theorem 2.3 is what makes its hypothesis checkable, and the two are linked `specialises`.
- Proposition 3.1 is the quasi-polynomial version and is proposed without a level: it is the general statement, and the quilt uses only the balanced case.
- Definition 4.1 is a forward reference to the sequel and carries nothing this quilt needs.

## [decision]
Nothing verified here; four proposals wait for the author.
"""


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


BUILDERS = {"synthetic": build_synthetic, "demo": build_demo, "showcase": build_showcase}


def _sync(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    # A session's readers' cursors and heartbeat are runtime state the quilt's .gitignore keeps out.
    shutil.copytree(
        src, dest, ignore=shutil.ignore_patterns("build", "__pycache__", ".git", "cursors", "attached.json")
    )


def _differences(a: Path, b: Path) -> list[str]:
    out: list[str] = []

    def committed(rel: str) -> bool:
        # The generator uses these copies while building the quilt, but the
        # quilt's .gitignore deliberately keeps them out of its committed copy.
        return not (
            rel.startswith("refs/")
            or (rel.startswith(".loom/sessions/") and ("/cursors/" in rel or rel.endswith("/attached.json")))
            or rel.startswith("digests/storage/cache/")
            or (rel.startswith("digests/storage/") and "/src/" in rel)
        )

    files = {rel for p in a.rglob("*") if p.is_file() if committed(rel := p.relative_to(a).as_posix())}
    other = {rel for p in b.rglob("*") if p.is_file() if committed(rel := p.relative_to(b).as_posix())}
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
