"""In-process token bucket rate limiter with asyncio-safe locking.

Rate limiting state is process-local and is not shared across multiple workers.
When Cortex runs multiple workers, this must be replaced with a shared-state
implementation (e.g. Redis-backed sliding window).

Design:
- TokenBucket: core algorithm — tracks tokens per key with refill over time.
- RateLimiter: reusable facade wrapping a TokenBucket with named configuration.
- ConcurrencyLimiter: tracks active slots (not rate-based) with atomic acquire/release.
- Automatic stale-entry cleanup on every check cycle to bound memory usage.

All public methods are async and use asyncio.Lock for thread-safety under
concurrent requests within the single event loop.
"""

import asyncio
import time
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()

# ── Token Bucket Core ────────────────────────────────────────────────────────


@dataclass
class _BucketState:
    """State for a single key's token bucket."""

    tokens: float
    last_refill: float
    # Track for memory cleanup
    last_access: float


class TokenBucket:
    """Generic token bucket rate limiter.

    Each key gets an independent bucket with `capacity` tokens that refill
    at `capacity / window_seconds` tokens per second.

    Thread-safe via asyncio.Lock. Stale entries are cleaned periodically.
    """

    def __init__(
        self,
        capacity: int,
        window_seconds: int,
        *,
        cleanup_interval: int = 300,
    ) -> None:
        self._capacity = capacity
        self._window_seconds = window_seconds
        self._refill_rate = capacity / window_seconds  # tokens per second
        self._buckets: dict[str, _BucketState] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.monotonic()

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def window_seconds(self) -> int:
        return self._window_seconds

    async def consume(self, key: str) -> tuple[bool, float, int]:
        """Try to consume one token for the given key.

        Returns:
            (allowed, retry_after_seconds, remaining_tokens)
            - allowed: True if the request is permitted
            - retry_after: seconds until a token is available (0 if allowed)
            - remaining: tokens remaining after this request
        """
        async with self._lock:
            now = time.monotonic()
            self._maybe_cleanup(now)

            bucket = self._buckets.get(key)
            if bucket is None:
                # First request for this key — full bucket minus one
                bucket = _BucketState(
                    tokens=self._capacity - 1,
                    last_refill=now,
                    last_access=now,
                )
                self._buckets[key] = bucket
                return True, 0.0, int(bucket.tokens)

            # Refill tokens based on elapsed time
            elapsed = now - bucket.last_refill
            refilled = bucket.tokens + (elapsed * self._refill_rate)
            bucket.tokens = min(refilled, self._capacity)
            bucket.last_refill = now
            bucket.last_access = now

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True, 0.0, int(bucket.tokens)

            # Denied — calculate retry_after
            deficit = 1 - bucket.tokens
            retry_after = deficit / self._refill_rate
            return False, retry_after, 0

    async def peek(self, key: str) -> int:
        """Return remaining tokens for a key without consuming."""
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets.get(key)
            if bucket is None:
                return self._capacity
            elapsed = now - bucket.last_refill
            refilled = bucket.tokens + (elapsed * self._refill_rate)
            return int(min(refilled, self._capacity))

    async def reset(self, key: str) -> None:
        """Remove a key's bucket (used in testing)."""
        async with self._lock:
            self._buckets.pop(key, None)

    def _maybe_cleanup(self, now: float) -> None:
        """Remove stale entries older than 2x the window. Called under lock."""
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        stale_threshold = now - (self._window_seconds * 2)
        stale_keys = [
            k for k, v in self._buckets.items() if v.last_access < stale_threshold
        ]
        for k in stale_keys:
            del self._buckets[k]
        if stale_keys:
            logger.debug("rate_limiter_cleanup", removed=len(stale_keys))


# ── Concurrency Limiter ──────────────────────────────────────────────────────


class ConcurrencyLimiter:
    """Tracks active concurrent slots per key.

    Unlike TokenBucket (rate-based), this tracks how many operations
    are currently in-flight. Slots are acquired atomically and released
    when the operation completes (success or failure).

    Thread-safe via asyncio.Lock.
    """

    def __init__(self, max_concurrent: int) -> None:
        self._max = max_concurrent
        self._active: dict[str, int] = {}
        self._lock = asyncio.Lock()

    @property
    def max_concurrent(self) -> int:
        return self._max

    async def acquire(self, key: str) -> tuple[bool, int]:
        """Try to acquire a slot.

        Returns:
            (acquired, current_count)
            - acquired: True if a slot was granted
            - current_count: active slots for this key after the operation
        """
        async with self._lock:
            current = self._active.get(key, 0)
            if current >= self._max:
                return False, current
            self._active[key] = current + 1
            return True, current + 1

    async def release(self, key: str) -> None:
        """Release a slot when operation completes."""
        async with self._lock:
            current = self._active.get(key, 0)
            if current <= 1:
                self._active.pop(key, None)
            else:
                self._active[key] = current - 1

    async def active_count(self, key: str) -> int:
        """Return current active count for a key."""
        async with self._lock:
            return self._active.get(key, 0)

    async def reset(self, key: str) -> None:
        """Reset a key (testing)."""
        async with self._lock:
            self._active.pop(key, None)


# ── RateLimiter Facade ───────────────────────────────────────────────────────


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    retry_after: float = 0.0
    remaining: int = 0
    error_type: str = "rate_limit_exceeded"
    message: str = "Too many requests. Please try again shortly."


class RateLimiter:
    """High-level facade for endpoint rate limiting.

    Wraps a TokenBucket with a descriptive name and default error messaging.
    Provides a clean interface for endpoint guards.
    """

    def __init__(
        self,
        name: str,
        capacity: int,
        window_seconds: int,
        *,
        error_type: str = "rate_limit_exceeded",
        message: str = "Too many requests. Please try again shortly.",
    ) -> None:
        self.name = name
        self._bucket = TokenBucket(capacity, window_seconds)
        self._error_type = error_type
        self._message = message

    async def check(self, key: str) -> RateLimitResult:
        """Check and consume one token. Returns result with allow/deny info."""
        allowed, retry_after, remaining = await self._bucket.consume(key)

        if not allowed:
            logger.info(
                "rate_limit_hit",
                limiter=self.name,
                key=key[:32],  # truncate for safety
                retry_after=round(retry_after, 1),
            )

        return RateLimitResult(
            allowed=allowed,
            retry_after=retry_after,
            remaining=remaining,
            error_type=self._error_type,
            message=self._message,
        )

    async def remaining(self, key: str) -> int:
        """Peek at remaining tokens."""
        return await self._bucket.peek(key)

    async def reset(self, key: str) -> None:
        """Reset a key (testing)."""
        await self._bucket.reset(key)

    @property
    def capacity(self) -> int:
        return self._bucket.capacity

    @property
    def window_seconds(self) -> int:
        return self._bucket.window_seconds
