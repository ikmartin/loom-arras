"""The project's files over a running `loom serve` (plan 0.22.7): sandboxed on the viewer's origin at `/_files/`, an HTML page on the frames origin with the bridge and nothing of loom's, opening an application on the person's click, and a Markdown edit published without a scan."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import PATIENCE, json_of, ok
from tests.unit.render._serve import get, post

PAGE = '<!doctype html><title>p</title><body><h1 id="a">A</h1><a href="quilt:dm-0003">x</a></body>\n'


def put(q: Path, rel: str, text: str | bytes = "x") -> Path:
    p = q / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def served(tmp_path: Path, serve) -> tuple[Any, Path, str]:  # type: ignore[no-untyped-def]
    """`loom serve` over a demo holding a page, a hidden file and an ignored one; the server, the quilt and the frames origin."""
    from tests.unit._quilts import demo

    q = demo(tmp_path)
    put(q, "notes/page.html", PAGE)
    put(q, "notes/a.md", "# A\n")
    put(q, ".hidden/s.txt")
    put(q, "scratch/s.txt")
    put(q, ".gitignore", "scratch/\n")
    s = serve(q)
    frames = json.loads(get(s.url + "_api")[2])["frames"]
    return s, q, frames


def test_a_shown_file_is_served_sandboxed_on_the_viewers_origin(served) -> None:  # type: ignore[no-untyped-def]
    s, _, _ = served
    status, headers, body = get(s.url + "_files/notes/page.html")
    assert status == 200 and body.decode() == PAGE
    assert headers["Content-Security-Policy"] == "sandbox" and headers["X-Content-Type-Options"] == "nosniff"
    for rel in ("_files/.hidden/s.txt", "_files/scratch/s.txt", "_files/%2e%2e/outside.txt", "_files/.loom/state.toml"):
        assert get(s.url + rel)[0] == 404, rel


def test_an_html_page_runs_on_the_frames_origin_with_the_bridge_and_nothing_of_looms(served) -> None:  # type: ignore[no-untyped-def]
    """Its own origin, so scripts and embedded players work, and never the viewer's: no `/_api`, no build, no store, no hidden file, only its own host, and the write API refuses it."""
    s, _, frames = served
    viewer = s.url.rstrip("/")
    status, headers, body = get(frames + "/notes/page.html")
    assert status == 200 and "Content-Security-Policy" not in headers and headers["X-Content-Type-Options"] == "nosniff"
    page = body.decode()
    assert page.index("parent.postMessage") < page.index("</body>") and json.dumps(viewer) in page
    other = viewer.replace("127.0.0.1", "localhost")
    assert json.dumps(other) in get(frames + "/notes/page.html?loom-viewer=" + other)[2].decode()
    assert "evil" not in get(frames + "/notes/page.html?loom-viewer=http://evil.example")[2].decode()
    assert get(frames + "/notes/a.md")[2] == b"# A\n"
    for rel in ("/_api", "/build/manifest.json", "/_files/notes/a.md", "/.hidden/s.txt", "/scratch/s.txt", "/"):
        assert get(frames + rel)[0] == 404, rel
    port = frames.rsplit(":", 1)[1]
    assert get(frames + "/notes/page.html", {"Host": f"rebound.example:{port}"})[0] == 404
    assert get(s.url + "_api", {"Origin": frames})[0] == 403
    import urllib.error
    import urllib.request

    with pytest.raises(urllib.error.HTTPError) as refused:
        urllib.request.urlopen(
            urllib.request.Request(frames + "/_api/here", data=b"{}", method="POST"), timeout=PATIENCE
        )
    assert refused.value.code == 501


def test_a_page_can_list_the_shown_files_and_nothing_else(served) -> None:  # type: ignore[no-untyped-def]
    """So a page finds what the project holds, new files included, without being told their names."""
    s, q, frames = served
    status, headers, body = get(frames + "/.loom/files.json")
    assert status == 200 and headers["Content-Type"] == "application/json"
    files = json.loads(body)["files"]
    assert files == sorted(files) and {"notes/page.html", "notes/a.md"} <= set(files)
    assert not [f for f in files if f.startswith((".hidden/", "scratch/", ".loom/"))]
    assert get(frames + "/.loom/state.toml")[0] == 404, "the one address under .loom it answers"
    port = frames.rsplit(":", 1)[1]
    assert get(frames + "/.loom/files.json", {"Host": f"rebound.example:{port}"})[0] == 404
    put(q, "notes/new.md", "# New\n")
    assert "notes/new.md" in json.loads(get(frames + "/.loom/files.json")[2])["files"]


def test_a_tick_publishes_from_the_last_scan(served) -> None:  # type: ignore[no-untyped-def]
    from loom.tasks import items

    s, q, _ = served
    p = put(q, "notes/b.md", "- [ ] one\n")
    deadline = time.time() + PATIENCE
    while time.time() < deadline:
        m = json.loads(get(s.url + "build/manifest.json")[2])
        if any(f["path"] == "notes/b.md" for f in m["files"]):
            break
        time.sleep(0.05)
    scan = s.last_report.result
    task = items(p.read_text(encoding="utf-8"))[0].id
    assert post(s.url + "_api/file-tick", {"path": "notes/b.md", "task": task, "done": True})[0] == 200
    assert s.last_report.result is scan
    assert p.read_text(encoding="utf-8") == "- [x] one\n"


