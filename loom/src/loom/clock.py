"""Timestamps, with LOOM_FIXED_TIME overriding the clock so fixtures are reproducible."""

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


def tex_date() -> dict[str, str]:
    """What a TeX run's environment takes so `\\today` prints LOOM_FIXED_TIME's date, as every other timestamp does under it; empty otherwise."""
    if not os.environ.get("LOOM_FIXED_TIME"):
        return {}
    return {"SOURCE_DATE_EPOCH": str(int(now().timestamp())), "FORCE_SOURCE_DATE": "1"}
