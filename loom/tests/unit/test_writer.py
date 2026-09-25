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
    # and the author, named, is not refused for the shell they happen to be in
    ok(
        "refs",
        "unreadable",
        "Bellamy19",
        "--why",
        "a study",
        "--author",
        "A. Author",
        "--quilt",
        str(q),
        env={"AI_AGENT": "1"},
    )
