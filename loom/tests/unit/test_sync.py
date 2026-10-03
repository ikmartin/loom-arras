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
    WORKSPACE,
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
    for rel, text in {"loom.sty": "% local support\n", **files}.items():
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

    def compile_ok(_root: Path, master: str, *_args: object, **_kwargs: object) -> SimpleNamespace:
        seen.append(master)
        return SimpleNamespace(ok=True)

    monkeypatch.setattr(sync, "compile_tex", compile_ok)
    return seen


def paired(tmp_path: Path, files: dict[str, str] | None = None) -> tuple[Path, Path]:
    """A quilt with no repository, paired with a fresh Overleaf project, its main published as `main.tex` and pushed."""
    root = quilt_at(tmp_path, files or {"drafting/main.tex": SOURCE})
    bare = overleaf(tmp_path)
    quilt = load_quilt(root)
    state = configure(quilt, str(bare), "main.tex")
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
    state = configure(quilt, str(bare), "main.tex")
    clone = workspace(root)
    assert clone == root / WORKSPACE and state.branch == "master"
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
    assert b"zk-0001}B" in patch and b"a/drafting/main.tex" in patch and b"b/new-section.tex" in patch
    report = build(quilt)
    assert report.manifest["incoming"]["workspace"] == str(bare)
    assert [change["key"] for change in report.manifest["incoming"]["changes"]] == ["zk-0001", "prose:new-section.tex"]
    bib = next(f for f in report.manifest["incoming"]["files"] if f["path"] == "references.bib")
    assert "A collaborator reference" in bib["diff"]
    with pytest.raises(SyncError, match="awaiting incorporation"):
        publish(quilt, state)

    after = pull_files(quilt, state)
    assert sorted(after) == ["drafting/main.tex", "new-section.tex", "references.bib"]
    assert b"zk-0001}B" in after["drafting/main.tex"] and b"the author's note" in after["drafting/main.tex"]
    assert (root / "drafting/main.tex").read_bytes() == before and not (root / "new-section.tex").exists()
    with pytest.raises(ApiError) as refusal:
        handle(root, "sync-incorporate", {"incoming": "0" * 40, "base": state.integrated})
    assert refusal.value.code == "revision-changed"
    finished = handle(root, "sync-incorporate", {"incoming": state.incoming, "base": state.integrated})["result"]
    state = SyncState.read(root)
    assert finished["integrated"] == state.integrated == state.incoming
    assert finished["paths"] == ["drafting/main.tex", "new-section.tex", "references.bib"]
    text = (root / "drafting/main.tex").read_text(encoding="utf-8")
    assert "zk-0001}B" in text and "% the author's note" in text  # applied hunk by hunk
    assert (root / "new-section.tex").read_text() == "New collaborator file.\n"
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
    assert said.startswith(f"incorporated {state.incoming[:7]} from ")
    assert "mathematics remains to be reviewed" in said and "as it was, stamped as landmarks (1)" in said
    names = [Path(str(e.get("landmark"))).stem for e in load_history(quilt.history_dir).landmarks()]
    assert any(n.startswith("main-before-pull-") for n in names), names
    latest = build(quilt).manifest["unresolved"][0]
    assert latest["pull"] == state.incoming and latest["local_changed"] is False


def test_the_quilt_s_own_repository_is_never_touched(tmp_path: Path, compiled: list[str]) -> None:
    """A quilt that is a repository keeps its history, index and refs through pairing, publishing, fetching and incorporating; loom's Git runs in its own clone."""
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE})
    run(root, "init", "-q", "-b", "main")
    run(root, "config", "user.name", "Tester")
    run(root, "config", "user.email", "tester@example.org")
    run(root, "add", ".")
    run(root, "commit", "-q", "-m", "the author's history")
    head, refs = run(root, "rev-parse", "HEAD"), run(root, "for-each-ref")
    bare = overleaf(tmp_path)
    said = flat(ok("sync", "init", str(bare), "--publish-main", "main.tex", cwd=root).stdout)
    assert said.startswith("paired with ") and "(master)" in said
    assert f"`.gitignore` does not ignore {WORKSPACE}/, loom's clone of the workspace fix: loom upgrade" in said
    (root / ".gitignore").write_text(".loom/workspace/\nbuild/\n", encoding="utf-8")
    assert ".gitignore" not in ok("sync", "init", str(bare), "--publish-main", "main.tex", cwd=root).output
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


