"""A local Git remote exercises the source-only round trip without network access."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from loom.render.build import build
from loom.scan.quilt import load_quilt
from loom.sync import SyncError, changed_files, configure, fetch, git, incoming_patch, publish, tree_files


def run(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_source_only_publication_and_incoming_fetch(tmp_path: Path, monkeypatch: object) -> None:
    import loom.sync as sync

    root = tmp_path / "quilt"
    root.mkdir()
    run(root, "init", "-b", "quilt")
    run(root, "config", "user.name", "Tester")
    run(root, "config", "user.email", "tester@example.org")
    (root / "drafting").mkdir()
    (root / ".loom").mkdir()
    (root / "config.toml").write_text(
        '[quilt]\nname = "test"\nmain = "drafting/main.tex"\ndrafting = "drafting"\ncanon = "canon"\nprefix = "zk"\nengine = "pdflatex"\n',
        encoding="utf-8",
    )
    source = (
        "\\documentclass{article}\n\\usepackage{loom}\n\\newtheorem{lemma}{Lemma}\n"
        "\\begin{document}\n\\begin{lemma}\\label{zk-0001}A\\end{lemma}\n\\end{document}\n"
    )
    (root / "drafting/main.tex").write_text(source, encoding="utf-8")
    (root / "loom.sty").write_text("% local support\n", encoding="utf-8")
    (root / ".loom/private.txt").write_text("private acceptance\n", encoding="utf-8")
    run(root, "add", ".")
    run(root, "commit", "-m", "private quilt")
    bare = tmp_path / "overleaf.git"
    subprocess.check_call(["git", "init", "--bare", str(bare)], stdout=subprocess.DEVNULL)
    run(root, "remote", "add", "origin", str(bare))
    run(root, "push", "origin", "HEAD:main")
    run(root, "fetch", "origin", "main")
    quilt = load_quilt(root)
    state = configure(quilt, "origin", "main", "main.tex")
    monkeypatch.setattr(sync, "compile_tex", lambda *_args, **_kwargs: SimpleNamespace(ok=True))  # type: ignore[attr-defined]
    commit, paths = publish(quilt, state, push=True)
    assert paths == ["loom.sty", "main.tex"]
    assert set(tree_files(root, commit)) == set(paths)
    assert b"private acceptance" not in b"".join(tree_files(root, commit).values())
    assert (root / ".loom/private.txt").read_text() == "private acceptance\n"
    collaborator = tmp_path / "collaborator"
    subprocess.check_call(["git", "clone", "-b", "main", str(bare), str(collaborator)], stdout=subprocess.DEVNULL)
    run(collaborator, "config", "user.name", "Colleague")
    run(collaborator, "config", "user.email", "colleague@example.org")
    (collaborator / "main.tex").write_text(source.replace("zk-0001}A", "zk-0001}B"), encoding="utf-8")
    (collaborator / "new-section.tex").write_text("New collaborator file.\n", encoding="utf-8")
    (collaborator / "references.bib").write_text("@book{source,title={A collaborator reference}}\n", encoding="utf-8")
    run(collaborator, "add", "main.tex", "new-section.tex", "references.bib")
    run(collaborator, "commit", "-m", "edit statement")
    run(collaborator, "push", "origin", "main")
    original = (root / "drafting/main.tex").read_bytes()
    state = fetch(quilt, state)
    assert (root / "drafting/main.tex").read_bytes() == original
    assert changed_files(root, state.integrated, state.incoming) == [
        {"status": "M", "path": "main.tex"},
        {"status": "A", "path": "new-section.tex"},
        {"status": "A", "path": "references.bib"},
    ]
    assert b"zk-0001}B" in incoming_patch(quilt, state)
    assert b"a/drafting/main.tex" in incoming_patch(quilt, state)
    assert b"b/new-section.tex" in incoming_patch(quilt, state)
    assert b"b/references.bib" in incoming_patch(quilt, state)
    report = build(quilt)
    assert report.manifest["incoming"]["commit"] == state.incoming
    assert [change["key"] for change in report.manifest["incoming"]["changes"]] == ["zk-0001"]
    bib = next(f for f in report.manifest["incoming"]["files"] if f["path"] == "references.bib")
    assert "A collaborator reference" in bib["diff"]
    assert report.manifest["keys"]["zk-0001"]["state"] == "draft"
    try:
        publish(quilt, state, push=True)
    except SyncError as exc:
        assert "awaiting incorporation" in str(exc)
    else:
        raise AssertionError("publishing an unreviewed incoming revision must refuse")
    assert git(root, "show", f"{state.incoming}:main.tex").startswith(b"\\documentclass")
