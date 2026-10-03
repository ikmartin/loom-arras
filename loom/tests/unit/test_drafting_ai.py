"""The documents an agent edits (book 4.1, 5.3; plan 0.17.1): `[quilt] drafting_ai`, derived ids, and the border an agent's permission file draws."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from loom.scan.labels import derived_of, is_id_shaped, plain_key
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.helpers import json_of, ok, refused, run
from tests.unit._quilts import demo

AS = ["--as", "Markas Hecht"]

# A hand-made agent document drafted from two of the demo's inline nodes, each defined id derived and the reference between them rewritten, as `loom draft --ai` writes one.
AIDOC = r"""\documentclass{amsart}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{loom}
\theoremstyle{plain}
\newtheorem{proposition}{Proposition}
\theoremstyle{remark}
\newtheorem{remark}{Remark}
\begin{document}
\begin{remark}\label{dm-0004-ai}
Closedness is where the involution being an automorphism matters.
\end{remark}
\begin{proposition}[Functoriality]\label{dm-0005-ai}
A map of widgets restricts to their fixed loci; compare Remark~\ref{dm-0004-ai}.
\end{proposition}
\end{document}
"""


@pytest.fixture(autouse=True)
def local_reviewer() -> None:
    """Status reports the local reviewer's acceptance, so the reviewer is the author who accepts."""
    from loom.scan.quilt import save_author

    save_author("Markas Hecht")


def with_copy(tmp_path: Path, name: str = "aidoc.tex", text: str = AIDOC) -> Path:
    """The demo quilt with an agent's copy of `drafting/main.tex` in `drafting-ai/`, made by `loom draft` and then rewritten to `text`, as an agent edits one."""
    q = demo(tmp_path)
    ok("draft", "drafting/main.tex", "--ai", name, cwd=q)
    (q / "drafting-ai" / name).write_text(text, encoding="utf-8")
    return q


def codes(q: Path, code: int = 0) -> list[dict]:  # type: ignore[type-arg]
    """`loom lint --json`, which exits 1 when it finds an error."""
    diagnostics: list[dict] = json_of("lint", "--json", cwd=q, code=code)["diagnostics"]  # type: ignore[type-arg]
    return diagnostics


def test_a_derived_id_names_its_counterpart_and_never_takes_a_citekey_prefix() -> None:
    assert is_id_shaped("zk-0001-ai") and derived_of("zk-0001-ai") == "zk-0001"
    assert plain_key("zk-0001-ai/proof/2") == "zk-0001/proof/2" and plain_key("zk-0001/proof") == "zk-0001/proof"
    assert derived_of("zk-0001") is None and not is_id_shaped("zk-001-ai")
    # under a citekey slug the local is paper-local, so `0001-ai` is an ordinary paper id and never derived
    assert is_id_shaped("arden24-0001-ai", {"arden24"})
    assert derived_of("zk-01-ai") is None


def test_an_agents_document_is_live_and_its_nodes_are_derived(tmp_path: Path) -> None:
    q = with_copy(tmp_path)
    result = scan(load_quilt(q))
    assert "drafting-ai/aidoc.tex" in result.masters
    assert result.document_role("drafting-ai/aidoc.tex") == "drafting-ai"
    assert result.document_role("drafting/main.tex") == "drafting"
    assert result.default_master == "drafting/main.tex"
    assert result.nodes["dm-0004-ai"].derived_of == "dm-0004"
    assert result.nodes["dm-0004"].derived_of is None
    assert any(e.src == "dm-0005-ai" and e.to == "dm-0004-ai" for e in result.edges.edges)
    assert not [d for d in codes(q) if d["code"] in ("loom:derived-id-in-drafting", "duplicate-id")]


