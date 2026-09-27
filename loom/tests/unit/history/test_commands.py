"""The workbench commands on the shim (book chapter 17): stamp and its landmarks, fork, revert, history with show, restore and verify, and what each records."""

from __future__ import annotations

import json
import re
from pathlib import Path

from loom.history.steps import text_hash
from tests.helpers import edit, exits, json_of, ok, refused, templated, the

PAPER = r"""\documentclass{article}
\usepackage{amsthm}
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}[theorem]{Lemma}
\begin{document}
\section{Setup}
\begin{lemma}\label{lem:a}
Alpha.
\end{lemma}
\begin{proof}
Obvious.
\end{proof}
\begin{theorem}[Main]\label{thm:main}
Beta uses Lemma~\ref{lem:a}.
\end{theorem}
\begin{proof}
Later.
\end{proof}
\end{document}
"""


def quilt(tmp_path: Path) -> Path:
    """PAPER imported, which drafts it at once, from a per-worker template."""

    def make(base: Path) -> None:
        paper = base / "paper"
        paper.mkdir()
        (paper / "main.tex").write_text(PAPER, encoding="utf-8")
        ok("init", str(base / "q"), "--from", str(paper / "main.tex"), "--prefix", "pp", "--yes", cwd=base)

    templated("history-drafted", tmp_path, make)
    return tmp_path / "q"


def ledger(q: Path) -> list[dict]:
    return [json.loads(x) for x in (q / ".loom" / "history" / "ledger.jsonl").read_text().splitlines()]


def test_stamp_given_a_document_keeps_its_text_as_a_landmark(tmp_path: Path) -> None:
    """Book 17.9: a stamp given a document freezes the keys it reaches and keeps its flat text, in loom's form, in the step as a landmark named by the message."""
    q = quilt(tmp_path)
    r = ok("stamp", "drafting/main.tex", "-m", "First landmark", cwd=q)
    assert "step 0002 froze 4 keys; landmark first-landmark, drafting/main.tex as it stands" in r.output

    step = ledger(q)[-1]
    assert step["action"] == "stamp" and step["step"] == 2 and step["dir"] == "0002-first-landmark"
    assert step["message"] == "First landmark" and step["in"] == "drafting/main.tex"
    assert step["landmark"] == "first-landmark.tex" and step["to"]["path"] == "first-landmark.tex"
    # sections are never versioned: a section has no text of its own that a version could hold (17.5)
    assert set(step["froze"]) == {"pp-0002", "pp-0002/proof", "pp-0003", "pp-0003/proof"}
    assert step["of"]["pp-0002/proof"] == "pp-0002@2"  # a proof version records the statement version it stood against
    assert sorted(step["reaches"]) == sorted(step["froze"])

    d = q / ".loom" / "history" / "0002-first-landmark"
    text = (d / "first-landmark.tex").read_text()
    assert step["to"]["hash"] == text_hash(text)
    assert (
        "\\usepackage{loom}" in text and "% !LOOM begin loom-macros" not in text
    )  # loom's form, so it can be restored
    assert "\\label{pp-0002}" in text  # the ids stay: versions are per key
    assert text == (q / "drafting" / "main.tex").read_text()  # a flat document is its own flat text
    assert (d / "preamble.tex").is_file() and (d / "pp-0002.tex").is_file() and (d / "pp-0002.proof.tex").is_file()
    assert "\\begin{lemma}" in (d / "pp-0002.tex").read_text()

    r = ok("stamp", "drafting/main.tex", "-m", "Unchanged", cwd=q)  # a landmark needs no key to have moved
    assert "step 0003 froze 0 keys; landmark unchanged" in r.output
    assert (q / ".loom" / "history" / "0003-unchanged" / "unchanged.tex").read_text() == text
    refused(
        "stamp",
        "drafting/main.tex",
        "-m",
        "first landmark",
        cwd=q,
        code=2,
        match="a landmark is already named first-landmark",
    )
    assert len(ledger(q)) == 3  # the refusal wrote nothing
    ok("history", "verify", cwd=q)