def test_open_is_the_persons_click_and_never_runs_code(served, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    from loom import files

    if not files.can_open():
        pytest.skip("loom opens applications on macOS and Linux")
    s, q, _ = served
    launched: list[list[str]] = []
    monkeypatch.setattr(files, "launch", launched.append)
    put(q, "deck.apkg", b"PK")
    put(q, "run.command", "#!/bin/sh\n")
    assert "open" in json.loads(get(s.url + "_api")[2])["capabilities"]
    builds = s.builds
    assert post(s.url + "_api/open", {"app": "Anki"}) == (200, {"ok": True, "result": "opened", "opened": "Anki"})
    assert post(s.url + "_api/open", {"file": "deck.apkg"})[0] == 200
    assert [a[-1] for a in launched] == ["Anki", str((q / "deck.apkg").resolve())]
    assert s.builds == builds, "opening changes nothing the manifest shows"
    for body, status, code in [
        ({"file": "run.command"}, 400, "not-openable"),
        ({"file": ".loom/state.toml"}, 404, "no-such-file"),
        ({"app": "Anki", "file": "deck.apkg"}, 400, "bad-request"),
        ({"app": "--args"}, 400, "bad-app"),
    ]:
        got = post(s.url + "_api/open", body)
        assert (got[0], got[1]["error"]["code"]) == (status, code), body
    assert post(s.url + "_api/open", {"app": "Anki"}, token="")[0] == 403
    assert len(launched) == 2


def test_a_markdown_edit_republishes_without_a_scan(served) -> None:  # type: ignore[no-untyped-def]
    """A file the scan never reads is published from the last scan: the body is new, the scan the same object."""
    s, q, _ = served
    time.sleep(0.3)
    before, scan = s.builds, s.last_report.result
    put(q, "notes/a.md", "# A changed\n")
    deadline = time.time() + PATIENCE
    while s.builds == before and time.time() < deadline:
        time.sleep(0.05)
    assert s.builds > before and s.last_report.result is scan
    m = json.loads(get(s.url + "build/manifest.json")[2])
    body = next(f["body"] for f in m["files"] if f["path"] == "notes/a.md")
    assert get(s.url + "build/" + body)[2].decode().startswith('<h1 id="a-changed">')


def test_a_file_the_viewer_shows_is_linked_by_its_path_and_a_place_in_it(served) -> None:  # type: ignore[no-untyped-def]
    from loom.cli._quilt import open_scan
    from loom.links import LinkError, resolve

    _, q, _ = served
    put(q, "notes/b.pdf", b"%PDF-1.4")
    put(q, "notes/fig.png", b"\x89PNG")
    result = open_scan(str(q))
    got = resolve(result, q, "quilt:notes/a.md#a")
    assert (got.kind, got.key, got.place) == ("file", "notes/a.md", "a")
    assert resolve(result, q, "quilt:notes/b.pdf#page=2").place == "page=2"
    assert resolve(result, q, "quilt:notes/page.html#anywhere").kind == "file"
    assert resolve(result, q, "quilt:notes/fig.png").kind == "file"
    for href, why in [
        ("quilt:notes/a.md#nope", "no heading nope"),
        ("quilt:notes/b.pdf#2", "page=N"),
        ("quilt:notes/fig.png#x", "linked whole"),
        ("quilt:.hidden/s.txt", "hidden"),
        ("quilt:scratch/s.txt", "hidden"),
    ]:
        with pytest.raises(LinkError, match=why):
            resolve(result, q, href)
    assert ok("link", "notes/a.md", "--at", "a", cwd=q).stdout.strip() == "[](quilt:notes/a.md#a)"


def test_loom_here_names_a_file_and_the_words_selected_in_it(served) -> None:  # type: ignore[no-untyped-def]
    s, q, _ = served
    place = {
        "route": "reading",
        "item": {"kind": "file", "id": "notes/page.html", "place": "a"},
        "selection": {"file": "notes/page.html", "text": "A"},
    }
    assert post(s.url + "_api/here", place) == (200, {"ok": True})
    looking = json_of("here", "--json", cwd=q)["looking"]
    assert looking["item"] == {
        "kind": "file",
        "path": "notes/page.html",
        "name": "notes/page.html",
        "link": "quilt:notes/page.html#a",
    }
    assert looking["selection"]["text"] == "A" and looking["selection"]["path"] == "notes/page.html"


def test_a_files_route_in_the_viewer_is_the_app_whatever_its_suffix(served) -> None:  # type: ignore[no-untyped-def]
    """`/file/notes/fig.png` names a file item and ends in an asset's suffix; it is answered with the app, while a missing asset elsewhere is still a 404."""
    s, _, _ = served
    status, _, body = get(s.url + "file/notes/fig.png")
    assert status == 200 and b"<title>arras</title>" in body
    assert get(s.url + "missing.png")[0] == 404
