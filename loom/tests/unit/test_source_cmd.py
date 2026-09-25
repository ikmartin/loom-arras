"""`loom source`: a key as written, its closure as one document, a whole document flattened, and an equation's label read through to the node that holds it; nothing is written, and a call naming a session is logged there."""

from __future__ import annotations

from pathlib import Path

from tests.helpers import ok, refused
from tests.unit._quilts import demo


def test_source_prints_a_key_and_its_closure(tmp_path: Path) -> None:
    """`loom source` replaced `loom bundle` as the way to read a result: it prints, so there is no file to go stale."""
    d = demo(tmp_path)
    sid = ok("ai", "start", "Reading dm-0002", cwd=d).stdout.strip()
    run_dir = d / ".loom" / "sessions" / sid
    r = ok("source", "dm-0002", "--session", sid, cwd=d)
    assert r.output.startswith("\\begin{lemma}[Orbits]\\label{dm-0002}")
    assert "% id:" not in r.output  # the key alone, not the closure document
    assert not list(run_dir.glob("*.tex"))  # nothing written into the session
    assert "loom source dm-0002" in (run_dir / "run.log").read_text()

    # the theorem's own closure is empty -- its dependency is declared inside the proof, so the proof key is the one with something to gather, which is also what a referee reads
    c = ok("source", "dm-0003/proof", "--closure", cwd=d)
    assert c.output.index("% id: dm-0002") < c.output.index("% id: dm-0003") < c.output.index("% proof: dm-0003/proof")
    assert "\\usepackage{loom}" in c.output


def test_source_prints_a_whole_document_flattened(tmp_path: Path) -> None:
    """An agent asked about a paper rather than a result needs the document; `loom linearize` would do it by superseding the master, and is denied to agents, so `loom source` takes a path (DR-155)."""
    d = demo(tmp_path)
    sid = ok("ai", "start", "Reading the paper", cwd=d).stdout.strip()
    run_dir = d / ".loom" / "sessions" / sid
    r = ok("source", "drafting/main.tex", "--session", sid, cwd=d)
    assert "\\documentclass" in r.output  # the document, preamble and all
    assert "\\input{" not in r.output  # every inclusion expanded in place
    assert "\\begin{lemma}[Orbits]\\label{dm-0002}" in r.output  # including the node files it pulls in
    assert "loom source drafting/main.tex" in (run_dir / "run.log").read_text()

    before = sorted(p.relative_to(d) for p in d.rglob("*.tex"))
    ok("source", "drafting/main.tex", cwd=d)
    assert sorted(p.relative_to(d) for p in d.rglob("*.tex")) == before  # nothing written, nothing superseded

    # --closure is a key's option
    refused("source", "drafting/main.tex", "--closure", cwd=d, code=2, match="already carries what it includes")

    # a path loom does not scan is not a document
    refused("source", "ai/runs/t/nope.tex", cwd=d, code=2, match="no such key: ai/runs/t/nope.tex")


def test_a_statements_closure_covers_the_proof_it_prints(tmp_path: Path) -> None:
    """The bundle printed the proof and excluded the lemmas that proof invokes, so an agent told the bundle was complete context saw undefined references (F2)."""
    d = demo(tmp_path)
    r = ok("source", "dm-0003", "--closure", cwd=d)
    ids = [ln.split()[-1] for ln in r.output.splitlines() if ln.startswith("% id:") or ln.startswith("% proof:")]
    assert "dm-0002" in ids  # used by dm-0003's proof, which this bundle prints
    assert ids[-1] == "dm-0003/proof" and ids.index("dm-0002") < ids.index("dm-0003")


def test_source_on_an_equation_label_prints_what_holds_it(tmp_path: Path) -> None:
    """An equation's label names a region, not a node, so `source` prints the node the equation sits inside."""
    d = demo(tmp_path)
    digest = d / "digests" / "Calloway14.tex"
    digest.write_text(
        digest.read_text()
        + "\n\\section*{Overview}\nWe prove\n\\begin{equation}\\label{Calloway14-eqx}x=y\\end{equation}\n"
    )
    r = ok("source", "Calloway14-eqx", cwd=d)
    assert "inside" in r.output and "x=y" in r.output, r.output
