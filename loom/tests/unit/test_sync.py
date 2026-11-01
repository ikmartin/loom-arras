"""A local bare repository stands in for Overleaf, so the document workspace round trip runs without network access."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from loom.history.ledger import load_history
from loom.render.api import ApiError, handle
from loom.render.build import build
from loom.review_queue import decide
from loom.scan.quilt import load_quilt, save_author
from loom.scan.scan import scan
from loom.sync import (
    SyncError,
    SyncState,
    changed_files,
    configure,
    exact_renames,
    fetch,
    incoming_patch,
    publish,
    pull_files,
    push_publication,
    tree_files,
    update_documents,
    workspace,
)
from tests.helpers import json_of, ok, refused

CONFIG = (
    '[quilt]\nname = "test"\nmain = "drafting/main.tex"\ndrafting = "drafting"\nprefix = "zk"\nengine = "pdflatex"\n'
)
PREAMBLE = "\\documentclass{article}\n\\usepackage{loom}\n\\newtheorem{lemma}{Lemma}\n"
SOURCE = PREAMBLE + "\\begin{document}\n\\begin{lemma}\\label{zk-0001}A\\end{lemma}\n\\end{document}\n"


def run(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def flat(text: str) -> str:
    """Output with its wrapping undone: a workspace at a temporary path is longer than a line."""
    return " ".join(text.split())


def quilt_at(tmp_path: Path, files: dict[str, str]) -> Path:
    """A quilt that is no repository: loom needs none to pair with a workspace."""
    root = tmp_path / "quilt"
    root.mkdir()
    (root / "config.toml").write_text(CONFIG, encoding="utf-8")
    for rel, text in {"drafting/loom.sty": "% local support\n", **files}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def overleaf(tmp_path: Path) -> Path:
    """A bare repository on `master` holding the project Overleaf starts every project with."""
    bare = tmp_path / "overleaf.git"
    subprocess.check_call(["git", "init", "-q", "--bare", "-b", "master", str(bare)])
    seed = tmp_path / "seed"
    subprocess.check_call(["git", "clone", "-q", str(bare), str(seed)], stderr=subprocess.DEVNULL)
    run(seed, "config", "user.name", "Overleaf")
    run(seed, "config", "user.email", "overleaf@example.org")
    (seed / "main.tex").write_text("\\documentclass{article}\n\\begin{document}\n\\end{document}\n", encoding="utf-8")
    run(seed, "add", ".")
    run(seed, "commit", "-q", "-m", "new project")
    run(seed, "push", "-q", "origin", "HEAD:master")
    return bare


def cloned(tmp_path: Path, bare: Path, name: str = "project") -> Path:
    """The person's own clone of the workspace at `tmp_path / name`: the directory `sync init` names."""
    clone = tmp_path / name
    subprocess.check_call(["git", "clone", "-q", str(bare), str(clone)], stderr=subprocess.DEVNULL)
    return clone


def colleague(tmp_path: Path, bare: Path) -> Path:
    clone = tmp_path / "collaborator"
    subprocess.check_call(["git", "clone", "-q", str(bare), str(clone)])
    run(clone, "config", "user.name", "Colleague")
    run(clone, "config", "user.email", "colleague@example.org")
    return clone


def edit(clone: Path, message: str, files: dict[str, str]) -> None:
    run(clone, "pull", "-q", "--ff-only")
    for rel, text in files.items():
        (clone / rel).parent.mkdir(parents=True, exist_ok=True)
        (clone / rel).write_text(text, encoding="utf-8")
    run(clone, "add", ".")
    run(clone, "commit", "-q", "-m", message)
    run(clone, "push", "-q", "origin", "HEAD:master")


