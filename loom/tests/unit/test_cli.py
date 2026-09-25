"""`loom --version` (book 12.2); `loom doctor` has its own file, `test_doctor.py`."""

from __future__ import annotations

from loom.version import __version__
from tests.helpers import ok


def test_cli_version() -> None:
    result = ok("--version")
    assert result.output.strip() == f"loom {__version__}"