def test_status_and_the_manifest_count_the_persons_nodes_once(tmp_path: Path) -> None:
    q = with_copy(tmp_path)
    keys = json_of("status", "--json", cwd=q)["keys"]
    assert "dm-0004" in keys and "dm-0004-ai" not in keys
    ok("build", cwd=q)
    m = json.loads((q / "build" / "manifest.json").read_text())
    directory = {x["path"]: x["directory"] for x in m["masters"]}
    assert directory == {
        "drafting/main.tex": "drafting",
        "drafting/outline.tex": "drafting",
        "drafting-ai/aidoc.tex": "drafting-ai",
    }
    assert m["nodes"]["dm-0004-ai"]["derived_of"] == "dm-0004" and "derived_of" not in m["nodes"]["dm-0004"]
    assert not [s for s in m["search"] if s["key"].endswith("-ai")]


def test_two_definitions_of_a_derived_id_are_a_duplicate_id(tmp_path: Path) -> None:
    q = with_copy(tmp_path)
    (q / "drafting-ai" / "second.tex").write_text(AIDOC, encoding="utf-8")
    dup = [d for d in codes(q, 1) if d["code"] == "duplicate-id"]
    assert {k for d in dup for k in d.get("keys", [])} >= {"dm-0004-ai"} or any(
        "dm-0004-ai" in d["message"] for d in dup
    )


def test_a_persons_document_neither_defines_nor_cites_a_derived_id(tmp_path: Path) -> None:
    q = with_copy(tmp_path)
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("matters; a merely", "matters (Remark~\\ref{dm-0004-ai}); a merely"))
    outline = q / "drafting" / "outline.tex"
    outline.write_text(
        outline.read_text().replace(
            "\\end{document}", "\\begin{remark}\\label{dm-0099-ai}Mine.\\end{remark}\n\\end{document}"
        )
    )
    found = [d["message"] for d in codes(q, 1) if d["code"] == "loom:derived-id-in-drafting"]
    assert any("cites dm-0004-ai" in x for x in found), found
    assert any(x.startswith("dm-0099-ai is an agent document's id") for x in found), found


def test_two_live_documents_may_not_share_a_name(tmp_path: Path) -> None:
    # `loom draft` refuses the name itself, so the document is written by hand, as a person or a sync might
    q = demo(tmp_path)
    (q / "drafting-ai").mkdir(exist_ok=True)
    (q / "drafting-ai" / "main.tex").write_text(AIDOC, encoding="utf-8")
    taken = [d for d in codes(q, 1) if d["code"] == "loom:document-stem-taken"]
    assert len(taken) == 1 and {x["file"] for x in taken[0]["locations"]} == {
        "drafting/main.tex",
        "drafting-ai/main.tex",
    }


def test_nothing_in_an_agents_document_is_accepted(tmp_path: Path) -> None:
    q = with_copy(tmp_path)
    refused(
        "accept",
        "dm-0004-ai",
        "--force",
        *AS,
        cwd=q,
        code=2,
        match="never accepted; acceptance belongs to the node it becomes, dm-0004",
    )
    refused(
        "accept",
        "--master",
        "drafting-ai/aidoc.tex",
        "--yes",
        "--force",
        *AS,
        cwd=q,
        code=2,
        match="nothing in an agent's document is accepted",
    )
    ok("accept", "dm-0001", "dm-0002", "--force", *AS, cwd=q)
    from loom.records.ledger import read_ledger

    assert not [row for row in read_ledger(q) if row.key.endswith("-ai") or row.master.startswith("drafting-ai/")]


def test_the_allocator_skips_a_number_a_derived_id_holds(tmp_path: Path) -> None:
    q = with_copy(tmp_path, text=AIDOC.replace("dm-0005-ai", "dm-00Z0-ai"))
    assert ok("id", "--next", cwd=q).stdout.strip() == "dm-00Z1"
    # and `loom id` gives a derived node no second label
    assert "dm-00Z" not in ok("id", "drafting-ai/aidoc.tex", cwd=q).stdout.replace("dm-00Z0-ai", "")


