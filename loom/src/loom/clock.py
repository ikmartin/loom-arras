"""Timestamps, with LOOM_FIXED_TIME overriding the clock so fixtures are reproducible (book 12.10)."""

from __future__ import annotations

import os
from datetime import UTC, datetime


def now() -> datetime:
    fixed = os.environ.get("LOOM_FIXED_TIME")
    if fixed:
        return datetime.fromisoformat(fixed.replace("Z", "+00:00")).astimezone(UTC)
    return datetime.now(UTC)


def today() -> str:
    return now().strftime("%Y-%m-%d")


def stamp() -> str:
    return now().strftime("%Y-%m-%dT%H:%M:%SZ")