@pytest.fixture
def compiled(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every document `publish` compiles, each passing; a test that needs a failure patches its own."""
    import loom.sync as sync

    seen: list[str] = []

    def compile_ok(_root: Path, _base: str, master: str, *_args: object, **_kwargs: object) -> SimpleNamespace:
        seen.append(master)
        return SimpleNamespace(ok=True)

    monkeypatch.setattr(sync, "compile_document", compile_ok)
    return seen


def paired(tmp_path: Path, files: dict[str, str] | None = None) -> tuple[Path, Path]:
    """A quilt with no repository, paired through a clone at `tmp_path / "project"` with a fresh Overleaf project, its main published as `main.tex` and pushed."""
    root = quilt_at(tmp_path, files or {"drafting/main.tex": SOURCE})
    bare = overleaf(tmp_path)
    quilt = load_quilt(root)
    state = configure(quilt, str(cloned(tmp_path, bare)), "main.tex")
    publication = publish(quilt, state)
    push_publication(quilt, state, publication.commit)
    return root, bare


def landmark_text(root: Path, name: str) -> str:
    history = load_history(load_quilt(root).history_dir)
    entry = history.landmark(name)
    assert entry is not None, name
    return history.landmark_path(entry).read_text(encoding="utf-8")


def test_a_quilt_that_is_no_repository_publishes_and_takes_a_pull(tmp_path: Path, compiled: list[str]) -> None:
    save_author("Tester")  # a quilt with no repository has no git user name to fall back on
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE, ".loom/private.txt": "private acceptance\n"})
    bare = overleaf(tmp_path)
    quilt = load_quilt(root)
    state = configure(quilt, str(cloned(tmp_path, bare)), "main.tex")
    clone = workspace(root)
    assert clone.resolve() == (tmp_path / "project").resolve() and (state.remote, state.branch) == ("origin", "master")
    assert state.integrated == run(bare, "rev-parse", "master")

    publication = publish(quilt, state)
    assert publication.paths == ["loom.sty", "main.tex"] and compiled == ["main.tex"]
    assert run(clone, "rev-parse", "refs/loom/publication") == publication.commit
    assert run(bare, "rev-parse", "master") != publication.commit  # prepared, not sent
    assert publication.landmarks == [f"main-published-{publication.commit[:12]}"]
    assert landmark_text(root, publication.landmarks[0]) == SOURCE
    push_publication(quilt, state, publication.commit)
    assert run(bare, "rev-parse", "master") == publication.commit
    published = tree_files(clone, publication.commit)
    assert set(published) == {"loom.sty", "main.tex"} and published["main.tex"] == SOURCE.encode()
    state = fetch(quilt, state)
    assert state.integrated == state.incoming == publication.commit
    assert incoming_patch(quilt, state) == b""

    other = colleague(tmp_path, bare)
    edit(
        other,
        "edit statement",
        {
            "main.tex": SOURCE.replace("zk-0001}A", "zk-0001}B"),
            "new-section.tex": "New collaborator file.\n",
            "references.bib": "@book{source,title={A collaborator reference}}\n",
        },
    )
    # the author's own edit, elsewhere in the file the pull changes, and never committed anywhere
    (root / "drafting/main.tex").write_text(SOURCE + "% the author's note\n", encoding="utf-8")
    before = (root / "drafting/main.tex").read_bytes()
    state = fetch(quilt, state)
    assert (root / "drafting/main.tex").read_bytes() == before
    assert changed_files(clone, state.integrated, state.incoming) == [
        {"status": "M", "path": "main.tex"},
        {"status": "A", "path": "new-section.tex"},
        {"status": "A", "path": "references.bib"},
    ]
    patch = incoming_patch(quilt, state)
    # the workspace's root is the main document's directory, so its files land there
    assert b"zk-0001}B" in patch and b"a/drafting/main.tex" in patch and b"b/drafting/new-section.tex" in patch
    report = build(quilt)
    assert report.manifest["incoming"]["workspace"] == str(bare)
    assert [change["key"] for change in report.manifest["incoming"]["changes"]] == [
        "zk-0001",
        "prose:drafting/new-section.tex",
    ]
    bib = next(f for f in report.manifest["incoming"]["files"] if f["path"] == "references.bib")
    assert "A collaborator reference" in bib["diff"]
    with pytest.raises(SyncError, match="awaiting incorporation"):
        publish(quilt, state)

    after = pull_files(quilt, state)
    assert sorted(after) == ["drafting/main.tex", "drafting/new-section.tex", "drafting/references.bib"]
    assert b"zk-0001}B" in after["drafting/main.tex"] and b"the author's note" in after["drafting/main.tex"]
    assert (root / "drafting/main.tex").read_bytes() == before and not (root / "drafting/new-section.tex").exists()
    with pytest.raises(ApiError) as refusal:
        handle(root, "sync-incorporate", {"incoming": "0" * 40, "base": state.integrated})
    assert refusal.value.code == "revision-changed"
    finished = handle(root, "sync-incorporate", {"incoming": state.incoming, "base": state.integrated})["result"]
    state = SyncState.read(root)
    assert finished["integrated"] == state.integrated == state.incoming
    assert finished["paths"] == ["drafting/main.tex", "drafting/new-section.tex", "drafting/references.bib"]
    text = (root / "drafting/main.tex").read_text(encoding="utf-8")
    assert "zk-0001}B" in text and "% the author's note" in text  # applied hunk by hunk
    assert (root / "drafting/new-section.tex").read_text() == "New collaborator file.\n"
    assert finished["landmarks"] == [f"main-before-pull-{state.incoming[:12]}"]
    assert landmark_text(root, finished["landmarks"][0]) == before.decode()
    assert not (root / ".git").exists()
    with pytest.raises(SyncError, match="no incoming revision"):
        pull_files(quilt, state)

    unresolved = build(quilt).manifest["unresolved"]
    assert [(row["key"], row["cause"], row["status"]) for row in unresolved] == [
        ("zk-0001", "incoming-pull", "needs-review")
    ]
    assert unresolved[0]["local_changed"] is False
    decide(scan(quilt), "zk-0001", "ok")
    assert build(quilt).manifest["unresolved"][0]["status"] == "ok"
    (root / "drafting/main.tex").write_text(text.replace("zk-0001}B", "zk-0001}C"), encoding="utf-8")
    changed = build(quilt).manifest["unresolved"][0]
    assert changed["status"] == "needs-review" and changed["invalidated"] and changed["local_changed"] is True
    (root / "drafting/main.tex").write_text(text, encoding="utf-8")
    assert build(quilt).manifest["unresolved"][0]["local_changed"] is False

    edit(other, "revise statement again", {"main.tex": SOURCE.replace("zk-0001}A", "zk-0001}D")})
    state = fetch(quilt, state)
    said = flat(ok("sync", "incorporate", cwd=root).stdout)
    assert (
        said.startswith("incorporated the revision of ") and state.incoming[:7] not in said
    )  # named by when, not its hash (T4)
    assert "mathematics remains to be reviewed" in said and "as it was, stamped as landmarks (1)" in said
    names = [Path(str(e.get("landmark"))).stem for e in load_history(quilt.history_dir).landmarks()]
    assert any(n.startswith("main-before-pull-") for n in names), names
    latest = build(quilt).manifest["unresolved"][0]
    assert latest["pull"] == state.incoming and latest["local_changed"] is False


def test_the_quilt_s_own_repository_is_never_touched(tmp_path: Path, compiled: list[str]) -> None:
    """A quilt that is a repository keeps its history, index and refs through pairing, publishing, fetching and incorporating; loom's Git runs in the sync directory."""
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE})
    run(root, "init", "-q", "-b", "main")
    run(root, "config", "user.name", "Tester")
    run(root, "config", "user.email", "tester@example.org")
    run(root, "add", ".")
    run(root, "commit", "-q", "-m", "the author's history")
    head, refs = run(root, "rev-parse", "HEAD"), run(root, "for-each-ref")
    bare = overleaf(tmp_path)
    project = cloned(tmp_path, bare)
    said = flat(ok("sync", "init", str(project), "--publish-main", "main.tex", cwd=root).stdout)
    assert said.startswith(f"paired {project} with ") and "(master)" in said
    ok("sync", "publish", "--push", cwd=root)
    edit(colleague(tmp_path, bare), "edit", {"main.tex": SOURCE.replace("zk-0001}A", "zk-0001}B")})
    ok("sync", "fetch", cwd=root)
    ok("sync", "incorporate", cwd=root)
    assert "zk-0001}B" in (root / "drafting/main.tex").read_text()
    assert run(root, "rev-parse", "HEAD") == head and run(root, "for-each-ref") == refs
    assert run(root, "diff", "--cached", "--name-only") == ""
    assert (
        run(root, "status", "--porcelain", "--", "drafting/main.tex") == "M drafting/main.tex"
    )  # the author commits it


