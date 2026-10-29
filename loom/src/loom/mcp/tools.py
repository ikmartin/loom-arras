"""The MCP tools, read off the agent commands: one per entry in `AGENT_COMMANDS` but `NOT_TOOLS`, its schema from the command's click parameters, and each call turned back into the command line that runs it.

Nothing here imports the MCP SDK, so the tool surface is tested and snapshotted without one. A tool keeps its command's name (K7): `loom status` is `loom_status`, and an option `--source-text` is the argument `source_text`.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any

import click
import click.core

from loom.ai.layout import ACTS, AGENT_COMMANDS, NETWORK, NOT_TOOLS

#: Parameters the server supplies itself: the quilt it serves, and the name it was started with.
SUPPLIED = ("--quilt", "--as", "--help")
#: Options that read standard input, which a call never has: over MCP, each item is a call of its own.
READS_STDIN = ("--batch",)
#: A group that runs on its own takes one word, which its hidden command reads: `history KEY`, `library WORK`.
GROUP_WORDS = {
    "history": (
        "key",
        "A key, to list its recorded versions and whether its text now is one; with none, the history's steps.",
    ),
    "library": (
        "work",
        "A work, by citekey, a fragment of one or of its author or title, or one of its result ids, to report that one work; with none, the whole library.",
    ),
}


class CallRefused(ValueError):
    """A call the tool's command could not be built from: an argument it does not take, one it needs, or a value of the wrong kind."""


@dataclass(frozen=True)
class Param:
    """One argument of a tool and where it goes on the command line.

    Parameters
    ----------
    name : str
        The argument's name in a call: an option's long name in snake case, or a positional's own.
    flag : str or None
        The option it sets (`--source-text`); None for a positional or a group's word.
    kind : str
        Its JSON type: `string`, `integer`, `boolean` or `array`.
    off : str or None, default None
        A flag pair's other half (`--no-sections`), given when the argument is false.
    required : bool, default False
    choices : tuple of str, default ()
    minimum : int or None, default None
    default : object, default None
        The value the command takes when the argument is left out, said in the schema.
    description : str, default ''
    word : bool, default False
        A group's word, placed straight after the group's name.
    """

    name: str
    flag: str | None
    kind: str
    off: str | None = None
    required: bool = False
    choices: tuple[str, ...] = ()
    minimum: int | None = None
    default: object = None
    description: str = ""
    word: bool = False


@dataclass
class ToolSpec:
    """One tool: its name, the command path it runs, its help and its arguments.

    `takes_as` is whether the command takes `--as`, which the server fills with the name it serves.
    """

    name: str
    path: str
    description: str
    params: list[Param] = field(default_factory=list)
    takes_as: bool = False


def tool_name(path: str) -> str:
    """The tool for a command path: `library propose` is `loom_library_propose`."""
    return "loom_" + path.replace(" ", "_")


def tools() -> list[ToolSpec]:
    """Every tool the server offers, sorted by name: each agent command but `NOT_TOOLS`, never one of the author's."""
    from loom.cli import main

    return sorted((_spec(path, _command(main, path)) for path in AGENT_COMMANDS - NOT_TOOLS), key=lambda s: s.name)


def _command(root: click.Command, path: str) -> click.Command:
    cmd = root
    for word in path.split():
        cmd = cmd.commands[word]  # type: ignore[attr-defined]
    return cmd


def _spec(path: str, cmd: click.Command) -> ToolSpec:
    params = [p for p in (_param(x) for x in cmd.params) if p is not None]
    if path in GROUP_WORDS:
        name, said = GROUP_WORDS[path]
        params.insert(0, Param(name, None, "string", description=said, word=True))
    return ToolSpec(
        name=tool_name(path),
        path=path,
        description=inspect.cleandoc(cmd.help or cmd.short_help or ""),
        params=params,
        takes_as=any(isinstance(p, click.Option) and "--as" in p.opts for p in cmd.params),
    )


def _given(value: object) -> object:
    """A click default, or None when it is click's own sentinel for none given."""
    return None if value is getattr(click.core, "UNSET", object()) else value


