"""loom serve: static routes with the SPA fallback, ETag on the manifest, republish on change, no outgoing requests."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from click.testing import CliRunner

from loom.cli import main
from loom.render.serve import ServeSession
from loom.scan.quilt import load_quilt


def demo(tmp_path: Path) -> Path:
    old = os.getcwd()
    try:
        os.chdir(tmp_path)
        r = CliRunner().invoke(main, ["init", str(tmp_path / "demo"), "--demo"])
    finally:
        os.chdir(old)
    assert r.exit_code == 0, r.output
    return tmp_path / "demo"


def fake_bundle(tmp_path: Path) -> Path:
    b = tmp_path / "bundle"
    (b / "_app").mkdir(parents=True)
    (b / "index.html").write_text("<!doctype html><title>arras</title><div id=app></div>")
    (b / "_app" / "x.js").write_text("console.log(1)")
    return b


def get(url: str, headers: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b""


@pytest.fixture
def session(tmp_path: Path):  # type: ignore[no-untyped-def]
    d = demo(tmp_path)
    s = ServeSession(load_quilt(d), fake_bundle(tmp_path), port=0, compile_masters=False, interval=0.2)
    s.start()
    yield s, d
    s.stop()


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


def test_serve_exit_2_without_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    d = demo(tmp_path)
    monkeypatch.delenv("LOOM_ARRAS_BUNDLE", raising=False)
    monkeypatch.setattr("loom.render.serve.find_bundle", lambda: None)
    old = os.getcwd()
    try:
        os.chdir(d)
        r = CliRunner().invoke(main, ["serve", "--port", "0"])
    finally:
        os.chdir(old)
    assert r.exit_code == 2 and "bundle" in r.output


def test_serve_spa_fallback_for_dotted_routes(session) -> None:  # type: ignore[no-untyped-def]
    s, _d = session
    status, _h, body = get(s.url + "node/Man12-thm-4.1")
    assert status == 200 and b"<!doctype html>" in body[:200].lower()  # a key with dots is a route, not a file
    status, _h, _b = get(s.url + "_app/immutable/missing.js")
    assert status == 404  # a missing asset stays a 404
    status, _h, _b = get(s.url + "favicon.png")
    assert status in (200, 404)


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
    assert status in (400, 404)  # nothing outside the store is reachable through it


def post(url: str, body: dict, token: str | None = None):  # type: ignore[no-untyped-def]
    """A write, carrying the token the running server minted. A caller that omits it is refused, which is the point."""
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is None:
        # the same place the viewer gets it: the discovery response this publisher serves
        base = url.split("/_api/")[0] + "/_api"
        token = json.loads(urllib.request.urlopen(base, timeout=5).read()).get("token", "")
    if token:
        headers["X-Loom-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def test_the_write_api_binds_to_loopback_only(session) -> None:  # type: ignore[no-untyped-def]
    """specs/write-api.md §3 has no authentication and says so, resting entirely on the socket never leaving this machine. That was an assumption until this test."""
    s, _ = session
    assert s.httpd is not None
    assert s.httpd.server_address[0] == "127.0.0.1"


def test_discovery_lists_what_this_publisher_serves(session) -> None:  # type: ignore[no-untyped-def]
    s, _ = session
    status, body = get(s.url + "/_api")[0], json.loads(get(s.url + "/_api")[2])
    assert status == 200
    assert body["write_api"] == 1
    assert "comment" in body["capabilities"] and "discard" in body["capabilities"]
    # an endpoint outside the list is a 404, which is what lets a viewer hide the affordance
    assert post(s.url + "/_api/accept", {"keys": ["dm-0003"]})[0] == 404


def test_a_comment_written_over_http_is_the_same_comment(session) -> None:  # type: ignore[no-untyped-def]
    """One implementation of what a comment is: the endpoint calls the function the CLI calls, so the two cannot drift."""
    s, d = session
    status, body = post(
        s.url + "/_api/comment",
        {
            "target": "dm-0003",
            "message": "Written from the viewer.",
            "kind": "objection",
            "severity": "minor",
            "author": "A Reader",
        },
    )
    assert status == 200, body
    log = (d / "annotations" / "log.jsonl").read_text(encoding="utf-8").splitlines()
    written = [json.loads(x) for x in log if x.strip()]
    mine = [e for e in written if e.get("body") == "Written from the viewer."]
    assert len(mine) == 1
    assert mine[0]["kind"] == "human" and mine[0]["author"] == "A Reader"
    assert mine[0]["severity"] == "minor"

    # and it can be answered, restated and withdrawn over the same surface
    ann = mine[0]["id"]
    assert post(s.url + "/_api/reply", {"annotation": ann, "message": "Noted.", "author": "A Reader"})[0] == 200
    assert post(s.url + "/_api/edit", {"annotation": ann, "message": "Restated.", "author": "A Reader"})[0] == 200
    assert post(s.url + "/_api/discard", {"annotation": ann, "reason": "mine", "author": "A Reader"})[0] == 200
    events = [json.loads(x) for x in (d / "annotations" / "log.jsonl").read_text().splitlines() if x.strip()]
    assert {e["event"] for e in events if e.get("id") == ann} >= {"created", "edited", "discarded"}


def test_a_refused_write_answers_rather_than_dying(session) -> None:  # type: ignore[no-untyped-def]
    s, _ = session
    status, body = post(s.url + "/_api/comment", {"message": "no target"})
    assert status == 400 and body["error"]["code"] == "missing-field"
    status, body = post(s.url + "/_api/comment", {"target": "nope-9999", "message": "x"})
    assert status in (400, 404) and "error" in body
    status, body = post(s.url + "/_api/discard", {"annotation": "a-1999-01-01-0001"})
    assert status in (400, 404) and "error" in body


def test_a_citation_suggestion_is_accepted_or_rejected_over_the_api(session) -> None:  # type: ignore[no-untyped-def]
    """0.10 shipped reference notes as a command only; this is where they become something a reader can answer."""
    s, d = session
    _, made = post(
        s.url + "/_api/comment",
        {"target": "dm-0003", "message": "Cite Manolache, Prop 3.2.", "kind": "citation", "author": "A Reader"},
    )
    ann = [
        json.loads(x)
        for x in (d / "annotations" / "log.jsonl").read_text().splitlines()
        if x.strip() and "Manolache" in x
    ][0]["id"]

    status, body = post(s.url + "/_api/refs-note", {"annotation": ann, "decision": "accept", "author": "A Reader"})
    assert status == 200, body
    notes = [json.loads(x) for x in (d / "reference-notes.jsonl").read_text().splitlines() if x.strip()]
    assert notes[-1]["for"] == ["dm-0003"]
    assert notes[-1]["identifier"] == {"verified": False}  # a breadcrumb, never a second source of identity truth
    # accepting also closes the finding, so the same suggestion is not answered twice
    events = [json.loads(x) for x in (d / "annotations" / "log.jsonl").read_text().splitlines() if x.strip()]
    assert any(e.get("id") == ann and e["event"] == "resolved" for e in events)

    status, body = post(s.url + "/_api/refs-note", {"annotation": ann, "decision": "sideways"})
    assert status == 400 and body["error"]["code"] == "bad-field"


def test_rejecting_a_citation_writes_no_breadcrumb(session) -> None:  # type: ignore[no-untyped-def]
    s, d = session
    post(
        s.url + "/_api/comment",
        {"target": "dm-0002", "message": "Cite something else.", "kind": "citation", "author": "R"},
    )
    ann = [
        json.loads(x)
        for x in (d / "annotations" / "log.jsonl").read_text().splitlines()
        if x.strip() and "something else" in x
    ][0]["id"]
    before = (d / "reference-notes.jsonl").read_text() if (d / "reference-notes.jsonl").exists() else ""
    status, _ = post(
        s.url + "/_api/refs-note", {"annotation": ann, "decision": "reject", "reason": "already cited", "author": "R"}
    )
    assert status == 200
    after = (d / "reference-notes.jsonl").read_text() if (d / "reference-notes.jsonl").exists() else ""
    assert after == before  # the reason rides on the resolve event; nothing is filed for a work nobody wanted


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


def test_the_watcher_does_not_chase_its_own_build(session) -> None:  # type: ignore[no-untyped-def]
    """Every build rewrites `.loom/last-seen.json`, so a watcher that watches it rebuilds once a second for ever after the first change: the manifest gets a new `generated` each time, and the viewer, which re-renders on a new hash, closed every comment box a second after it was opened."""
    from loom.render.watch import snapshot

    s, d = session
    assert not [p for p in snapshot(d) if p.name == "last-seen.json"]

    node = d / "nodes" / "dm-0002.tex"
    time.sleep(0.3)
    node.write_text(node.read_text().replace("[Orbits]", "[Orbits, again]"))
    deadline = time.time() + 6
    while s.builds < 2 and time.time() < deadline:
        time.sleep(0.1)
    assert s.builds >= 2, "the change was not picked up"
    settled = s.builds
    time.sleep(2)  # ten watcher intervals with nothing changing
    assert s.builds == settled


def test_a_write_without_the_token_is_refused_over_the_wire(session) -> None:  # type: ignore[no-untyped-def]
    """A browser blocks a cross-origin response and never the request, so any page the author happens to be reading could otherwise POST into their quilt (plan 0.13 §8)."""
    s, _ = session
    body = {"target": "sy-0001", "message": "from somewhere else", "author": "Nobody"}
    status, said = post(s.url + "_api/comment", body, token="")
    assert status == 403 and "X-Loom-Token" in said["error"]["message"]

    # and the token is served where the viewer reads it, so a legitimate write is not made harder
    _, _, discovery = get(s.url + "_api")
    assert json.loads(discovery)["token"]
    # carrying it gets past the gate; whether the write itself is well formed is another test's business
    assert post(s.url + "_api/comment", body)[0] != 403


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
