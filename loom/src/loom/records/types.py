"""The quilt's annotation types: `.loom/annotation-types.toml`, the presets a person picks from and an agent reads.

A type is a label with a look, whether its annotations stay open until resolved, whether they are listed in Notes, and instructions for agents. An annotation names its type by id and keeps its own look, so nothing here is needed to read one: a missing or malformed file loads the defaults with a diagnostic and never stops a quilt from loading.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from loom.paths import ANNOTATION_TYPES

#: The colours an annotation can take; what each means is its reader's.
COLORS = ("grey", "brown", "red", "orange", "yellow", "green", "blue", "purple", "pink")
#: How an annotation is drawn on words.
STYLES = ("underline", "highlight", "strike")
#: A type's id: what annotations name it by, so it reaches a URL fragment and a CSS hook.
ID = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
WEIGHTS = (1, 5)
OPACITIES = (0, 100)
#: How an annotation with no type is drawn when nothing is set on it: a thin grey underline.
UNTYPED = {"color": "grey", "style": "underline", "weight": 1, "opacity": 100}


@dataclass(frozen=True)
class Look:
    """How an annotation is drawn: a colour, a style, a thickness in whole pixels and an opacity in percent."""

    color: str
    style: str
    weight: int
    opacity: int

    def to_dict(self) -> dict[str, Any]:
        return {"color": self.color, "style": self.style, "weight": self.weight, "opacity": self.opacity}


@dataclass(frozen=True)
class AnnotationType:
    id: str
    name: str
    look: Look
    open: bool  # an annotation of this type stays open until someone resolves it; False: it only informs
    notes: bool  # annotations of this type are also listed in Notes
    instructions: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "look": self.look.to_dict(),
            "open": self.open,
            "notes": self.notes,
            "instructions": self.instructions,
        }


@dataclass
class Types:
    """The quilt's types in file order, the file they came from (None: the defaults), and one problem per thing that could not be read."""

    types: list[AnnotationType]
    source: str | None
    problems: list[str]

    def get(self, type_id: str | None) -> AnnotationType | None:
        return next((t for t in self.types if t.id == type_id), None)

    def find(self, given: str) -> AnnotationType | None:
        """A type by its id or its name, either in any case."""
        g = given.strip().lower()
        return next((t for t in self.types if g in (t.id, t.name.lower())), None)


def type_named(types: Types, given: str | None) -> AnnotationType | None:
    """The type `given` names by id or name; None for no type. Refused, naming the quilt's types, when it names none."""
    if given is None or not given.strip():
        return None
    t = types.find(given)
    if t is None:
        listed = ", ".join(f"{x.id} ({x.name})" for x in types.types) or "none"
        raise ValueError(f"no type {given!r} in this quilt; its types are {listed}, and an annotation may have none")
    return t


def drawn_look(t: AnnotationType | None, own: dict[str, Any]) -> dict[str, Any]:
    """The whole look an annotation is drawn with: its type's, or the untyped one, under what is set on it."""
    return {**(t.look.to_dict() if t else UNTYPED), **own}


def default_text() -> str:
    """The defaults as `loom init` writes them, comments included."""
    return resources.files("loom").joinpath("assets", "init", "annotation-types.toml").read_text(encoding="utf-8")


def look_problem(look: dict[str, Any]) -> str | None:
    """Why a look as given cannot be drawn; None when it can. Each of the four fields is optional here, since a look given on the command line overrides only what it names."""
    if "color" in look and look["color"] not in COLORS:
        return f"color must be one of {', '.join(COLORS)}"
    if "style" in look and look["style"] not in STYLES:
        return f"style must be one of {', '.join(STYLES)}"
    for field, (lo, hi), unit in (("weight", WEIGHTS, "whole pixels"), ("opacity", OPACITIES, "percent")):
        if field in look:
            v = look[field]
            if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
                return f"{field} is {unit} from {lo} to {hi}"
    return None


def _one(entry: Any, n: int, seen: set[str]) -> tuple[AnnotationType | None, str | None]:
    """The `n`th `[[type]]` as a type, or why it is skipped."""
    if not isinstance(entry, dict):
        return None, f"type {n} is not a table"
    tid = entry.get("id")
    if not isinstance(tid, str) or not ID.match(tid):
        return None, f"type {n} has no id of lowercase letters, digits and hyphens"
    if tid in seen:
        return None, f"type {tid!r} is given twice; the first is kept"
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        return None, f"type {tid!r} has no name"
    look = {k: entry[k] for k in ("color", "style", "weight", "opacity") if k in entry}
    missing = [k for k in ("color", "style", "weight", "opacity") if k not in look]
    if missing:
        return None, f"type {tid!r} has no {', '.join(missing)}"
    why = look_problem(look)
    if why:
        return None, f"type {tid!r}: {why}"
    flags = {k: entry.get(k, False) for k in ("open", "notes")}
    bad = [k for k, v in flags.items() if not isinstance(v, bool)]
    if bad:
        return None, f"type {tid!r}: {' and '.join(bad)} must be true or false"
    instructions = entry.get("instructions", "")
    if not isinstance(instructions, str):
        return None, f"type {tid!r}: instructions must be text"
    return AnnotationType(
        id=tid,
        name=name.strip(),
        look=Look(**look),
        open=flags["open"],
        notes=flags["notes"],
        instructions=instructions.strip(),
    ), None


