"""A copy of loom's synthetic quilt per test, and a server wired to capture what it publishes.

The quilt is copied rather than used in place so that nothing a test does can reach loom's own tree, and so that a test may edit files freely.
"""

from __future__ import annotations

import shutil
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest
from lsprotocol import types as lsp

from loom_lsp.server import LoomLanguageServer
from loom_lsp.workspace import uri_of

QUILTS = Path(__file__).resolve().parents[2] / "loom" / "tests" / "quilts"


def master_of(root: Path) -> Path:
    """The quilt's main master, as loom resolves it: `[quilt] main`, else `<drafting>/main.tex`.

    Mirrors QuiltConfig.from_dict without the user config, which a test never reads.
    """
    table = tomllib.loads((root / "config.toml").read_text(encoding="utf-8")).get("quilt", {})
    drafting = str(table.get("drafting", "drafting")).strip("/") or "drafting"
    return root / str(table.get("main", f"{drafting}/main.tex"))


def pytest_sessionstart(session: pytest.Session) -> None:
    """Stop the run once, naming the cause, when the synthetic quilt no longer has the master the suite opens."""
    main = master_of(QUILTS / "synthetic")
    if not main.is_file():
        pytest.exit(f"loom's synthetic quilt has no master at {main}; did the fixture layout change?", returncode=1)


@pytest.fixture
def quilt(tmp_path: Path) -> Path:
    dest = tmp_path / "synthetic"
    shutil.copytree(QUILTS / "synthetic", dest)
    return dest


@pytest.fixture
def master(quilt: Path) -> Path:
    """The copied quilt's main master."""
    return master_of(quilt)


@pytest.fixture
def demo(tmp_path: Path) -> Path:
    dest = tmp_path / "demo"
    shutil.copytree(QUILTS / "demo", dest)
    return dest


class Harness:
    """A server whose published diagnostics are captured instead of sent."""

    def __init__(self) -> None:
        self.server = LoomLanguageServer()
        self.published: dict[str, list[lsp.Diagnostic]] = {}
        self.server.text_document_publish_diagnostics = self._capture  # type: ignore[method-assign]

    def _capture(self, params: lsp.PublishDiagnosticsParams) -> None:
        self.published[params.uri] = list(params.diagnostics)

    def uri(self, path: Path) -> str:
        return uri_of(path)

    def open(self, path: Path, text: str | None = None) -> str:
        from loom_lsp.server import did_open

        uri = self.uri(path)
        body = path.read_text(encoding="utf-8") if text is None else text
        did_open(
            self.server,
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(uri=uri, language_id="tex", version=1, text=body)
            ),
        )
        return uri

    def change(self, path: Path, text: str) -> str:
        from loom_lsp.server import did_change

        uri = self.uri(path)
        did_change(
            self.server,
            lsp.DidChangeTextDocumentParams(
                text_document=lsp.VersionedTextDocumentIdentifier(uri=uri, version=2),
                content_changes=[lsp.TextDocumentContentChangeWholeDocument(text=text)],
            ),
        )
        # the change is debounced; a test wants the answer now
        root = self.server.workspace_for(uri)
        assert root is not None
        self.server.rescan_now(root.root)
        return uri

    def diagnostics(self, path: Path) -> list[lsp.Diagnostic]:
        return self.published.get(self.uri(path), [])

    def position_of(self, path: Path, needle: str, extra: int = 0) -> lsp.Position:
        """The LSP position of `needle` in the file, offset by `extra` characters."""
        from loom_lsp.encoding import Mapper

        m = Mapper(path.read_text(encoding="utf-8"), encoding=self.server.encoding)
        line, char = m.position(m.text.index(needle) + extra)
        return lsp.Position(line=line, character=char)


@pytest.fixture
def harness() -> Iterator[Harness]:
    h = Harness()
    yield h