def test_init_takes_the_workspace_url(tmp_path: Path) -> None:
    root = quilt_at(tmp_path, {"drafting/main.tex": SOURCE})
    refused("sync", "init", cwd=root, code=2, match="Missing argument 'URL'")
    refused("sync", "init", "--remote", "origin", cwd=root, code=2, match="No such option")
    refused("sync", "init", str(tmp_path / "nowhere.git"), cwd=root, code=2, match="git clone")
    assert not (root / WORKSPACE).exists()
    empty = tmp_path / "empty.git"
    subprocess.check_call(["git", "init", "-q", "--bare", str(empty)])
    refused("sync", "init", str(empty), cwd=root, code=2, match="has no commits; create the project there first")
    assert "Overleaf project" in ok("sync", "init", "--help").output


def test_a_missing_clone_or_an_old_record_is_refused_with_the_command_that_pairs_again(
    tmp_path: Path, compiled: list[str]
) -> None:
    import shutil

    root, _ = paired(tmp_path)
    shutil.rmtree(root / WORKSPACE)
    refused("sync", "fetch", cwd=root, code=2, match="pair again with `loom sync init URL`")
    (root / ".loom/source-sync.json").write_text(
        '{"remote":"origin","branch":"main","master":"drafting/main.tex","integrated":"abc"}\n', encoding="utf-8"
    )
    with pytest.raises(SyncError, match="pair again with `loom sync init URL`"):
        SyncState.read(root)


