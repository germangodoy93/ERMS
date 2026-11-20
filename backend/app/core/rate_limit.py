"""In-memory sliding-window counter of failed logins per IP.

Complements the per-account lockout: it slows down attempts spread over many accounts from
one address. It is per process (one backend instance on Railway today); with several
instances it should move to Redis.
"""

import threading
import time
from collections import defaultdict, deque


class FailureLimiter:
    def __init__(self, max_failures: int, window_seconds: int) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()
        return hits

    def retry_after(self, key: str) -> int:
        """Seconds until the key may try again; 0 if it is not blocked."""
        now = time.monotonic()
        with self._lock:
            hits = self._prune(key, now)
            if len(hits) < self.max_failures:
                return 0
            return max(1, int(hits[0] + self.window_seconds - now))

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
