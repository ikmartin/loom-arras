"""`loom serve` (book 9.8): one loop with three jobs, watch, serve, compile.

Serves the arras bundle at / (with index.html as the fallback for any path that is not a file of the bundle or an asset, so the viewer's routes work, dots in keys included) and build/ at /build/. The manifest carries an ETag so the viewer's poll costs nothing while unchanged. Loom never notifies the viewer; the viewer polls.
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
from loom.refs.pages import STORAGE, storage_root
from loom.render.build import BuildReport, build
from loom.render.watch import Watcher
from loom.scan.quilt import Quilt
from loom.tex.runner import compile_tex, normalise_engine

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


SERVE_JSON = ".loom/serve.json"


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
        json.dumps({"port": port, "pid": os.getpid(), "token": token, "url": f"http://127.0.0.1:{port}/"}, indent=1)
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
        An absolute `http://127.0.0.1:<port>/...` URL, or '' when no server holds the file's pid.

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
    if not isinstance(port, int) or not isinstance(pid, int):
        return ""
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return ""
    return f"http://127.0.0.1:{port}/{path.lstrip('/')}"


class LoomHandler(SimpleHTTPRequestHandler):
    bundle_dir: Path = Path(".")
    build_dir: Path = Path(".")
    refs_dir: Path = Path(".")
    #: The quilt to write into. `None` serves the corpus read-only and answers `/_api` with 404, which is the
    #: discovery mechanism working: a viewer that gets 404 shows no editing affordances.
    quilt_root: Path | None = None
    #: Rebuild the manifest, set when the server owns one. **A write rebuilds before it answers** (plan 0.13.1): the
    #: watcher's filesystem scan and the viewer's manifest poll are a second each, so a change that costs 40ms to
    #: build took ~1.3s to appear, and the `refresh()` a viewer runs on the answer raced the rebuild and lost.
    rebuild: Callable[[], None] | None = None
    #: What starts and stops an agent's turn, set when the server owns one (plan 0.14): `agent-stop` is answered by it.
    launcher: Any = None

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        if os.environ.get("LOOM_SERVE_LOG"):
            super().log_message(format, *args)

    def _resolve(self) -> Path | None:
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith("/build/"):
            rel = path[len("/build/") :]
            target = (self.build_dir / rel).resolve()
            return target if str(target).startswith(str(self.build_dir.resolve())) and target.is_file() else None
        if path.startswith("/" + STORAGE + "/"):
            # the first thing the server offers that it did not generate: a work's fetched PDF or source, so the
            # viewer can open a reference at the place a comment points to. Localhost only, read only, and still
            # confined to one directory by the same prefix check the build tree gets (DR-110).
            rel = unquote(path[len("/" + STORAGE + "/") :])
            target = (self.refs_dir / rel).resolve()
            return target if str(target).startswith(str(self.refs_dir.resolve())) and target.is_file() else None
        if path == "/_api" or path.startswith("/_api/"):
            return None  # answered by do_GET and do_POST, never from the file tree
        rel = path.lstrip("/")
        target = (self.bundle_dir / rel).resolve() if rel else self.bundle_dir / "index.html"
        if str(target).startswith(str(self.bundle_dir.resolve())):
            if target.is_file():
                return target
            if target.is_dir() and (target / "index.html").is_file():
                return target / "index.html"
        if rel.startswith("_app/") or Path(rel).suffix.lower() in ASSET_SUFFIXES:
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
        self.end_headers()
        self.wfile.write(data)

    #: Set when the socket binds; every write must carry it (plan 0.13 §8).
    token: str = ""

    def _csrf(self) -> str:
        """Why this request must be refused, or '' when it may proceed.

        Three checks, and together they are CSRF protection rather than a login: they keep other *pages* out, not other people. A browser blocks a cross-origin **response** and never the **request**, so any page the author happens to be reading could otherwise POST into their quilt and create, resolve or discard. A cross-site form post cannot set a custom header, so requiring one closes it; requiring JSON closes the simple-form path that needs no header at all; and a foreign `Origin` is refused outright.
        """
        origin = self.headers.get("Origin")
        port = self.server.server_address[1] if isinstance(self.server.server_address, tuple) else 0
        if origin and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
            return f"this request came from {origin}, which is not this server"
        kind = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if kind != "application/json":
            return "a write must be application/json"
        if self.token and self.headers.get("X-Loom-Token") != self.token:
            return "this request carries no valid X-Loom-Token"
        return ""

    def do_POST(self) -> None:  # noqa: N802
        """The write API (specs/write-api.md). Localhost only, like everything else this server does."""
        from loom.render.api import ApiError, handle

        path = self.path.split("?", 1)[0]
        if not path.startswith("/_api/") or self.quilt_root is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        refused = self._csrf()
        if refused:
            self._json(HTTPStatus.FORBIDDEN, {"error": {"code": "refused", "message": refused}})
            return
        if path == "/_api/agent-stop":
            self._agent_stop()
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(body, dict):
                raise ValueError("body must be an object")
        except (UnicodeDecodeError, ValueError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": {"code": "bad-json", "message": str(exc)}})
            return
        try:
            answer = handle(self.quilt_root, path[len("/_api/") :], body)
            # The manifest is current when the answer arrives, so the viewer's own refresh finds the write on its
            # first try rather than after two polling loops.
            if self.rebuild is not None:
                self.rebuild()
            self._json(HTTPStatus.OK, answer)
        except ApiError as exc:
            self._json(exc.status, {"error": {"code": exc.code, "message": exc.message}})
        except Exception as exc:  # noqa: BLE001
            # A write that failed for a reason nobody anticipated is still the publisher's answer, not a dead socket.
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": {"code": "failed", "message": str(exc)}})

    def _agent_stop(self) -> None:
        """`POST /_api/agent-stop {session}`: end the running turn in a session. Answered by the server's launcher, since the process is its own."""
        from loom.agent import launching

        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except (ValueError, UnicodeDecodeError):
            body = {}
        sid = str(body.get("session", "")) if isinstance(body, dict) else ""
        if self.launcher is None or self.quilt_root is None or not launching(self.quilt_root):
            self._json(
                HTTPStatus.CONFLICT, {"error": {"code": "not-launching", "message": "agents are not launched here"}}
            )
            return
        stopped = self.launcher.stop(sid)
        self._json(
            HTTPStatus.OK, {"ok": True, "result": "stopped" if stopped else "nothing was running", "session": sid}
        )

    def _events(self) -> None:
        """`GET /_api/events?session=<id>&since=<seq>`: what has landed in a session's inbox since a sequence number.

        **Fine events for appends, coarse for everything else** (plan 0.13 §8). A message is the smallest unit loom can stream -- it never sees the model, so a "typing" feel could only come from an agent writing partial messages -- and everything else a reader needs still arrives through the manifest it already polls. Rebuilding the whole manifest per message would reintroduce the re-render that closed open boxes under the reader.

        The answer carries `seq`, so a client that finds a gap between what it has and what it is given knows it missed some and resyncs the coarse way rather than stitching a stream together from the middle.
        """
        from urllib.parse import parse_qs, urlsplit

        from loom.agent import report
        from loom.mailbox import attached, public, transcript
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
                "attached": [
                    {"who": r.get("who", ""), "kind": r.get("kind", "")} for r in attached(self.quilt_root, sid)
                ],
                "agent": report(self.quilt_root, sid),
            },
        )

    def _packet(self) -> None:
        """`GET /_api/packet?session=<id>`: what the person's next message in a session will carry, as rows and as the text the agent will read (plan 0.14).

        The text is `render_changes` of the same rows `post` will record, so the viewer's preview is what is sent and not a description of it.
        """
        from urllib.parse import parse_qs, urlsplit

        from loom.cli._common import whoever
        from loom.mailbox import pending, render_changes
        from loom.sessions import ID, sessions

        if self.quilt_root is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        sid = (parse_qs(urlsplit(self.path).query).get("session") or [""])[0]
        if not ID.match(sid):
            self._json(
                HTTPStatus.BAD_REQUEST, {"error": {"code": "bad-session", "message": f"not a session id: {sid}"}}
            )
            return
        found = sessions(self.quilt_root).get(sid)
        if found is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": {"code": "no-such-session", "message": f"no session {sid}"}})
            return
        # the viewer's own name, as the message it will go with is named (`_message`), unless the caller says whose
        who = (parse_qs(urlsplit(self.path).query).get("author") or [""])[0] or whoever(self.quilt_root, sniff=False)
        rows = pending(self.quilt_root, found, who)
        keep = ("id", "kind", "act", "target", "work", "page")
        self._json(
            HTTPStatus.OK,
            {"session": sid, "rows": [{k: r.get(k) for k in keep} for r in rows], "text": render_changes(rows)},
        )

    def _page(self) -> bool:
        """Answer `/build/transcripts/<session>/<n>.json` from the inbox itself, and say whether this was one.

        The build writes these pages, but a message rebuilds nothing, so under a running server they go stale; the Chat reads the newest page on opening and would otherwise receive the whole tail since the last build in one poll (study F14).
        """
        import re as _re

        m = _re.fullmatch(r"/build/transcripts/(s-\d{4}-\d{2}-\d{2}-\d{4})/(\d+)\.json", self.path.split("?", 1)[0])
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
        if self.path.split("?", 1)[0] == "/_api/packet":
            self._packet()
            return
        if self.path.split("?", 1)[0] == "/_api":
            from loom.render.api import discovery

            if self.quilt_root is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._json(HTTPStatus.OK, {**discovery(), "token": self.token})
            return
        target = self._resolve()
        if target is None or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix in (".html", ".js", ".css", ".json", ".svg"):
            ctype += "; charset=utf-8"
        etag = '"' + hashlib.sha256(data).hexdigest()[:32] + '"'
        if self.headers.get("If-None-Match") == etag:
            self.send_response(HTTPStatus.NOT_MODIFIED)
            self.send_header("ETag", etag)
            self.end_headers()
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_HEAD(self) -> None:  # noqa: N802
        target = self._resolve()
        if target is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self.send_response(HTTPStatus.OK)
        self.end_headers()


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
        self.watcher: Watcher | None = None
        self.last_report: BuildReport | None = None
        from loom.agent import Launcher

        self.launcher = Launcher(quilt.root, interval)

    def rebuild(self, changed: list[Path] | None = None) -> None:
        with self.lock:
            report = build(self.quilt)
            self.last_report = report
            self.builds += 1
        if changed is not None:
            names = ", ".join(p.relative_to(self.quilt.root).as_posix() for p in changed[:3])
            print(
                f"loom serve: rebuilt after change to {names}{' …' if len(changed) > 3 else ''}; {len(report.rendered)} fragment(s) re-rendered",
                file=sys.stderr,
            )
        if (
            self.compile_masters
            and changed is not None
            and any(p.suffix in (".tex", ".sty", ".cls", ".bib") for p in changed)
        ):
            threading.Thread(target=self._compile_default, name="loom-compile", daemon=True).start()

    def _compile_default(self) -> None:
        from loom.scan.scan import scan

        result = scan(self.quilt)
        master = result.default_master
        if master is None:
            return
        closure = result.closures.get(master)
        engine = normalise_engine((closure.engine if closure else None) or self.quilt.config.engine)
        res = compile_tex(self.quilt.root, master, self.quilt.root / "build" / Path(master).stem, engine)
        print(f"loom serve: compiled {master}: {'ok' if res.ok else 'FAILED ' + res.first_error}", file=sys.stderr)
        if res.ok:
            self.rebuild()

    def listen(self) -> None:
        """Settle the launcher, bind the port and start serving. The build has not run yet, so `/build/` answers 503 until `start` finishes it.

        The launcher settles here, before the socket takes a write: what was waiting is old, and a message posted from now on, during the first build included, starts a turn.
        """
        self.launcher.settle()
        handler = type(
            "Handler",
            (LoomHandler,),
            {
                "bundle_dir": self.bundle_dir,
                "build_dir": self.quilt.root / "build",
                "refs_dir": storage_root(self.quilt.root),
                # The write API is served for the quilt being served, and only ever over this loopback socket.
                "quilt_root": self.quilt.root,
                "rebuild": self.rebuild,
                "launcher": self.launcher,
            },
        )
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.port = self.httpd.server_address[1]
        handler.token = write_serve_json(self.quilt.root, self.port)  # type: ignore[attr-defined]
        threading.Thread(target=self.httpd.serve_forever, name="loom-http", daemon=True).start()

    def start(self) -> None:
        """Listen, then run the first build and begin watching. A cold first build can take a while, so callers that want the URL early call `listen` first."""
        if self.httpd is None:
            self.listen()
        self.first_build()
        self.watcher = Watcher(self.quilt.root, self.rebuild, self.interval)
        self.watcher.start()
        self.launcher.start()

    def first_build(self) -> None:
        """The initial publish, reported as it happens: on a cold cache it compiles every block the converter cannot translate."""
        started = time.perf_counter()
        print("loom serve: building the quilt ...", file=sys.stderr, flush=True)
        self.rebuild()
        errors = sum(1 for d in self.last_report.diagnostics if d.severity == "error") if self.last_report else 0
        fragments = len(self.last_report.rendered) if self.last_report else 0
        # a quilt with errors renders strangely rather than failing, so say so at startup instead of leaving it to be discovered
        note = f"; {errors} error(s) -- run loom lint" if errors else ""
        print(
            f"loom serve: built {fragments} fragment(s) in {time.perf_counter() - started:.1f}s{note}",
            file=sys.stderr,
            flush=True,
        )

    def stop(self) -> None:
        self.launcher.close()
        if self.watcher:
            self.watcher.stop()
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        # nothing is listening any more, so nothing should tell a command that something is
        (self.quilt.root / SERVE_JSON).unlink(missing_ok=True)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"


def locate_bundle() -> Path | None:
    """The bundle to serve, or None; raises BundleEnvError for a LOOM_ARRAS_BUNDLE that names none."""
    info = find_bundle()
    return info.path if info else None
