"""The project's files as the viewer shows them: which are shown, what kind each is, and the bodies the publisher draws for Markdown files and notebooks.

One predicate, `Shown.is_shown`, decides what is hidden for the manifest, the server, the links and the watcher, so they never disagree: any path with a segment starting with `.` (loom's `.loom/` among them), tools' directories (`node_modules`, `__pycache__`), the history and sync directories, and whatever the quilt's `.gitignore` files ignore. Git's global excludes are not read.
"""

from __future__ import annotations

import html
import json
import os
import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, unquote

if TYPE_CHECKING:
    from loom.scan.quilt import Quilt
    from loom.scan.scan import ScanResult
    from loom.tasks import Task

#: Where `loom serve` answers a shown file on the viewer's own origin, sandboxed.
FILES_URL = "/_files/"
#: Where a Markdown file's or notebook's rendered body is published, under the build output.
BODIES = "files"
#: Tools' directories, hidden by name at any depth like a dot-directory.
TOOL_DIRS = frozenset({"node_modules", "__pycache__"})
SUFFIX_KINDS = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".svg": "image",
    ".webp": "image",
    ".ipynb": "notebook",
}
#: The kinds a `quilt:` link may name by the file's path; a `.tex` file is linked by its document or its keys instead.
LINKABLE = frozenset({"markdown", "html", "pdf", "image", "notebook", "text", "other"})
#: The kinds whose body the publisher draws, and whose places are their headings.
DRAWN = frozenset({"markdown", "notebook"})
#: What `loom serve` opens in its application on the person's click: documents only, never a file that runs code.
OPENABLE = frozenset(
    {
        ".ipynb",
        ".csv",
        ".xlsx",
        ".xls",
        ".ods",
        ".docx",
        ".odt",
        ".pptx",
        ".key",
        ".numbers",
        ".pages",
        ".apkg",
        ".colpkg",
        ".mp4",
        ".mov",
        ".mp3",
        ".m4a",
        ".wav",
        ".epub",
        ".djvu",
    }
)
TEXT_LIMIT = 1 << 20


@dataclass(frozen=True)
class _Rule:
    """One `.gitignore` line: whether it re-includes, whether it matches directories only, and its pattern relative to the file's directory."""

    regex: re.Pattern[str]
    negate: bool
    directory: bool


def _rules(text: str) -> list[_Rule]:
    """A `.gitignore`'s lines as rules, in order; comments, blank lines and patterns naming nothing are dropped."""
    from loom.agents import _glob

    out: list[_Rule] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        negate = line.startswith("!")
        if negate:
            line = line[1:]
        if line.startswith("\\"):
            line = line[1:]
        directory = line.endswith("/")
        anchored = line.startswith("/") or "/" in line.strip("/")
        body = line.strip("/")
        if not body:
            continue
        out.append(_Rule(re.compile(("^" if anchored else "^(?:.*/)?") + _glob(body) + "$"), negate, directory))
    return out


