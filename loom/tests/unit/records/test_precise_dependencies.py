"""Equation freshness follows whole displays and explicit support, never section ownership."""

from pathlib import Path

from loom.cli.review import write_acceptance
from loom.records.store import Records
from loom.review_queue import fingerprint
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.helpers import ok


def quilt(tmp_path: Path):
    root = tmp_path / "q"
    ok("init", str(root), "--demo", cwd=tmp_path)
    path = root / "drafting" / "main.tex"
    path.write_text(r"""\documentclass{article}
\usepackage{amsmath}
\newtheorem{lemma}{Lemma}
\begin{document}
\section{Outer}\label{sec:outer}
Unrelated prose.
\subsection{Inner}\label{sec:inner}
\begin{align}\label{eq:first}
x&=1\\
y&=2\label{eq:second}
\end{align}
\begin{lemma}\label{q-0001}
% !LOOM basis: assumption
Use \eqref{eq:first}; see \ref{sec:outer}.
\end{lemma}
\end{document}
""")
    return root, path


def test_section_prose_and_pending_decision_ignore_containment(tmp_path):
    root, path = quilt(tmp_path)
    r = scan(load_quilt(root))
    write_acceptance(r, ["q-0001"], "Reviewer")
    before = fingerprint(r, "q-0001")
    path.write_text(path.read_text().replace("Unrelated prose.", "Changed unrelated prose."))
    now = scan(load_quilt(root))
    rec = Records(root, now.quilt.history_dir, reviewer="Reviewer")
    assert rec.key_states(now)["q-0001"].fresh
    assert fingerprint(now, "q-0001") == before
    assert rec.derived(now, rec.key_states(now))["q-0001"]["settled"]
    assert rec.direct_keys(now, "q-0001") == ["equation:eq:first"]


def test_whole_display_change_and_removal(tmp_path):
    root, path = quilt(tmp_path)
    r = scan(load_quilt(root))
    write_acceptance(r, ["q-0001"], "Reviewer")
    path.write_text(path.read_text().replace("y&=2", "y&=3"))
    now = scan(load_quilt(root))
    rec = Records(root, now.quilt.history_dir, reviewer="Reviewer")
    causes = rec.key_states(now)["q-0001"].causes
    assert [(c.kind, c.id) for c in causes] == [("dependency-changed", "equation:eq:first")]
    assert "y&=2" in rec.diff_for(now, causes[0], "q-0001")
    path.write_text(path.read_text().replace(r"\label{eq:first}", ""))
    now = scan(load_quilt(root))
    assert any(c.kind == "dependency-removed" for c in rec.key_states(now)["q-0001"].causes)


def test_legacy_owner_snapshot_recovers_exact_equation(tmp_path):
    from loom.records.ledger import AcceptRow, append_rows
    from loom.records.snapshots import write_snapshot
    from loom.render.manifest import own_text

    root, path = quilt(tmp_path)
    r = scan(load_quilt(root))
    owner = r.dependencies.owners["equation:eq:first"]
    own, _ = write_snapshot(root, own_text(r, r.nodes["q-0001"]), r.quilt.history_dir)
    prior, _ = write_snapshot(root, own_text(r, r.nodes[owner]), r.quilt.history_dir)
    append_rows(
        root,
        [
            AcceptRow(
                "q-0001",
                "Reviewer",
                "2026-09-28T00:00:00Z",
                own,
                "",
                r.default_master,
                {owner: prior},
                direct={owner: prior},
            )
        ],
    )
    path.write_text(path.read_text().replace("y&=2", "y&=3"))
    now = scan(load_quilt(root))
    causes = Records(root, now.quilt.history_dir, reviewer="Reviewer").key_states(now)["q-0001"].causes
    assert [(c.kind, c.id) for c in causes] == [("dependency-changed", "equation:eq:first")]


