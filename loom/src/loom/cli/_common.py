"""Shared CLI plumbing: exit codes, JSON output, and the two error classes every command raises.

Exit codes follow the book's 12.1: 0 success, 1 a content problem the author can fix in the source, 2 a usage or environment problem.
"""

from __future__ import annotations

import json
from typing import Any

import click

EXIT_OK = 0
EXIT_CONTENT = 1
EXIT_USAGE = 2


class ContentError(click.ClickException):
    """A problem in the quilt's content (lint errors, failed identity test, refused write). Exit 1."""

    exit_code = EXIT_CONTENT

    def format_message(self) -> str:
        return self.message


class EnvError(click.ClickException):
    """A usage or environment problem (bad arguments, missing tool, no author name). Exit 2."""

    exit_code = EXIT_USAGE

    def format_message(self) -> str:
        return self.message


def emit_json(obj: Any) -> None:
    """Print one JSON document to stdout and nothing else there; diagnostics go to stderr."""
    click.echo(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def note(message: str) -> None:
    """Progress or diagnostic text, always on stderr so --json stdout stays clean."""
    click.echo(message, err=True)
