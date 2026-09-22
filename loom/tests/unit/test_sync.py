"""A local Git remote exercises the source-only round trip without network access."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from loom.render.api import ApiError, handle
from loom.render.build import build
from loom.review_queue import decide
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from loom.sync import (
    SyncError,
    SyncState,
    changed_files,
    configure,
    fetch,
    finish_incorporation,
    git,
    incoming_patch,
    prepare_incorporation,
    publish,
    tree_files,
)


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
    prepare_incorporation(quilt, state)
    assert (root / "drafting/main.tex").read_bytes() == original
    try:
        finish_incorporation(quilt, state)
    except SyncError as exc:
        assert "does not match the reviewed pull" in str(exc)
    else:
        raise AssertionError("finishing before applying the exact patch must refuse")
    try:
        handle(root, "sync-incorporate", {"incoming": "0" * 40, "base": state.integrated})
    except ApiError as exc:
        assert exc.code == "revision-changed"
    else:
        raise AssertionError("the one-click action must stay pinned to the displayed revision")
    assert (root / "drafting/main.tex").read_bytes() == original
    finished = handle(
        root,
        "sync-incorporate",
        {"incoming": state.incoming, "base": state.integrated},
    )["result"]
    state = SyncState.read(root)
    assert finished["integrated"] == state.incoming
    assert run(root, "show", "--format=", "--name-only", "HEAD").splitlines() == [".loom/source-sync.json"]
    assert sorted(run(root, "show", "--format=", "--name-only", "HEAD^").splitlines()) == [
        "drafting/main.tex",
        "new-section.tex",
        "references.bib",
    ]
    assert (
        run(root, "diff", "--name-only", "HEAD", "--", "drafting/main.tex", "new-section.tex", "references.bib") == ""
    )
    assert finish_incorporation(quilt, state)["integrated"] == state.incoming
    unresolved = build(quilt).manifest["unresolved"]
    assert [(row["key"], row["cause"], row["status"]) for row in unresolved] == [
        ("zk-0001", "incoming-pull", "needs-review")
    ]
    assert unresolved[0]["local_changed"] is False
    assert "zk-0001" in state.review_baselines
    state.review_baselines.clear()  # a quilt incorporated before baseline tracking existed
    state.write(root)
    assert build(quilt).manifest["unresolved"][0]["local_changed"] is False
    decide(scan(quilt), "zk-0001", "ok")
    assert build(quilt).manifest["unresolved"][0]["status"] == "ok"
    (root / "drafting/main.tex").write_text(source.replace("zk-0001}A", "zk-0001}C"), encoding="utf-8")
    changed = build(quilt).manifest["unresolved"][0]
    assert changed["status"] == "needs-review" and changed["invalidated"]
    assert changed["local_changed"] is True
    run(root, "add", "drafting/main.tex")
    run(root, "commit", "-m", "local statement edit")
    assert build(quilt).manifest["unresolved"][0]["local_changed"] is True
    (root / "drafting/main.tex").write_text(source.replace("zk-0001}A", "zk-0001}B"), encoding="utf-8")
    assert build(quilt).manifest["unresolved"][0]["local_changed"] is False
    run(root, "add", "drafting/main.tex")
    run(root, "commit", "-m", "restore incorporated statement")
    (collaborator / "main.tex").write_text(source.replace("zk-0001}A", "zk-0001}D"), encoding="utf-8")
    run(collaborator, "add", "main.tex")
    run(collaborator, "commit", "-m", "revise statement again")
    run(collaborator, "push", "origin", "main")
    state = fetch(quilt, state)
    second = handle(root, "sync-incorporate", {"incoming": state.incoming, "base": state.integrated})["result"]
    assert second["integrated"] == state.incoming
    latest = build(quilt).manifest["unresolved"][0]
    assert latest["pull"] == state.incoming
    assert latest["local_changed"] is False
