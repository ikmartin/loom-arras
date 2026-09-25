"""Canon documents in the build (book 9.3, 17.1): a landmark is rendered as a document, with no node identity, its own macros, and a place in the manifest."""

from __future__ import annotations

import json
from pathlib import Path

from loom.render.build import build
from loom.scan.quilt import load_quilt
from tests.helpers import exits, ok, templated, the

PAPER = r"""\documentclass{article}
\usepackage{amsthm}
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}[theorem]{Lemma}
\newcommand{\gadget}{\mathsf{G}}
\title{Widgets}
\begin{document}
\maketitle
\section{Setup}\label{sec:setup}
\begin{lemma}\label{lem:a}
Every $\gadget$ is a widget.
\end{lemma}
\begin{proof}
Obvious.
\end{proof}
\begin{theorem}[Main]\label{thm:main}
By Lemma~\ref{lem:a} and Section~\ref{sec:setup}.
\end{theorem}
\end{document}
"""

FIXED = {"LOOM_FIXED_TIME": "2026-09-16T00:00:00Z"}


def quilt(tmp_path: Path) -> Path:
    """PAPER imported and drafted at a fixed time, from a per-worker template."""

    def make(base: Path) -> None:
        paper = base / "paper"
        paper.mkdir()
        (paper / "main.tex").write_text(PAPER, encoding="utf-8")
        ok("init", str(base / "q"), "--from", str(paper / "main.tex"), "--prefix", "pp", "--yes", cwd=base, env=FIXED)
        ok("draft", "canon/main.tex", "--yes", cwd=base / "q", env=FIXED)

    templated("canon-drafted", tmp_path, make)
    return tmp_path / "q"


def manifest(q: Path) -> dict:
    return json.loads((q / "build" / "manifest.json").read_text())


def test_a_canon_document_is_a_fragment_without_identity(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("build", cwd=q, env=FIXED)
    frag = (q / "build" / "fragments" / "canon" / "main.html").read_text()
    assert 'data-fragment="canon"' in frag and 'data-macros="canon:main"' in frag
    assert "<h1" in frag and "Widgets" in frag
    assert 'class="env env-lemma"' in frag
    assert "data-key=" not in frag and "data-id=" not in frag  # a landmark's theorems are not nodes
    assert 'id="lem-a"' in frag and 'id="sec-setup"' in frag  # anchors, so a link into the page lands
    assert 'href="#lem-a"' in frag and "ref-dangling" not in frag

    m = manifest(q)
    (entry,) = m["canon"]
    assert entry["path"] == "canon/main.tex" and entry["stem"] == "main" and entry["title"] == "Widgets"
    assert entry["fragment"] == "fragments/canon/main.html"
    assert entry["step"] == "0001" and entry["name"] == "main"
    assert entry["macros"] == "canon:main"
    assert any(mac["name"] == "gadget" for mac in m["macros"]["sets"]["canon:main"])
    assert "canon/main.tex" not in m["nodes"]  # never scanned: it defines nothing
    assert any(s["kind"] == "canon" for s in m["search"])


def test_the_project_name_is_the_corpus_name(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("build", cwd=q, env=FIXED)
    assert manifest(q)["corpus"]["name"] == "q"  # the directory's name when [quilt] name is unset
    cfg = q / "config.toml"
    cfg.write_text(cfg.read_text().replace('name = "q"', 'name = "The widget paper"'))
    ok("build", cwd=q, env=FIXED)
    assert manifest(q)["corpus"]["name"] == "The widget paper"


def test_a_canon_fragment_is_cached_and_pruned(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("build", cwd=q, env=FIXED)
    warm = build(load_quilt(q))
    assert "canon:canon/main.tex" in warm.skipped and warm.rendered == []  # unchanged: skipped
    (q / "canon" / "main.tex").unlink()
    ok("build", cwd=q, env=FIXED)
    assert not (q / "build" / "fragments" / "canon" / "main.html").exists()
    assert manifest(q)["canon"] == []


def test_a_conflicted_key_is_published_with_no_text(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    (q / "nodes").mkdir(exist_ok=True)
    (q / "nodes" / "pp-0002.tex").write_text(
        "\\begin{lemma}\\label{pp-0002}\nA second definition.\n\\end{lemma}\n", encoding="utf-8"
    )
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("\\end{document}", "\\input{nodes/pp-0002}\n\\end{document}"))
    exits(1, "build", cwd=q, env=FIXED, match="duplicate-id")  # an error exit, and the build is still published
    m = manifest(q)
    node = m["nodes"]["pp-0002"]
    assert node["state"] == "conflicted" and node["fragment"] == "" and node["file"] == ""
    assert node["conflict"] == ["drafting/main.tex", "nodes/pp-0002.tex"]
    key = m["keys"]["pp-0002"]
    assert key["state"] == "conflicted" and key["hash"] == "" and key["uses"] == []
    assert m["states"]["labels"]["conflicted"] == {"label": "conflicted", "color": "negative"}
    d = the(m["diagnostics"], lambda x: x["code"] == "duplicate-id", "duplicate-id diagnostic")
    assert [f["command"] for f in d["fixes"]][0].startswith("loom fork pp-0002 --in")
    assert not (q / "build" / "fragments" / "nodes" / "pp-0002.html").exists()


def test_a_key_whose_text_a_landmark_recorded_carries_its_version(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("canonize", "drafting/main.tex", "--to", "canon/main-v1.tex", "-m", "one", cwd=q, env=FIXED)
    ok("build", cwd=q, env=FIXED)
    m = manifest(q)
    assert m["keys"]["pp-0002"]["version"] == {"step": "0002", "name": "main-v1"}
    assert m["keys"]["pp-0002/proof"]["version"] == {"step": "0002", "name": "main-v1"}
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("Obvious.", "Obvious, really."))
    ok("build", cwd=q, env=FIXED)
    m2 = manifest(q)
    assert m2["keys"]["pp-0002"]["version"] == {"step": "0002", "name": "main-v1"}  # the statement did not move
    assert "version" not in m2["keys"]["pp-0002/proof"]  # the proof did
