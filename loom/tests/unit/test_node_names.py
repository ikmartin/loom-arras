from pathlib import Path

from loom.cli._quilt import open_scan
from loom.records.snapshots import read_snapshot
from loom.records.store import Records
from loom.render.manifest import key_hash
from loom.review_queue import decide, pending
from tests.helpers import ok
from tests.unit._quilts import demo


def test_renaming_preserves_own_and_downstream_acceptance_and_pending_ok(tmp_path: Path) -> None:
    q = demo(tmp_path)
    ok("accept", "dm-0001", "dm-0002", "--proofs", "--author", "A. Author", cwd=q)
    before = open_scan(str(q))
    original = key_hash(before, "dm-0001")
    decide(before, "dm-0002/proof", "ok")
    source = q / "nodes/dm-0001.tex"
    text = source.read_text()
    source.write_text(text.replace("\\end{definition}", "% !LOOM name: Fixed points\n\\end{definition}"))
    after = open_scan(str(q))
    assert after.nodes["dm-0001"].directives["name"] == "Fixed points"
    assert key_hash(after, "dm-0001") != original
    assert "Fixed points" not in read_snapshot(q, original)
    states = Records(q).key_states(after)
    assert all(states[k].fresh for k in ("dm-0001", "dm-0002", "dm-0002/proof"))
    assert pending(after) == ["dm-0002/proof"]
    ok("accept", "dm-0001", "--author", "A. Author", cwd=q)
    saved = Records(q).latest["dm-0001"].text
    assert "Fixed points" in read_snapshot(q, saved)
    source.write_text(source.read_text().replace("Fixed points", "Fixed-point definition"))
    assert Records(q).key_states(open_scan(str(q)))["dm-0001"].fresh
    source.write_text(source.read_text().replace("\\end{definition}", "A new hypothesis.\n\\end{definition}"))
    assert not Records(q).key_states(open_scan(str(q)))["dm-0001"].fresh


def test_name_metadata_is_node_local_and_invalid_names_are_diagnosed(tmp_path: Path) -> None:
    q = demo(tmp_path)
    source = q / "nodes/dm-0001.tex"
    source.write_text("% !LOOM name: must not inherit\n" + source.read_text())
    result = open_scan(str(q))
    assert "name" not in result.nodes["dm-0001"].directives
    assert any(d.code == "loom:invalid-name" for d in result.lint)
    source.write_text(
        source.read_text().replace("\\end{definition}", "% !LOOM name: First\n% !LOOM name: Last\n\\end{definition}")
    )
    result = open_scan(str(q))
    assert result.nodes["dm-0001"].directives["name"] == "Last"
    assert any("multiple names" in d.message for d in result.lint)


def test_manifest_names_are_searchable_without_becoming_reference_aliases(tmp_path: Path) -> None:
    from loom.render.manifest import build_manifest

    q = demo(tmp_path)
    source = q / "nodes/dm-0001.tex"
    source.write_text(
        source.read_text().replace("\\end{definition}", "% !LOOM name: Fixed <points> Ω\n\\end{definition}")
    )
    result = open_scan(str(q))
    manifest = build_manifest(result, {}, {}, [])
    node = manifest["nodes"]["dm-0001"]
    assert node["name"] == "Fixed <points> Ω"
    assert node["title"] == "Widget"
    assert node["name"] not in node["aliases"]
    search = next(x for x in manifest["search"] if x["key"] == "dm-0001")
    assert search["title"] == node["name"] and "Widget" in search["excerpt"]


def test_display_name_hash_does_not_hide_math_or_other_directives() -> None:
    from loom.scan.hashing import mathematical_hash

    text = "\\begin{lemma}\nA statement.\n\\end{lemma}\n"
    named = text.replace("A statement.", "% !LOOM name: A name\nA statement.")
    assert mathematical_hash(text) == mathematical_hash(named)
    assert mathematical_hash(named) != mathematical_hash(named.replace("A statement.", "A changed statement."))
    assert mathematical_hash(named) != mathematical_hash(
        named.replace("A statement.", "% !LOOM basis: assumption\nA statement.")
    )
    assert mathematical_hash("\\begin{verbatim}\n% !LOOM name: printed\n\\end{verbatim}") != mathematical_hash(
        "\\begin{verbatim}\n\\end{verbatim}"
    )


def test_names_survive_inline_and_atomize_without_rendering(tmp_path: Path) -> None:
    from tests.unit.render.test_inline_env import quilt

    q = quilt(tmp_path)
    source = q / "drafting/main.tex"
    source.write_text(
        source.read_text().replace("\\end{definition}", "% !LOOM name: Invisible display name\n\\end{definition}")
    )
    ok("build", cwd=q)
    fragments = list((q / "build/fragments").rglob("*.html"))
    assert fragments and not any("Invisible display name" in p.read_text() for p in fragments)
    ok("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q)
    assert any("% !LOOM name: Invisible display name" in p.read_text() for p in (q / "nodes").glob("*.tex"))
    ok("inline", "drafting/spine.tex", "drafting/back.tex", "--all", cwd=q)
    assert "% !LOOM name: Invisible display name" in (q / "drafting/back.tex").read_text()


def test_missing_old_snapshot_never_establishes_name_equivalence(tmp_path: Path) -> None:
    from loom.records.snapshots import snapshots_dir

    q = demo(tmp_path)
    ok("accept", "dm-0001", "--author", "A. Author", cwd=q)
    original = Records(q).latest["dm-0001"].text
    (snapshots_dir(q) / f"{original.split(':')[1]}.tex").unlink()
    source = q / "nodes/dm-0001.tex"
    source.write_text(source.read_text().replace("\\end{definition}", "% !LOOM name: A name\n\\end{definition}"))
    assert not Records(q).key_states(open_scan(str(q)))["dm-0001"].fresh


def test_empty_names_fall_back_and_nested_names_stay_with_their_owner(tmp_path: Path) -> None:
    q = demo(tmp_path)
    source = q / "nodes/dm-0001.tex"
    source.write_text(
        source.read_text().replace(
            "\\end{definition}",
            "% !LOOM name: Parent\n\\begin{lemma}\\label{dm-0099}\n% !LOOM name: Child\nNested result.\n\\end{lemma}\n\\end{definition}",
        )
    )
    result = open_scan(str(q))
    assert result.nodes["dm-0001"].directives["name"] == "Parent"
    assert result.nodes["dm-0099"].directives["name"] == "Child"
    source.write_text(source.read_text().replace("% !LOOM name: Parent", "% !LOOM name: Parent\n% !LOOM name:  "))
    result = open_scan(str(q))
    assert result.nodes["dm-0001"].directives["name"] == ""
    assert any("must not be empty" in d.message for d in result.lint)
