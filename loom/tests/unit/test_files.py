"""The project's files as the viewer shows them (plan 0.22.7): which are shown, what kind each is, the bodies drawn for Markdown files and notebooks, the front door, and what `loom serve` will open in another application."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers import json_of, ok
from tests.unit._quilts import demo


@pytest.fixture
def q(tmp_path: Path) -> Path:
    return demo(tmp_path)


def put(q: Path, rel: str, text: str | bytes = "x") -> Path:
    p = q / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    return p


def test_dot_paths_tools_and_what_the_gitignore_files_ignore_are_hidden(q: Path) -> None:
    """One predicate for every reader: a dot segment, a tool's directory, and the quilt's `.gitignore` files read in every directory, the last match winning and a deeper file's rules coming later."""
    from loom.files import Shown
    from loom.scan.quilt import load_quilt

    put(q, ".gitignore", "*.log\n!keep.log\nnotes/scratch/\n")
    put(q, "notes/.gitignore", "secret.md\n")
    for rel in (
        "notes/a.md",
        "notes/secret.md",
        "notes/scratch/s.txt",
        "keep.log",
        "other.log",
        ".hidden/x.md",
        "node_modules/m.js",
        "notes/sub/b.md",
    ):
        put(q, rel)
    shown = Shown.of(load_quilt(q))
    walked = set(shown.walk())
    for rel in ("notes/a.md", "keep.log", "notes/sub/b.md", "README.md", "drafting/main.tex"):
        assert rel in walked and shown.is_shown(rel), rel
    for rel in (
        "notes/secret.md",
        "notes/scratch/s.txt",
        "other.log",
        ".hidden/x.md",
        "node_modules/m.js",
        ".gitignore",
        ".loom/state.toml",
        "../outside.md",
        "/etc/passwd",
    ):
        assert rel not in walked and not shown.is_shown(rel), rel


def test_each_file_has_one_kind(q: Path) -> None:
    from loom.files import kind_of

    put(q, "notes/a.md")
    put(q, "notes/p.html")
    put(q, "fig.PNG")
    put(q, "run.ipynb", "{}")
    put(q, "data.csv", "a,b\n1,2\n")
    put(q, "deck.apkg", b"PK\x03\x04\x00\x00")
    masters = {"drafting/main.tex"}
    kinds = {
        rel: kind_of(q, rel, masters)
        for rel in (
            "notes/a.md",
            "notes/p.html",
            "fig.PNG",
            "run.ipynb",
            "data.csv",
            "deck.apkg",
            "drafting/main.tex",
            "drafting/nodes/dm-0001.tex",
        )
    }
    assert kinds == {
        "notes/a.md": "markdown",
        "notes/p.html": "html",
        "fig.PNG": "image",
        "run.ipynb": "notebook",
        "data.csv": "text",
        "deck.apkg": "other",
        "drafting/main.tex": "document",
        "drafting/nodes/dm-0001.tex": "tex",
    }


def test_a_markdown_file_is_drawn_with_ids_on_its_headings_and_its_links_resolved() -> None:
    """A relative link to a shown file becomes the `quilt:` link the viewer follows, a document's by its name; a relative image is read from `/_files/`."""
    from loom.files import headings, render_file_markdown

    kinds = {
        "notes/day2.md": "markdown",
        "notes/fig.png": "image",
        "paper/main.tex": "document",
        "notes/a b.md": "markdown",
    }
    text = (
        "# Setup\n\nRead [day 2](day2.md#plan), [the paper](../paper/main.tex), [spaced](a%20b.md), "
        "[gone](nothing.md) and [Anki](app:Anki), with $x_i y_i$.\n\n![a figure](fig.png)\n\n## Setup\n"
    )
    body = render_file_markdown(text, "notes/day1.md", kinds)
    assert headings(body) == {"setup", "setup-1"}
    assert 'href="quilt:notes/day2.md#plan"' in body
    assert 'href="quilt:paper/main.tex"' in body
    assert 'href="quilt:notes/a%20b.md"' in body
    assert 'href="nothing.md"' in body and 'href="app:Anki"' in body
    assert 'src="/_files/notes/fig.png"' in body
    assert r"\(x_i y_i\)" in body


def test_a_notebook_is_drawn_read_only_from_its_saved_cells() -> None:
    """Loom runs nothing: code and its saved outputs are drawn as saved, an image as an image, and an HTML output by its plain form or a note, never as HTML in the viewer."""
    from loom.files import headings, render_notebook

    cells = [
        {"cell_type": "markdown", "source": ["## Setup\n", "Some $a_i$."]},
        {
            "cell_type": "code",
            "execution_count": 3,
            "source": ["print(1 < 2)"],
            "outputs": [
                {"output_type": "stream", "name": "stdout", "text": ["True\n"]},
                {"output_type": "display_data", "data": {"image/png": "iVBORw0KGgo=\n"}},
                {"output_type": "execute_result", "data": {"text/html": ["<b>t</b>"], "text/plain": ["frame"]}},
                {"output_type": "display_data", "data": {"text/html": ["<script>x()</script>"]}},
                {"output_type": "error", "ename": "E", "evalue": "v", "traceback": ["\x1b[31mBoom\x1b[0m"]},
            ],
        },
        {"cell_type": "markdown", "source": "## Setup"},
    ]
    body = render_notebook(json.dumps({"nbformat": 4, "cells": cells, "metadata": {}}), "run.ipynb", {})
    assert headings(body) == {"setup", "setup-1"}
    assert "[3]" in body and "print(1 &lt; 2)" in body and ">True\n<" in body
    assert 'src="data:image/png;base64,iVBORw0KGgo="' in body
    assert ">frame<" in body and "<b>t</b>" not in body and "<script>" not in body
    assert "An HTML output, not drawn." in body
    assert "Boom" in body and "\x1b" not in body
    assert "nbformat 4" in render_notebook(json.dumps({"nbformat": 3, "worksheets": []}), "old.ipynb", {})
    assert "not valid JSON" in render_notebook("{", "bad.ipynb", {})