def test_equation_support_and_enclosing_statement_are_distinct(tmp_path):
    root, path = quilt(tmp_path)
    source = (
        path.read_text()
        .replace(
            r"\begin{align}",
            r"\begin{lemma}\label{q-0002}" + "\n% !LOOM basis: assumption\nEnclosing claim.\n" + r"\begin{align}",
        )
        .replace(r"\end{align}", r"\end{align}\end{lemma}")
    )
    source = source.replace("x&=1", r"x&=1\quad\text{by \ref{q-0003}}")
    source = source.replace(
        r"\end{document}",
        r"\begin{lemma}\label{q-0003}" + "\n% !LOOM basis: assumption\nSupport claim.\n" + r"\end{lemma}\end{document}",
    )
    path.write_text(source)
    r = scan(load_quilt(root))
    write_acceptance(r, ["q-0001", "q-0002", "q-0003"], "Reviewer")
    path.write_text(source.replace("Enclosing claim.", "Changed enclosing claim."))
    now = scan(load_quilt(root))
    rec = Records(root, now.quilt.history_dir, reviewer="Reviewer")
    states = rec.key_states(now)
    assert states["q-0001"].fresh
    assert not states["q-0002"].fresh
    assert "q-0002" not in now.dependencies.closure("q-0001")
    path.write_text(source.replace("Support claim.", "Changed support claim."))
    now = scan(load_quilt(root))
    causes = rec.key_states(now)["q-0001"].causes
    assert any(c.id == "q-0003" and c.via == "equation:eq:first" for c in causes)
    assert not rec.derived(now, rec.key_states(now))["q-0001"]["settled"]


def test_unknown_display_is_not_accepted_or_treated_as_fresh(tmp_path):
    import pytest

    from loom.cli._common import ContentError

    root, path = quilt(tmp_path)
    r = scan(load_quilt(root))
    write_acceptance(r, ["q-0001"], "Reviewer")
    path.write_text(
        path.read_text().replace(r"\begin{align}", r"\begin{custommath}").replace(r"\end{align}", r"\end{custommath}")
    )
    now = scan(load_quilt(root))
    state = Records(root, now.quilt.history_dir, reviewer="Reviewer").key_states(now)["q-0001"]
    assert not state.fresh
    assert any(c.kind == "dependency-scope-unavailable" for c in state.causes)
    with pytest.raises(ContentError):
        write_acceptance(now, ["q-0001"], "Reviewer")


def test_other_reviewer_has_no_invented_equation_baseline(tmp_path):
    root, path = quilt(tmp_path)
    r = scan(load_quilt(root))
    write_acceptance(r, ["q-0001"], "Alice")
    state = Records(root, r.quilt.history_dir, reviewer="Bob").key_states(r)["q-0001"]
    assert state.row is None


def test_section_removal_and_equation_move_do_not_change_context(tmp_path):
    root, path = quilt(tmp_path)
    r = scan(load_quilt(root))
    write_acceptance(r, ["q-0001"], "Reviewer")
    old = fingerprint(r, "q-0001")
    path.write_text(
        path.read_text()
        .replace(r"\section{Outer}\label{sec:outer}", "")
        .replace(r"\subsection{Inner}\label{sec:inner}", "")
    )
    now = scan(load_quilt(root))
    assert fingerprint(now, "q-0001") == old
    assert Records(root, now.quilt.history_dir, reviewer="Reviewer").key_states(now)["q-0001"].fresh
    assert any(d.code == "dangling-link" for d in now.edges.diagnostics)


def test_missing_legacy_evidence_is_explicit(tmp_path):
    from loom.records.ledger import AcceptRow, append_rows
    from loom.records.snapshots import write_snapshot
    from loom.render.manifest import own_text

    root, _ = quilt(tmp_path)
    r = scan(load_quilt(root))
    owner = r.dependencies.owners["equation:eq:first"]
    own, _ = write_snapshot(root, own_text(r, r.nodes["q-0001"]), r.quilt.history_dir)
    append_rows(
        root,
        [
            AcceptRow(
                "q-0001",
                "Reviewer",
                "2026-09-28T00:00:00Z",
                own,
                "",
                r.default_master,
                {owner: "sha256:" + "0" * 64},
                direct={owner: "sha256:" + "0" * 64},
            )
        ],
    )
    state = Records(root, r.quilt.history_dir, reviewer="Reviewer").key_states(r)["q-0001"]
    assert not state.fresh
    assert [(c.kind, c.id) for c in state.causes] == [("dependency-baseline-unavailable", "equation:eq:first")]
    write_acceptance(r, ["q-0001"], "Reviewer")
    assert Records(root, r.quilt.history_dir, reviewer="Reviewer").key_states(r)["q-0001"].fresh
