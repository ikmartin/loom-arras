"""Who a write is recorded as, a person or an agent (DR-185, plan 0.13 §8): identity is declared, and the guard on the author's verbs is on the identity, not on the shell it came from."""

from __future__ import annotations

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
    # and an explicit identity wins over the marker
    assert writer(q, "A. Author")[1] == "person"


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
        ["refs", "unreadable", "Bellamy19", "--why", "no"],
        ["refs", "verify", "Bellamy19-prop-3.1"],
    ):
        refused(*verb, "--author", "Referee (Agent)", "--quilt", str(q), code=2, match="is an agent", env=unmarked)
    # and under an agent marker the author's name does not pass either: a name cannot be checked, and an agent typing the author's is the case to stop (DR-325-ikmartin)
    refused(
        "refs", "unreadable", "Bellamy19", "--why", "a study", "--author", "A. Author", "--quilt", str(q),
        code=2, match="whatever --author or --as says", env={"AI_AGENT": "1"},
    )  # fmt: skip
    # without the marker the author, named, is the author
    ok("refs", "unreadable", "Bellamy19", "--why", "a study", "--author", "A. Author", "--quilt", str(q), env=unmarked)


def test_every_act_that_is_the_authors_or_destroys_refuses_under_an_agent_marker(tmp_path: Path) -> None:
    """The guard follows the act, not the command (K5): each of these refuses with the author's name declared, and leaves the quilt as it was."""
    q = showcase(tmp_path)
    marked = {"AI_AGENT": "1"}
    acts = [
        ["accept", "sh-0001", "--as", "A. Author"],
        ["refs", "verify", "Bellamy19-prop-3.1", "--author", "A. Author"],
        ["refs", "discard", "Bellamy19-prop-3.1", "--reason", "no", "--author", "A. Author"],
        ["refs", "drop", "--work", "Bellamy19", "--yes"],
        ["refs", "cite", "--accept", "a-0000-00-00-0000", "--author", "A. Author"],
        ["ai", "discard", "--before", "2100-01-01"],
        ["session", "delete", "s-2026-09-16-0001", "--purge", "--yes", "--as", "A. Author"],
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
        q, "Bellamy19-thm-3.2", "Bellamy19-thm-2.3", "same-notion", "an agent's reading", "s-2026-09-16-0001"
    )
    marked = {"AI_AGENT": "1"}
    refused("refs", "unlink", theirs.id, "--quilt", str(q), code=2, match="asserted by A. Author", env=marked)
    ok("refs", "unlink", mine.id, "--quilt", str(q), env=marked)
    assert [x.id for x in read_links(q)].count(theirs.id) == 1
    removed = [json.loads(ln) for ln in (q / "digests" / "links-removed.jsonl").read_text().splitlines()]
    assert removed[-1]["link"]["id"] == mine.id and removed[-1]["removed_by"]
