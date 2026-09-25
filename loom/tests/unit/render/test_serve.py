"""loom serve: static routes with the SPA fallback, ETag on the manifest, the fetched-work store, republish on change, no outgoing requests. The write API is test_write_api.py."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from tests.helpers import ok, refused
from tests.unit._quilts import demo
from tests.unit.render._serve import get


def test_serve_static_routes(session) -> None:  # type: ignore[no-untyped-def]
    s, d = session
    status, headers, body = get(s.url)
    assert status == 200 and b"<title>arras</title>" in body
    status, _, body = get(s.url + "node/dm-0003")
    assert status == 200 and b"<title>arras</title>" in body  # SPA fallback
    status, _, body = get(s.url + "_app/x.js")
    assert status == 200 and body == b"console.log(1)"
    status, headers, body = get(s.url + "build/manifest.json")
    assert status == 200 and headers["Content-Type"].startswith("application/json")
    manifest = json.loads(body)
    assert manifest["corpus"]["name"] == "The loom demo"  # [quilt] name, not the directory
    etag = headers["ETag"]
    status, _, _ = get(s.url + "build/manifest.json", {"If-None-Match": etag})
    assert status == 304
    status, _, body = get(s.url + "build/fragments/nodes/dm-0003.html")
    assert status == 200 and b'data-id="dm-0003"' in body
    assert get(s.url + "build/../config.toml")[0] == 404
    assert get(s.url + "missing.css")[0] == 404
    assert get(s.url + "_api")[0] == 200  # the write API answers here now; 404 is what a read-only publisher sends


def test_serve_republishes_on_change(session) -> None:  # type: ignore[no-untyped-def]
    s, d = session
    _, headers, _ = get(s.url + "build/manifest.json")
    before = headers["ETag"]
    node = d / "nodes" / "dm-0002.tex"
    time.sleep(0.3)
    node.write_text(node.read_text().replace("[Orbits]", "[Orbits, revised]"))
    os.utime(node, None)
    deadline = time.time() + 6
    after = before
    while time.time() < deadline:
        _, headers, body = get(s.url + "build/manifest.json")
        after = headers["ETag"]
        if after != before:
            break
        time.sleep(0.2)
    assert after != before, "manifest did not change within the deadline"
    assert json.loads(body)["nodes"]["dm-0002"]["title"] == "Orbits, revised"
    deadline = time.time() + 3
    while s.builds < 2 and time.time() < deadline:  # the counter steps after the publish the ETag already shows
        time.sleep(0.1)
    assert s.builds >= 2


def test_serve_no_notification_sent(session, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    s, d = session
    calls: list[str] = []
    import http.client

    original = http.client.HTTPConnection.request

    def spy(self, method, url, *a, **k):  # type: ignore[no-untyped-def]
        if self.host not in ("127.0.0.1", "localhost"):
            calls.append(f"{method} {self.host}{url}")
        return original(self, method, url, *a, **k)

    monkeypatch.setattr(http.client.HTTPConnection, "request", spy)
    s.rebuild([d / "nodes" / "dm-0001.tex"])
    assert calls == []


def test_serve_refuses_a_loom_arras_bundle_that_names_no_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The variable is the person's choice of viewer: serving another one instead would hide the mistake, and a suite pointed at a fresh build would pass against the old one."""
    d = tmp_path / "demo"
    ok("init", str(d), "--demo")
    monkeypatch.setenv("LOOM_ARRAS_BUNDLE", str(tmp_path / "nowhere"))
    refused("serve", "--port", "0", cwd=d, code=2, match=f"LOOM_ARRAS_BUNDLE={tmp_path / 'nowhere'} is not a directory")


def test_serve_exit_2_without_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = demo(tmp_path)
    monkeypatch.delenv("LOOM_ARRAS_BUNDLE", raising=False)
    monkeypatch.setattr("loom.render.serve.find_bundle", lambda: None)
    refused("serve", "--port", "0", cwd=d, code=2, match="bundle")


def test_serve_spa_fallback_for_dotted_routes(session) -> None:  # type: ignore[no-untyped-def]
    s, _d = session
    status, _h, body = get(s.url + "node/Man12-thm-4.1")
    assert status == 200 and b"<!doctype html>" in body[:200].lower()  # a key with dots is a route, not a file
    status, _h, _b = get(s.url + "_app/immutable/missing.js")
    assert status == 404  # a missing asset stays a 404
    status, _h, _b = get(s.url + "favicon.png")
    assert status == 404  # so does a file-typed path the bundle lacks, outside _app/