def test_a_landmark_stamp_requires_a_message_and_refuses_a_conflicted_key(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    refused("stamp", "drafting/main.tex", cwd=q, code=2, match="Missing option '--message'")
    node = q / "nodes" / "pp-0002.tex"
    node.parent.mkdir(exist_ok=True)
    node.write_text("\\begin{lemma}\\label{pp-0002}\nA second definition.\n\\end{lemma}\n", encoding="utf-8")
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("\\end{document}", "\\input{nodes/pp-0002}\n\\end{document}"))
    r = refused("stamp", "drafting/main.tex", "-m", "x", cwd=q, code=1, match="defined by two files")
    assert "pp-0002" in r.output
    assert len(ledger(q)) == 1 and not (q / ".loom" / "history" / "0002-x").exists()


def test_stamp_records_only_what_moved(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("stamp", "-m", "one", cwd=q)
    assert "landmark" not in ledger(q)[-1]  # a stamp given no document keeps no text
    refused("stamp", "-m", "nothing changed", cwd=q, code=1, match="nothing to stamp")
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("Alpha.", "Alpha, revised."))
    ok("stamp", "-m", "Referee points", cwd=q)
    step = ledger(q)[-1]
    assert step["action"] == "stamp" and step["dir"] == "0003-stamp-referee-points"
    assert list(step["froze"]) == ["pp-0002"] and step["preamble"] is None
    d = q / ".loom" / "history" / "0003-stamp-referee-points"
    assert [p.name for p in sorted(d.iterdir())] == ["pp-0002.tex"]
    assert "Alpha, revised." in (d / "pp-0002.tex").read_text()


def test_history_lists_steps_and_a_key_s_versions(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("stamp", "drafting/main.tex", "-m", "one", cwd=q)
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("Alpha.", "Alpha, revised."))
    ok("stamp", "-m", "two", cwd=q)
    r = ok("history", cwd=q)
    assert "0001  import" in r.output and "0002  stamp" in r.output and '"one"' in r.output
    assert "0003  stamp" in r.output and '"two"' in r.output
    k = ok("history", "pp-0002", cwd=q)
    assert "pp-0002@2" in k.output and "pp-0002@3" in k.output and "head: the text of @3" in k.output
    j = json_of("history", "pp-0002", "--json", cwd=q)
    assert j["head_is"] == 3 and len(j["versions"]) == 2


