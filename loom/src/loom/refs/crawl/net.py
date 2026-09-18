"""A polite client for one service: spaced requests, cached answers, an injected transport (book 8.13.2).

Every crawl client goes through this, so the spacing a service asks for and the cache that makes a second plan fast are the same everywhere, and tests replace the transport rather than the network.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from loom.version import __version__

USER_AGENT = f"loom/{__version__} (+https://github.com/ikmartin/loom)"

Transport = Callable[[str, dict[str, str]], bytes]


class ServiceError(Exception):
    """A service could not be reached or refused the request."""


class NotFound(ServiceError):
    """The service answered that it has no such record."""


def http(url: str, headers: dict[str, str]) -> bytes:
    """GET with loom's User-Agent; the default transport."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return bytes(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NotFound(url.split("?")[0]) from exc
        raise ServiceError(f"{url.split('?')[0]}: HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ServiceError(f"{url.split('?')[0]}: {exc.reason}") from exc


class Service:
    """One service's requests: at least `spacing` seconds apart, and answered from `cache` when asked before.

    Parameters
    ----------
    name : str
        Names the cache directory and the counters.
    spacing : float
        Seconds between two requests that reach the network.
    cache : Path or None, default None
        A directory of raw answers keyed by URL. Headers are not part of the key, so a key sent as a header never names a file.
    transport : callable, default `http`
    refresh : bool, default False
        Ignore cached answers.
    """

    def __init__(
        self, name: str, spacing: float, cache: Path | None = None, transport: Transport = http, refresh: bool = False
    ) -> None:
        self.name = name
        self.spacing = spacing
        self.cache = cache / name if cache else None
        self.transport = transport
        self.refresh = refresh
        self.requests = 0
        self.cached = 0
        self.failures = 0
        self.last_failure = ""
        self._last = 0.0

    def _path(self, url: str) -> Path | None:
        return self.cache / (hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]) if self.cache else None

    def get(self, url: str, headers: dict[str, str] | None = None) -> bytes:
        """The body at `url`; NotFound is cached too, so a record known to be absent is not asked for again."""
        path = self._path(url)
        if path is not None and not self.refresh:
            if path.with_suffix(".absent").is_file():
                self.cached += 1
                raise NotFound(url.split("?")[0])
            if path.is_file():
                self.cached += 1
                return path.read_bytes()
        wait = self._last + self.spacing - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        self.requests += 1
        try:
            body = self.transport(url, headers or {})
        except NotFound:
            if path is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.with_suffix(".absent").write_text(url, encoding="utf-8")
            raise
        except ServiceError as exc:
            self.failures += 1
            self.last_failure = str(exc)
            raise
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        return body

    def get_json(self, url: str, headers: dict[str, str] | None = None) -> Any:
        try:
            return json.loads(self.get(url, headers).decode("utf-8"))
        except ValueError as exc:
            raise ServiceError(f"{self.name}: an answer that is not JSON from {url.split('?')[0]}") from exc
