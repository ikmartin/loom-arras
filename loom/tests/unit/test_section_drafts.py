"""Section drafts isolate source edits without hiding shared-source consequences."""

from pathlib import Path

import pytest

from loom.adopt import comparison, incorporate, prepare, refresh
from loom.history.ledger import load_history
from loom.history.steps import write_step
from loom.reshape.copy import plan_copy
from loom.scan.quilt import load_quilt, save_author
from loom.scan.scan import scan
from loom.section_drafts import capture_context, check_overlap
from loom.sync import SyncError

DOC = "drafting/main.tex"
TEXT = r"""\documentclass{article}
\newtheorem{lemma}{Lemma}
\begin{document}
\section{First}\label{zk-0100}
First prose.
\begin{lemma}\label{zk-0001}
First statement.
\end{lemma}
\subsection{Details}\label{zk-0101}
Detail prose.
\section{Second}\label{zk-0200}
Second prose.
\begin{lemma}\label{zk-0002}
Second statement uses \ref{zk-0001}.
\end{lemma}
\end{document}
"""


@pytest.fixture
def quilt(tmp_path: Path):
    save_author("Tester")
    (tmp_path / "drafting").mkdir()
    (tmp_path / "drafting-ai").mkdir()
    (tmp_path / "config.toml").write_text('[quilt]\nname="sections"\nprefix="zk"\nmain="drafting/main.tex"\n')
    (tmp_path / DOC).write_text(TEXT)
    return load_quilt(tmp_path)


def copy(q, key="zk-0100", name="first"):
    result = scan(q)
    h = load_history(q.history_dir)
    target = f"drafting-ai/{name}.tex"
    p = plan_copy(result, h, DOC, target, key)
    check_overlap(result, DOC, p.scope)
    context = capture_context(result, DOC)
    (q.root / target).write_text(p.text)
    write_step(
        h,
        "copy",
        "copy-" + name,
        p.freeze,
        "Tester",
        {"from": DOC, "to": target, "bases": p.bases, "scope": p.scope, "suffix": p.suffix, "context": context},
        p.source_text,
        "main.tex",
    )
    return target


def edit(q, path, old, new):
    p = q.root / path
    p.write_text(p.read_text().replace(old, new))


def test_two_scopes_and_qualified_identity(quilt):
    a = copy(quilt)
    b = copy(quilt, "zk-0200", "second")
    assert "zk-0001-ai-01" in (quilt.root / a).read_text()
    assert "zk-0002-ai-02" in (quilt.root / b).read_text()
    assert "Second prose" not in (quilt.root / a).read_text()
    assert "zk-0001}" in (quilt.root / b).read_text()
    assert scan(quilt).nodes["zk-0001-ai-01"].derived_of == "zk-0001"
    with pytest.raises(SyncError, match="overlaps"):
        copy(quilt, "zk-0101", "details")


def test_section_adoption_preserves_outside_and_partial_proposals(quilt):
    a = copy(quilt)
    edit(quilt, a, "First statement.", "Improved statement.")
    edit(quilt, a, "First prose.", "Improved prose.")
    edit(quilt, DOC, "Second prose.", "Author's new second prose.")
    result = scan(quilt)
    data = comparison(result, a)
    assert {r["key"] for r in data["changes"]} == {"zk-0001"}
    p = prepare(result, a, ["zk-0001"])
    incorporate(scan(quilt), a, p["token"])
    assert (quilt.root / DOC).read_text() == TEXT.replace("First statement.", "Improved statement.").replace(
        "Second prose.", "Author's new second prose."
    )
    assert comparison(scan(quilt), a)["document_changed"]
    p = prepare(scan(quilt), a, [], True)
    incorporate(scan(quilt), a, p["token"])
    assert "Improved prose." in (quilt.root / DOC).read_text()
    assert not prepare(scan(quilt), a, [], True)["patch"]


def test_preamble_is_independent(quilt):
    a = copy(quilt)
    edit(quilt, a, "\\begin{document}", "\\newcommand{\\foo}{x}\n\\begin{document}")
    edit(quilt, a, "First prose.", "New prose.")
    p = prepare(scan(quilt), a, [], True)
    assert "newcommand" not in p["patch"]
    incorporate(scan(quilt), a, p["token"])
    p = prepare(scan(quilt), a, [], preamble=True)
    assert "newcommand" in p["patch"]
    incorporate(scan(quilt), a, p["token"])
    assert not comparison(scan(quilt), a)["preamble_changed"]


