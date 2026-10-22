"""In-memory runtime primitives."""

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class MemoryLockStore:
    """Tiny process-local lock store for single-process deployments."""

    ttl_seconds: int
    locks: dict[str, float] = field(default_factory=dict)

    def acquire(self, key: str) -> bool:
        """Acquire a lock if missing or expired."""

        now = time.monotonic()
        expires_at = self.locks.get(key)
        if expires_at is not None and expires_at > now:
            return False
        self.locks[key] = now + self.ttl_seconds
        return True

    def release(self, key: str) -> None:
        """Release a lock."""

        self.locks.pop(key, None)


@dataclass(slots=True)
class MemoryRateLimiter:
    """Process-local fixed-window rate limiter."""

    ttl_seconds: int
    buckets: dict[str, tuple[int, float]] = field(default_factory=dict)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        """Return whether a keyed action is allowed."""

        now = time.monotonic()
        count, reset_at = self.buckets.get(key, (0, now + window_seconds))
        if reset_at <= now:
            count = 0
            reset_at = now + window_seconds
        if count >= limit:
            return False
        self.buckets[key] = (count + 1, reset_at)
        self._cleanup(now)
        return True

    def _cleanup(self, now: float) -> None:
        """Drop expired limiter buckets."""

        expired = [
            key for key, (_, reset_at) in self.buckets.items() if reset_at + self.ttl_seconds < now
        ]
        for key in expired:
            self.buckets.pop(key, None)