def test_a_record_without_documents_selects_the_main_document(tmp_path: Path) -> None:
    (tmp_path / ".loom").mkdir()
    (tmp_path / ".loom/source-sync.json").write_text(
        '{"url":"overleaf.git","branch":"master","master":"drafting/main.tex","integrated":"abc"}\n',
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
            "shared/common.tex": "\\begin{lemma}\\label{zk-0001}Shared.\\end{lemma}\n",
            ".loom/private.txt": "private\n",
        },
    )
    bare = overleaf(tmp_path)
    quilt = load_quilt(root)
    state = configure(quilt, str(bare), "main.tex")
    state = update_documents(quilt, state, "add", "drafting/toy.tex")
    assert SyncState.read(root).documents == ["drafting/main.tex", "drafting/toy.tex"]
    tip = run(bare, "rev-parse", "master")

    def toy_fails(_root: Path, master: str, *_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(ok=master != "drafting/toy.tex", first_error="toy failed")

    monkeypatch.setattr(sync, "compile_tex", toy_fails)
    with pytest.raises(SyncError, match="drafting/toy.tex does not compile"):
        publish(quilt, state)
    assert load_history(quilt.history_dir).landmarks() == []  # a refused publication stamps nothing
    monkeypatch.setattr(sync, "compile_tex", lambda *_a, **_k: SimpleNamespace(ok=True))

    publication = publish(quilt, state)
    assert publication.paths == ["drafting/toy.tex", "loom.sty", "main.tex", "shared/common.tex"]
    assert set(tree_files(workspace(root), publication.commit)) == set(publication.paths)
    assert len(publication.landmarks) == 2 and run(bare, "rev-parse", "master") == tip
    again = publish(quilt, SyncState.read(root))
    assert again.reused and again.commit == publication.commit and len(load_history(quilt.history_dir).landmarks()) == 2
    (root / "shared/common.tex").write_text("\\begin{lemma}\\label{zk-0001}Shared, edited.\\end{lemma}\n")
    edited = publish(quilt, SyncState.read(root))  # what is on disk publishes; nothing has to be committed
    assert edited.commit != publication.commit
    assert b"Shared, edited." in tree_files(workspace(root), edited.commit)["shared/common.tex"]

    collision = SyncState.read(root)
    collision.published_main = "drafting/toy.tex"
    with pytest.raises(SyncError, match="two quilt files"):
        publish(quilt, collision)

    said = flat(ok("sync", "publish", cwd=root).stdout)
    assert said.startswith(f"prepared {edited.commit[:7]}: 4 files for drafting/main.tex, drafting/toy.tex")
    assert "loom sync publish --push sends it" in said
    pushed = flat(ok("sync", "publish", "--push", cwd=root).stdout)
    assert "stamped earlier as landmarks" in pushed  # the revision prepared above, not stamped again
    assert pushed.startswith(f"published {edited.commit[:7]} to ")
    state = SyncState.read(root)
    assert run(bare, "rev-parse", "master") == state.prepared == state.integrated == state.incoming
    assert flat(ok("sync", "publish", cwd=root).stdout).startswith("nothing to publish: ")

    (root / "shared/common.tex").write_text("\\begin{lemma}\\label{zk-0001}Shared, again.\\end{lemma}\n")
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

    with pytest.raises(SyncError, match="cannot be removed"):
        update_documents(quilt, state, "remove", "drafting/main.tex")
    state = update_documents(quilt, state, "remove", "drafting/toy.tex")
    assert state.documents == ["drafting/main.tex"]
    state = update_documents(quilt, state, "add", "drafting/toy.tex")
    (root / "drafting/toy.tex").unlink()
    state = update_documents(quilt, state, "remove", "drafting/toy.tex")
    assert state.documents == ["drafting/main.tex"]

    # a collaborator's push after preparation is rejected, and the prepared revision kept
    (root / "shared/common.tex").write_text("\\begin{lemma}\\label{zk-0001}Shared, third.\\end{lemma}\n")
    publication = publish(quilt, state)
    edit(colleague(tmp_path, bare), "collaborator update", {"notes.tex": "A note.\n"})
    with pytest.raises(SyncError, match="Publication rejected"):
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
    (root / "extra.tex").write_text("mine\n", encoding="utf-8")
    edit(other, "add a file", {"extra.tex": "theirs\n"})
    state = fetch(quilt, state)
    with pytest.raises(SyncError, match="extra.tex already exists locally"):
        pull_files(quilt, state)
    assert (root / "extra.tex").read_text() == "mine\n"


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
            "sections/one.tex": "\\begin{lemma}\\label{zk-0001}A\\end{lemma}\n",
        },
    )
    bare = overleaf(tmp_path)
    configure(load_quilt(root), str(bare), "main.tex")
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
    state = configure(quilt, str(bare))
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
    run(other, "mv", "drafting/main.tex", "drafting/paper.tex")
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
    assert state.published_main == "drafting/paper.tex"  # Overleaf keeps the collaborator's name at the next publish
    assert state.master == "drafting/main.tex"  # the record is followed, never rewritten
    assert json_of("status", "--json", cwd=root)["keys"]["zk-0001"]["acceptance"]["fresh"] is True
    assert not [x for x in json_of("lint", "--json", cwd=root)["diagnostics"] if x["code"] == "loom:document-gone"]
    assert "drafting/main.tex -> drafting/paper.tex (renamed in a pull)" in ok("history", cwd=root).stdout


def test_a_rename_with_an_edit_is_not_recorded_and_the_document_is_gone(tmp_path: Path, compiled: list[str]) -> None:
    root, other = renamed_pair(tmp_path)
    text = (other / "drafting/main.tex").read_text(encoding="utf-8")
    run(other, "rm", "-q", "drafting/main.tex")
    edit(other, "rename and edit", {"drafting/paper.tex": text.replace("zk-0001}A", "zk-0001}B")})
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