@dataclass
class Shown:
    """What the viewer shows of one quilt: `is_shown` for a single path, `walk` for all of them.

    Build one per quilt and keep it: each directory's `.gitignore` is read once and read again only when its modification time changes.
    """

    root: Path
    hidden_dirs: tuple[str, ...] = ()  # quilt-relative directories hidden by path: the history and the sync directory
    _ignores: dict[str, tuple[float, list[_Rule]]] = field(default_factory=dict, repr=False)

    @classmethod
    def of(cls, quilt: Quilt) -> Shown:
        """The shown files of `quilt`, its history and sync directories hidden."""
        from loom.sync import skipped_directory

        synced = skipped_directory(quilt.root)
        dirs = (PurePosixPath(quilt.config.history).as_posix(), *((synced,) if synced else ()))
        return cls(quilt.root, tuple(d.strip("/") for d in dirs))

    def _rules_in(self, directory: str) -> list[_Rule]:
        path = self.root / directory / ".gitignore" if directory else self.root / ".gitignore"
        try:
            mtime = path.stat().st_mtime
        except OSError:
            self._ignores.pop(directory, None)
            return []
        cached = self._ignores.get(directory)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        try:
            rules = _rules(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            rules = []
        self._ignores[directory] = (mtime, rules)
        return rules

    def _ignored(self, rel: str, is_dir: bool) -> bool:
        """Whether the `.gitignore` files from the root down to `rel`'s directory ignore it; the last match wins, and a deeper file's rules come later."""
        parts = rel.split("/")
        ignored = False
        for depth in range(len(parts)):
            directory = "/".join(parts[:depth])
            sub = "/".join(parts[depth:])
            for rule in self._rules_in(directory):
                if rule.directory and not is_dir:
                    continue
                if rule.regex.match(sub):
                    ignored = not rule.negate
        return ignored

    def _hidden_name(self, rel: str) -> bool:
        parts = rel.split("/")
        if any(p.startswith(".") or p in TOOL_DIRS for p in parts):
            return True
        return any(rel == d or rel.startswith(f"{d}/") for d in self.hidden_dirs)

    def is_shown(self, rel: str) -> bool:
        """Whether the quilt-relative path `rel` is one the viewer shows: in the quilt, not hidden by name or path, and not ignored, nor in a directory that is."""
        if not rel or rel.startswith("/") or "\\" in rel:
            return False
        parts = PurePosixPath(rel).parts
        if any(p in ("..", ".") for p in parts):
            return False
        rel = "/".join(parts)
        if self._hidden_name(rel):
            return False
        for depth in range(1, len(parts)):
            if self._ignored("/".join(parts[:depth]), True):
                return False
        return not self._ignored(rel, (self.root / rel).is_dir())

    def walk(self) -> list[str]:
        """Every shown file, quilt-relative and sorted; a symbolic link that leads out of the quilt is left out, since nothing outside it is served."""
        root = self.root.resolve()
        found: list[str] = []
        for folder, dirs, names in os.walk(self.root):
            here = Path(folder).relative_to(self.root).as_posix()
            here = "" if here == "." else here
            dirs[:] = sorted(
                d
                for d in dirs
                if not self._hidden_name(f"{here}/{d}".lstrip("/"))
                and not self._ignored(f"{here}/{d}".lstrip("/"), True)
            )
            for name in names:
                rel = f"{here}/{name}".lstrip("/")
                if self._hidden_name(rel) or self._ignored(rel, False):
                    continue
                path = Path(folder) / name
                if path.is_symlink() and not path.resolve().is_relative_to(root):
                    continue
                if path.is_file():
                    found.append(rel)
        return sorted(found)


_TEXT_SEEN: dict[tuple[str, float, int], bool] = {}


def _is_text(path: Path) -> bool:
    """Whether `path` reads as UTF-8 text, small enough to show: no NUL in its first 8 KB and at most 1 MB; remembered by modification time and size."""
    try:
        st = path.stat()
    except OSError:
        return False
    key = (str(path), st.st_mtime, st.st_size)
    if key in _TEXT_SEEN:
        return _TEXT_SEEN[key]
    ok = False
    if st.st_size <= TEXT_LIMIT:
        try:
            data = path.read_bytes()
            ok = b"\x00" not in data[:8192]
            if ok:
                data.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            ok = False
    _TEXT_SEEN[key] = ok
    return ok


def kind_of(root: Path, rel: str, masters: set[str] | frozenset[str] = frozenset()) -> str:
    """What the viewer does with the shown file `rel`: `document` (a master), `tex`, a drawn or framed kind by suffix, `text`, or `other`."""
    suffix = PurePosixPath(rel).suffix.lower()
    if suffix == ".tex":
        return "document" if rel in masters else "tex"
    if suffix in SUFFIX_KINDS:
        return SUFFIX_KINDS[suffix]
    return "text" if _is_text(root / rel) else "other"


def slug(text: str, seen: dict[str, int]) -> str:
    """A heading's id as GitHub writes it: lower case, punctuation dropped, spaces as hyphens; a repeat takes `-1`, `-2`."""
    base = re.sub(r"[^\w\- ]", "", re.sub(r"loommathx\d+x", "", text).strip().lower()).replace(" ", "-") or "section"
    n = seen.get(base, 0)
    seen[base] = n + 1
    return base if n == 0 else f"{base}-{n}"


def _target(href: str, directory: str, kinds: dict[str, str]) -> tuple[str, str, str] | None:
    """(path, place, kind) of the shown file a relative `href` names from `directory`, or None when it is not relative or names nothing shown."""
    if not href or href.startswith(("/", "#", "?")) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", href):
        return None
    path, _, place = href.partition("#")
    path = unquote(path.split("?", 1)[0])
    joined = posixpath.normpath(posixpath.join(directory, path)) if directory else posixpath.normpath(path)
    if joined.startswith("..") or joined not in kinds:
        return None
    return joined, place, kinds[joined]


def _link(href: str, directory: str, kinds: dict[str, str]) -> str:
    """A relative link to a shown file as the `quilt:` link the viewer follows (a document's by its path, as every link to one is), and any other `href` as it stands."""
    got = _target(href, directory, kinds)
    if got is None:
        return href
    path, place, kind = got
    if kind == "document":
        return f"quilt:{quote(path)}"
    return f"quilt:{quote(path)}" + (f"#{place}" if place else "") if kind in LINKABLE else href


def _heading_words(inline: Any) -> str:
    """What a heading's id is made from: its source, less any raw HTML tags in it."""
    text = str(inline.content)
    for child in inline.children or []:
        if child.type == "html_inline":
            text = text.replace(child.content, "", 1)
    return text


def _rewriter(directory: str, kinds: dict[str, str], seen: dict[str, int]) -> Any:
    """The token pass a file's Markdown takes: ids on its headings, a relative link to a shown file turned into a `quilt:` link (a document's by its path, as every link to one is), a relative image into its `/_files/` address."""

    def walk(tokens: list[Any]) -> None:
        for i, tok in enumerate(tokens):
            if tok.type == "heading_open" and i + 1 < len(tokens):
                tok.attrSet("id", slug(_heading_words(tokens[i + 1]), seen))
            for child in tok.children or []:
                if child.type == "link_open":
                    href = str(child.attrGet("href") or "")
                    child.attrSet("href", _link(href, directory, kinds))
                elif child.type == "image":
                    got = _target(str(child.attrGet("src") or ""), directory, kinds)
                    if got is not None and got[2] == "image":
                        child.attrSet("src", FILES_URL + quote(got[0]))

    return walk


def render_file_markdown(
    text: str, rel: str, kinds: dict[str, str], seen: dict[str, int] | None = None, *, tasks: list[Task] | None = None
) -> str:
    """The Markdown file `rel` drawn as the publisher draws pages, with ids on its headings, its relative links resolved against the shown files `kinds`, its raw HTML through the allowlist (`loom.raw_html`), and each task item a `li.task`.

    Only a file's body takes raw HTML; pages and messages escape it. `seen` carries heading ids across calls, so a notebook's cells number repeats as one document does. `tasks` collects each item and makes its box tickable, for text that is a whole file; a notebook's cell passes none, so its boxes are only drawn.
    """
    from loom.raw_html import clean
    from loom.records.store import render_markdown
    from loom.tasks import mark_items

    directory = posixpath.dirname(rel)
    rewrite = _rewriter(directory, kinds, {} if seen is None else seen)
    mark = mark_items(text, tasks)

    def walk(tokens: list[Any]) -> None:
        mark(tokens)
        rewrite(tokens)

    def resolve(name: str, url: str) -> str:
        if name == "href":
            return _link(url, directory, kinds)
        got = _target(url, directory, kinds)
        return url if got is None else FILES_URL + quote(got[0])

    return render_markdown(text, tokens=walk, raw=lambda source, words: clean(source, resolve, words))


def headings(body: str) -> set[str]:
    """The heading ids a drawn body carries, written by Markdown or by a file's own HTML: the places a link into it may name."""
    return set(re.findall(r'<h[1-6]\b[^>]*?\sid="([^"]+)"', body))


_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _joined(value: Any) -> str:
    return "".join(value) if isinstance(value, list) else str(value or "")


def _output(out: dict[str, Any]) -> str:
    """One saved output of a code cell: text and errors as written, an image as an image, an HTML or script output by its plain form."""
    kind = out.get("output_type")
    if kind == "stream":
        return f'<pre class="nb-out">{html.escape(_ANSI.sub("", _joined(out.get("text"))))}</pre>'
    if kind == "error":
        trace = "\n".join(_joined(t) for t in out.get("traceback") or []) or f"{out.get('ename')}: {out.get('evalue')}"
        return f'<pre class="nb-out nb-error">{html.escape(_ANSI.sub("", trace))}</pre>'
    data = out.get("data") or {}
    for mime in ("image/png", "image/jpeg"):
        if mime in data:
            return f'<img class="nb-image" alt="" src="data:{mime};base64,{_joined(data[mime]).strip()}">'
    if "image/svg+xml" in data:
        import base64

        svg = base64.b64encode(_joined(data["image/svg+xml"]).encode("utf-8")).decode("ascii")
        return f'<img class="nb-image" alt="" src="data:image/svg+xml;base64,{svg}">'
    if "text/plain" in data:
        return f'<pre class="nb-out">{html.escape(_ANSI.sub("", _joined(data["text/plain"])))}</pre>'
    if data:
        return '<p class="nb-note">An HTML output, not drawn.</p>'
    return ""


def render_notebook(text: str, rel: str, kinds: dict[str, str]) -> str:
    """The notebook `rel` drawn read-only from its saved cells: Markdown cells as a Markdown file is, code as code with its count, and each output as `_output` draws it. Loom runs nothing."""
    try:
        nb = json.loads(text)
    except ValueError:
        return '<p class="nb-note">This notebook is not valid JSON.</p>'
    if not isinstance(nb, dict) or nb.get("nbformat") != 4 or not isinstance(nb.get("cells"), list):
        return '<p class="nb-note">Only nbformat 4 notebooks are drawn.</p>'
    language = str(((nb.get("metadata") or {}).get("kernelspec") or {}).get("language") or "")
    seen: dict[str, int] = {}
    parts: list[str] = []
    for cell in nb["cells"]:
        if not isinstance(cell, dict):
            continue
        source = _joined(cell.get("source"))
        if cell.get("cell_type") == "markdown":
            body = render_file_markdown(source, rel, kinds, seen)
            parts.append(f'<div class="nb-markdown">{body}</div>')
        elif cell.get("cell_type") == "code":
            count = cell.get("execution_count")
            label = f"[{count}]" if count is not None else "[ ]"
            lang = f' data-language="{html.escape(language)}"' if language else ""
            outputs = "".join(_output(o) for o in cell.get("outputs") or [] if isinstance(o, dict))
            parts.append(
                f'<div class="nb-code"><span class="nb-count">{label}</span><pre{lang}><code>{html.escape(source)}</code></pre>{outputs}</div>'
            )
    return "\n".join(parts)


def attach_files(result: ScanResult, manifest: dict[str, Any], files: dict[str, str | bytes]) -> None:
    """Publish the shown files into `manifest["files"]` and `corpus.home`, and each Markdown file's and notebook's body into `files` under `BODIES`.

    Called once per build; the research state is listed like any Markdown file, and the viewer opens its page from the row. Every file carries `denied`, from `agents.denied_by`: what keeps agents out, or None where they may write it, so the viewer never matches the deny list itself and never guesses where a publisher said nothing.
    """
    from loom.agents import always_denied, denied_by

    root = result.quilt.root
    config = result.quilt.config
    shown = Shown.of(result.quilt)
    masters = set(result.masters)
    paths = shown.walk()
    kinds = {rel: kind_of(root, rel, masters) for rel in paths}
    entries: list[dict[str, Any]] = []
    for rel in paths:
        kind = kinds[rel]
        try:
            size = (root / rel).stat().st_size
        except OSError:
            continue
        entry: dict[str, Any] = {"path": rel, "kind": kind, "bytes": size}
        why = denied_by(config, rel)
        entry["denied"] = None if why is None else {"by": why, "always": always_denied(config, why)}
        if kind in DRAWN:
            try:
                text = (root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            body = (
                render_file_markdown(text, rel, kinds, tasks=[])
                if kind == "markdown"
                else render_notebook(text, rel, kinds)
            )
            entry["body"] = f"{BODIES}/{rel}.html"
            files[entry["body"]] = body
        entries.append(entry)
    manifest["files"] = entries
    manifest["corpus"]["home"] = home(result.quilt, set(paths))


def home(quilt: Quilt, shown: set[str]) -> str | None:
    """The file the viewer opens on when the browser remembers no place: `[quilt] home` when it names a shown file, else the root `README.md`, else None (`loom:home-missing` says when the setting names nothing)."""
    named = quilt.config.home
    if named and named in shown:
        return named
    return "README.md" if "README.md" in shown else None


#: An application's name as `open -a` and `gtk-launch` take it: words, never a path or an option.
APP_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,63}$")


class OpenRefused(Exception):
    """Why `loom serve` will not open what a click asked for; `code` is the write API's error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def can_open(platform: str = sys.platform) -> bool:
    """Whether this machine has a way to open an application or a file for the person: macOS and Linux."""
    return platform == "darwin" or platform.startswith("linux")


def open_command(
    shown: Shown, *, app: str | None = None, file: str | None = None, platform: str = sys.platform
) -> list[str]:
    """The command that opens the application `app`, or the shown file `file` in its application, or OpenRefused.

    A file opens only when its suffix is a document's (`OPENABLE`) and no executable bit is set, so a click never runs code: an agent can write a file into the quilt and a link to it, but not make the person's click execute it.
    """
    if not can_open(platform):
        raise OpenRefused("unsupported", "this machine has no way for loom to open an application")
    darwin = platform == "darwin"
    if app is not None:
        if not APP_NAME.match(app):
            raise OpenRefused("bad-app", f"{app!r} is not an application's name")
        return ["open", "-a", app] if darwin else ["gtk-launch", app]
    if file is None:
        raise OpenRefused("missing-field", "name an app or a file")
    if not shown.is_shown(file):
        raise OpenRefused("no-such-file", f"{file} is not a file the viewer shows")
    path = (shown.root / file).resolve()
    if not path.is_relative_to(shown.root.resolve()) or not path.is_file():
        raise OpenRefused("no-such-file", f"{file} is not a file the viewer shows")
    if PurePosixPath(file).suffix.lower() not in OPENABLE:
        raise OpenRefused(
            "not-openable",
            f"{file} is not a document loom opens in its application; loom never opens a file that may run code",
        )
    if path.stat().st_mode & 0o111:
        raise OpenRefused("not-openable", f"{file} is executable, and loom never opens a file that may run code")
    return ["open", str(path)] if darwin else ["xdg-open", str(path)]


def launch(argv: list[str]) -> None:
    """Start `argv` detached from the server, its output discarded; the person sees the application, not loom."""
    subprocess.Popen(
        argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
    )
