"""The MCP resources and prompts as data, without the SDK: each address read by the reading command it stands for, what is refused and why, and what the list holds."""

from __future__ import annotations

from pathlib import Path

import pytest

from loom.ai.layout import ACTS, AGENT_COMMANDS, MODES
from loom.mcp.prompts import link_argv, message, mode_argv, prompts
from loom.mcp.resources import STATE, TEMPLATES, NotAResource, listed, reading
from loom.scan.quilt import load_quilt
from loom.scan.scan import scan
from tests.unit._quilts import demo, showcase

LANDMARK = ".loom/history/0001-flows-v1/flows-v1.tex"

READS = [
    ("quilt:sh-0007", ("source", "sh-0007")),
    ("quilt:sh-0007?closure", ("source", "--closure", "sh-0007")),
    ("quilt:sh-0007%2Fproof", ("source", "sh-0007/proof")),
    ("quilt:sh-0007#sh-0007-eq", ("source", "sh-0007")),
    ("quilt:drafting/main-atomic.tex", ("source", "drafting/main-atomic.tex")),
    ("quilt:drafting/main-atomic.tex#sh-0007", ("source", "sh-0007")),
    (f"quilt:{LANDMARK}", ("history", "show", "flows-v1")),
    ("quilt:flows-v1", ("history", "show", "flows-v1")),
    ("quilt:-x", ("source", "--", "-x")),
    ("cited:doi:10.4171/showcase/19-2", ("library", "read", "doi:10.4171/showcase/19-2")),
    (
        "cited:doi:10.4171/showcase/19-2?page=3&quote=The%20defect",
        ("library", "read", "doi:10.4171/showcase/19-2", "3"),
    ),
]


@pytest.fixture(scope="module")
def quilt(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return showcase(tmp_path_factory.mktemp("q"))


@pytest.mark.parametrize(("uri", "words"), READS, ids=[u for u, _ in READS])
def test_each_address_is_read_by_the_command_it_stands_for(quilt: Path, uri: str, words: tuple[str, ...]) -> None:
    assert reading(uri, load_quilt(quilt)).argv == words


def test_the_research_state_is_the_one_address_read_without_a_command(quilt: Path) -> None:
    assert reading(f"quilt:{STATE}", load_quilt(quilt)).argv is None


@pytest.mark.parametrize(
    ("uri", "said"),
    [
        ("quilt:a-2026-01-01-1", "loom_ai_annotations"),
        ("quilt:s-2026-01-01-0001", "loom_session_list"),
        ("https://example.org", "the addresses `loom link` prints"),
        ("quilt:", "names no key"),
        ("cited:", "names no work"),
        ("cited:doi:10.1/x?page=0", "a number from 1"),
        ("quilt:sh-0007?at=accepted", "takes only ?closure"),
        ("quilt:state?closure", "read whole"),
        (f"quilt:{LANDMARK}#sh-0007", "read whole"),
    ],
)
def test_what_is_no_resource_is_refused_with_what_reads_it(quilt: Path, uri: str, said: str) -> None:
    with pytest.raises(NotAResource, match=said.replace("?", r"\?")):
        reading(uri, load_quilt(quilt))


def test_every_command_a_prompt_or_resource_runs_is_an_agent_command_that_only_reads(quilt: Path) -> None:
    """The one-table rule: a prompt or a read runs nothing an agent's tools could not, and nothing that writes."""

    def path(words: tuple[str, ...] | list[str]) -> str:
        return next(p for n in (2, 1) if (p := " ".join(words[:n])) in ACTS)

    paths = {path(words) for _, words in READS} | {path(link_argv("sh-0007")), path(mode_argv("quick"))}
    assert paths == {"source", "history show", "library read", "link", "ai mode"}
    assert all(p in AGENT_COMMANDS and ACTS[p] == "read" for p in paths), paths


def test_the_list_holds_what_a_person_would_mention_and_the_templates_the_rest(quilt: Path) -> None:
    result = scan(load_quilt(quilt))
    got = {r.uri: r for r in listed(result)}
    assert "quilt:state" in got and "quilt:drafting/main-atomic.tex" in got and f"quilt:{LANDMARK}" in got
    assert got["quilt:sh-0007"].title.startswith("Proposition") and "quilt:sh-0007/proof" not in got
    assert got["cited:doi:10.4171/showcase/19-2"].name == "Bellamy19"
    assert not [u for u in got if u.startswith("quilt:Bellamy19-")]  # a digest's results are reached by template
    assert all(reading(u, result.quilt) for u in got)  # every listed address reads
    assert [t.uri for t in TEMPLATES] == [
        "quilt:{+key}",
        "quilt:{+key}?closure",
        "cited:{+work}",
        "cited:{+work}?page={page}",
    ]


def test_a_quilt_with_no_research_state_lists_none(tmp_path: Path) -> None:
    assert not [r for r in listed(scan(load_quilt(demo(tmp_path)))) if r.uri == "quilt:state"]


def test_a_prompt_per_mode_described_by_the_quilts_own_copy(tmp_path: Path) -> None:
    q = demo(tmp_path)
    mode = q / "ai" / "modes" / "quick.md"
    mode.write_text(mode.read_text().replace("When it fits: a question asked in passing", "When it fits: a quick one"))
    got = prompts(q)
    assert [p.name for p in got] == MODES
    assert got[0].description.startswith("a quick one") and all(p.description for p in got)
    said = message("quick", "dm-0002", "quilt:dm-0002", "# Mode: quick\n")
    assert said.startswith("Work in loom's quick mode on `dm-0002` (quilt:dm-0002).") and "loom_ai_orient" in said
    assert "ask me what to work on" in message("quick", "", "", "# Mode: quick\n")