def test_the_agent_may_write_in_its_directory_under_the_quilts_own_names(tmp_path: Path) -> None:
    q = demo(tmp_path)
    cfg = q / "config.toml"
    cfg.write_text(
        cfg.read_text().replace('drafting = "drafting"', 'drafting = "drafting"\ndrafting_ai = "with-agent"')
    )
    shutil.rmtree(q / "ai")
    shutil.rmtree(q / ".claude", ignore_errors=True)
    ok("ai", "init", cwd=q)
    perms = json.loads((q / ".claude" / "settings.json").read_text())["permissions"]
    assert "Edit(/with-agent/**)" in perms["allow"] and "Edit(/drafting-ai/**)" not in perms["allow"]
    assert "Edit(/drafting/**)" in perms["deny"]
    doctor = {i["name"]: i["status"] for i in json.loads(run("doctor", "--json", cwd=q).stdout)["items"]}
    assert doctor["permissions"] == "ok"


def test_init_makes_the_agents_directory_and_names_it(tmp_path: Path) -> None:
    ok("init", str(tmp_path / "q"), cwd=tmp_path)
    q = tmp_path / "q"
    assert (q / "drafting-ai").is_dir()
    assert 'drafting_ai = "drafting-ai"' in (q / "config.toml").read_text()
    assert "drafting-ai/*.aux" in (q / ".gitignore").read_text()


def test_the_document_workspace_never_selects_an_agents_document(tmp_path: Path) -> None:
    from loom.sync import SyncError, SyncState, update_documents

    q = with_copy(tmp_path)
    state = SyncState(url="overleaf.git", branch="master", master="drafting/main.tex", integrated="")
    with pytest.raises(SyncError, match="an agent's document, which is never published"):
        update_documents(load_quilt(q), state, "add", "drafting-ai/aidoc.tex")


# ---- the copy (phase 2) ---------------------------------------------------------------------------------------


def copy_of_main(tmp_path: Path) -> Path:
    """The demo quilt with `loom draft drafting/main.tex --ai aidoc.tex` run in it."""
    q = demo(tmp_path)
    ok("draft", "drafting/main.tex", "--ai", "aidoc.tex", cwd=q)
    return q


def test_the_copy_is_flat_and_every_label_it_defines_is_derived(tmp_path: Path) -> None:
    import re

    q = copy_of_main(tmp_path)
    text = (q / "drafting-ai" / "aidoc.tex").read_text()
    assert "\\input{" not in text, "every inclusion expanded"
    labels = re.findall(r"\\label\{([^}]*)\}", text)
    assert labels and all(lab.endswith("-ai") for lab in labels)
    assert "\\label{dm-0001-ai}" in text and "\\label{eq:fix-ai}" in text
    assert "\\ref{lem:orbits-ai}" in text and "\\eqref{eq:fix-ai}" in text
    assert "\\cite[Proposition 3.2]{Calloway14}" in text  # a citation is no label
    lint = codes(q)
    assert not [d for d in lint if d["severity"] == "error"], lint


def test_the_copy_step_records_a_readable_base_for_every_node(tmp_path: Path) -> None:
    from loom.history.ledger import load_history
    from loom.history.versions import read_version

    q = copy_of_main(tmp_path)
    result = scan(load_quilt(q))
    history = load_history(result.quilt.history_dir)
    line = history.entries[-1]
    assert (
        line.action == "copy" and line.get("from") == "drafting/main.tex" and line.get("to") == "drafting-ai/aidoc.tex"
    )
    bases = history.bases("drafting-ai/aidoc.tex", result.masters)
    assert bases == line.get("bases")
    assert {"dm-0001-ai", "dm-0002-ai", "dm-0003-ai", "dm-0005-ai"} <= set(bases)
    for derived, base in bases.items():
        assert base["key"] == plain_key(derived)
        read_version(history, base["key"], str(base["step"]))  # the base is a version loom can read back
    assert history.copy_of("drafting-ai/aidoc.tex", result.masters) == "drafting/main.tex"
    # the step keeps the source's flat text, which staleness compares the prose and preamble against
    assert (history.dir / (line.dir or "") / "main.tex").read_text().startswith("\\documentclass")
    assert re.search(r"^0002  copy  ", ok("history", cwd=q).stdout, re.M)
    ok("history", "verify", cwd=q)


