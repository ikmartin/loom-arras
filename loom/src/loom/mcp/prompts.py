"""The MCP prompts: one per mode, the person's shortcut to it (`/mcp__loom__flow KEY` in Claude Code), each expanding to the quilt's own copy of the mode and the target it was given.

Nothing here imports the MCP SDK. The server checks a target with `loom link` and reads the mode with `loom ai mode`, so a prompt runs the reading commands a tool would; a mode an agent picks itself is `loom_ai_mode`, and the prompt is only the person's way of naming one.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

#: The one argument every prompt takes. Claude Code splits a prompt's arguments on whitespace, so it is one word, and the rest of a request is said in the conversation.
TARGET = "target"
TARGET_SAID = "What to work on, as one word: a key, a document's path, or a cited work's citekey or identifier; with none, what the conversation names."


@dataclass(frozen=True)
class PromptSpec:
    """One prompt: the mode it starts, and the mode's `When it fits:` line as the line a client's menu shows."""

    name: str
    description: str


def prompts(root: Path) -> list[PromptSpec]:
    """A prompt per mode, in `MODES` order, each described by the quilt's own copy of the mode."""
    from loom.ai.layout import MODES
    from loom.ai.orient import fits

    return [PromptSpec(name, fits(root, name)) for name in MODES]


def link_argv(target: str) -> list[str]:
    """`loom link TARGET`, which refuses a target that names nothing and prints the address of one that does."""
    return ["link", *(["--"] if target.startswith("-") else []), target]


def mode_argv(name: str) -> list[str]:
    """`loom ai mode NAME`, the quilt's copy of the mode, else the shipped one."""
    return ["ai", "mode", name]


def message(name: str, target: str, href: str, mode: str) -> str:
    """The user message a prompt expands to: the mode and its target, orientation first if it has not happened, then the mode in full."""
    on = (
        f"on `{target}` ({href})"
        if target
        else "on what this conversation names; if it names nothing yet, ask me what to work on"
    )
    return (
        f"Work in loom's {name} mode {on}. If you have not called `loom_ai_orient` in this conversation, call it first. "
        "The mode, as this quilt keeps it:\n\n" + mode.rstrip("\n") + "\n"
    )
