"""`loom serve` (book 9.8): one loop with three jobs, watch, serve, compile.

Serves the arras bundle at / (with index.html as the fallback for any path without an extension, so the viewer's routes work) and build/ at /build/. The manifest carries an ETag so the viewer's poll costs nothing while unchanged. Loom never notifies the viewer; the viewer polls.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import sys
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from loom.arras_bundle import find_bundle
from loom.render.build import build
from loom.render.watch import Watcher
from loom.scan.quilt import Quilt
from loom.tex.runner import compile_tex, normalise_engine

DEFAULT_PORT = 8791


class LoomHandler(SimpleHTTPRequestHandler):
    bundle_dir: Path = Path(".")
    build_dir: Path = Path(".")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        if os.environ.get("LOOM_SERVE_LOG"):
            super().log_message(format, *args)

    def _resolve(self) -> Path | None:
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path.startswith("/build/"):
            rel = path[len("/build/") :]
            target = (self.build_dir / rel).resolve()
            return target if str(target).startswith(str(self.build_dir.resolve())) and target.is_file() else None
        if path == "/_api":
            return None
        rel = path.lstrip("/")
        target = (self.bundle_dir / rel).resolve() if rel else self.bundle_dir / "index.html"
        if str(target).startswith(str(self.bundle_dir.resolve())):
            if target.is_file():
                return target
            if target.is_dir() and (target / "index.html").is_file():
                return target / "index.html"
        if "." not in Path(rel).name:
            return self.bundle_dir / "index.html"
        return None

    def do_GET(self) -> None:  # noqa: N802
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

    def rebuild(self, changed: list[Path] | None = None) -> None:
        with self.lock:
            report = build(self.quilt)
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

    def start(self) -> None:
        handler = type(
            "Handler", (LoomHandler,), {"bundle_dir": self.bundle_dir, "build_dir": self.quilt.root / "build"}
        )
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.port = self.httpd.server_address[1]
        self.rebuild()
        self.watcher = Watcher(self.quilt.root, self.rebuild, self.interval)
        self.watcher.start()
        threading.Thread(target=self.httpd.serve_forever, name="loom-http", daemon=True).start()

    def stop(self) -> None:
        if self.watcher:
            self.watcher.stop()
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"


def locate_bundle() -> Path | None:
    info = find_bundle()
    return info.path if info else None
