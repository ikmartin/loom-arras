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
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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


class LoomHandler(SimpleHTTPRequestHandler):
    bundle_dir: Path = Path(".")
    build_dir: Path = Path(".")
    refs_dir: Path = Path(".")
    #: The quilt to write into. `None` serves the corpus read-only and answers `/_api` with 404, which is the
    #: discovery mechanism working: a viewer that gets 404 shows no editing affordances.
    quilt_root: Path | None = None

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
            self._json(HTTPStatus.OK, handle(self.quilt_root, path[len("/_api/") :], body))
        except ApiError as exc:
            self._json(exc.status, {"error": {"code": exc.code, "message": exc.message}})
        except Exception as exc:  # noqa: BLE001
            # A write that failed for a reason nobody anticipated is still the publisher's answer, not a dead socket.
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": {"code": "failed", "message": str(exc)}})

    def _events(self) -> None:
        """`GET /_api/events?session=<id>&since=<seq>`: what has landed in a session's inbox since a sequence number.

        **Fine events for appends, coarse for everything else** (plan 0.13 §8). A message is the smallest unit loom can stream -- it never sees the model, so a "typing" feel could only come from an agent writing partial messages -- and everything else a reader needs still arrives through the manifest it already polls. Rebuilding the whole manifest per message would reintroduce the re-render that closed open boxes under the reader.

        The answer carries `seq`, so a client that finds a gap between what it has and what it is given knows it missed some and resyncs the coarse way rather than stitching a stream together from the middle.
        """
        from urllib.parse import parse_qs, urlsplit

        from loom.mailbox import last_seq, read_events

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
        events = read_events(self.quilt_root, sid, since)
        self._json(
            HTTPStatus.OK,
            {
                "session": sid,
                "from": since,
                "seq": last_seq(self.quilt_root, sid),
                "events": [e.to_json() for e in events],
            },
        )

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] == "/_api/events":
            self._events()
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
        """Bind the port and start serving. The build has not run yet, so `/build/` answers 503 until `start` finishes it."""
        handler = type(
            "Handler",
            (LoomHandler,),
            {
                "bundle_dir": self.bundle_dir,
                "build_dir": self.quilt.root / "build",
                "refs_dir": storage_root(self.quilt.root),
                # The write API is served for the quilt being served, and only ever over this loopback socket.
                "quilt_root": self.quilt.root,
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
    info = find_bundle()
    return info.path if info else None
