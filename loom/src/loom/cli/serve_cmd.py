"""`loom serve [--port N] [--open] [--no-compile]` (book 12.5)."""

from __future__ import annotations

import time
import webbrowser

import click

from loom.cli._common import EnvError, note
from loom.cli._quilt import open_quilt, quilt_option
from loom.render.serve import DEFAULT_PORT, ServeSession, locate_bundle


@click.command()
@click.option("--port", default=DEFAULT_PORT, show_default=True, help="Port to listen on; fails if busy.")
@click.option("--open", "open_browser", is_flag=True, help="Open the browser.")
@click.option("--no-compile", is_flag=True, help="Never run latexmk after a change.")
@quilt_option
def serve(port: int, open_browser: bool, no_compile: bool, quilt_path: str | None) -> None:
    """Watch, republish, and serve arras at / and build/ at /build/ until interrupted."""
    quilt = open_quilt(quilt_path)
    bundle = locate_bundle()
    if bundle is None:
        raise EnvError(
            "the arras viewer bundle is not installed: set LOOM_ARRAS_BUNDLE, install the arras package, or use a loom checkout with the vendored bundle"
        )
    session = ServeSession(quilt, bundle, port, compile_masters=not no_compile)
    try:
        session.start()
    except OSError as exc:
        raise EnvError(f"cannot listen on port {port}: {exc}") from exc
    note(f"loom serve: {session.url}  (build directory at {session.url}build/; Ctrl-C to stop)")
    if open_browser:
        webbrowser.open(session.url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        note("loom serve: stopping")
    finally:
        session.stop()
