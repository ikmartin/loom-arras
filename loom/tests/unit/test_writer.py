"""Who a write is recorded as, a person or an agent (DR-185, plan 0.13 §8): identity is declared, and under an agent marker a declared name must say it is an agent's."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from loom.cli._common import AGENT_MARKERS, is_agent, writer
from tests.helpers import ok, refused
from tests.unit._quilts import demo, showcase


def test_an_agent_that_has_not_said_who_it_is_is_refused_rather_than_guessed_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Identity is declared, not sniffed: a marker distinguishes well today and an author may ask an agent to run a command."""
    q = demo(tmp_path)
    assert writer(q, "Referee Agent") == ("Referee Agent", "agent")
    assert writer(q, "A. Author") == ("A. Author", "person")
    monkeypatch.setenv("AI_AGENT", "1")
    with pytest.raises(Exception, match="has not said who it is"):
        writer(q, None)
    assert writer(q, "Referee Agent") == ("Referee Agent", "agent")


def test_a_write_that_names_nobody_under_a_marker_is_refused_by_every_command(tmp_path: Path) -> None:
    """`loom annotate` and `loom note` recorded such a write as `agent` while `loom new` and `loom session say` refused it; now all of them ask, and the refusal names what the app goes by."""
    q = demo(tmp_path)
    log = q / ".loom/annotations" / "log.jsonl"
    before = log.read_text()
    for act in (
        ["annotate", "dm-0002", "A finding.", "--type", "note"],
        ["annotate", "dm-0002", "A finding.", "--type", "note", "--dry-run"],
        ["note", "Worth keeping.", "--on", "dm-0002"],
        ["session", "say", "Said."],
        ["new", "lemma"],
        ["since"],
        ["write", "state", "A state."],
    ):
        refused(*act, cwd=q, env={"CLAUDECODE": "1"}, code=2, match='--as "Claude Code Agent"')
    assert log.read_text() == before
    made = ok(
        "annotate",
        "dm-0002",
        "A finding.",
        "--type",
        "note",
        "--as",
        "Claude Code Agent",
        cwd=q,
        env={"CLAUDECODE": "1"},
    )
    assert made.stdout.split()[0] in log.read_text()


def test_under_a_marker_a_name_that_does_not_say_it_is_an_agent_is_refused(tmp_path: Path) -> None:
    """Two of five agents signed `Claude` and `Claude Haiku 5.5`, and those notes were recorded as a person's, so `loom since` handed them back as what the person did. A name cannot be checked (DR-325-ikmartin), so under a marker it must say what the marker says: every command that records a declared name refuses, says how to sign, and writes nothing. With no marker the same name is taken at its word."""
    q = demo(tmp_path)
    log = q / ".loom/annotations" / "log.jsonl"
    before = log.read_text()
    marked = {"CLAUDECODE": "1"}
    for name in ("Claude", "Claude Haiku 5.5", "A. Author"):
        for act in (
            ["annotate", "dm-0002", "A finding.", "--type", "note"],
            ["note", "Worth keeping.", "--on", "dm-0002"],
            ["session", "say", "Said."],
            ["session", "new", "--name", "A sitting"],
            ["since"],
            ["write", "state", "A state."],
            ["new", "lemma", "--print"],
            ["draft", "drafting/main.tex", "--ai", "copy.tex"],
            [
                "library",
                "relate",
                "Calloway14-prop-3.2",
                "Calloway14-prop-3.3",
                "--kind",
                "same-notion",
                "--why",
                "A reason.",
            ],
        ):
            refused(*act, "--as", name, cwd=q, env=marked, code=2, match=f"{name} does not say it is an agent")
    refused(
        "note",
        "Worth keeping.",
        "--on",
        "dm-0002",
        "--as",
        "Claude",
        cwd=q,
        env=marked,
        code=2,
        match='--as "Claude Code Agent"',
    )
    assert log.read_text() == before
    # the same name in a shell with no marker is a person's, and a name that says so is an agent's in either
    unmarked = {m: None for m in AGENT_MARKERS}
    assert ok("annotate", "dm-0002", "Mine.", "--type", "note", "--as", "A. Author", cwd=q, env=unmarked)
    assert ok("annotate", "dm-0002", "Theirs.", "--type", "note", "--as", "Claude Agent", cwd=q, env=marked)
    kinds = {e["body"]: (e["author"], e["kind"]) for e in map(json.loads, log.read_text().splitlines()) if "body" in e}
    assert kinds["Mine."] == ("A. Author", "human") and kinds["Theirs."] == ("Claude Agent", "agent")


