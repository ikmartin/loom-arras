"""What the client tier's tests share: the person's environment, read before the isolation every test runs under narrows it, and the gate that keeps the tier from spending unasked."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

#: The client is the person's, and runs with their login: their HOME, PATH and config directory, read at import.
PERSON = {k: os.environ[k] for k in ("HOME", "PATH", "XDG_CONFIG_HOME") if k in os.environ}


def gate(client: str | None, name: str) -> None:
    """Skip unless asked, and unless the client is installed: the tier spends on the person's account."""
    if os.environ.get("LOOM_CLIENT_TESTS") != "1":
        pytest.skip("LOOM_CLIENT_TESTS is not 1")
    if client is None:
        pytest.skip(f"{name} is not on PATH")


def person_env(first: Path | None = None) -> dict[str, str]:
    """The environment a client runs in: this one, with the person's HOME, PATH and config directory back, and `first` ahead on PATH."""
    env = {k: v for k, v in os.environ.items() if k != "XDG_CONFIG_HOME"} | PERSON
    path = PERSON.get("PATH", "/usr/bin:/bin")
    env["PATH"] = os.pathsep.join([str(first), path]) if first else path
    return env