def test_refresh_retains_scope_namespace_and_proposals(quilt):
    a = copy(quilt)
    edit(quilt, a, "First statement.", "Proposal.")
    edit(quilt, DOC, "Detail prose.", "New author detail.")
    edit(quilt, DOC, "Second prose.", "Unrelated change.")
    refresh(scan(quilt), a)
    text = (quilt.root / a).read_text()
    assert "Proposal." in text and "New author detail." in text
    assert "Unrelated change." not in text and "zk-0001-ai-01" in text
    assert not refresh(scan(quilt), a)["updated"]


def test_root_removal_or_escape_refused(quilt):
    a = copy(quilt)
    edit(quilt, a, "\\end{document}", "\\section{Escaped}Outside.\n\\end{document}")
    with pytest.raises(SyncError, match="outside"):
        comparison(scan(quilt), a)
    assert (quilt.root / DOC).read_text() == TEXT


def test_included_section_preserves_inclusion_and_other_file(quilt):
    (quilt.root / "parts").mkdir()
    start = TEXT.index("\\section{First}")
    end = TEXT.index("\\section{Second}")
    (quilt.root / "parts/first.tex").write_text(TEXT[start:end])
    (quilt.root / DOC).write_text(TEXT[:start] + "\\input{parts/first}\n" + TEXT[end:])
    before = (quilt.root / DOC).read_text()
    a = copy(quilt)
    edit(quilt, a, "First prose.", "New prose.")
    p = prepare(scan(quilt), a, [], True)
    incorporate(scan(quilt), a, p["token"])
    assert (quilt.root / DOC).read_text() == before
    assert "New prose." in (quilt.root / "parts/first.tex").read_text()


def test_close_keeps_snapshot_frees_scope_and_reopen_checks_overlap(quilt):
    from loom.draft_lifecycle import close_draft, reopen_draft
    from loom.render.build import build

    a = copy(quilt)
    edit(quilt, a, "First statement.", "Proposal.")
    before = (quilt.root / a).read_bytes()
    assert close_draft(scan(quilt), a, "Tester")["confirmation_required"]
    assert a in scan(quilt).masters
    assert close_draft(scan(quilt), a, "Tester", confirmed=True)["closed"]
    result = scan(quilt)
    assert a not in result.masters
    assert "zk-0001-ai-01" not in result.nodes
    manifest = build(quilt).manifest
    closed = next(m for m in manifest["masters"] if m["path"] == a)
    assert closed["closed"] and "zk-0001-ai-01" in closed["closed_keys"]
    assert "Proposal." in (quilt.root / "build" / closed["fragment"]).read_text()
    assert (quilt.root / a).read_bytes() == before
    b = copy(quilt, name="replacement")
    with pytest.raises(SyncError, match="overlaps"):
        reopen_draft(scan(quilt), a, "Tester")
    close_draft(scan(quilt), b, "Tester", confirmed=True)
    assert not reopen_draft(scan(quilt), a, "Tester")["closed"]
    assert a in scan(quilt).masters


def test_saved_context_stays_readable_until_refresh(quilt):
    from loom.drafts import copy_states
    from loom.render.build import build
    from loom.section_drafts import pinned_scan

    a = copy(quilt, "zk-0200", "second")
    edit(quilt, DOC, "First statement.", "Changed outside scope.")
    saved = pinned_scan(scan(quilt), a)
    assert "First statement." in saved.files[DOC].text
    state = copy_states(scan(quilt), load_history(quilt.history_dir))[0]
    assert not state.stale
    manifest = build(quilt).manifest
    master = next(m for m in manifest["masters"] if m["path"] == a)
    assert master["context_changed"]
    html = (quilt.root / "build" / master["fragment"]).read_text()
    assert "data-context-document=" in html
    context = next(m for m in manifest["masters"] if m["path"] == master["context_document"])
    assert "First statement." in (quilt.root / "build" / context["fragment"]).read_text()
    refresh(scan(quilt), a)
    assert "Changed outside scope." in pinned_scan(scan(quilt), a).files[DOC].text