def _param(p: click.Parameter) -> Param | None:
    """`p` as a tool's argument, or None for one the server supplies."""
    t = p.type
    kind = "integer" if isinstance(t, click.types.IntParamType) else "string"
    choices = tuple(str(c) for c in t.choices) if isinstance(t, click.Choice) else ()
    minimum = t.min if isinstance(t, click.IntRange) and t.min is not None else None
    if isinstance(p, click.Argument):
        array = p.nargs == -1
        return Param(
            p.name or "",
            None,
            "array" if array else kind,
            required=p.required,
            choices=choices,
            minimum=minimum,
        )
    assert isinstance(p, click.Option)
    longs = [o for o in p.opts if o.startswith("--")]
    flag = longs[0] if longs else p.opts[0]
    if flag in SUPPLIED or flag in READS_STDIN:
        return None
    name = flag.lstrip("-").replace("-", "_")
    if p.is_flag:
        off = next((o for o in p.secondary_opts if o.startswith("--")), None)
        return Param(name, flag, "boolean", off=off, default=bool(_given(p.default)), description=p.help or "")
    default = _given(p.default)
    return Param(
        name,
        flag,
        "array" if p.multiple else kind,
        required=p.required,
        choices=choices,
        minimum=minimum,
        default=None if p.multiple else default,
        description=p.help or "",
    )


def schema(spec: ToolSpec) -> dict[str, Any]:
    """The tool's input schema: one property per argument, its type, choices, minimum and default, the required ones named, and nothing else accepted."""
    props: dict[str, Any] = {}
    for p in spec.params:
        item: dict[str, Any] = {"type": "integer" if p.kind == "integer" else "string"}
        if p.choices:
            item["enum"] = list(p.choices)
        if p.minimum is not None:
            item["minimum"] = p.minimum
        prop: dict[str, Any] = {"type": "array", "items": item} if p.kind == "array" else dict(item)
        if p.kind == "boolean":
            prop = {"type": "boolean"}
        if p.default not in (None, "", False):
            prop["default"] = p.default
        if p.description:
            prop["description"] = p.description
        props[p.name] = prop
    out: dict[str, Any] = {"type": "object", "properties": props, "additionalProperties": False}
    required = [p.name for p in spec.params if p.required]
    if required:
        out["required"] = required
    return out


def hints(spec: ToolSpec) -> dict[str, bool]:
    """The tool's annotations from what its command does (`ACTS`): a reader is read-only; a derivation rewrites only `build/` and may be repeated; a write adds; a replacement puts new text in place of old."""
    act = ACTS[spec.path]
    return {
        "read_only_hint": act == "read",
        "destructive_hint": act == "replace",
        "idempotent_hint": act in ("read", "derive"),
        "open_world_hint": spec.path in NETWORK,
    }


def argv(spec: ToolSpec, arguments: dict[str, Any], *, as_name: str) -> list[str]:
    """The command line a call stands for, after `loom`: the path, the group's word, the options, then the positionals.

    Refused before anything runs, with `CallRefused`: an argument the tool does not take, a required one left out, a value of the wrong type, and a text of `-`, which reads a shell's standard input where a call has none. A positional left out before one given moves the later one up, as the command line does (`annotate`'s reply takes its message where a target would go).
    """
    names = {p.name for p in spec.params}
    unknown = sorted(set(arguments) - names)
    if unknown:
        takes = ", ".join(sorted(names)) or "no arguments"
        raise CallRefused(f"{spec.name} takes no {', '.join(unknown)}; it takes {takes}")
    missing = [p.name for p in spec.params if p.required and arguments.get(p.name) in (None, "", [])]
    if missing:
        raise CallRefused(f"{spec.name} needs {', '.join(missing)}")
    out = spec.path.split()
    options: list[str] = []
    positionals: list[str] = []
    for p in spec.params:
        value = arguments.get(p.name)
        if value is None:
            continue
        said = _checked(spec, p, value)
        if p.word:
            out += said
        elif p.flag is None:
            positionals += said
        elif p.kind == "boolean":
            options += [p.flag] if value else ([p.off] if p.off else [])
        else:
            for one in said:
                options += [p.flag, one]
    if spec.takes_as:
        options += ["--as", as_name]
    # a positional that looks like an option is still a positional
    end = ["--"] if any(x.startswith("-") for x in positionals) else []
    return out + options + end + positionals


def _checked(spec: ToolSpec, p: Param, value: Any) -> list[str]:
    """`value` as the words it puts on the command line, refused when it is not of `p`'s type."""
    want = {"string": str, "integer": int, "boolean": bool, "array": list}[p.kind]
    if not isinstance(value, want) or (p.kind == "integer" and isinstance(value, bool)):
        raise CallRefused(
            f"{spec.name}: {p.name} is {p.kind if p.kind != 'array' else 'a list'}, not {type(value).__name__}"
        )
    values = [str(v) for v in value] if isinstance(value, list) else [] if p.kind == "boolean" else [str(value)]
    for v in values:
        if v.strip() == "-":
            raise CallRefused(
                f"{spec.name}: {p.name} is `-`, which reads a shell's standard input; give the text itself"
            )
    return values
