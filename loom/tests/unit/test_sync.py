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
    update_documents,
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
    commit, paths = publish(quilt, state)
    assert run(root, "rev-parse", state.publication_ref) == commit
    assert run(bare, "rev-parse", "main") != commit
    run(root, "push", "origin", f"{state.publication_ref}:main")
    state = fetch(quilt, state)
    assert state.integrated == state.incoming == commit
    assert incoming_patch(quilt, state) == b""
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
        publish(quilt, state)
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


def test_multiple_selected_documents_prepare_one_clean_union_locally(tmp_path: Path, monkeypatch: object) -> None:
    import loom.sync as sync

    root = tmp_path / "quilt"
    root.mkdir()
    run(root, "init", "-b", "quilt")
    run(root, "config", "user.name", "Tester")
    run(root, "config", "user.email", "tester@example.org")
    (root / "drafting").mkdir()
    (root / "shared").mkdir()
    (root / ".loom").mkdir()
    (root / "canon").mkdir()
    (root / "config.toml").write_text(
        '[quilt]\nname = "test"\nmain = "drafting/main.tex"\ndrafting = "drafting"\ncanon = "canon"\nprefix = "zk"\nengine = "pdflatex"\n',
        encoding="utf-8",
    )
    preamble = "\\documentclass{article}\n\\usepackage{loom}\n\\newtheorem{lemma}{Lemma}\n"
    (root / "drafting/main.tex").write_text(
        preamble + "\\begin{document}\n\\input{shared/common}\n\\end{document}\n", encoding="utf-8"
    )
    (root / "drafting/toy.tex").write_text(
        preamble
        + "\\begin{document}\n\\input{shared/common}\n\\begin{lemma}\\label{zk-0002}Toy.\\end{lemma}\n\\end{document}\n",
        encoding="utf-8",
    )
    (root / "drafting/private.tex").write_text(
        preamble + "\\begin{document}Not selected.\\end{document}\n", encoding="utf-8"
    )
    (root / "shared/common.tex").write_text("\\begin{lemma}\\label{zk-0001}Shared.\\end{lemma}\n", encoding="utf-8")
    (root / "loom.sty").write_text("% local support\n", encoding="utf-8")
    (root / ".loom/private.txt").write_text("private\n", encoding="utf-8")
    (root / "canon/main.tex").write_text("private landmark\n", encoding="utf-8")
    run(root, "add", ".")
    run(root, "commit", "-m", "private quilt")
    bare = tmp_path / "overleaf.git"
    subprocess.check_call(["git", "init", "--bare", str(bare)], stdout=subprocess.DEVNULL)
    run(root, "remote", "add", "origin", str(bare))
    run(root, "push", "origin", "HEAD:main")
    run(root, "fetch", "origin", "main")
    quilt = load_quilt(root)
    state = configure(quilt, "origin", "main", "main.tex")
    selection_head = run(root, "rev-parse", "HEAD")
    state = update_documents(quilt, state, "add", "drafting/toy.tex")
    assert run(root, "rev-parse", "HEAD") == selection_head
    assert run(root, "diff", "--cached", "--name-only") == ""
    assert SyncState.read(root).documents == ["drafting/main.tex", "drafting/toy.tex"]
    run(root, "add", ".loom/source-sync.json")
    run(root, "commit", "-m", "select Overleaf documents")

    compiled: list[str] = []

    remote_before = run(root, "rev-parse", "refs/remotes/origin/main")

    def compile_secondary_failure(_root: Path, master: str, *_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(ok=master != "drafting/toy.tex", first_error="toy failed")

    monkeypatch.setattr(sync, "compile_tex", compile_secondary_failure)  # type: ignore[attr-defined]
    try:
        publish(quilt, state)
    except SyncError as exc:
        assert "drafting/toy.tex does not compile" in str(exc)
    else:
        raise AssertionError("a broken secondary document must prevent publication")
    assert run(root, "rev-parse", "refs/remotes/origin/main") == remote_before

    def compile_ok(_root: Path, master: str, *_args: object, **_kwargs: object) -> SimpleNamespace:
        compiled.append(master)
        return SimpleNamespace(ok=True)

    monkeypatch.setattr(sync, "compile_tex", compile_ok)  # type: ignore[attr-defined]
    commit, paths = publish(quilt, state)
    assert compiled == ["main.tex", "drafting/toy.tex"]
    assert paths == ["drafting/toy.tex", "loom.sty", "main.tex", "shared/common.tex"]
    assert set(tree_files(root, commit)) == set(paths)
    assert ".loom/private.txt" not in tree_files(root, commit)
    assert "canon/main.tex" not in tree_files(root, commit)
    assert "drafting/private.tex" not in tree_files(root, commit)
    assert run(root, "show", "--format=", "--name-only", "HEAD") == ".loom/source-sync.json"
    assert "select Overleaf documents" in run(root, "log", "-1", "--format=%s")
    assert run(root, "rev-parse", state.publication_ref) == commit
    assert state.prepared_from == run(root, "rev-parse", "HEAD")
    assert state.integrated == remote_before
    assert run(bare, "rev-parse", "main") == remote_before
    assert run(root, "diff", "--cached", "--name-only") == ""

    from click.testing import CliRunner

    from loom.cli.sync import sync as sync_cli

    result = CliRunner().invoke(sync_cli, ["publish", "--quilt", str(root)])
    assert result.exit_code == 0, result.output
    assert "Prepared document workspace revision" in result.output
    assert state.publication_ref in result.output
    assert "Remote unchanged" in result.output
    assert "git push" not in result.output
    assert "--push" not in CliRunner().invoke(sync_cli, ["publish", "--help"]).output
    assert "document workspace" in CliRunner().invoke(sync_cli, ["init", "--help"]).output
    state = SyncState.read(root)
    prepared = state.prepared
    original = (root / "drafting/toy.tex").read_text()
    for path in ["drafting/toy.tex", "shared/common.tex"]:
        target = root / path
        content = target.read_text()
        target.write_text(content + "% uncommitted edit\n")
        import pytest

        with pytest.raises(SyncError, match="uncommitted"):
            publish(quilt, state)
        target.write_text(content)
    (root / "drafting/toy.tex").write_text(original + "% staged change\n")
    run(root, "add", "drafting/toy.tex")
    (root / "drafting/toy.tex").write_text(original)
    with pytest.raises(SyncError, match="staged"):
        publish(quilt, state)
    run(root, "reset", "HEAD", "--", "drafting/toy.tex")
    (root / "shared/common.tex").unlink()
    with pytest.raises(SyncError, match="uncommitted"):
        publish(quilt, state)
    run(root, "restore", "shared/common.tex")
    assert run(root, "rev-parse", state.publication_ref) == prepared
    collision = SyncState.read(root)
    collision.published_main = "drafting/toy.tex"
    with pytest.raises(SyncError, match="two quilt files"):
        publish(quilt, collision)
    run(root, "push", "origin", f"{state.publication_ref}:main")
    state = fetch(quilt, SyncState.read(root))
    assert state.integrated == state.incoming == prepared
    assert incoming_patch(quilt, state) == b""
    assert not build(quilt).manifest.get("incoming")

    main = root / "drafting/main.tex"
    main.write_text(
        main.read_text().replace(r"\usepackage{loom}", r"\usepackage{loom}" + "\n" + r"\usepackage{amsmath}")
    )
    run(root, "add", "drafting/main.tex")
    run(root, "commit", "-m", "use a system package")
    (root / "amsmath.sty").write_text("% uncommitted local package shadows the system copy\n")
    with pytest.raises(SyncError, match="amsmath.sty is not committed"):
        publish(quilt, state)
    (root / "amsmath.sty").unlink()

    try:
        update_documents(quilt, state, "remove", "drafting/main.tex")
    except SyncError as exc:
        assert "cannot be removed" in str(exc)
    else:
        raise AssertionError("the primary selected document must not be removable")
    state = update_documents(quilt, state, "remove", "drafting/toy.tex")
    assert state.documents == ["drafting/main.tex"]
    state = update_documents(quilt, state, "add", "drafting/toy.tex")
    (root / "drafting/toy.tex").unlink()
    state = update_documents(quilt, state, "remove", "drafting/toy.tex")
    assert state.documents == ["drafting/main.tex"]


def test_old_sync_state_defaults_to_the_primary_document(tmp_path: Path) -> None:
    root = tmp_path
    (root / ".loom").mkdir()
    (root / ".loom/source-sync.json").write_text(
        '{"remote":"origin","branch":"main","master":"drafting/main.tex","integrated":"abc"}\n',
        encoding="utf-8",
    )
    assert SyncState.read(root).documents == ["drafting/main.tex"]