def test_choices_cas_and_only_changed_choices_invalidated(quilt):
    from loom.adopt import decide, decisions

    a = copy(quilt)
    edit(quilt, a, "First statement.", "Proposal.")
    result = scan(quilt)
    data = comparison(result, a)
    row = decide(result, a, ["zk-0001"], False, data["fingerprint"], "Tester", revision=0)
    assert row["revision"] == 1
    with pytest.raises(SyncError, match="another tab"):
        decide(result, a, [], False, data["fingerprint"], "Tester", revision=0)
    edit(quilt, DOC, "Second prose.", "Unrelated.")
    assert decisions(scan(quilt), a, "Tester")["keys"] == ["zk-0001"]
    edit(quilt, a, "Proposal.", "Different proposal.")
    choices = decisions(scan(quilt), a, "Tester")
    assert choices["keys"] == [] and choices["invalidated"] == ["zk-0001"]


def test_missing_preamble_definition_requires_explicit_choice(quilt):
    a = copy(quilt)
    edit(quilt, a, "\\begin{document}", "\\newcommand{\\newterm}{x}\n\\begin{document}")
    edit(quilt, a, "First statement.", r"Now $\newterm$.")
    with pytest.raises(SyncError, match="Include Preamble"):
        prepare(scan(quilt), a, ["zk-0001"])
    p = prepare(scan(quilt), a, ["zk-0001"], preamble=True)
    assert "newcommand" in p["patch"]


def test_source_move_keeps_scope_and_current_destination(quilt):
    from tests.helpers import ok

    a = copy(quilt)
    edit(quilt, a, "First statement.", "Moved proposal.")
    ok("mv", DOC, "drafting/renamed.tex", cwd=quilt.root)
    result = scan(load_quilt(quilt.root))
    p = prepare(result, a, ["zk-0001"])
    assert p["source"] == "drafting/renamed.tex"
    incorporate(result, a, p["token"])
    assert "Moved proposal." in (quilt.root / "drafting/renamed.tex").read_text()


def test_shared_node_in_disjoint_scopes_changes_once(quilt):
    (quilt.root / "nodes").mkdir()
    node = TEXT[TEXT.index("\\begin{lemma}") : TEXT.index("\\end{lemma}") + len("\\end{lemma}")]
    (quilt.root / "nodes/shared.tex").write_text(node)
    text = TEXT.replace(node, "\\input{nodes/shared}")
    text = text.replace("Second prose.", "Second prose.\n\\input{nodes/shared}")
    (quilt.root / DOC).write_text(text)
    a = copy(quilt)
    b = copy(quilt, "zk-0200", "second")
    edit(quilt, a, "First statement.", "Shared proposal.")
    p = prepare(scan(quilt), a, ["zk-0001"])
    incorporate(scan(quilt), a, p["token"])
    assert (quilt.root / DOC).read_text() == text
    assert "Shared proposal." in (quilt.root / "nodes/shared.tex").read_text()
    assert any(
        row["key"] == "zk-0001" and "Shared proposal." in row["current"]
        for row in comparison(scan(quilt), b)["changes"]
    )


@pytest.mark.tex
def test_section_preview_compiles_in_saved_paper_context(quilt):
    from loom.section_drafts import preview_in_paper

    a = copy(quilt, "zk-0200", "second")
    preview = preview_in_paper(scan(quilt), a)
    assert (quilt.root / "build" / preview["pdf"]).read_bytes().startswith(b"%PDF")
    assert (quilt.root / DOC).read_text() == TEXT


def test_close_draft_with_removed_scope_root_keeps_its_text(quilt):
    from loom.draft_lifecycle import close_draft

    a = copy(quilt)
    edit(quilt, a, "\\label{zk-0100-ai-01}", "")
    assert close_draft(scan(quilt), a, "Tester")["confirmation_required"]
    close_draft(scan(quilt), a, "Tester", confirmed=True)
    assert a not in scan(quilt).masters


def test_local_style_edit_invalidates_exact_preview(quilt):
    (quilt.root / "local.sty").write_text("\\newcommand{\\localterm}{x}\n")
    edit(quilt, DOC, "\\begin{document}", "\\usepackage{local}\n\\begin{document}")
    a = copy(quilt)
    edit(quilt, a, "First statement.", "Changed statement.")
    p = prepare(scan(quilt), a, ["zk-0001"])
    (quilt.root / "local.sty").write_text("\\newcommand{\\localterm}{y}\n")
    with pytest.raises(SyncError, match="context changed"):
        incorporate(scan(quilt), a, p["token"])