def parse_types(text: str) -> tuple[list[AnnotationType], list[str]]:
    """The types a file's text holds, and one problem per entry skipped; raises `tomllib.TOMLDecodeError` when it is not TOML."""
    data = tomllib.loads(text)
    entries = data.get("type", [])
    if not isinstance(entries, list):
        return [], ["`type` must be an array of tables, written [[type]]"]
    out: list[AnnotationType] = []
    problems: list[str] = []
    seen: set[str] = set()
    for n, entry in enumerate(entries, 1):
        t, why = _one(entry, n, seen)
        if t is None:
            problems.append(why or f"type {n} is not readable")
            continue
        seen.add(t.id)
        out.append(t)
    return out, problems


def defaults() -> list[AnnotationType]:
    types, _ = parse_types(default_text())
    return types


def load_types(root: Path) -> Types:
    """The quilt's annotation types: its file's, or the defaults, said as a problem, when there is no file or it is not TOML.

    An entry that cannot be read is skipped and named; the rest of the file still counts, so one bad edit costs one type rather than every type a mode names.
    """
    path = root / ANNOTATION_TYPES
    if not path.is_file():
        return Types(
            defaults(),
            None,
            [f"{ANNOTATION_TYPES} is missing, so the default types are used; `loom upgrade` writes them into it"],
        )
    try:
        text = path.read_text(encoding="utf-8")
        types, problems = parse_types(text)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return Types(defaults(), None, [f"{ANNOTATION_TYPES} cannot be read ({exc}); the default types are used"])
    return Types(types, ANNOTATION_TYPES, [f"{ANNOTATION_TYPES}: {p}" for p in problems])


class TypesRefused(ValueError):
    """Types a write cannot save, and why, naming the type."""


def _slug(name: str, taken: set[str]) -> str:
    """An id for a type from its name: lower case, a hyphen for each run of anything but letters and digits, starting with a letter, unique among `taken`."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    base = re.sub(r"^[^a-z]+", "", base)[:36].strip("-") or "type"
    out, n = base, 2
    while out in taken:
        out, n = f"{base}-{n}", n + 1
    return out


def _quoted(text: str) -> str:
    """`text` as a TOML basic string on one line."""
    import json

    return json.dumps(text, ensure_ascii=False)


def _block(text: str) -> str:
    """`text` as a TOML multi-line basic string, opening and closing on lines of their own."""
    # the delimiter spelled out, since three quotes in a row in this file would read as a docstring to a line-based check
    fence = '"' * 3
    body = text.strip().replace("\\", "\\\\").replace(fence, '""\\"')
    return fence + "\n" + body + "\n" + fence if body else '""'


def types_text(given: list[Any]) -> str:
    """The types file for `given`, in its order and with the defaults' header comment, an id drawn from the name where none is given; TypesRefused names the type it cannot write.

    Parameters
    ----------
    given : list of dict
        The types as a write sends them, each `{id?, name, color, style, weight, opacity, open, notes, instructions}`.

    Returns
    -------
    str
        The file's text, which `parse_types` reads back to the same types.
    """
    header = default_text().split("\n[[type]]", 1)[0].rstrip() + "\n"
    ids: set[str] = set()
    names: set[str] = set()
    blocks: list[str] = []
    for n, entry in enumerate(given, 1):
        if not isinstance(entry, dict):
            raise TypesRefused(f"type {n} is not an object")
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            raise TypesRefused(f"type {n} has no name")
        name = name.strip()
        said = f"type {name!r}"
        if name.lower() in names:
            raise TypesRefused(f"{said} is named twice")
        names.add(name.lower())
        tid = entry.get("id")
        if tid in (None, ""):
            tid = _slug(name, ids | {str(e.get("id")) for e in given if isinstance(e, dict) and e.get("id")})
        if not isinstance(tid, str) or not ID.match(tid):
            raise TypesRefused(f"{said}: its id is lowercase letters, digits and hyphens, starting with a letter")
        if tid in ids:
            raise TypesRefused(f"{said}: the id {tid!r} is given twice")
        ids.add(tid)
        look = {k: entry.get(k) for k in ("color", "style", "weight", "opacity")}
        missing = [k for k, v in look.items() if v is None]
        if missing:
            raise TypesRefused(f"{said} has no {', '.join(missing)}")
        why = look_problem(look)
        if why:
            raise TypesRefused(f"{said}: {why}")
        flags = {k: entry.get(k, False) for k in ("open", "notes")}
        if any(not isinstance(v, bool) for v in flags.values()):
            raise TypesRefused(f"{said}: open and notes are true or false")
        instructions = entry.get("instructions", "")
        if not isinstance(instructions, str):
            raise TypesRefused(f"{said}: its instructions are text")
        blocks.append(
            "\n".join(
                [
                    "[[type]]",
                    f"id = {_quoted(tid)}",
                    f"name = {_quoted(name)}",
                    f"color = {_quoted(str(look['color']))}",
                    f"style = {_quoted(str(look['style']))}",
                    f"weight = {look['weight']}",
                    f"opacity = {look['opacity']}",
                    f"open = {'true' if flags['open'] else 'false'}",
                    f"notes = {'true' if flags['notes'] else 'false'}",
                    f"instructions = {_block(instructions)}",
                ]
            )
        )
    return header + "".join(f"\n{b}\n" for b in blocks)


def save_types(root: Path, given: list[Any] | None) -> Types:
    """Write the quilt's types file whole: `given` in its order, or the defaults for None; TypesRefused when one cannot be written, and nothing is written then.

    Parameters
    ----------
    root : Path
        The quilt.
    given : list of dict, optional
        The types, as `types_text` takes them; None writes the defaults.

    Returns
    -------
    Types
        The types as the file now reads.
    """
    text = default_text() if given is None else types_text(given)
    _parsed, problems = parse_types(text)
    if problems:
        raise TypesRefused("; ".join(problems))
    path = root / ANNOTATION_TYPES
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return load_types(root)