def test_the_sync_directory_s_files_and_branch_are_never_touched(tmp_path: Path, compiled: list[str]) -> None:
    """Pairing, publishing, pushing, fetching and incorporating leave the person's clone as they left it: its HEAD, checked-out branch, index and files. Only its tracking branch and loom's own refs move."""
    save_author("Tester")
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE})
    bare = overleaf(tmp_path)
    project = cloned(tmp_path, bare)
    head, branch = run(project, "rev-parse", "HEAD"), run(project, "symbolic-ref", "HEAD")
    files = {p.name: p.read_bytes() for p in project.iterdir() if p.is_file()}
    ok("sync", "init", str(project), "--publish-main", "main.tex", cwd=root)
    ok("sync", "publish", "--push", cwd=root)
    edit(colleague(tmp_path, bare), "edit", {"main.tex": SOURCE.replace("zk-0001}A", "zk-0001}B")})
    ok("sync", "fetch", cwd=root)
    ok("sync", "incorporate", cwd=root)
    assert run(project, "rev-parse", "HEAD") == head and run(project, "symbolic-ref", "HEAD") == branch
    assert run(project, "status", "--porcelain") == ""
    assert {p.name: p.read_bytes() for p in project.iterdir() if p.is_file()} == files
    assert run(project, "rev-parse", "refs/remotes/origin/master") == run(bare, "rev-parse", "master")
    refs = {line.split()[-1] for line in run(project, "for-each-ref").splitlines()}
    assert {r for r in refs if not r.startswith("refs/loom/")} == {
        "refs/heads/master",
        "refs/remotes/origin/HEAD",
        "refs/remotes/origin/master",
    }


def test_init_takes_a_clone_of_the_workspace(tmp_path: Path) -> None:
    """`sync init` names the person's clone and refuses anything else, each refusal naming what clears it; nothing is cloned, and no record is written."""
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE})
    bare = overleaf(tmp_path)
    refused("sync", "init", cwd=root, code=2, match="Missing argument 'DIR'")
    for url in ("https://git.overleaf.com/0123abcd", "git@github.com:someone/paper.git"):
        for dry in ((), ("--dry-run",)):
            r = refused("sync", "init", url, *dry, cwd=root, code=2, match="is a URL")
            assert f"git clone {url} DIR" in flat(r.stderr) and "loom sync init DIR" in flat(r.stderr), r.stderr
    refused("sync", "init", str(tmp_path / "nowhere"), cwd=root, code=2, match="is not a directory")
    (tmp_path / "plain").mkdir()
    refused("sync", "init", str(tmp_path / "plain"), cwd=root, code=2, match="is not a Git repository")
    refused("sync", "init", str(bare), cwd=root, code=2, match="is a bare repository")
    project = cloned(tmp_path, bare)
    (project / "sub").mkdir()
    refused("sync", "init", str(project / "sub"), cwd=root, code=2, match="is inside the repository")
    run(project, "branch", "--unset-upstream")
    refused("sync", "init", str(project), cwd=root, code=2, match="follows no remote")
    empty = tmp_path / "empty.git"
    subprocess.check_call(["git", "init", "-q", "--bare", str(empty)])
    hollow = cloned(tmp_path, empty, "hollow")
    refused("sync", "init", str(hollow), cwd=root, code=2, match="has no commits; create the project there first")
    assert not (root / ".loom/source-sync.json").exists()
    assert "Overleaf project" in ok("sync", "init", "--help").output


