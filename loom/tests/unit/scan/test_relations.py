"""The `see:` relation (book 5.11.3, plan 0.2 §2): a link a viewer shows that the mathematics never sees."""

from __future__ import annotations

from pathlib import Path

from tests.unit.scan.helpers import PREAMBLE, make_quilt


def _master(body: str) -> str:
    return PREAMBLE + "\\begin{document}\n\\section{Setup}\\label{ab-0010}\n" + body + "\n\\end{document}\n"


def _quilt(tmp_path: Path, nodes: dict[str, str], inputs: list[str] | None = None):  # type: ignore[no-untyped-def]
    lines = "\n".join(f"\\input{{{rel[:-4]}}}" for rel in (inputs if inputs is not None else sorted(nodes)))
    files = {"drafts/main.tex": _master(lines), **nodes}
    return make_quilt(tmp_path, files)


DEF = "\\begin{definition}[Widget]\\label{ab-0001}\\label{def:widget}\nA widget.\n\\end{definition}\n"


def test_directive_see_node_level(tmp_path: Path) -> None:
    r = _quilt(
        tmp_path,
        {
            "nodes/ab-0001.tex": DEF,
            "nodes/ab-0002.tex": "\\begin{lemma}\\label{ab-0002}\n% !LOOM see: ab-0001\nA lemma.\n\\end{lemma}\n",
        },
    )
    assert [(x.from_key, x.to_key, x.kind) for x in r.relations] == [("ab-0002", "ab-0001", "see")]
    assert r.relations[0].file == "nodes/ab-0002.tex" and r.relations[0].line == 2


def test_directive_see_file_level_applies_to_all(tmp_path: Path) -> None:
    """Scope follows `tags:`: in a file's first twenty lines before any node the directive applies to every node the file defines."""
    r = _quilt(
        tmp_path,
        {
            "nodes/ab-0001.tex": DEF,
            "nodes/ab-0002.tex": (
                "% !LOOM see: ab-0001\n"
                "\\begin{lemma}\\label{ab-0002}\nOne.\n\\end{lemma}\n"
                "\\begin{lemma}\\label{ab-0003}\nTwo.\n\\end{lemma}\n"
            ),
        },
    )
    assert {(x.from_key, x.to_key) for x in r.relations} == {("ab-0002", "ab-0001"), ("ab-0003", "ab-0001")}


def test_see_resolves_alias_and_digest_id(tmp_path: Path) -> None:
    digest = (
        "% !LOOM digest: Zz99\n"
        "% !LOOM requires: amsthm\n"
        "\\begin{theorem}[Theorem 1.1]\\label{Zz99-thm-1.1}\nTheirs.\n\\end{theorem}\n"
    )
    r = _quilt(
        tmp_path,
        {
            "nodes/ab-0001.tex": DEF,
            "refs/Zz99.tex": digest,
            "nodes/ab-0002.tex": (
                "\\begin{lemma}\\label{ab-0002}\n% !LOOM see: def:widget, Zz99-thm-1.1\nA lemma.\n\\end{lemma}\n"
            ),
        },
        inputs=["nodes/ab-0001.tex", "nodes/ab-0002.tex"],
    )
    assert {x.to_key for x in r.relations} == {"ab-0001", "Zz99-thm-1.1"}  # an alias and a digest node id both resolve


def test_see_dangling_link_with_location(tmp_path: Path) -> None:
    r = _quilt(
        tmp_path,
        {"nodes/ab-0002.tex": "\\begin{lemma}\\label{ab-0002}\n% !LOOM see: ab-9999\nA lemma.\n\\end{lemma}\n"},
    )
    d = [x for x in r.diagnostics if x.code == "dangling-link"]
    assert len(d) == 1 and d[0].severity == "error"
    assert "ab-9999" in d[0].message
    assert d[0].locations[0].file == "nodes/ab-0002.tex" and d[0].locations[0].line == 2
    assert d[0].keys == ["ab-0002"]
    assert r.relations == []


def test_see_redundant_info(tmp_path: Path) -> None:
    r = _quilt(
        tmp_path,
        {
            "nodes/ab-0001.tex": DEF,
            "nodes/ab-0002.tex": (
                "\\begin{lemma}\\label{ab-0002}\\label{lem:two}\n"
                "% !LOOM see: lem:two, ab-0001, def:widget\n"
                "A lemma.\n\\end{lemma}\n"
            ),
        },
    )
    codes = [x.code for x in r.diagnostics if x.code == "loom:see-redundant"]
    assert len(codes) == 2  # the self-relation and the duplicate of ab-0001 under its alias
    assert [(x.from_key, x.to_key) for x in r.relations] == [("ab-0002", "ab-0001")]
    assert all(x.severity == "info" for x in r.diagnostics if x.code == "loom:see-redundant")


def test_see_not_in_closure_bundle_or_acceptance(tmp_path: Path) -> None:
    """A relation is never a dependency: it enters no edge, no closure, and nothing that walks the graph."""
    r = _quilt(
        tmp_path,
        {
            "nodes/ab-0001.tex": DEF,
            "nodes/ab-0002.tex": "\\begin{lemma}\\label{ab-0002}\n% !LOOM see: ab-0001\nA lemma.\n\\end{lemma}\n",
        },
    )
    assert r.relations  # the relation exists
    assert not [e for e in r.edges.edges if e.src == "ab-0002"]  # and no edge was created for it
    assert r.graph is not None
    assert r.graph.closure("ab-0002") == ["ab-0002"]
    assert r.graph.downstream("ab-0001") == []


def test_manifest_relations_shape(tmp_path: Path) -> None:
    """specs/manifest.md §16: a top-level list, kind `see`, with the directive's location. Nodes gain no field."""
    from loom.render.manifest import build_manifest

    r = _quilt(
        tmp_path,
        {
            "nodes/ab-0001.tex": DEF,
            "nodes/ab-0002.tex": "\\begin{lemma}\\label{ab-0002}\n% !LOOM see: ab-0001\nA lemma.\n\\end{lemma}\n",
        },
    )
    m = build_manifest(r, {}, {}, [])
    assert m["relations"] == [
        {"from": "ab-0002", "to": "ab-0001", "kind": "see", "src": {"file": "nodes/ab-0002.tex", "line": 2}}
    ]
    assert "see" not in m["nodes"]["ab-0002"] and "relations" not in m["nodes"]["ab-0002"]