def test_serve_offers_a_works_fetched_artifacts(session) -> None:  # type: ignore[no-untyped-def]
    """The viewer opens a reference at the place a comment points to, so the server offers what was fetched -- the first thing it serves that it did not generate (DR-110). Localhost, read only, and confined to the store by the same prefix check the build tree gets."""
    s, d = session
    home = d / "digests" / "storage" / "arxiv" / "0805.2065v2"
    home.mkdir(parents=True, exist_ok=True)
    (home / "paper.pdf").write_bytes(b"%PDF-1.4\nfetched\n")

    status, headers, body = get(s.url + "digests/storage/arxiv/0805.2065v2/paper.pdf")
    assert status == 200 and body.startswith(b"%PDF") and headers["Content-Type"] == "application/pdf"

    status, _, _ = get(s.url + "digests/storage/arxiv/0805.2065v2/absent.pdf")
    assert status == 404  # a missing artifact is a 404, never the app shell

    status, _, _ = get(s.url + "digests/storage/../../config.toml")
    assert status == 404  # nothing outside the store is reachable through it


def test_the_watcher_watches_what_the_write_api_writes(tmp_path: Path) -> None:
    """A write through `loom serve`'s own API appended to the log and the page it came from never changed: the watcher's directory list still said `comments/`, the name the log replaced in 0.10, and `.jsonl` was not a watched suffix (DR-174)."""
    from loom.render.watch import snapshot

    q = tmp_path / "q"
    (q / "annotations").mkdir(parents=True)
    (q / "nodes").mkdir()
    (q / "config.toml").write_text('[quilt]\nname = "q"\n', encoding="utf-8")
    (q / "annotations" / "log.jsonl").write_text('{"event": "created"}\n', encoding="utf-8")
    (q / "reference-notes.jsonl").write_text('{"work": "doi:10/x"}\n', encoding="utf-8")
    (q / "nodes" / "n.tex").write_text("\\begin{lemma}\\end{lemma}\n", encoding="utf-8")

    watched = {p.relative_to(q).as_posix() for p in snapshot(q)}
    assert "annotations/log.jsonl" in watched
    assert "reference-notes.jsonl" in watched
    assert {"config.toml", "nodes/n.tex"} <= watched


def test_the_watcher_does_not_chase_its_own_build(session, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    """Every build rewrites `.loom/last-seen.json`, so a watcher that watches it rebuilds once a second for ever after the first change: the manifest gets a new `generated` each time, and the viewer, which re-renders on a new hash, closed every comment box a second after it was opened."""
    from loom.render import watch
    from loom.render.watch import snapshot

    polls = [0]

    def counted(root: Path) -> dict[Path, float]:
        polls[0] += 1
        return snapshot(root)

    monkeypatch.setattr(watch, "snapshot", counted)
    s, d = session
    assert not [p for p in snapshot(d) if p.name == "last-seen.json"]

    node = d / "nodes" / "dm-0002.tex"
    time.sleep(0.3)
    node.write_text(node.read_text().replace("[Orbits]", "[Orbits, again]"))
    deadline = time.time() + 6
    while s.builds < 2 and time.time() < deadline:
        time.sleep(0.1)
    assert s.builds >= 2, "the change was not picked up"
    settled, seen = s.builds, polls[0]
    # a watcher that chased its own build would rebuild on the first poll after it, so three polls settle it
    deadline = time.time() + 6
    while polls[0] < seen + 3 and time.time() < deadline:
        time.sleep(0.05)
    assert polls[0] >= seen + 3, "the watcher stopped polling"
    assert s.builds == settled


def test_a_link_into_the_running_viewer_is_offered_only_while_one_is_running(tmp_path: Path) -> None:
    """`serve.json` outlives the process that wrote it, so a command that printed a link from the file alone would send its reader to a tab that never loads (plan 0.13 §9, the `open:` line)."""
    import json as _json

    from loom.render.serve import SERVE_JSON, open_url, write_serve_json

    root = tmp_path / "quilt"
    root.mkdir()
    assert open_url(root) == "", "nothing has ever served this quilt"

    write_serve_json(root, 8791)
    # this process wrote it and this process is alive, which is the case the check is meant to pass
    assert open_url(root) == "http://127.0.0.1:8791/"
    assert open_url(root, "library/Bellamy19?page=2") == "http://127.0.0.1:8791/library/Bellamy19?page=2"

    # a pid nothing holds: the file is stale and the honest answer is no link at all
    p = root / SERVE_JSON
    data = _json.loads(p.read_text())
    data["pid"] = 2**22  # above every pid_max this runs on
    p.write_text(_json.dumps(data))
    assert open_url(root) == ""