def test_init_refuses_the_quilt_s_repository_and_loom_s_own_directories(tmp_path: Path) -> None:
    """Loom runs Git only in a repository of the workspace's own: never the quilt's, a worktree of it, or a clone inside a directory loom rewrites."""
    root, _ = quilt_with_upstream(tmp_path)
    refused("sync", "init", str(root), cwd=root, code=2, match="holds this quilt")
    run(root, "worktree", "add", "-q", "-b", "side", str(tmp_path / "side"))
    refused("sync", "init", str(tmp_path / "side"), cwd=root, code=2, match="worktree of this quilt's own repository")
    bare = overleaf(tmp_path)
    for inside in (".loom/overleaf", ".loom/build/overleaf"):
        refused("sync", "init", str(cloned(root, bare, inside)), cwd=root, code=2, match="is inside .loom/")
    config = root / "config.toml"
    config.write_text(config.read_text().replace("[quilt]\n", '[quilt]\nhistory = "hist"\n', 1))
    refused("sync", "init", str(cloned(root, bare, "hist/overleaf")), cwd=root, code=2, match="is inside hist/")
    assert not (root / ".loom/source-sync.json").exists()


def test_a_missing_clone_or_an_old_record_is_refused_with_the_command_that_pairs_again(
    tmp_path: Path, compiled: list[str]
) -> None:
    import shutil

    root, _ = paired(tmp_path)
    shutil.rmtree(tmp_path / "project")
    refused("sync", "fetch", cwd=root, code=2, match="name it again with `loom sync init DIR`")
    (root / ".loom/source-sync.json").write_text(
        '{"remote":"origin","branch":"main","master":"drafting/main.tex","integrated":"abc"}\n', encoding="utf-8"
    )
    with pytest.raises(SyncError, match="pair again with `loom sync init DIR`"):
        SyncState.read(root)


def test_a_record_without_documents_selects_the_main_document(tmp_path: Path) -> None:
    (tmp_path / ".loom").mkdir()
    (tmp_path / ".loom/source-sync.json").write_text(
        '{"directory":"project","remote":"origin","url":"overleaf.git","branch":"master","master":"drafting/main.tex","integrated":"abc"}\n',
        encoding="utf-8",
    )
    assert SyncState.read(tmp_path).documents == ["drafting/main.tex"]


