"""loom build on the demo and synthetic quilts: layout, fragments, manifest shape, dialect validity, incremental rendering, atomic publish."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.render import build as build_mod
from loom.render import publish as publish_mod
from loom.render.build import build
from loom.scan.quilt import load_quilt

REPO = Path(__file__).resolve().parents[3]
VALIDATOR = REPO / "tests" / "tools" / "validate_dialect.py"


def run(*args: str, cwd: Path):  # type: ignore[no-untyped-def]
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return CliRunner().invoke(main, list(args))
    finally:
        os.chdir(old)


def demo(tmp_path: Path) -> Path:
    r = run("init", str(tmp_path / "demo"), "--demo", cwd=tmp_path)
    assert r.exit_code == 0, r.output
    return tmp_path / "demo"


def synthetic(tmp_path: Path) -> Path:
    dest = tmp_path / "synthetic"
    shutil.copytree(REPO / "tests" / "quilts" / "synthetic", dest)
    return dest


def validate(build_dir: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(build_dir / "fragments")], capture_output=True, text=True, check=False
    )
    return proc.returncode, proc.stdout


def test_build_layout_and_manifest(tmp_path: Path) -> None:
    d = demo(tmp_path)
    assert run("compile", cwd=d).exit_code == 0
    r = run("build", cwd=d)
    assert r.exit_code == 0, r.output
    b = d / "build"
    assert (b / "manifest.json").exists()
    assert (b / "fragments" / "nodes" / "dm-0003.html").exists()
    assert (b / "fragments" / "masters" / "main.html").exists()
    assert (b / "fragments" / "digests" / "Man12.html").exists()
    m = json.loads((b / "manifest.json").read_text())
    for field in (
        "interface_version",
        "publisher",
        "generated",
        "corpus",
        "masters",
        "nodes",
        "keys",
        "regions",
        "edges",
        "inclusion",
        "states",
        "annotations",
        "threads",
        "diagnostics",
        "tags",
        "taxa",
        "references",
        "macros",
        "search",
    ):
        assert field in m, field
    assert m["interface_version"] == 1 and m["publisher"]["name"] == "loom"
    assert m["corpus"]["root_label"] == "Widgets and their fixed loci"
    master = m["masters"][0]
    assert master["default"] and master["numbering_known"] and master["fragment"] == "fragments/masters/main.html"
    n = m["nodes"]["dm-0003"]
    assert n["taxon"] == "Theorem" and n["title"] == "Main" and n["numbers"]["drafting/main.tex"]["number"] == "2.1"
    assert n["parent"]["drafting/main.tex"] == "dm-0011" and n["proofs"] == ["dm-0003/proof"]
    k = m["keys"]["dm-0003/proof"]
    assert k["kind"] == "proof" and k["hash"].startswith("sha256:")
    assert set(k["closure"]) == {
        "dm-0002",
        "dm-0003",
        "Man12-prop-3.2",
        "Man12-setup",
    }  # the postnote edge brings the digest nodes in (book 8.11)
    assert m["keys"]["dm-0005/proof"]["state"] == "incomplete"
    assert m["regions"]["dm-0001#eq:fix"]["numbers"]["drafting/main.tex"]["number"] == "1.1"
    assert any(e["from"] == "dm-0003/proof" and e["to"] == "dm-0002" for e in m["edges"])
    tree = m["inclusion"]["drafting/main.tex"]
    assert [c["key"] for c in tree["children"]] == ["dm-0010", "dm-0011"]
    assert [c["key"] for c in tree["children"][0]["children"]] == ["nodes/dm-0001.tex", "nodes/dm-0002.tex"]
    assert m["references"]["Man12"]["digest"]["nodes"] == ["Man12-setup", "Man12-prop-3.2"]
    assert m["taxa"]["Lemma"]["count"] == 1 and "setup" in m["tags"]
    assert any(s["key"] == "dm-0002" and "lem:orbits" in s["aliases"] for s in m["search"])
    assert {x["name"] for x in m["macros"]["default"]} == {"Fix"}


def test_fragment_kinds_and_dialect_validity(tmp_path: Path) -> None:
    d = synthetic(tmp_path)
    assert run("compile", cwd=d).exit_code == 0
    r = run("build", cwd=d)
    assert r.exit_code == 1, r.output  # the synthetic quilt has three intentional errors
    b = d / "build"
    node = (b / "fragments" / "nodes" / "sy-0003.html").read_text()
    assert node.startswith(
        '<div data-fragment="node" class="env env-theorem" id="sy-0003" data-id="sy-0003"'
    )  # a real anchor target, so a link into a document lands
    assert node.count("<details ") == 2 and 'data-of="sy-0003"' in node
    assert '<span class="number">2.1</span>' in node
    master = (b / "fragments" / "masters" / "main.html").read_text()
    assert 'data-fragment="master"' in master
    assert (
        "data-included" not in master
        and '<div class="included" data-key="nodes/sy-0002.tex" data-file="nodes/sy-0002.tex"' in master
    )
    assert '<section id="sy-0300" data-id="sy-0300" data-level="2"' in master and "<h2 " in master
    assert 'class="include"' not in master
    section = (b / "fragments" / "nodes" / "sy-0200.html").read_text()
    assert section.count('<div class="include" data-key=') == 2  # the input of sy-0003 and the subsection
    subsection = (b / "fragments" / "nodes" / "sy-0201.html").read_text()
    assert subsection.count('<div class="include" data-key=') >= 4
    digest = (b / "fragments" / "digests" / "Kre99.html").read_text()
    assert 'data-macros="Kre99"' in digest and "Kre99-thm-2.1" in digest
    for html in (node, master, section, digest):
        assert "<script" not in html and "<html" not in html
    code, out = validate(b)
    assert code == 0, out
    assert (b / "svg").is_dir() and any((b / "svg").iterdir())


def test_build_incremental_by_hash(tmp_path: Path) -> None:
    d = demo(tmp_path)
    first = build(load_quilt(d))
    assert len(first.rendered) > 5 and first.skipped == []
    second = build(load_quilt(d))
    assert second.rendered == [] and len(second.skipped) == len(first.rendered)
    node = d / "nodes" / "dm-0002.tex"
    node.write_text(node.read_text().replace("one or two points", "one or two points at most"))
    third = build(load_quilt(d))
    assert "dm-0002" in third.rendered and "drafting/main.tex" in third.rendered and "dm-0001" not in third.rendered
    for name in ("dm-0001", "dm-0003"):
        f = d / "nodes" / f"{name}.tex"
        f.write_text(f.read_text() + "\n% touched\n")
    fourth = build(load_quilt(d), keys=["dm-0003"])
    assert set(fourth.rendered) == {"dm-0003", "drafting/main.tex"}
    fifth = build(load_quilt(d))
    assert "dm-0001" in fifth.rendered and "dm-0003" not in fifth.rendered
    m = json.loads((d / "build" / "manifest.json").read_text())
    assert len(m["nodes"]) == len(first.manifest["nodes"])


def test_a_change_in_looms_own_code_re_renders_everything(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # a checkout's version never moves, so the cache would otherwise keep publishing the HTML an edited converter was meant to replace
    d = demo(tmp_path)
    first = build(load_quilt(d))
    assert build(load_quilt(d)).rendered == []
    monkeypatch.setattr(build_mod, "_code_hash", lambda: "another converter")
    after = build(load_quilt(d))
    assert set(after.rendered) == set(first.rendered) and after.skipped == []


def test_force_renders_every_fragment_again(tmp_path: Path) -> None:
    d = demo(tmp_path)
    first = build(load_quilt(d))
    assert build(load_quilt(d)).rendered == []
    forced = build(load_quilt(d), force=True)
    assert set(forced.rendered) == set(first.rendered) and forced.skipped == []
    r = run("build", "--force", cwd=d)
    assert r.exit_code == 0 and ", 0 unchanged" in r.output


def test_build_atomic_publish_interrupted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = demo(tmp_path)
    build(load_quilt(d))
    before = (d / "build" / "manifest.json").read_text()
    original = publish_mod.write_atomic

    def boom(path: Path, data: str | bytes) -> None:
        if path.name == "manifest.json":
            raise RuntimeError("interrupted")
        original(path, data)

    monkeypatch.setattr(publish_mod, "write_atomic", boom)
    (d / "nodes" / "dm-0002.tex").write_text((d / "nodes" / "dm-0002.tex").read_text() + "\n% touched\n")
    with pytest.raises(RuntimeError):
        build(load_quilt(d))
    assert (d / "build" / "manifest.json").read_text() == before
    assert not list((d / "build").rglob("*.tmp"))


def test_build_exit_1_on_errors_still_publishes(tmp_path: Path) -> None:
    d = demo(tmp_path)
    (d / "nodes" / "bad.tex").write_text("\\begin{lemma}\\label{dm-0001}\ndup\n\\end{lemma}\n")
    r = run("build", cwd=d)
    assert r.exit_code == 1 and "duplicate-id" in r.output
    m = json.loads((d / "build" / "manifest.json").read_text())
    assert any(x["code"] == "duplicate-id" for x in m["diagnostics"])


def test_build_dir_deletable_and_regenerated(tmp_path: Path) -> None:
    d = demo(tmp_path)
    build(load_quilt(d))
    shutil.rmtree(d / "build")
    rep = build(load_quilt(d))
    assert (d / "build" / "manifest.json").exists() and rep.rendered


def test_a_display_that_is_a_picture_goes_to_the_fallback(tmp_path: Path) -> None:
    """A commutative diagram written inside a numbered display is a picture, not a formula: handing it to the viewer's mathematics renderer sets the whole block in error colour, which is what the relative localization and ACGS papers showed."""
    from loom.render.convert import renders_as_math

    assert not renders_as_math(r"\[\tag{2}\begin{tikzcd} a \arrow[r] & b \end{tikzcd}\]")
    assert not renders_as_math(r"\[\xymatrix{A \ar[r] & B}\]")  # a command, not an environment
    assert not renders_as_math(r"\[\includegraphics{a.pdf}\]")
    # and everything a renderer does handle stays mathematics
    assert renders_as_math(r"\begin{align*}\begin{pmatrix}1\end{pmatrix}\end{align*}")
    assert renders_as_math(r"\[\begin{cases} 1 & x > 0 \end{cases}\]")
    assert renders_as_math(r"\[x^2 + \frac{1}{2}\]")
