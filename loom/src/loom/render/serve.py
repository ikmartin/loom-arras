"""`loom serve`: one loop with three jobs, watch, serve, compile.

Serves the arras bundle at / (with index.html as the fallback for any path that is not a file of the bundle or an asset, so the viewer's routes work, dots in keys included) and .loom/build/ at /build/. The manifest carries an ETag so the viewer's poll costs nothing while unchanged, and `/_api/stream` says each time a new one is published, so a viewer that listens fetches it at once rather than on its next poll.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import sys
import threading
import time
from collections.abc import Callable
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from loom.arras_bundle import find_bundle
from loom.files import FILES_URL, Shown
from loom.paths import BUILD, SERVE_JSON, STORE_ADDRESS, document_build
from loom.refs.pages import storage_root
from loom.render.build import BuildReport, build
from loom.render.watch import Watcher, scan_unread, snapshot
from loom.scan.quilt import Quilt
from loom.scan.scan import ScanResult
from loom.tex.runner import CompileResult, compile_document, normalise_engine

DEFAULT_PORT = 8791
ASSET_SUFFIXES = {
    ".js",
    ".mjs",
    ".css",
    ".map",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".json",
    ".woff",
    ".woff2",
    ".ttf",
    ".txt",
    ".webmanifest",
}


#: The addresses the server answers loom's files at, fixed wherever the directories behind them sit.
BUILD_URL = "/build/"
STORE_URL = f"/{STORE_ADDRESS}/"
#: How often an idle stream says it is still open, so a proxy or a sleeping laptop does not drop it unseen.
HEARTBEAT = 15.0
#: The headers everything but the viewer's bundle is served with -- `/build/`, `/digests/storage/`, `/_files/` and every JSON answer -- so a page there runs no script and has an opaque origin, never the viewer's: an agent writes the build output and the project's files, and a page that ran as the viewer could read the token and post the author's acts.
CONFINED = {"Content-Security-Policy": "sandbox", "X-Content-Type-Options": "nosniff"}
#: What the frames origin adds to an HTML page so that the page can ask the viewer to open a link and say what is selected in it, and nothing else. `%s` is the viewer's origin, the only window it posts to.
BRIDGE = """<script>(function(){var V=%s;function post(m){try{parent.postMessage(m,V)}catch(e){}}
document.addEventListener('click',function(e){var a=e.target&&e.target.closest?e.target.closest('a[href]'):null;if(!a)return;var h=a.getAttribute('href')||'';
if(/^(quilt|cited|app):/i.test(h)){e.preventDefault();post({loom:'open',href:h});return}
if(/^https?:/i.test(h)&&!a.target){e.preventDefault();window.open(a.href,'_blank','noopener')}},true);
var t;document.addEventListener('selectionchange',function(){clearTimeout(t);t=setTimeout(function(){post({loom:'selection',text:String(window.getSelection()||'').trim().slice(0,4000)})},150)});
window.addEventListener('hashchange',function(){post({loom:'place',hash:decodeURIComponent(location.hash.slice(1))})});})();</script>"""


def from_elsewhere(request: SimpleHTTPRequestHandler) -> str:
    """Why the browser says this request came from a page that is not this server's, or '' when it does not.

    `Origin` comes on a POST and a cross-origin fetch, `null` from a sandboxed page; `Sec-Fetch-Site` on every request a current browser makes, `none` when the person typed the address. A request with neither came from no browser's page, and is answered.
    """
    port = request.server.server_address[1] if isinstance(request.server.server_address, tuple) else 0
    origin = request.headers.get("Origin")
    if origin and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
        return f"this request came from {origin}, which is not this server"
    site = request.headers.get("Sec-Fetch-Site")
    if site and site not in ("same-origin", "none"):
        return f"this request came from a {site} page, which is not this server"
    return ""


class Publications:
    """Every publication the server makes, counted, and how its compiles stand, so `/_api/stream` can say that either changed."""
def addressed_here(request: SimpleHTTPRequestHandler) -> bool:
    """Whether the request's `Host` is this server's own: `127.0.0.1` or `localhost`, at its port.

    A browser sends the name its page was loaded by. A domain pointed at 127.0.0.1 (DNS rebinding) is same-origin with this server as the browser sees it, so `from_elsewhere` finds nothing wrong with its page's requests, and they still name the domain here.
    """
    port = request.server.server_address[1] if isinstance(request.server.server_address, tuple) else 0
    return (request.headers.get("Host") or "").lower() in (f"127.0.0.1:{port}", f"localhost:{port}")



    def __init__(self) -> None:
        self._cond = threading.Condition()
        self.count = 0
        self.compiles = 0
        self.compile_state = b"{}"
        self._closed = False

    def published(self) -> None:
        with self._cond:
            self.count += 1
            self._cond.notify_all()

    def compiled(self, state: bytes) -> None:
        """How the compiles stand now, as one line of JSON."""
        with self._cond:
            self.compiles += 1
            self.compile_state = state
            self._cond.notify_all()

    def close(self) -> None:
        """End every stream: the server is stopping."""
        with self._cond:
            self._closed = True
            self._cond.notify_all()

    def wait(self, seen: tuple[int, int], timeout: float) -> tuple[int, int] | None:
        """The publication and compile counts once either is past `seen`, or as they stand after `timeout`; None once closed."""
        with self._cond:
            self._cond.wait_for(lambda: self._closed or (self.count, self.compiles) != seen, timeout)
            return None if self._closed else (self.count, self.compiles)


def write_serve_json(root: Path, port: int) -> str:
    """Record where this server is listening, and the token a write must carry; return the token.

    Two jobs in one file. A command that wants to print an openable link reads the port and the pid to know whether anything is listening. The **token** is what makes the write API safe to leave running: a browser blocks a cross-origin *response* and never the *request*, so any page the author happens to be reading could otherwise POST into their quilt. A cross-site form post cannot set a custom header, so requiring one closes it. This is CSRF protection and not a login -- it keeps other *pages* out, not other people.
    """
    import os
    import secrets

    token = secrets.token_urlsafe(24)
    p = root / SERVE_JSON
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {
                "port": port,
                "pid": os.getpid(),
                "token": token,
                "url": f"http://127.0.0.1:{port}/",
                # a copied quilt carries the file, and a link it printed would open the other quilt's viewer
                "root": str(Path(root).resolve()),
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    return token


def read_serve_json(root: Path) -> dict[str, object]:
    """What the running server said about itself, or {} when nothing is listening."""
    try:
        data = json.loads((root / SERVE_JSON).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def open_url(root: Path, path: str = "") -> str:
    """A link into the running viewer, or '' when nothing is listening.

    Parameters
    ----------
    root : Path
        The quilt root.
    path : str, default ''
        Where in the viewer to land, without a leading slash; '' is the home page.

    Returns
    -------
    str
        An absolute `http://127.0.0.1:<port>/...` URL, or '' when no server holds the file's pid or the file names another quilt.

    Notes
    -----
    The pid is checked rather than trusted: `serve.json` outlives the process that wrote it, and a command that printed a dead link would send its reader to a browser tab that never loads. `os.kill(pid, 0)` asks the kernel whether the process exists without touching it.

    See Also
    --------
    write_serve_json : What puts the port, the pid and the token there.
    """
    import os

    data = read_serve_json(root)
    port, pid = data.get("port"), data.get("pid")
    if not isinstance(port, int) or not isinstance(pid, int) or data.get("root") != str(Path(root).resolve()):
        return ""
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return ""
    return f"http://127.0.0.1:{port}/{path.lstrip('/')}"


def viewer_version(bundle: Path) -> str:
    """The version a built viewer names itself by (`_app/version.json`); '' where it names none."""
    try:
        return str(json.loads((bundle / "_app" / "version.json").read_text(encoding="utf-8")).get("version", ""))
    except (OSError, ValueError, AttributeError):
        return ""


def code_stamp() -> tuple[int, int]:
    """loom's Python as it stands on disk: how many modules, and the newest one's mtime, which an edit, a merge or an install moves."""
    import loom

    times = [p.stat().st_mtime_ns for p in Path(loom.__file__).parent.rglob("*.py")]
    return len(times), max(times, default=0)


class HeldBundle:
    """The viewer a server started with, copied aside and served from the copy, and whether loom on disk has moved on since.

    `loom serve` keeps the Python it started with, so serving the bundle from where it is vendored would hand a newer viewer to an older server once it is vendored again. `stale()` is what `/_api` reports, so a viewer can say to restart.
    """

    def __init__(self, source: Path) -> None:
        import shutil
        import tempfile

        self.source = source
        self._tmp = tempfile.TemporaryDirectory(prefix="loom-viewer-")
        self.path = Path(self._tmp.name) / "viewer"
        shutil.copytree(source, self.path)
        self.version = viewer_version(self.path)
        self.code = code_stamp()

    def stale(self) -> bool:
        """Whether the viewer vendored, or loom's code, has changed since the server started."""
        return viewer_version(self.source) != self.version or code_stamp() != self.code

    def close(self) -> None:
        self._tmp.cleanup()