def test_selected_documents_publish_one_union_from_the_files_on_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, compiled: list[str]
) -> None:
    import loom.sync as sync

    root = quilt_at(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE + "\\begin{document}\n\\input{shared/common}\n\\end{document}\n",
            "drafting/toy.tex": PREAMBLE
            + "\\begin{document}\n\\input{shared/common}\n\\begin{lemma}\\label{zk-0002}Toy.\\end{lemma}\n\\end{document}\n",
            "drafting/private.tex": PREAMBLE + "\\begin{document}Not selected.\\end{document}\n",
            "drafting/shared/common.tex": "\\begin{lemma}\\label{zk-0001}Shared.\\end{lemma}\n",
            ".loom/private.txt": "private\n",
        },
    )
    bare = overleaf(tmp_path)
    quilt = load_quilt(root)
    state = configure(quilt, str(cloned(tmp_path, bare)), "main.tex")
    state = update_documents(quilt, state, "add", "drafting/toy.tex")
    assert SyncState.read(root).documents == ["drafting/main.tex", "drafting/toy.tex"]
    tip = run(bare, "rev-parse", "master")

    def toy_fails(_root: Path, _base: str, master: str, *_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(ok=master != "toy.tex", first_error="toy failed")

    monkeypatch.setattr(sync, "compile_document", toy_fails)
    with pytest.raises(SyncError, match="drafting/toy.tex does not compile"):
        publish(quilt, state)
    assert load_history(quilt.history_dir).landmarks() == []  # a refused publication stamps nothing
    monkeypatch.setattr(sync, "compile_document", lambda *_a, **_k: SimpleNamespace(ok=True))

    publication = publish(quilt, state)
    # the main document's directory is the workspace's root, so its files publish by their paths from there
    assert publication.paths == ["loom.sty", "main.tex", "shared/common.tex", "toy.tex"]
    assert set(tree_files(workspace(root), publication.commit)) == set(publication.paths)
    assert len(publication.landmarks) == 2 and run(bare, "rev-parse", "master") == tip
    again = publish(quilt, SyncState.read(root))
    assert again.reused and again.commit == publication.commit and len(load_history(quilt.history_dir).landmarks()) == 2
    (root / "drafting/shared/common.tex").write_text("\\begin{lemma}\\label{zk-0001}Shared, edited.\\end{lemma}\n")
    edited = publish(quilt, SyncState.read(root))  # what is on disk publishes; nothing has to be committed
    assert edited.commit != publication.commit
    assert b"Shared, edited." in tree_files(workspace(root), edited.commit)["shared/common.tex"]

    collision = SyncState.read(root)
    collision.published_main = "toy.tex"
    with pytest.raises(SyncError, match="two quilt files"):
        publish(quilt, collision)

    said = flat(ok("sync", "publish", cwd=root).stdout)
    assert said.startswith("prepared the revision of ") and ": 4 files for drafting/main.tex, drafting/toy.tex" in said
    assert "loom sync publish --push sends it" in said
    pushed = flat(ok("sync", "publish", "--push", cwd=root).stdout)
    assert "stamped earlier as landmarks" in pushed  # the revision prepared above, not stamped again
    assert pushed.startswith("published the revision of ") and edited.commit[:7] not in pushed
    state = SyncState.read(root)
    assert run(bare, "rev-parse", "master") == state.prepared == state.integrated == state.incoming
    assert flat(ok("sync", "publish", cwd=root).stdout).startswith("nothing to publish: ")

    (root / "drafting/shared/common.tex").write_text("\\begin{lemma}\\label{zk-0001}Shared, again.\\end{lemma}\n")
    publication = publish(quilt, state)
    saved_git = sync.git

    def transport_failure(cwd: Path, *args: str, **kwargs: object) -> bytes:
        if args[0] == "push":
            raise SyncError("connection lost")
        return saved_git(cwd, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(sync, "git", transport_failure)
    with pytest.raises(SyncError, match="outcome uncertain"):
        push_publication(quilt, state, publication.commit)
    assert SyncState.read(root).prepared == publication.commit
    assert SyncState.read(root).integrated != publication.commit
    monkeypatch.setattr(sync, "git", saved_git)
    saved_write = SyncState.write

    def disk_failure(self: SyncState, root: Path) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(SyncState, "write", disk_failure)
    with pytest.raises(SyncError, match="recording local success failed"):
        push_publication(quilt, state, publication.commit)
    assert run(bare, "rev-parse", "master") == publication.commit
    monkeypatch.setattr(SyncState, "write", saved_write)
    state = fetch(quilt, SyncState.read(root))
    assert state.integrated == state.incoming == publication.commit

    with pytest.raises(SyncError, match="is the document the workspace.s main file is published from, so it stays"):
        update_documents(quilt, state, "remove", "drafting/main.tex")
    state = update_documents(quilt, state, "remove", "drafting/toy.tex")
    assert state.documents == ["drafting/main.tex"]
    state = update_documents(quilt, state, "add", "drafting/toy.tex")
    (root / "drafting/toy.tex").unlink()
    state = update_documents(quilt, state, "remove", "drafting/toy.tex")
    assert state.documents == ["drafting/main.tex"]

    # a collaborator's push after preparation is rejected, and the prepared revision kept
    (root / "drafting/shared/common.tex").write_text("\\begin{lemma}\\label{zk-0001}Shared, third.\\end{lemma}\n")
    publication = publish(quilt, state)
    edit(colleague(tmp_path, bare), "collaborator update", {"notes.tex": "A note.\n"})
    with pytest.raises(SyncError, match="has moved since the last fetch"):
        push_publication(quilt, state, publication.commit)
    assert SyncState.read(root).prepared == publication.commit
    state = fetch(quilt, SyncState.read(root))
    assert state.incoming != state.integrated
    with pytest.raises(SyncError, match="incoming"):
        publish(quilt, state)


def test_a_pull_that_does_not_apply_or_would_overwrite_a_file_writes_nothing(
    tmp_path: Path, compiled: list[str]
) -> None:
    root, bare = paired(tmp_path)
    quilt = load_quilt(root)
    other = colleague(tmp_path, bare)
    edit(other, "edit", {"main.tex": SOURCE.replace("zk-0001}A", "zk-0001}B")})
    state = fetch(quilt, SyncState.read(root))
    (root / "drafting/main.tex").write_text(SOURCE.replace("zk-0001}A", "zk-0001}Z"), encoding="utf-8")
    refused("sync", "incorporate", cwd=root, code=1, match="Read it with `loom sync status --patch`")
    assert "zk-0001}Z" in (root / "drafting/main.tex").read_text()
    assert not [e for e in load_history(quilt.history_dir).landmarks() if "before-pull" in str(e.get("landmark"))]
    (root / "drafting/main.tex").write_text(SOURCE, encoding="utf-8")
    (root / "drafting/extra.tex").write_text("mine\n", encoding="utf-8")
    edit(other, "add a file", {"extra.tex": "theirs\n"})
    state = fetch(quilt, state)
    with pytest.raises(SyncError, match="drafting/extra.tex already exists locally"):
        pull_files(quilt, state)
    assert (root / "drafting/extra.tex").read_text() == "mine\n"


def test_a_failure_while_incorporating_restores_every_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, compiled: list[str]
) -> None:
    import loom.sync as sync

    root, bare = paired(tmp_path)
    quilt = load_quilt(root)
    edit(colleague(tmp_path, bare), "edit", {"main.tex": SOURCE.replace("zk-0001}A", "zk-0001}B")})
    state = fetch(quilt, SyncState.read(root))
    record = (root / ".loom/source-sync.json").read_bytes()
    landmarks = len(load_history(quilt.history_dir).landmarks())

    def broken(*_args: object) -> None:
        raise RuntimeError("interrupted")

    monkeypatch.setattr(sync, "_record_moves", broken)
    with pytest.raises(RuntimeError, match="interrupted"):
        sync.incorporate(quilt, state)
    assert (root / "drafting/main.tex").read_text() == SOURCE
    assert (root / ".loom/source-sync.json").read_bytes() == record
    assert len(load_history(quilt.history_dir).landmarks()) == landmarks


def test_sync_follows_a_linearized_main_and_overleaf_keeps_its_file_name(tmp_path: Path, compiled: list[str]) -> None:
    """A sync record written before `loom linearize` publishes the flat document as Overleaf's main, and a pull lands in it; the record keeps the path it was written with (plan 0.16 phase 1)."""
    root = quilt_at(
        tmp_path,
        {
            "drafting/main.tex": PREAMBLE + "\\begin{document}\n\\input{sections/one}\n\\end{document}\n",
            "drafting/sections/one.tex": "\\begin{lemma}\\label{zk-0001}A\\end{lemma}\n",
        },
    )
    bare = overleaf(tmp_path)
    configure(load_quilt(root), str(cloned(tmp_path, bare)), "main.tex")
    ok("linearize", "drafting/main.tex", "--to", "drafting/flat.tex", "--no-check", cwd=root)
    quilt = load_quilt(root)
    state = SyncState.read(root)
    assert state.master == "drafting/main.tex"
    publication = publish(quilt, state)
    push_publication(quilt, SyncState.read(root), publication.commit)
    assert publication.paths == [
        "loom.sty",
        "main.tex",
    ]  # the same name on Overleaf; the inlined section is no longer an input
    assert tree_files(workspace(root), publication.commit)["main.tex"] == (root / "drafting/flat.tex").read_bytes()
    assert SyncState.read(root).master == "drafting/main.tex"  # resolved when read, never rewritten

    other = colleague(tmp_path, bare)
    text = (root / "drafting/flat.tex").read_text(encoding="utf-8")
    edit(other, "edit statement", {"main.tex": text.replace("zk-0001}A", "zk-0001}B")})
    state = fetch(quilt, SyncState.read(root))
    patch = incoming_patch(quilt, state)
    assert b"a/drafting/flat.tex" in patch and b"drafting/main.tex" not in patch
    assert [c["key"] for c in build(quilt).manifest["incoming"]["changes"]] == ["zk-0001"]
    original = (root / "drafting/main.tex").read_bytes()
    handle(root, "sync-incorporate", {"incoming": state.incoming, "base": state.integrated})
    assert "zk-0001}B" in (root / "drafting/flat.tex").read_text(encoding="utf-8")
    assert (root / "drafting/main.tex").read_bytes() == original


# ---- a collaborator's rename (plan 0.16 phase 2) ------------------------------------------------


def renamed_pair(tmp_path: Path) -> tuple[Path, Path]:
    """A quilt paired with an Overleaf project whose main is `drafting/main.tex`, `zk-0001` accepted in it, and a collaborator's clone."""
    save_author("Tester")  # status shows the local reviewer's acceptance, and this quilt has no git user to name one
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE})
    ok("accept", "zk-0001", "--force", "--as", "Tester", cwd=root)
    bare = overleaf(tmp_path)
    quilt = load_quilt(root)
    state = configure(quilt, str(cloned(tmp_path, bare)))
    push_publication(quilt, state, publish(quilt, state).commit)
    return root, colleague(tmp_path, bare)


