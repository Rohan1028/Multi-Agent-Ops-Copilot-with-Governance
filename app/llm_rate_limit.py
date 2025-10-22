from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict


class RateLimitExceeded(RuntimeError):
    pass


@dataclass
class Bucket:
    limit: int
    interval: float
    timestamps: Deque[float]
    lock: threading.Lock


class RateLimiter:
    """Simple in-memory rate limiter with per-key token buckets."""

    def __init__(self) -> None:
        self._buckets: Dict[str, Bucket] = {}
        self._global_lock = threading.Lock()

    def configure(self, key: str, *, per_minute: int) -> None:
        with self._global_lock:
            if per_minute <= 0:
                self._buckets.pop(key, None)
                return
            interval = 60.0 / per_minute
            self._buckets[key] = Bucket(
                limit=per_minute,
                interval=interval,
                timestamps=deque(),
                lock=threading.Lock(),
            )

    def _ensure_bucket(self, key: str) -> Bucket | None:
        return self._buckets.get(key)

    def acquire(self, key: str, *, block: bool = True, timeout: float | None = None) -> None:
        bucket = self._ensure_bucket(key)
        if bucket is None:
            return
        deadline = time.monotonic() + timeout if timeout is not None else None
        while True:
            with bucket.lock:
                now = time.monotonic()
                interval = 60.0 / bucket.limit if bucket.limit else 0.0
                while bucket.timestamps and now - bucket.timestamps[0] >= interval:
                    bucket.timestamps.popleft()
                if len(bucket.timestamps) < bucket.limit:
                    bucket.timestamps.append(now)
                    return
                if not block:
                    raise RateLimitExceeded(f"Rate limit exceeded for key {key}")
                oldest = bucket.timestamps[0]
                sleep_for = max(0.0, interval - (now - oldest))
            if deadline is not None and time.monotonic() + sleep_for > deadline:
                raise RateLimitExceeded(f"Rate limit timeout for key {key}")
            time.sleep(sleep_for)