class LoomHandler(SimpleHTTPRequestHandler):
    bundle_dir: Path = Path(".")
    #: The viewer copied aside at start, which `/_api` reports on; None where the bundle is served from where it lies.
    held: HeldBundle | None = None
    build_dir: Path = Path(".")
    refs_dir: Path = Path(".")
    #: The quilt to write into. `None` serves the corpus read-only and answers `/_api` with 404, which is the
    #: discovery mechanism working: a viewer that gets 404 shows no editing affordances.
    quilt_root: Path | None = None
    #: Rebuild the manifest, set when the server owns one. Most writes rebuild before answering; pending review
    #: decisions publish queue metadata only (DR-315-luisa). The original immediate-publish rule (plan 0.13.1): the
    #: watcher's filesystem scan and the viewer's manifest poll are a second each, so a change that costs 40ms to
    #: build took ~1.3s to appear, and the `refresh()` a viewer runs on the answer raced the rebuild and lost.
    rebuild: Callable[..., None] | None = None
    publication_lock: Any = None
    #: The server's publications, set when it owns a build: what `/_api/stream` reports.
    publications: Publications | None = None
    #: The library runs the viewer started (`loom.jobs`), which `GET /_api/jobs` reports; None where nothing runs them.
    jobs: Any = None
    #: What the viewer shows of the quilt, which `/_files/` answers; None serves no project file.
    shown: Shown | None = None
    #: The frames origin's address, which `GET /_api` gives the viewer; '' when there is none.
    frames: str = ""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        if os.environ.get("LOOM_SERVE_LOG"):
            super().log_message(format, *args)

    def _resolve(self) -> Path | None:
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith(BUILD_URL):
            rel = path[len(BUILD_URL) :]
            target = (self.build_dir / rel).resolve()
    def parse_request(self) -> bool:
        """Refuse, before any method answers it, a request that names another host (`addressed_here`): the token at `/_api` and every file the server reads out would otherwise go to a rebinding domain's page."""
        if not super().parse_request():
            return False
        if not addressed_here(self):
            self.send_error(HTTPStatus.FORBIDDEN, "This server answers only as 127.0.0.1 or localhost, at its own port")
            return False
        return True

            return target if str(target).startswith(str(self.build_dir.resolve())) and target.is_file() else None
        if path.startswith(STORE_URL):
            # the first thing the server offers that it did not generate: a work's fetched PDF or source, so the
            # viewer can open a reference at the place a comment points to. Localhost only, read only, and still
            # confined to one directory by the same prefix check the build tree gets (DR-110).
            rel = unquote(path[len(STORE_URL) :])
            target = (self.refs_dir / rel).resolve()
            return target if str(target).startswith(str(self.refs_dir.resolve())) and target.is_file() else None
        if path.startswith(FILES_URL):
            # a project file the viewer shows, sandboxed like the build output: an image, a PDF, text, or an HTML page drawn with no script where no frames origin runs
            rel = unquote(path[len(FILES_URL) :])
            if self.shown is None or not self.shown.is_shown(rel):
                return None
            root = self.shown.root.resolve()
            target = (root / rel).resolve()
            return target if target.is_relative_to(root) and target.is_file() else None
        if path == "/_api" or path.startswith("/_api/"):
            return None  # answered by do_GET and do_POST, never from the file tree
        rel = path.lstrip("/")
        target = (self.bundle_dir / rel).resolve() if rel else self.bundle_dir / "index.html"
        if str(target).startswith(str(self.bundle_dir.resolve())):
            if target.is_file():
                return target
            if target.is_dir() and (target / "index.html").is_file():
                return target / "index.html"
        # a project file's route in the viewer ends in the file's own suffix, `.png` or `.json` among them, and is a route all the same
        if not rel.startswith("file/") and (rel.startswith("_app/") or Path(rel).suffix.lower() in ASSET_SUFFIXES):
            return None  # a missing asset is a 404, never the app shell
        return (
            self.bundle_dir / "index.html"
        )  # every other path is a viewer route, dots included (`/node/ro-thm-1.0.1`)

    def _json(self, status: HTTPStatus | int, payload: dict[str, object]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._confine(True)  # every API answer, and the transcript pages `_page` answers under /build/
        self.end_headers()
        self.wfile.write(data)

    #: Set when the socket binds; every write must carry it (plan 0.13 §8).
    token: str = ""

    def _csrf(self) -> str:
        """Why this request must be refused, or '' when it may proceed.

        Three checks, and together they are CSRF protection rather than a login: they keep other *pages* out, not other people. A browser blocks a cross-origin **response** and never the **request**, so any page the author happens to be reading could otherwise POST into their quilt and create, resolve or discard. A cross-site form post cannot set a custom header, so requiring one closes it; requiring JSON closes the simple-form path that needs no header at all; and a request the browser says came from another page (`from_elsewhere`) is refused outright.
        """
        elsewhere = from_elsewhere(self)
        if elsewhere:
            return elsewhere
        kind = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if kind != "application/json":
            return "a write must be application/json"
        if self.token and self.headers.get("X-Loom-Token") != self.token:
            return "this request carries no valid X-Loom-Token"
        return ""

    def do_POST(self) -> None:  # noqa: N802
        """The write API (specs/write-api.md). Localhost only, like everything else this server does."""
        from loom.render.api import NO_REBUILD, RECORD_WRITES, ApiError, handle

        path = self.path.split("?", 1)[0]
        if not path.startswith("/_api/") or self.quilt_root is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        refused = self._csrf()
        if refused:
            self._json(HTTPStatus.FORBIDDEN, {"error": {"code": "refused", "message": refused}})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        from loom.render.api import MAX_BODY

        if length > MAX_BODY:
            self._json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": {"code": "too-large", "message": f"a write is at most {MAX_BODY // (1024 * 1024)} MB"}},
            )
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(body, dict):
                raise ValueError("body must be an object")
        except (UnicodeDecodeError, ValueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": {"code": "bad-json", "message": str(exc)}})
            return
        try:
            endpoint = path[len("/_api/") :]
            # Queue-only publication must not race a source rebuild publishing an older queue.
            from contextlib import nullcontext

            # the reader's place touches memory only, so it never waits behind a rebuild
            lock = self.publication_lock if self.publication_lock is not None and endpoint != "here" else nullcontext()
            with lock:
                answer = handle(self.quilt_root, endpoint, body)
            # The viewer's refresh finds the write immediately. Reads need no rebuild; review decisions already published queue metadata without touching document renderings.
            if self.rebuild is not None and endpoint not in NO_REBUILD:
                self.rebuild(records=endpoint in RECORD_WRITES)
            self._json(HTTPStatus.OK, answer)
        except ApiError as exc:
            self._json(exc.status, exc.answer())
        except Exception as exc:  # noqa: BLE001
            # A write that failed for a reason nobody anticipated is still the publisher's answer, not a dead socket.
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": {"code": "failed", "message": str(exc)}})

    def _events(self) -> None:
        """`GET /_api/events?session=<id>&since=<seq>`: what has landed in a session's inbox since a sequence number.

        **Fine events for appends, coarse for everything else** (plan 0.13 §8). A message is the smallest unit loom can stream -- it never sees the model, so a "typing" feel could only come from an agent writing partial messages -- and everything else a reader needs still arrives through the manifest it already polls. Rebuilding the whole manifest per message would reintroduce the re-render that closed open boxes under the reader.

        The answer carries `seq`, so a client that finds a gap between what it has and what it is given knows it missed some and resyncs the coarse way rather than stitching a stream together from the middle.
        """
        from urllib.parse import parse_qs, urlsplit

        from loom.mailbox import public, transcript
        from loom.sessions import ID

        if self.quilt_root is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        query = parse_qs(urlsplit(self.path).query)
        sid = (query.get("session") or [""])[0]
        try:
            since = int((query.get("since") or ["0"])[0])
        except ValueError:
            since = 0
        if not sid:
            self._json(HTTPStatus.BAD_REQUEST, {"error": {"code": "missing-field", "message": "session is required"}})
            return
        # The id is joined into a path, so it is held to the shape an id has.
        if not ID.match(sid):
            self._json(
                HTTPStatus.BAD_REQUEST, {"error": {"code": "bad-session", "message": f"not a session id: {sid}"}}
            )
            return
        log = transcript(self.quilt_root, sid)
        events = log.since(since)
        self._json(
            HTTPStatus.OK,
            {
                "session": sid,
                "from": since,
                "seq": log.seq,
                "events": [public(e) for e in events],
            },
        )

    def _page(self) -> bool:
        """Answer `/build/transcripts/<session>/<n>.json` from the inbox itself, and say whether this was one.

        The build writes these pages, but a message rebuilds nothing, so under a running server they go stale; the Chat reads the newest page on opening and would otherwise receive the whole tail since the last build in one poll (study F14).
        """
        import re as _re

        from loom.records.ids import SESSION

        m = _re.fullmatch(_re.escape(BUILD_URL) + rf"transcripts/({SESSION})/(\d+)\.json", self.path.split("?", 1)[0])
        if m is None or self.quilt_root is None:
            return False
        from loom.mailbox import page

        self._json(HTTPStatus.OK, page(self.quilt_root, m.group(1), int(m.group(2))))
        return True

    def do_GET(self) -> None:  # noqa: N802
        if self._page():
            return
        if self.path.split("?", 1)[0] == "/_api/events":
            self._events()
            return
        if self.path.split("?", 1)[0] == "/_api/stream":
            self._stream()
            return
        if self.path.split("?", 1)[0] == "/_api/here":
            self._here()
            return
        if self.path.split("?", 1)[0] == "/_api/jobs":
            self._jobs()
            return
        if self.path.split("?", 1)[0] == "/_api":
            from loom.render.api import discovery

            if self.quilt_root is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            # the token is the viewer's alone: a page in another origin, a sandboxed one's `null` included, is not given it
            elsewhere = from_elsewhere(self)
            if elsewhere:
                self._json(HTTPStatus.FORBIDDEN, {"error": {"code": "refused", "message": elsewhere}})
                return
            frames = {"frames": self.frames} if self.frames else {}
            # the viewer this server serves, and whether loom has been updated under it, so a page can say to reload or to restart
            served = {"viewer": self.held.version, "stale": self.held.stale()} if self.held else {}
            self._json(
                HTTPStatus.OK,
                {**discovery(), "token": self.token, "stream": self.publications is not None, **frames, **served},
            )
            return
        target = self._resolve()
        if target is None or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix in (".html", ".js", ".css", ".json", ".svg"):
            ctype += "; charset=utf-8"
        held = self.path.split("?", 1)[0].startswith((BUILD_URL, STORE_URL, FILES_URL))
        etag = '"' + hashlib.sha256(data).hexdigest()[:32] + '"'
        if self.headers.get("If-None-Match") == etag:
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.send_header("ETag", etag)
            self._confine(held)  # a 304's headers replace the cached copy's, which may predate them
            self.end_headers()
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache")
        self._confine(held)
        self.end_headers()
        self.wfile.write(data)

    def _confine(self, held: bool) -> None:
        """Send `CONFINED` for a file the quilt holds; the viewer's own bundle runs unconfined."""
        if held:
            for name, value in CONFINED.items():
                self.send_header(name, value)

    def _here(self) -> None:
        """`GET /_api/here`: the last place a viewer tab reported, for `loom here`, which reads the token from `.loom/serve.json`.

        Where a person is reading, and the words they selected, are theirs: the token is required, and so is this server's own origin when a browser sends one.
        """
        from loom.render.api import reading_place

        if self.quilt_root is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        elsewhere = from_elsewhere(self)
        if elsewhere:
            self._json(HTTPStatus.FORBIDDEN, {"error": {"code": "refused", "message": elsewhere}})
            return
        if not self.token or self.headers.get("X-Loom-Token") != self.token:
            self._json(
                HTTPStatus.FORBIDDEN,
                {"error": {"code": "refused", "message": "this request carries no valid X-Loom-Token"}},
            )
            return
        self._json(HTTPStatus.OK, reading_place(self.quilt_root))

    def _jobs(self) -> None:
        """`GET /_api/jobs`: the library runs the viewer started, newest first, each with its steps and, once done, its report; this server's origin and the token are required, as for `/_api/here`."""
        if self.quilt_root is None or self.jobs is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        elsewhere = from_elsewhere(self)
        if elsewhere:
            self._json(HTTPStatus.FORBIDDEN, {"error": {"code": "refused", "message": elsewhere}})
            return
        if not self.token or self.headers.get("X-Loom-Token") != self.token:
            self._json(
                HTTPStatus.FORBIDDEN,
                {"error": {"code": "refused", "message": "this request carries no valid X-Loom-Token"}},
            )
            return
        self._json(HTTPStatus.OK, {"jobs": self.jobs.recent()})

    def _stream(self) -> None:
        """`GET /_api/stream`: a server-sent event, `manifest`, carrying nothing, each time a new manifest is published, and `compiles`, carrying how every compile stands, on opening and each time that changes.

        The viewer fetches the manifest as it would on a poll and learns nothing of what changed. Held open on its own thread; a comment every `HEARTBEAT` seconds keeps an idle one alive, and the server's stop ends it.
        """
        pubs = self.publications
        if pubs is None or self.quilt_root is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        seen = (pubs.count, pubs.compiles)
        try:
            self.wfile.write(b": open\n\nevent: compiles\ndata: " + pubs.compile_state + b"\n\n")
            self.wfile.flush()
            while True:
                now = pubs.wait(seen, HEARTBEAT)
                if now is None:
                    return
                if now == seen:
                    self.wfile.write(b": still open\n\n")
                if now[0] != seen[0]:
                    self.wfile.write(b"event: manifest\ndata:\n\n")
                if now[1] != seen[1]:
                    self.wfile.write(b"event: compiles\ndata: " + pubs.compile_state + b"\n\n")
                seen = now
                self.wfile.flush()
        except OSError:
            return

    def do_HEAD(self) -> None:  # noqa: N802
        target = self._resolve()
        if target is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.end_headers()


class FramesHandler(SimpleHTTPRequestHandler):
    """The frames origin: the project's shown files on a port of their own, so an HTML page runs as a page of its own origin, never the viewer's.

    It answers GET and HEAD for shown files and nothing else -- no `/_api`, no bundle, no build output, no store -- and only to a request addressed to its own host and port, which keeps a rebinding domain out. An HTML page gets `BRIDGE`. A page here can read the project's other shown files, as any page on a local server can, but never the viewer: the write API refuses this origin (`from_elsewhere`) and sends no CORS headers.
    """

    shown: Shown | None = None
    #: The viewer origins a page may be told to post to: this server's sibling at 127.0.0.1 and at localhost.
    viewers: tuple[str, ...] = ()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        if os.environ.get("LOOM_SERVE_LOG"):
            super().log_message(format, *args)

    def _target(self) -> Path | None:
        if not addressed_here(self) or self.shown is None:
            return None
        rel = unquote(self.path.split("?", 1)[0].split("#", 1)[0].lstrip("/"))
        if not self.shown.is_shown(rel):
            return None
        root = self.shown.root.resolve()
        target = (root / rel).resolve()
        return target if target.is_relative_to(root) and target.is_file() else None

    def _listing(self) -> bytes | None:
        """`/.loom/files.json`: every shown file's path, the one thing here that is not a shown file, at an address no shown file can have since `.loom` is never shown; so a page can find what the project holds."""
        if self.path.split("?", 1)[0] != "/.loom/files.json" or self.shown is None or not addressed_here(self):
            return None
        return json.dumps({"files": self.shown.walk()}).encode("utf-8")

    def _answer(self, body: bool) -> None:
        from urllib.parse import parse_qs, urlsplit

        listing = self._listing()
        if listing is not None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(listing)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if body:
                self.wfile.write(listing)
            return
        target = self._target()
        if target is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix.lower() in (".html", ".htm"):
            asked = (parse_qs(urlsplit(self.path).query).get("loom-viewer") or [""])[0]
            viewer = asked if asked in self.viewers else (self.viewers[0] if self.viewers else "")
            script = (BRIDGE % json.dumps(viewer)).encode("utf-8")
            at = data.lower().rfind(b"</body>")
            data = data[:at] + script + data[at:] if at != -1 else data + script
            ctype = "text/html; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if body:
            self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        self._answer(True)

    def do_HEAD(self) -> None:  # noqa: N802
        self._answer(False)


class ServeSession:
    def __init__(
        self,
        quilt: Quilt,
        bundle_dir: Path,
        port: int = DEFAULT_PORT,
        compile_masters: bool = True,
        interval: float = 1.0,
    ) -> None:
        self.quilt = quilt
        self.bundle_dir = bundle_dir
        self.port = port
        self.compile_masters = compile_masters
        self.interval = interval
        self.lock = threading.Lock()
        self.builds = 0
        self.httpd: ThreadingHTTPServer | None = None
        self.frames: ThreadingHTTPServer | None = None
        self.shown = Shown.of(quilt)
        self.watcher: Watcher | None = None
        self.held: HeldBundle | None = None
        self.last_report: BuildReport | None = None
        self.published: dict[Path, float] = {}  # the watched files as the last publication read them
        self.publications = Publications()
        from loom.jobs import Jobs
        from loom.render.compiles import Compiles

        self.jobs = Jobs(self._run_job)
        self.compiles = (
            Compiles(self._compile, first=self._reading, told=self._compiles_told, made=lambda doc: self.rebuild())
            if compile_masters
            else None
        )

    def rebuild(
        self,
        changed: list[Path] | None = None,
        records: bool = False,
        progress: Callable[[str, str, int, int | None], None] | None = None,
    ) -> None:
        """Publish the quilt as it is now, building only what changed since the last publication.

        The files are read just before the build, and that reading is what the publication answers for: the watcher is set to it, so a write the API has published is not built again when the watcher sees it, and a change made during a build is seen afterwards. A call from the watcher (`changed` given) builds nothing when everything it saw is already published. A change the scan does not read (`records`, or a watcher's change that `scan_unread` judges so: a record, or a Markdown file) builds from the last scan. Every file changed since the last publication, whoever wrote it, asks for the compiles it reaches; the first publication leaves that to `first_build`.
        """
        root = self.quilt.root
        with self.lock:
            if not records:
                self._reload()
            seen = snapshot(root, self.shown)
            moved = [p for p, m in seen.items() if self.published.get(p) != m] + [
                p for p in self.published if p not in seen
            ]
            first = self.builds == 0
            if changed is not None:
                changed = moved
                if not changed:
                    return
                records = scan_unread(root, changed)
            reuse = self.last_report.result if records and self.last_report is not None else None
            if progress is None and changed is not None:
                from loom.cli.report import Progress

                with Progress("rebuilding") as shown:
                    report = build(self.quilt, reuse=reuse, progress=shown.told, tex=self.compile_masters)
            else:
                report = build(self.quilt, reuse=reuse, progress=progress, tex=self.compile_masters)
            self.last_report = report
            self.builds += 1
            self.published = seen
            if self.watcher is not None:
                self.watcher.rebaseline(seen)
            self.publications.published()
        if changed is not None:
            from loom.cli.report import counted

            names = ", ".join(p.relative_to(self.quilt.root).as_posix() for p in changed[:3])
            print(
                f"loom serve: rebuilt after change to {names}{' …' if len(changed) > 3 else ''}; {counted(len(report.rendered), 'block')} re-rendered",
                file=sys.stderr,
            )
        if self.compiles is not None and moved and not first:
            from loom.render.compiles import needs_compiling

            # the watcher's change, or a write through the API (a suggested edit taken, a version restored), which the watcher is set past
            due = needs_compiling(report.result, moved, self._built)
            if due:
                self.compiles.want(due)

    def _run_job(self, job: Any, progress: Callable[[str, str, int, int], None]) -> dict[str, Any]:
        """One library run the viewer started: `refs.update.update` on the quilt as it is now, outside the publication lock, then a rebuild, so the manifest shows what it made. Its report is what `loom library update` prints."""
        from loom.refs.update import update
        from loom.scan.quilt import load_quilt

        built = update(
            load_quilt(self.quilt.root),
            tuple(job.works),
            steps=tuple(s.name for s in job.steps),
            redo=job.redo,
            online=job.online,
            progress=progress,
        )
        self.rebuild()
        return built.report().to_json()

    def _reload(self) -> None:
        """Read `config.toml` again, so a setting saved in the viewer or by hand is what the next build uses; a file that no longer parses keeps the last config, and says so."""
        import tomllib

        from loom.scan.quilt import load_quilt

        try:
            quilt = load_quilt(self.quilt.root)
        except (tomllib.TOMLDecodeError, OSError) as exc:
            print(f"loom serve: config.toml does not parse, so the last config stays: {exc}", file=sys.stderr)
            return
        # what the viewer shows stays as serving began: it follows `[quilt] history`, which Settings never changes
        if quilt.config != self.quilt.config:
            self.quilt = quilt

    def _current_scan(self) -> ScanResult | None:
        """The last publication's scan while nothing the scan reads has changed since, for the write API to annotate against rather than scanning again; None otherwise."""
        if self.last_report is None:
            return None
        now = snapshot(self.quilt.root, self.shown)
        changed = [p for p, m in now.items() if self.published.get(p) != m] + [
            p for p in self.published if p not in now
        ]
        return self.last_report.result if scan_unread(self.quilt.root, changed) else None

    def _built(self, doc: str) -> Path:
        """Where a document's compiled PDF is, as `loom compile` writes it."""
        return self.quilt.root / document_build(doc) / f"{Path(doc).stem}.pdf"

    def _compile(self, doc: str, started: Callable[[Any], None]) -> CompileResult:
        """One run of the compile queue: the document as the last publication's scan read it, carried on past a recoverable error, then its HTML from that compile's aux.

        The PDF is published as soon as it is made, since its pages answer before TeX4ht's longer pass; the page then replaces the translator's rendering at the next publication.
        """
        import shutil

        from loom.scan.scan import scan
        from loom.tex.tex4ht import compile_html

        result = self.last_report.result if self.last_report is not None else scan(self.quilt)
        closure = result.closures.get(doc)
        engine = normalise_engine((closure.engine if closure else None) or self.quilt.config.engine)
        build = self.quilt.root / document_build(doc)
        res = compile_document(
            self.quilt.root, result.base_of(doc), doc, build, engine, halt_on_error=False, started=started
        )
        said = "ok" if res.pdf is not None and not res.errors else ("with errors" if res.pdf else "FAILED")
        print(f"loom serve: compiled {doc}: {said}{'' if said == 'ok' else ': ' + res.first_error}", file=sys.stderr)
        if res.pdf is not None and shutil.which("make4ht"):
            self.rebuild()
            envs = [*(closure.taxa if closure else ()), "proof"]
            page = compile_html(
                self.quilt.root,
                result.base_of(doc),
                doc,
                build / "html",
                envs=envs,
                engine=engine,
                seed=build,
                started=started,
            )
            if page.html is None:
                print(f"loom serve: no HTML for {doc}: {page.first_error}", file=sys.stderr)
        return res

    def _reading(self) -> str | None:
        """The document the reader has open, as text or as its PDF, which compiles before any other."""
        from loom.render.api import reading_place

        item = ((reading_place(self.quilt.root).get("place") or {}).get("item")) or {}
        return item.get("id") if item.get("kind") in ("document", "pdf") else None

    def _compiles_told(self) -> None:
        """Say how the compiles stand, on the stream and in the build output for `loom status`."""
        from loom.render.compiles import COMPILES_JSON
        from loom.render.publish import write_atomic

        if self.compiles is None:
            return
        state = json.dumps(self.compiles.state(), separators=(",", ":"))
        try:
            write_atomic(self.quilt.root / BUILD / COMPILES_JSON, state)
        except OSError:
            pass  # the stream still says it
        self.publications.compiled(state.encode("utf-8"))

    def listen(self) -> None:
        """Bind the port and start serving. The build has not run yet, so until `start` finishes it `/build/` serves what an earlier build left, or 404."""
        self.held = HeldBundle(self.bundle_dir)
        handler = type(
            "Handler",
            (LoomHandler,),
            {
                "bundle_dir": self.held.path,
                "held": self.held,
                "build_dir": self.quilt.root / BUILD,
                "refs_dir": storage_root(self.quilt.root),
                # The write API is served for the quilt being served, and only ever over this loopback socket.
                "quilt_root": self.quilt.root,
                "rebuild": self.rebuild,
                "publication_lock": self.lock,
                "publications": self.publications,
                "jobs": self.jobs,
            },
        )
        from loom.render.api import offer_jobs, offer_scan

        offer_scan(self.quilt.root, self._current_scan)
        offer_jobs(self.quilt.root, self.jobs)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.port = self.httpd.server_address[1]
        handler.token = write_serve_json(self.quilt.root, self.port)  # type: ignore[attr-defined]
        shown = self.shown
        frames = type(
            "Frames",
            (FramesHandler,),
            {"shown": shown, "viewers": (f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}")},
        )
        self.frames = ThreadingHTTPServer(("127.0.0.1", 0), frames)
        handler.shown = shown  # type: ignore[attr-defined]
        handler.frames = f"http://127.0.0.1:{self.frames.server_address[1]}"  # type: ignore[attr-defined]
        threading.Thread(target=self.frames.serve_forever, name="loom-frames", daemon=True).start()
        # Capture inputs before clients can change them, including during the first build.
        self.watcher = Watcher(self.quilt.root, self.rebuild, self.interval, shown)
        threading.Thread(target=self.httpd.serve_forever, name="loom-http", daemon=True).start()

    def start(self) -> None:
        """Listen, then run the first build and begin watching. A cold first build can take a while, so callers that want the URL early call `listen` first."""
        if self.httpd is None:
            self.listen()
        self.first_look()
        self.first_build()
        assert self.watcher is not None
        self.watcher.start()

    def first_look(self) -> None:
        """Take the reviewer's first look at the open files when they have none and the quilt tracks edits, so an agent's first edits show in Review's Your Changes; nothing without a reviewer name."""
        from loom.looks import read_look, take
        from loom.scan.quilt import reviewer_identity

        who = reviewer_identity(self.quilt.root)[0]
        if self.quilt.config.track_edits and who and read_look(self.quilt.root, who) is None:
            take(self.quilt, who)

    def first_build(self) -> None:
        """The initial publish, reported as it happens: on a cold cache it compiles every block the converter cannot translate."""
        from loom.cli.diagnostics import has_errors, tally
        from loom.cli.report import Progress, counted

        started = time.perf_counter()
        with Progress("scanning") as progress:
            self.rebuild(progress=progress.told)
        if self.compiles is not None and self.last_report is not None:
            import shutil

            from loom.render.compiles import needs_compiling

            # what changed while no server watched: a document never compiled, edited since its PDF, or without the page its text is read from
            self.compiles.want(
                needs_compiling(self.last_report.result, None, self._built, pages=shutil.which("make4ht") is not None)
            )
        errors = [d for d in self.last_report.diagnostics if d.severity == "error"] if self.last_report else []
        blocks = len(self.last_report.rendered) if self.last_report else 0
        # a quilt with errors renders strangely rather than failing, so say so at startup instead of leaving it to be discovered
        result = self.last_report.result if self.last_report else None
        note = f"; {tally(errors, result)}; loom lint lists them" if has_errors(errors, result) else ""
        print(
            f"loom serve: built {counted(blocks, 'block')} in {time.perf_counter() - started:.1f}s{note}",
            file=sys.stderr,
            flush=True,
        )

    def stop(self) -> None:
        from loom.render.compiles import COMPILES_JSON

        if self.compiles is not None:
            self.compiles.stop()
        (self.quilt.root / BUILD / COMPILES_JSON).unlink(missing_ok=True)
        self.publications.close()
        if self.watcher:
            self.watcher.stop()
        for server in (self.httpd, self.frames):
            if server:
                server.shutdown()
                server.server_close()
        # nothing is listening any more, so nothing should tell a command that something is
        (self.quilt.root / SERVE_JSON).unlink(missing_ok=True)
        if self.held:
            self.held.close()
        from loom.render.api import forget_place

        forget_place(self.quilt.root)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"


def locate_bundle() -> Path | None:
    """The bundle to serve, or None; raises BundleEnvError for a LOOM_ARRAS_BUNDLE that names none."""
    info = find_bundle()
    return info.path if info else None