def test_one_copy_per_document_never_over_a_file_or_a_taken_name(tmp_path: Path) -> None:
    q = copy_of_main(tmp_path)
    refused(
        "draft",
        "drafting/main.tex",
        "--ai",
        "again.tex",
        cwd=q,
        code=2,
        match="overlaps drafting-ai/aidoc.tex",
    )
    refused("draft", "drafting/outline.tex", "--ai", "aidoc.tex", cwd=q, code=2, match="exists; draft never overwrites")
    refused("draft", "drafting/outline.tex", "--ai", "main.tex", cwd=q, code=2, match="already named main")
    refused("draft", "drafting-ai/aidoc.tex", "--ai", "copy2.tex", cwd=q, code=2, match="is an agent document")
    refused("draft", "drafting/missing.tex", "--ai", "x.tex", cwd=q, code=2, match="is not a live document")


def test_a_copy_is_stale_when_the_persons_side_moves_mathematically(tmp_path: Path) -> None:
    q = copy_of_main(tmp_path)
    assert json_of("ai", "drafts", "--json", cwd=q)["copies"] == [
        {
            "copy": "drafting-ai/aidoc.tex",
            "source": "drafting/main.tex",
            "scope": {"kind": "document"},
            "suffix": "-ai",
            "context": None,
            "context_changed": False,
            "stale": False,
            "changed": [],
            "gone": [],
            "prose": False,
            "preamble": False,
        }
    ]
    assert "aidoc.tex  drafted from drafting/main.tex  fresh" in ok("ai", "drafts", cwd=q).stdout
    # a display name is no mathematical change
    node = q / "nodes" / "dm-0001.tex"
    node.write_text("% !LOOM name: The widget\n" + node.read_text())
    assert json_of("ai", "drafts", "--json", cwd=q)["copies"][0]["stale"] is False
    (q / "nodes" / "dm-0002.tex").write_text(
        (q / "nodes" / "dm-0002.tex").read_text().replace("one or two points", "at most two points")
    )
    main = q / "drafting" / "main.tex"
    main.write_text(
        main.read_text()
        .replace("the simplest object", "the plainest object")
        .replace("\\newcommand{\\Fix}", "\\newcommand{\\Mine}{m}\n\\newcommand{\\Fix}")
    )
    state = json_of("ai", "drafts", "--json", cwd=q)["copies"][0]
    assert state["stale"] and state["changed"] == ["dm-0002"] and state["prose"] and state["preamble"]
    said = " ".join(ok("ai", "drafts", cwd=q).stdout.split())  # the line wraps
    assert "stale: dm-0002 changed; the prose between nodes; the preamble" in said


def test_an_agent_may_make_a_copy_and_never_adopt_one(tmp_path: Path) -> None:
    """A copy writes only into the agent's drafting directory and records its bases; the person's documents are untouched, so an agent may make one. Taking it back is the author's."""
    from loom.ai.layout import AGENT_COMMANDS

    assert {"draft", "ai drafts", "ai refresh"} <= AGENT_COMMANDS and "adopt" not in AGENT_COMMANDS
    q = demo(tmp_path)
    before = {p: p.read_bytes() for p in (q / "drafting").rglob("*") if p.is_file()}
    ok("draft", "drafting/main.tex", "--ai", "aidoc.tex", cwd=q, env={"CLAUDECODE": "1"})
    assert (q / "drafting-ai" / "aidoc.tex").is_file()
    assert {p: p.read_bytes() for p in (q / "drafting").rglob("*") if p.is_file()} == before
    assert "aidoc.tex" in ok("ai", "drafts", cwd=q, env={"CLAUDECODE": "1"}).stdout