def test_a_marker_names_the_agent_as_its_apps_server_does(monkeypatch: pytest.MonkeyPatch) -> None:
    """Over MCP the server signs as `<App> Agent`, so a shell agent told the same name writes the same records. Apps set the generic `AI_AGENT` beside their own marker, which says more; every name says it is an agent, or a session it opened would read as a person's."""
    from loom.ai.clients import CLIENTS
    from loom.cli._common import AGENT_NAMES, agent_name

    apps = {c.agent for c in CLIENTS}
    for marker, name in AGENT_NAMES.items():
        assert is_agent(name) and (name in apps or marker == "AI_AGENT"), name
    assert set(AGENT_NAMES) == set(AGENT_MARKERS)
    assert agent_name() is None
    monkeypatch.setenv("AI_AGENT", "claude-code_2-1-317_agent")
    assert agent_name() == "agent"
    monkeypatch.setenv("CLAUDECODE", "1")
    assert agent_name() == "Claude Code Agent"


def test_a_declared_agent_is_an_agent_however_its_name_is_punctuated() -> None:
    """`Referee (Agent)` is the form the orientation asks for and the showcase writes, so `(agent)` and `agent` are one word here: a name read otherwise shows a parked agent in the session picker as a person, and lets it run the author's own verbs."""
    for name in ("Referee (Agent)", "Claude (AI)", "Referee [Agent]", "Referee Agent", "referee-agent", "AI", "bot"):
        assert is_agent(name), name
    for name in ("A. Author", "Wren Halloway", "Aiden Pearce", "Aimee"):
        assert not is_agent(name), name


def test_the_authors_verbs_refuse_a_declared_agent_whatever_shell_it_is_in(tmp_path: Path) -> None:
    """The declared name alone must refuse, so every agent marker is unset here to prove it is the name doing the work."""
    q = showcase(tmp_path)
    unmarked = {m: None for m in AGENT_MARKERS}
    for verb in (
        ["library", "ignore", "Bellamy19", "--why", "no"],
        ["library", "verify", "Bellamy19-prop-3.1"],
    ):
        refused(*verb, "--as", "Referee (Agent)", "--quilt", str(q), code=2, match="is an agent", env=unmarked)
    # and under an agent marker the author's name does not pass either: a name cannot be checked, and an agent typing the author's is the case to stop (DR-325-ikmartin)
    refused(
        "library", "ignore", "Bellamy19", "--why", "a study", "--as", "A. Author", "--quilt", str(q),
        code=2, match="whatever --as says", env={"AI_AGENT": "1"},
    )  # fmt: skip
    # without the marker the author, named, is the author
    ok("library", "ignore", "Bellamy19", "--why", "a study", "--as", "A. Author", "--quilt", str(q), env=unmarked)


def test_every_act_that_is_the_authors_or_destroys_refuses_under_an_agent_marker(tmp_path: Path) -> None:
    """The guard follows the act, not the command (K5): each of these refuses with the author's name declared, and leaves the quilt as it was."""
    q = showcase(tmp_path)
    marked = {"AI_AGENT": "1"}
    acts = [
        ["accept", "sh-0001", "--as", "A. Author"],
        ["library", "verify", "Bellamy19-prop-3.1", "--as", "A. Author"],
        ["library", "discard", "Bellamy19-prop-3.1", "--why", "no", "--as", "A. Author"],
        ["library", "ignore", "Bellamy19", "--why", "no", "--as", "A. Author"],
        ["library", "drop", "--work", "Bellamy19", "--yes"],
        ["library", "verify", "a-0000-00-00-m2qyj6", "--as", "A. Author"],
        ["library", "import", str(q / ".loom/digests" / "Bellamy19.tex"), "--name", "Other20"],
        ["ai", "discard", "--before", "2100-01-01"],
        ["session", "delete", "s-2026-09-16-p9z37z", "--purge", "--yes", "--as", "A. Author"],
        ["sync", "publish", "--push"],
        ["sync", "incorporate"],
    ]
    for act in acts:
        refused(*act, "--quilt", str(q), code=2, match="an agent is running this shell", env=marked)


def test_an_agent_may_remove_only_a_link_a_session_asserted(tmp_path: Path) -> None:
    """Removing the author's link is the author's; an agent's own link is its own to withdraw, and either removal is recorded with who made it."""
    import json

    from loom.refs.links import add_link, read_links

    q = showcase(tmp_path)
    theirs = add_link(q, "Bellamy19-thm-2.3", "Bellamy19-thm-3.2", "depends-on", "the author's reading", "A. Author")
    mine = add_link(
        q, "Bellamy19-thm-3.2", "Bellamy19-thm-2.3", "same-notion", "an agent's reading", "s-2026-09-16-p9z37z"
    )
    marked = {"AI_AGENT": "1"}
    undo = ("library", "relate", "--quilt", str(q), "--why", "a misreading", "--undo")
    refused(*undo, theirs.id, code=2, match="asserted by A. Author", env=marked)
    # a declared agent name is refused the same way, with no marker in the shell
    refused(*undo, theirs.id, "--as", "Referee (Agent)", code=2, match="asserted by A. Author")
    ok(*undo, mine.id, env=marked)
    assert [x.id for x in read_links(q)].count(theirs.id) == 1
    removed = [json.loads(ln) for ln in (q / ".loom/digests" / "links-removed.jsonl").read_text().splitlines()]
    assert removed[-1]["link"]["id"] == mine.id and removed[-1]["removed_by"] and removed[-1]["why"] == "a misreading"
