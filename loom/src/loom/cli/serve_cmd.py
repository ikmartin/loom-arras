"""`loom serve [--port N] [--open] [--no-compile]`."""

from __future__ import annotations

import time
import webbrowser

import click

from loom.cli._common import EnvError, note
from loom.cli._quilt import open_quilt, quilt_option
from loom.render.serve import DEFAULT_PORT, ServeSession, locate_bundle, open_url


@click.command()
@click.option("--port", default=DEFAULT_PORT, show_default=True, help="Port to listen on; fails if busy.")
@click.option("--open", "open_browser", is_flag=True, help="Open the browser.")
@click.option("--no-compile", is_flag=True, help="Never run latexmk after a change.")
@quilt_option
def serve(port: int, open_browser: bool, no_compile: bool, quilt_path: str | None) -> None:
    """Serve the viewer for this quilt and keep it current: it republishes on every change until interrupted.

    The viewer is at /, and the build directory it reads at /build/. One server runs per quilt.
    """
    from loom.arras_bundle import BundleEnvError

    quilt = open_quilt(quilt_path)
    try:
        bundle = locate_bundle()
    except BundleEnvError as e:
        raise EnvError(f"{e}: point it at a built arras (the directory holding index.html), or unset it") from None
    if bundle is None:
        raise EnvError(
            "the arras viewer bundle is not installed: set LOOM_ARRAS_BUNDLE, or use a loom checkout with the vendored bundle"
        )
    running = open_url(quilt.root)
    if running:
        # two servers on one quilt rebuild after each other's writes and hand out two tokens for one write API
        raise EnvError(f"loom serve is already running for this quilt at {running}; open that, or stop it first")
    session = ServeSession(quilt, bundle, port, compile_masters=not no_compile)
    try:
        session.listen()
    except OSError as exc:
        why = exc.strerror or str(exc)
        raise EnvError(
            f"cannot listen on port {port}: {why}; pass --port N for another, or stop what holds it"
        ) from exc
    # the URL first: a cold first build compiles every block the converter cannot translate, and a silent wait looks like a hang
    note(f"loom serve: {session.url}  (build directory at {session.url}build/; Ctrl-C to stop)")
    if open_browser:
        webbrowser.open(session.url)
    # A terminal closed or a `kill` stops a server with SIGTERM, not Ctrl-C; either way it stops cleanly, so `.loom/serve.json` never tells a command that something is still listening.
    import signal

    def _term(*_: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _term)
    session.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        note("loom serve: stopping")
    finally:
        session.stop()