def moves(root: Path) -> list[dict]:
    import json

    p = root / ".loom" / "history" / "ledger.jsonl"
    lines = [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.is_file() else []
    return [x for x in lines if x["action"] == "move"]


def test_a_collaborator_s_exact_rename_is_recorded_when_the_pull_is_incorporated(
    tmp_path: Path, compiled: list[str]
) -> None:
    root, other = renamed_pair(tmp_path)
    run(other, "mv", "main.tex", "paper.tex")
    run(other, "commit", "-q", "-m", "rename")
    run(other, "push", "-q", "origin", "HEAD:master")
    quilt = load_quilt(root)
    state = fetch(quilt, SyncState.read(root))
    assert moves(root) == []  # never on fetch
    handle(root, "sync-incorporate", {"incoming": state.incoming, "base": state.integrated})
    assert [{k: m[k] for k in ("from", "to", "moved", "via")} for m in moves(root)] == [
        {"from": "drafting/main.tex", "to": "drafting/paper.tex", "moved": False, "via": "sync"}
    ]
    assert 'main = "drafting/paper.tex"' in (root / "config.toml").read_text()
    state = SyncState.read(root)
    assert state.published_main == "paper.tex"  # Overleaf keeps the collaborator's name at the next publish
    assert state.master == "drafting/main.tex"  # the record is followed, never rewritten
    assert json_of("status", "--json", cwd=root)["keys"]["zk-0001"]["acceptance"]["fresh"] is True
    assert not [x for x in json_of("lint", "--json", cwd=root)["diagnostics"] if x["code"] == "loom:document-gone"]
    assert "drafting/main.tex -> drafting/paper.tex (renamed in a pull)" in ok("history", cwd=root).stdout


def test_a_rename_with_an_edit_is_not_recorded_and_the_document_is_gone(tmp_path: Path, compiled: list[str]) -> None:
    root, other = renamed_pair(tmp_path)
    text = (other / "main.tex").read_text(encoding="utf-8")
    run(other, "rm", "-q", "main.tex")
    edit(other, "rename and edit", {"paper.tex": text.replace("zk-0001}A", "zk-0001}B")})
    quilt = load_quilt(root)
    state = fetch(quilt, SyncState.read(root))
    handle(root, "sync-incorporate", {"incoming": state.incoming, "base": state.integrated})
    assert moves(root) == []
    gone = [x for x in json_of("lint", "--json", cwd=root)["diagnostics"] if x["code"] == "loom:document-gone"]
    assert [g["fixes"][0]["command"] for g in gone] == ["loom mv drafting/main.tex NEW"]


def test_only_an_unambiguous_identical_pair_is_a_rename(tmp_path: Path) -> None:
    """Two identical files deleted and one added, or one deleted and two added, cannot say which went where."""
    root = tmp_path / "r"
    root.mkdir()
    run(root, "init", "-q", "-b", "main")
    run(root, "config", "user.name", "Tester")
    run(root, "config", "user.email", "tester@example.org")
    for name, body in (("a.tex", "same\n"), ("b.tex", "same\n"), ("c.tex", "c\n"), ("d.tex", "d\n")):
        (root / name).write_text(body, encoding="utf-8")
    run(root, "add", ".")
    run(root, "commit", "-q", "-m", "before")
    before = run(root, "rev-parse", "HEAD")
    run(root, "rm", "-q", "a.tex", "b.tex", "c.tex", "d.tex")
    (root / "e.tex").write_text("same\n", encoding="utf-8")
    (root / "f.tex").write_text("c\n", encoding="utf-8")
    (root / "g.tex").write_text("d\n", encoding="utf-8")
    (root / "h.tex").write_text("d\n", encoding="utf-8")
    run(root, "add", ".")
    run(root, "commit", "-q", "-m", "after")
    assert exact_renames(root, before, run(root, "rev-parse", "HEAD")) == [("c.tex", "f.tex")]


def test_incorporating_a_pull_is_one_command_and_the_author_s() -> None:
    """`sync incorporate` is the one way in, beside Incoming; the two-step prepare and finish are gone, and an agent is refused."""
    for gone in ("prepare", "finish", "incorporated"):
        refused("sync", gone, code=2, match="No such command")
    refused("sync", "incorporate", code=2, match="an agent is running this shell", env={"AI_AGENT": "1"})


def quilt_with_upstream(tmp_path: Path) -> tuple[Path, Path]:
    """The re-grade's reproduction: a quilt that is a repository whose `origin` is a bare repository holding the whole quilt."""
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE})
    run(root, "init", "-q", "-b", "main")
    run(root, "config", "user.name", "Tester")
    run(root, "config", "user.email", "tester@example.org")
    run(root, "add", ".")
    run(root, "commit", "-q", "-m", "the author's history")
    upstream = tmp_path / "upstream.git"
    subprocess.check_call(["git", "init", "-q", "--bare", "-b", "main", str(upstream)])
    run(root, "remote", "add", "origin", str(upstream))
    run(root, "push", "-q", "origin", "main")
    return root, upstream