def test_revert_prints_a_patch_and_records_it(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("stamp", "-m", "one", cwd=q)
    main = q / "drafting" / "main.tex"
    before = main.read_text()
    main.write_text(before.replace("Alpha.", "Alpha, revised."))
    r = ok("revert", "pp-0002@2", cwd=q)
    assert "-Alpha, revised." in r.output and "+Alpha." in r.output
    assert main.read_text() != before  # loom prints the patch; applying it is the author's act
    assert ledger(q)[-1]["action"] == "revert" and ledger(q)[-1]["step"] == 2
    assert "the text of @2" in r.output
    refused("revert", "pp-0002@9", cwd=q, code=1, match="no step 9")


def test_fork_gives_a_document_its_own_copy(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q)
    (q / "drafting" / "talk.tex").write_text(
        "\\documentclass{article}\n\\usepackage{amsthm}\n\\usepackage{loom}\n"
        "\\newtheorem{theorem}{Theorem}\n\\newtheorem{lemma}[theorem]{Lemma}\n"
        "\\begin{document}\n\\input{nodes/pp-0002}\nSee Lemma~\\ref{pp-0002}.\n\\end{document}\n",
        encoding="utf-8",
    )
    r = ok("fork", "pp-0002", "--in", "drafting/talk.tex", cwd=q)
    stems = [p.stem for p in (q / "nodes").glob("pp-*.tex")]
    new_id = the(stems, lambda s: s not in ("pp-0001", "pp-0002", "pp-0003"), "forked node")
    assert f"Wrote nodes/{new_id}.tex" in r.output
    assert f"\\label{{{new_id}}}" in (q / "nodes" / f"{new_id}.tex").read_text()
    assert f"+\\input{{nodes/{new_id}}}" in r.output and f"+See Lemma~\\ref{{{new_id}}}." in r.output
    assert "\\input{nodes/pp-0002}" in (q / "drafting" / "talk.tex").read_text()  # the patch is the author's to apply
    line = ledger(q)[-1]
    assert line["action"] == "fork" and line["new"] == new_id and line["from"]["id"] == "pp-0002"
    assert line["in"] == "drafting/talk.tex"


def test_fork_from_a_recorded_version(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("stamp", "-m", "one", cwd=q)
    main = q / "drafting" / "main.tex"
    main.write_text(main.read_text().replace("Alpha.", "Alpha, revised."))
    r = ok("fork", "pp-0002", "--in", "drafting/main.tex", "--from", "@2", "--as", "pp-0100", cwd=q)
    assert "+Alpha." in r.output and "pp-0100" in r.output  # the older text, under the new id
    assert ledger(q)[-1]["from"]["step"] == 2
    refused("fork", "pp-0002", "--in", "drafting/main.tex", "--as", "pp-0001", cwd=q, code=1, match="taken")


def test_a_retired_id_is_never_allocated_again_and_written_again_is_reuse_or_recovery(tmp_path: Path) -> None:
    """An id the history recorded names one node forever: the allocator skips it, the same text back under it is a recovery, and different text under it is reuse."""
    q = quilt(tmp_path)
    ok("stamp", "-m", "one", cwd=q)
    main = q / "drafting" / "main.tex"
    text = main.read_text()
    start = text.index("\\begin{theorem}")
    end = text.index("\\end{proof}", text.index("Later.")) + len("\\end{proof}\n")
    main.write_text(text[:start] + text[end:])
    ok("stamp", "-m", "dropped the theorem", cwd=q)
    assert ledger(q)[-1]["removed"] == ["pp-0003", "pp-0003/proof"]
    nxt = ok("id", "--next", cwd=q).output.strip()
    assert nxt == "pp-0004", nxt  # pp-0003 is retired: the allocator consults the history

    main.write_text(text)  # the same text back under the same id
    lint = ok("lint", cwd=q)
    assert "loom:node-recovered" in lint.output and "loom:id-reused" not in lint.output

    main.write_text(text.replace("Beta uses", "Gamma uses"))
    lint2 = exits(1, "lint", cwd=q)
    assert "loom:id-reused" in lint2.output and "an id names one node forever" in lint2.output


def test_history_verify_reports_an_edited_record(tmp_path: Path) -> None:
    q = quilt(tmp_path)
    ok("stamp", "-m", "one", cwd=q)
    v = q / ".loom" / "history" / "0002-stamp-one" / "pp-0002.tex"
    v.write_text(v.read_text() + "% edited by hand\n")
    r = exits(1, "history", "verify", cwd=q)
    assert "loom:history-edited" in r.output and "pp-0002" in r.output
    v.unlink()
    r2 = exits(1, "history", "verify", cwd=q)
    assert "loom:history-missing" in r2.output


def plant(q: Path, *lines: dict[str, object] | str) -> None:
    """Append raw lines to the ledger, as a hand edit or a bad merge would."""
    with (q / ".loom" / "history" / "ledger.jsonl").open("a", encoding="utf-8") as fh:
        for line in lines:
            fh.write((line if isinstance(line, str) else json.dumps({"when": "x", "actor": None, **line})) + "\n")


def test_a_ledger_that_cannot_be_read_in_full_is_history_corrupt(tmp_path: Path) -> None:
    """Book 17.15: a malformed line or a step out of order is reported by lint and `history verify` as an error, and the rest of the ledger still loads."""
    q = quilt(tmp_path)
    ok("stamp", "-m", "one", cwd=q)
    plant(q, "{not json", {"action": "stamp", "step": 1, "dir": "0001-again", "froze": {}})
    for cmd in (("lint",), ("history", "verify")):
        r = exits(1, *cmd, cwd=q, match="loom:history-corrupt")
        assert "the history ledger cannot be read in full: line 3 is not JSON" in r.output, r.output
        assert "line 4: step 1 does not follow step 2" in r.output, r.output
    js = json_of("history", "verify", "--json", cwd=q, code=1)
    assert [d["code"] for d in js] == ["loom:history-corrupt", "loom:history-corrupt"]
    assert all(d["severity"] == "error" and d["subject"] == "record" for d in js)
    assert "0002  stamp" in ok("history", cwd=q).output  # what could be read still is


def test_verify_names_each_part_of_a_step_that_is_missing_or_edited(tmp_path: Path) -> None:
    """The preamble and a landmark's text are checked like the version files; a step whose directory is gone is one error, not one per file."""
    q = quilt(tmp_path)
    ok("stamp", "drafting/main.tex", "-m", "v1", cwd=q)
    d = q / ".loom" / "history" / "0002-v1"
    pre, copy = d / "preamble.tex", d / "v1.tex"
    pre.write_text(pre.read_text() + "\\usepackage{xy}\n")
    copy.write_text(copy.read_text() + "% edited\n")
    r = exits(1, "history", "verify", cwd=q)
    assert "the preamble of step 0002 does not hash to what the ledger recorded" in r.output, r.output
    assert "the copy of v1.tex of step 0002 does not hash to what the ledger recorded" in r.output, r.output
    pre.unlink()
    copy.unlink()
    r = exits(1, "history", "verify", cwd=q)
    assert "loom:history-missing" in r.output and "the preamble of step 0002 is missing from .loom/history" in r.output
    assert "the copy of v1.tex of step 0002 is missing" in r.output, r.output
    for p in d.iterdir():
        p.unlink()
    d.rmdir()
    js = json_of("history", "verify", "--json", cwd=q, code=1)
    missing = the(js, lambda x: x["code"] == "loom:history-missing", "loom:history-missing diagnostic")
    assert missing["message"] == "the directory 0002-v1 of step 0002 is missing from .loom/history"


def test_ancestry_the_history_no_longer_resolves_is_dangling(tmp_path: Path) -> None:
    """A fork or a revert naming a step the ledger does not have (or a key that step did not hold) is a warning: verify reports it and still exits 0."""
    q = quilt(tmp_path)
    ok("stamp", "-m", "one", cwd=q)
    assert "loom:dangling-ancestry" not in ok("history", "verify", cwd=q).output
    plant(
        q,
        {"action": "fork", "new": "pp-0100", "from": {"id": "pp-0002", "step": 7}, "in": "drafting/main.tex"},
        {"action": "fork", "new": "pp-0101", "from": {"id": "pp-0999", "step": 2}, "in": "drafting/main.tex"},
        {"action": "revert", "key": "pp-0002", "step": 7, "in": "drafting/main.tex"},
    )
    r = ok("history", "verify", cwd=q)
    assert r.output.count("loom:dangling-ancestry") == 3, r.output
    assert "pp-0100 was forked from pp-0002@7, which the history no longer resolves" in r.output
    assert "pp-0101 was forked from pp-0999@2, which the history no longer resolves" in r.output
    assert "pp-0002 was reverted to @7, which the history no longer resolves" in r.output
    js = json_of("lint", "--json", cwd=q)
    assert sum(d["code"] == "loom:dangling-ancestry" for d in js) == 3


def test_stamp_given_a_document_records_only_the_keys_it_reaches(tmp_path: Path) -> None:
    """Book 17.9: a document narrows a stamp to what it reaches, and its landmark is its flat text; a document that is not live in the drafting directory is refused."""
    q = quilt(tmp_path)
    ok("stamp", "-m", "one", cwd=q)
    ok("atomize", "drafting/main.tex", "drafting/spine.tex", cwd=q)
    (q / "drafting" / "talk.tex").write_text(
        "\\documentclass{article}\n\\usepackage{amsthm}\n\\usepackage{loom}\n"
        "\\newtheorem{theorem}{Theorem}\n\\newtheorem{lemma}[theorem]{Lemma}\n"
        "\\begin{document}\n\\input{nodes/pp-0002}\n\\end{document}\n",
        encoding="utf-8",
    )
    edit(q / "nodes" / "pp-0002.tex", "Alpha.", "Alpha, revised.")
    edit(q / "nodes" / "pp-0003.tex", "Beta uses", "Gamma uses")
    r = ok("stamp", "drafting/talk.tex", "-m", "talk", cwd=q)
    assert "step 0003 froze 1 keys; landmark talk, drafting/talk.tex as it stands" in r.output
    step = ledger(q)[-1]
    assert list(step["froze"]) == ["pp-0002"] and step["in"] == "drafting/talk.tex"
    assert "pp-0003" not in step["reaches"] and "pp-0002" in step["reaches"]
    landmark = (q / ".loom" / "history" / "0003-talk" / "talk.tex").read_text()
    assert "Alpha, revised." in landmark and "\\input{nodes/" not in landmark  # flat: the node inlined
    refused("stamp", "drafting/main.tex", "-m", "x", cwd=q, code=2, match="drafting/main.tex is not a live document")
    refused("stamp", "nodes/pp-0002.tex", "-m", "x", cwd=q, code=2, match="nodes/pp-0002.tex is not a live document")
    assert list(ledger(q)[-1]["froze"]) == ["pp-0002"]  # the refusals wrote nothing
    ok("stamp", "-m", "the rest", cwd=q)
    assert list(ledger(q)[-1]["froze"]) == ["pp-0003"]


def test_stamp_with_no_ids_has_nothing_to_stamp(tmp_path: Path) -> None:
    paper = tmp_path / "p.tex"
    paper.write_text("\\documentclass{article}\n\\begin{document}\nProse only.\n\\end{document}\n")
    q = tmp_path / "q"
    ok("init", str(q), "--from", str(paper), "--prefix", "pp", "--yes", cwd=tmp_path)
    refused("stamp", "-m", "x", cwd=q, code=1, match="nothing to stamp: no key has moved since step 0001")


def test_revert_expands_child_markers_from_the_head_and_refuses_when_a_child_is_gone(tmp_path: Path) -> None:
    """Book 17.5: a version records a nested result as `% !LOOM child: KEY`; reverting puts the head's text of that child back, and is refused when the child no longer exists."""
    paper = tmp_path / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(
        PAPER.replace(
            "Later.", "We first need\n\\begin{lemma}\\label{lem:b}\nGamma.\n\\end{lemma}\nand then we are done."
        ),
        encoding="utf-8",
    )
    q = tmp_path / "q"
    ok("init", str(q), "--from", str(paper / "main.tex"), "--prefix", "pp", "--yes", cwd=tmp_path)
    ok("stamp", "-m", "one", cwd=q)
    proof = (q / ".loom" / "history" / "0002-stamp-one" / "pp-0003.proof.tex").read_text()
    child = re.search(r"% !LOOM child: (pp-\d+)", proof)
    assert child is not None, proof
    main = q / "drafting" / "main.tex"
    edit(main, "and then we are done.", "and so we finish.")
    edit(main, "Gamma.", "Gamma, revised.")
    r = ok("revert", "pp-0003/proof@2", cwd=q)
    assert "-and so we finish." in r.output and "+and then we are done." in r.output
    assert "Gamma, revised." in json_of("revert", "pp-0003/proof@2", "--json", cwd=q)["patched"]
    assert (
        "!LOOM child" not in r.output and "-Gamma, revised." not in r.output
    )  # the child is the head's, not the step's

    text = main.read_text()
    start = text.index("\\begin{lemma}", text.index("We first need"))
    main.write_text(text[:start] + text[text.index("\\end{lemma}", start) + len("\\end{lemma}\n") :])
    refused(
        "revert",
        "pp-0003/proof@2",
        cwd=q,
        code=1,
        match=f"the version stands for {child.group(1)}, which the quilt no longer has",
    )


def test_history_show_prints_a_landmark_by_name_step_or_document_and_plain_drops_loom(tmp_path: Path) -> None:
    """Book 17.9: a landmark is named by its name, its step, or DOC@STEP; `--plain` is the paper without loom, which compiles without loom.sty forever."""
    q = quilt(tmp_path)
    assert ok("history", "show", "main@1", cwd=q).stdout == PAPER  # the import's landmark: the paper as received
    main = q / "drafting" / "main.tex"
    drafted = main.read_text()
    ok("stamp", "drafting/main.tex", "-m", "v1", cwd=q)
    edit(main, "Alpha.", "Alpha, revised.")
    ok("stamp", "-m", "two", cwd=q)
    for ref in ("v1", "2", "0002", "main@2", "v1@2"):
        assert ok("history", "show", ref, cwd=q).stdout == drafted, ref
    plain = ok("history", "show", "v1", "--plain", cwd=q).stdout
    assert "\\usepackage{loom}" not in plain and "% !LOOM begin loom-macros" in plain
    assert "\\providecommand{\\uses}" in plain and "\\label{pp-0002}" in plain
    js = json_of("history", "show", "main@2", "--json", cwd=q)
    assert js == {"landmark": "v1", "step": 2, "in": "drafting/main.tex", "text": drafted}
    for ref in ("nope", "3", "talk@2", "main@9"):  # step 3 is a stamp given no document: no landmark
        refused(
            "history",
            "show",
            ref,
            cwd=q,
            code=2,
            match=f"no landmark answers to {ref}; the landmarks are main (@1), v1 (@2)",
        )


def test_history_restore_drafts_a_landmark_as_a_new_document_and_records_it(tmp_path: Path) -> None:
    """A restored document is loom's own file: the package line and an id on every node without one, never over an existing path, only directly in the drafting directory, and only by the author."""
    q = quilt(tmp_path)
    r = ok("history", "restore", "main@1", "--to", "drafting/old.tex", cwd=q)
    assert "Wrote drafting/old.tex from landmark main (@1), 3 ids inserted" in r.output
    old = (q / "drafting" / "old.tex").read_text()
    assert old.splitlines()[1] == "\\usepackage{loom}"
    assert (
        "\\begin{lemma}\\label{pp-0005}\\label{lem:a}" in old
    )  # fresh ids, in document order, the author's labels kept
    assert "\\label{pp-0002}" not in old  # the paper as received had no ids, and the quilt's are taken
    line = ledger(q)[-1]
    assert line["action"] == "restore" and line["from"] == {"landmark": "main", "step": 1}
    assert line["to"] == {"path": "drafting/old.tex", "hash": text_hash(old)} and line["ids"] == 3
    assert re.search(r"^\s+restore\s+\S+\s+main \(@1\) -> drafting/old\.tex$", ok("history", cwd=q).output, re.M)

    main = q / "drafting" / "main.tex"
    ok("stamp", "drafting/main.tex", "-m", "v1", cwd=q)
    kept = main.read_text()
    main.unlink()  # the document is gone; its landmark brings it back
    r = ok("history", "restore", "v1", "--to", "drafting/main.tex", cwd=q)
    assert "0 ids inserted" in r.output  # loom's form: the ids stay, so versions still follow each key
    assert main.read_text() == kept

    n = len(ledger(q))
    refused(
        "history", "restore", "v1", "--to", "drafting/main.tex", cwd=q, code=2, match="exists; restore never overwrites"
    )
    refused("history", "restore", "v1", "--to", "nodes/v1.tex", cwd=q, code=2, match="goes directly under drafting/")
    refused("history", "restore", "v1", cwd=q, code=2, match="needs --to FILE")
    refused("history", "restore", "nope", "--to", "drafting/x.tex", cwd=q, code=2, match="no landmark answers to nope")
    refused(
        "history",
        "restore",
        "v1",
        "--to",
        "drafting/x.tex",
        cwd=q,
        env={"AI_AGENT": "1"},
        code=2,
        match="loom history restore is the author's",
    )
    assert len(ledger(q)) == n and not (q / "drafting" / "x.tex").exists()  # the refusals wrote nothing


def test_restoring_a_landmark_whose_ids_are_still_live_adds_no_second_id(tmp_path: Path) -> None:
    """A node whose id another live document also defines is a demoted definition, not a node without an id: the restored copy keeps its label and gains none, and says the ids are shared."""
    q = quilt(tmp_path)
    ok("stamp", "drafting/main.tex", "-m", "v1", cwd=q)
    r = ok("history", "restore", "v1", "--to", "drafting/again.tex", cwd=q)
    text = (q / "drafting" / "again.tex").read_text()
    assert re.search(r"\\label\{pp-[0-9A-Z]{4}\}\s*\\label\{pp-", text) is None, text
    assert "0 ids inserted" in r.stdout
    assert "defines ids another live document also defines" in r.output