def test_the_manifest_lists_the_shown_files_and_the_front_door(q: Path) -> None:
    """Each shown file with its kind and size, a drawn body published beside the fragments, and `corpus.home`: `[quilt] home` when it names a shown file, else the root README.md; a setting naming nothing is a warning."""
    put(q, "notes/a.md", "# A\n")
    put(q, ".loom/copies/hidden.md", "# no\n")
    ok("build", cwd=q)
    built = q / ".loom/build"
    m = json.loads((built / "manifest.json").read_text())
    by = {f["path"]: f for f in m["files"]}
    assert by["notes/a.md"]["kind"] == "markdown" and by["notes/a.md"]["bytes"] == 4
    assert (built / by["notes/a.md"]["body"]).read_text().startswith('<h1 id="a">A</h1>')
    assert by["drafting/main.tex"]["kind"] == "document" and "body" not in by["drafting/main.tex"]
    assert not [p for p in by if p.startswith(".")]
    assert m["corpus"]["home"] == "README.md"

    cfg = q / "config.toml"
    cfg.write_text(cfg.read_text().replace("[quilt]\n", '[quilt]\nhome = "notes/a.md"\n', 1))
    ok("build", cwd=q)
    assert json.loads((built / "manifest.json").read_text())["corpus"]["home"] == "notes/a.md"

    cfg.write_text(cfg.read_text().replace('home = "notes/a.md"', 'home = "notes/gone.md"'))
    ok("build", cwd=q)
    assert json.loads((built / "manifest.json").read_text())["corpus"]["home"] == "README.md"
    codes = [d["code"] for d in json_of("lint", "--json", cwd=q)["diagnostics"]]
    assert "loom:home-missing" in codes


def test_a_file_no_agent_may_write_says_what_keeps_agents_out(q: Path) -> None:
    """`denied` from the one predicate loom's commands ask, so the viewer never matches the deny list: the list's entry as written, or a protection that holds whatever it says; null on a file agents may write, so a viewer never reads silence as permission."""
    put(q, "notes/a.md", "# A\n")
    cfg = q / "config.toml"
    text = cfg.read_text()
    cfg.write_text(
        text.replace("[agents]\n", '[agents]\ndeny = ["drafting/"]\n', 1)
        if "[agents]\n" in text
        else text + '\n[agents]\ndeny = ["drafting/"]\n'
    )
    ok("build", cwd=q)
    by = {f["path"]: f for f in json.loads((q / ".loom/build/manifest.json").read_text())["files"]}
    assert by["drafting/main.tex"]["denied"] == {"by": "drafting/", "always": False}
    assert by["config.toml"]["denied"] == {"by": "config.toml", "always": True}
    assert by["notes/a.md"]["denied"] is None and by["README.md"]["denied"] is None


def test_loom_opens_an_application_or_a_document_and_never_a_file_that_runs_code(q: Path) -> None:
    """An application by its name, a document by an allowlist of suffixes with no executable bit, and nothing hidden; a click never runs code an agent wrote."""
    from loom.files import OpenRefused, Shown, open_command
    from loom.scan.quilt import load_quilt

    put(q, "deck.apkg", b"PK")
    put(q, "run.command", "#!/bin/sh\n")
    put(q, "data.csv", "a\n").chmod(0o755)
    put(q, ".loom/x.apkg", b"PK")
    shown = Shown.of(load_quilt(q))
    assert open_command(shown, app="Anki", platform="darwin") == ["open", "-a", "Anki"]
    assert open_command(shown, app="Anki", platform="linux") == ["gtk-launch", "Anki"]
    assert open_command(shown, file="deck.apkg", platform="darwin") == ["open", str((q / "deck.apkg").resolve())]
    assert open_command(shown, file="deck.apkg", platform="linux")[0] == "xdg-open"
    for kwargs, code in [
        ({"app": "-a Terminal"}, "bad-app"),
        ({"app": "../Evil"}, "bad-app"),
        ({"file": "run.command"}, "not-openable"),
        ({"file": "data.csv"}, "not-openable"),
        ({"file": ".loom/x.apkg"}, "no-such-file"),
        ({"file": "nothing.apkg"}, "no-such-file"),
    ]:
        with pytest.raises(OpenRefused) as got:
            open_command(shown, platform="darwin", **kwargs)  # type: ignore[arg-type]
        assert got.value.code == code, kwargs
    with pytest.raises(OpenRefused) as got:
        open_command(shown, app="Anki", platform="win32")
    assert got.value.code == "unsupported"