def test_sync_init_refuses_the_quilt_s_own_upstream_however_it_is_spelled(tmp_path: Path) -> None:
    """Defect 1: pairing with a remote of the quilt's own repository would let a publish replace the quilt with its documents. The clone's remote is compared however its URL is spelled."""
    root, upstream = quilt_with_upstream(tmp_path)
    before = run(upstream, "rev-parse", "main")
    copy = cloned(tmp_path, upstream, "copy")
    for url in (str(upstream), str(upstream) + "/", f"file://{upstream}", "../upstream.git"):
        run(copy, "remote", "set-url", "origin", url)
        for dry in ((), ("--dry-run",)):
            r = refused("sync", "init", str(copy), *dry, cwd=root, code=2, match="origin")
            assert "own" in r.stderr and r.stdout == "", r.output
    assert not (root / ".loom/source-sync.json").exists() and run(upstream, "rev-parse", "main") == before


def test_publish_push_refuses_a_workspace_that_holds_a_quilt(tmp_path: Path, compiled: list[str]) -> None:
    """The second guard. `sync init` refuses a clone whose tip holds a quilt, and a record whose workspace has come to hold one since still never publishes over it."""
    save_author("Tester")
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE})
    bare = overleaf(tmp_path)
    project = cloned(tmp_path, bare)
    ok("sync", "init", str(project), cwd=root)
    edit(colleague(tmp_path, bare), "a quilt", {"config.toml": CONFIG})
    run(project, "fetch", "-q", "origin")
    state = SyncState.read(root)
    state.integrated = run(project, "rev-parse", "refs/remotes/origin/master")
    state.write(root)
    before = run(bare, "rev-parse", "master")
    r = refused("sync", "publish", "--push", cwd=root, code=2, match="config.toml")
    assert "[quilt]" in r.stderr and r.stdout == "", r.output
    assert run(bare, "rev-parse", "master") == before
    refused("sync", "init", str(project), cwd=root, code=2, match="holds a config.toml with a [quilt] table")


