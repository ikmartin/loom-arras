"""The MCP tool surface, read off the agent commands: which tools there are, their schemas and hints, and the command line a call becomes. None of it needs the SDK."""

from __future__ import annotations

import re
import runpy
from pathlib import Path

import pytest

from loom.ai.layout import ACTS, AGENT_COMMANDS, NOT_TOOLS, command_tree
from loom.mcp.tools import CallRefused, argv, schema, tool_name, tools

REPO = Path(__file__).resolve().parents[2]
SPECS = {s.name: s for s in tools()}


def test_the_tools_are_the_agent_commands_and_none_of_the_authors() -> None:
    assert {s.path for s in SPECS.values()} == AGENT_COMMANDS - NOT_TOOLS
    authors = set(command_tree()) - AGENT_COMMANDS
    assert authors and not {tool_name(p) for p in authors} & set(SPECS), "an author's command is a tool"
    assert not {"loom_serve", "loom_mcp", "loom_session_next", "loom_session_watch"} & set(SPECS)
    assert all(re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", name) for name in SPECS)


def test_every_agent_command_says_what_it_does() -> None:
    """The hints come from one table beside `AGENT_COMMANDS`, which must cover it exactly."""
    assert set(ACTS) == AGENT_COMMANDS
    assert set(ACTS.values()) <= {"read", "derive", "write", "replace"}


def test_the_checked_in_surface_is_what_the_tree_generates() -> None:
    """A changed flag is a changed tool, so the surface is checked in and shows as a diff (docs/mcp-tools.json)."""
    mod = runpy.run_path(str(REPO / "scripts" / "gen_mcp_tools.py"), run_name="not_main")
    assert (REPO / "docs" / "mcp-tools.json").read_text(encoding="utf-8") == mod["generate"](), (
        "run scripts/gen_mcp_tools.py"
    )


def test_a_schema_says_types_choices_defaults_and_what_is_required() -> None:
    s = schema(SPECS["loom_library_search"])
    assert s["type"] == "object" and s["additionalProperties"] is False and s["required"] == ["text"]
    props = s["properties"]
    assert props["work"] == {"type": "array", "items": {"type": "string"}, "description": props["work"]["description"]}
    assert props["limit"]["type"] == "integer" and props["limit"]["minimum"] == 1 and props["limit"]["default"] == 20
    assert props["pages"]["type"] == "boolean" and "quilt" not in props
    assert "as" not in schema(SPECS["loom_annotate"])["properties"]  # the server supplies who is acting
    assert "batch" not in schema(SPECS["loom_annotate"])["properties"]  # it reads stdin, which a call has none of
    assert schema(SPECS["loom_annotate"])["properties"]["severity"]["enum"] == ["major", "moderate", "minor"]
    assert schema(SPECS["loom_id"])["properties"]["sections"]["default"] is True


@pytest.mark.parametrize(
    ("tool", "arguments", "line"),
    [
        (
            "loom_annotate",
            {"target": "dm-0002", "message": "Which orbits?", "kind": "question"},
            ["annotate", "--kind", "question", "--as", "Test Agent", "dm-0002", "Which orbits?"],
        ),
        # a reply names no target: its message takes the target's place, as on the command line
        ("loom_annotate", {"reply": "a-1", "message": "Yes."}, ["annotate", "--reply", "a-1", "--as", "Test Agent", "Yes."]),
        ("loom_annotate", {"reply": "a-1", "message": "-1 is odd"}, ["annotate", "--reply", "a-1", "--as", "Test Agent", "--", "-1 is odd"]),
        ("loom_history", {"key": "dm-0002", "json": True}, ["history", "dm-0002", "--json"]),
        ("loom_library", {"work": "Calloway14"}, ["library", "Calloway14"]),
        ("loom_id", {"file": "drafting/x.tex", "sections": False}, ["id", "--no-sections", "drafting/x.tex"]),
        ("loom_library_search", {"text": "orbit", "work": ["A", "B"]}, ["library", "search", "--work", "A", "--work", "B", "orbit"]),
        (
            "loom_library_propose",
            {"work": "Calloway14", "local": "rem-9.1", "source_text": "An involution", "statement": "S", "page": "1"},
            [
                "library", "propose", "--local", "rem-9.1", "--page", "1", "--source-text", "An involution",
                "--statement", "S", "--as", "Test Agent", "Calloway14",
            ],
        ),
    ],
)  # fmt: skip
def test_a_call_is_the_command_line_it_stands_for(tool: str, arguments: dict[str, object], line: list[str]) -> None:
    assert argv(SPECS[tool], arguments, as_name="Test Agent") == line


@pytest.mark.parametrize(
    ("tool", "arguments", "said"),
    [
        ("loom_status", {"bogus": 1}, "takes no bogus"),
        ("loom_deps", {}, "needs key"),
        ("loom_annotate", {"target": "dm-0002", "message": "-"}, "give the text itself"),
        ("loom_library_search", {"text": "x", "limit": "20"}, "limit is integer"),
        ("loom_status", {"stale": "yes"}, "stale is boolean"),
        ("loom_library_search", {"text": "x", "work": "A"}, "work is a list"),
    ],
)
def test_a_call_that_names_nothing_its_command_takes_is_refused(
    tool: str, arguments: dict[str, object], said: str
) -> None:
    with pytest.raises(CallRefused, match=said):
        argv(SPECS[tool], arguments, as_name="Test Agent")
