"""The operator password guarding every /admin route (specs/LEARN.md §6.1.1).

HTTP Basic authentication, checked by one dependency (`require_admin`) that
the /admin router applies to all of its routes, so no route can forget it.
The username is ignored. With no password configured, /admin does not exist:
every route answers 404, so forgetting to configure it never exposes the page.
"""
from __future__ import annotations

import base64
import binascii
import os
import pathlib
import secrets
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

MAX_FAILURES = 5
WINDOW_SECONDS = 60.0


def admin_password() -> str | None:
    """`ADMIN_PASSWORD_FILE` wins over `ADMIN_PASSWORD`; unset or empty is None.
    Read per request, so a changed secret needs no restart."""
    path = os.environ.get("ADMIN_PASSWORD_FILE")
    value = pathlib.Path(path).read_text().strip() if path else os.environ.get("ADMIN_PASSWORD")
    return value or None


class FailureLimiter:
    """After MAX_FAILURES failures from one client address within
    WINDOW_SECONDS, refuse further attempts until the oldest of them ages out.
    In memory, per process; enough for one uvicorn process, reset on restart."""

    def __init__(self, max_failures: int = MAX_FAILURES, window: float = WINDOW_SECONDS):
        self.max_failures = max_failures
        self.window = window
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()  # sync dependencies run on the thread pool

    def _prune(self, client: str, now: float) -> deque[float]:
        q = self._failures.setdefault(client, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        return q

    def blocked(self, client: str) -> bool:
        with self._lock:
            return len(self._prune(client, time.monotonic())) >= self.max_failures

    def record_failure(self, client: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(client, now).append(now)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


limiter = FailureLimiter()


def basic_password(request: Request) -> str | None:
    """The password half of a Basic `Authorization` header, or None when there
    is none or it is malformed. Parsed here rather than by FastAPI's HTTPBasic,
    which answers 401 on its own before this module can say 404, and decodes
    as ASCII only; browsers send UTF-8 (or Latin-1, from older ones)."""
    scheme, _, param = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "basic":
        return None
    try:
        raw = base64.b64decode(param.strip(), validate=True)
    except (binascii.Error, ValueError):
        return None
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        decoded = raw.decode("latin-1")
    _user, sep, password = decoded.partition(":")
    return password if sep else None


def require_admin(request: Request) -> None:
    password = admin_password()
    if password is None:
        raise HTTPException(status_code=404, detail="Not Found")
    client = request.client.host if request.client else "unknown"
    # Before the password check: a locked-out client is refused even with
    # the right password, or the lockout would be a guessing oracle.
    if limiter.blocked(client):
        raise HTTPException(status_code=429, detail="too many failed attempts")
    challenge = {"WWW-Authenticate": 'Basic realm="admin", charset="UTF-8"'}
    given = basic_password(request)
    if given is None:
        # A browser's first request never carries credentials: not a failure.
        raise HTTPException(status_code=401, headers=challenge)
    if not secrets.compare_digest(given.encode(), password.encode()):
        limiter.record_failure(client)
        raise HTTPException(status_code=401, headers=challenge)