def test_a_rejected_push_says_the_workspace_moved_and_what_to_run(tmp_path: Path, compiled: list[str]) -> None:
    """Defect 8: the verdict first, git's hints dropped, and no "Done."."""
    save_author("Tester")
    root, bare = paired(tmp_path)
    (root / "drafting/main.tex").write_text(SOURCE.replace("zk-0001}A", "zk-0001}Mine"))
    ok("sync", "publish", cwd=root)
    edit(colleague(tmp_path, bare), "theirs", {"notes.tex": "A note.\n"})
    r = refused("sync", "publish", "--push", cwd=root, code=2, match="has moved")
    first = flat(r.stderr)
    assert first.startswith("Error: ") and first.index("loom sync fetch") < first.index("prepared"), r.stderr
    for noise in ("hint:", "Done", "git pull", "[rejected]", "To "):
        assert noise not in r.stderr, (noise, r.stderr)


def test_sync_says_only_what_happened(tmp_path: Path, compiled: list[str]) -> None:
    """T7: a fetch with nothing new said "fetched" with the old time, a selected document added again said "added", and pairing again set `--publish-main` back without a word; T4: revisions were named by their hashes."""
    import re

    def verdict(args: tuple[str, ...]) -> str:
        return " ".join(ok(*args, cwd=root).stdout.split("\n\n")[0].split())

    save_author("Tester")
    root, bare = paired(tmp_path)
    edit(colleague(tmp_path, bare), "theirs", {"notes.tex": "A note.\n"})
    first = verdict(("sync", "fetch"))
    assert first.startswith("fetched the revision of ") and "1 file changed" in first, first
    again = verdict(("sync", "fetch"))
    assert again.startswith("nothing new from ") and "fetched" not in again, again
    assert "the viewer's Incoming panel" in again
    status = ok("sync", "status", cwd=root).stdout
    assert not re.search(r"\b[0-9a-f]{7}\b", status), status  # hashes are in the JSON only
    added = verdict(("sync", "documents", "add", "drafting/main.tex"))
    assert added.startswith("drafting/main.tex is already selected; nothing changed"), added
    ok("sync", "init", str(tmp_path / "project"), cwd=root)  # paired again without --publish-main
    assert SyncState.read(root).published_main == "main.tex"


def test_a_sync_directory_inside_the_quilt_is_never_read_as_the_quilt_s(tmp_path: Path) -> None:
    """Its files are copies of the quilt's sources, so the scan, the watcher, the importer's mirror and a section draft's context all leave it out, and no id is defined twice."""
    from loom.render.watch import snapshot
    from loom.reshape.importer import _mirror_quilt
    from loom.section_drafts import capture_context

    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE})
    bare = overleaf(tmp_path)
    edit(colleague(tmp_path, bare), "the paper", {"main.tex": SOURCE})
    configure(load_quilt(root), str(cloned(root, bare, "overleaf")), "main.tex")
    assert SyncState.read(root).directory == "overleaf"
    quilt = load_quilt(root)
    result = scan(quilt)
    assert result.nodes["zk-0001"].kind != "conflict" and result.nodes["zk-0001"].reached_by == ["drafting/main.tex"]
    assert not any(p.relative_to(root).parts[0] == "overleaf" for p in snapshot(root))
    _mirror_quilt(quilt, tmp_path / "mirror")
    assert (tmp_path / "mirror/drafting/main.tex").is_file() and not (tmp_path / "mirror/overleaf").exists()
    assert not any(
        p.startswith("overleaf/") for p in capture_context(result, "drafting/main.tex", write=False)["hashes"]
    )
    refused("mv", "overleaf/main.tex", "drafting/other.tex", cwd=root, code=2, match="is inside overleaf/")


def test_documents_published_together_sit_under_the_main_document_s_directory(tmp_path: Path) -> None:
    """The main document's directory is the workspace's root, where Overleaf compiles it, so a document beside it in another directory cannot publish with it."""
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE, "talks/talk.tex": SOURCE.replace("zk-0001", "zk-0002")})
    state = configure(load_quilt(root), str(cloned(tmp_path, overleaf(tmp_path))), "main.tex")
    with pytest.raises(SyncError, match="outside drafting/, the directory of drafting/main.tex"):
        update_documents(load_quilt(root), state, "add", "talks/talk.tex")