def test_the_agents_directory_holds_copies_that_define_derived_ids(tmp_path: Path) -> None:
    """A document written straight into the directory has no copy step, so nothing can be adopted or refreshed from it, and a plain id defined there writes into the person's id space; lint refuses both, and adoption says why (book 4.4)."""
    q = demo(tmp_path)
    (q / "drafting-ai").mkdir(exist_ok=True)
    (q / "drafting-ai" / "scratch.tex").write_text(
        AIDOC.replace("dm-0005-ai", "dm-0901").replace("dm-0004-ai", "dm-0900-ai"), encoding="utf-8"
    )
    found = {d["code"]: d for d in codes(q, code=1)}
    assert (
        found["loom:agent-document-not-a-copy"]["fixes"][0]["command"] == "loom draft drafting/main.tex --ai NAME.tex"
    )
    assert "dm-0901 is defined in drafting-ai/scratch.tex" in found["loom:plain-id-in-drafting-ai"]["message"]
    refused("adopt", "drafting-ai/scratch.tex", "--json", cwd=q, code=2, match="is not a copy")


# ---- the interface other plans build on (phase 3) -------------------------------------------------------------


def test_the_fixtures_agent_copy_carries_every_field_the_interface_names() -> None:
    fixture = json.loads((Path(__file__).parents[1] / "fixture" / "manifest.json").read_text())
    masters = {m["path"]: m for m in fixture["masters"]}
    assert masters["drafting-ai/aidoc.tex"]["directory"] == "drafting-ai"
    assert masters["drafting-ai/aidoc.tex"]["copy_of"] == "drafting/main.tex"
    assert [m["path"] for m in fixture["masters"]][-1] == "drafting-ai/aidoc.tex"  # the person's documents first
    nodes = fixture["nodes"]
    assert nodes["sy-0002-ai"]["derived_of"] == "sy-0002" and nodes["sy-0002-ai"]["base"]["key"] == "sy-0002"
    # one of each kind a copy differs from its source by
    assert "sy-999C-ai" in nodes and "base" not in nodes["sy-999C-ai"]  # written new by the agent
    assert "sy-0202" in nodes and "sy-0202-ai" not in nodes  # deleted from the copy
    assert "sy-000A-ai" in nodes  # moved, unchanged


def test_the_fixtures_copy_is_stale_where_the_author_changed_a_node_after_it() -> None:
    q = Path(__file__).parents[1] / "quilts" / "synthetic"
    state = json_of("ai", "drafts", "--json", cwd=q)["copies"][0]
    assert state["copy"] == "drafting-ai/aidoc.tex" and state["changed"] == ["sy-0001"] and not state["gone"]


def test_bases_follow_adopt_and_refresh_lines_and_a_move_of_the_copy(tmp_path: Path) -> None:
    from loom.history.ledger import append_entry, load_history

    q = copy_of_main(tmp_path)
    history_dir = load_quilt(q).history_dir
    moved = {"key": "dm-0002", "step": 1, "hash": "sha256:adopted"}
    append_entry(
        history_dir,
        "adopt",
        {"copy": "drafting-ai/aidoc.tex", "taken": ["dm-0002-ai"], "kept": [], "bases": {"dm-0002-ai": moved}},
        "Markas Hecht",
    )
    refreshed = {"key": "dm-0003", "step": 1, "hash": "sha256:refreshed"}
    append_entry(
        history_dir, "refresh", {"copy": "drafting-ai/aidoc.tex", "bases": {"dm-0003-ai": refreshed}}, "An Agent"
    )
    (q / "drafting-ai" / "aidoc.tex").rename(q / "drafting-ai" / "agentdoc.tex")
    append_entry(
        history_dir,
        "move",
        {"from": "drafting-ai/aidoc.tex", "to": "drafting-ai/agentdoc.tex", "moved": False},
        "Markas Hecht",
    )
    result = scan(load_quilt(q))
    history = load_history(history_dir)
    bases = history.bases("drafting-ai/agentdoc.tex", result.masters)
    assert bases["dm-0002-ai"] == moved and bases["dm-0003-ai"] == refreshed
    assert bases["dm-0001-ai"]["key"] == "dm-0001"
    assert (
        history.bases("drafting-ai/aidoc.tex", result.masters) == bases
    )  # the path a record wrote leads to the same copy
    assert history.copy_of("drafting-ai/agentdoc.tex", result.masters) == "drafting/main.tex"
