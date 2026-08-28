"""Comprehensive tests for Cortex rate limiting system.

Tests cover:
- TokenBucket: below/at/above limit, reset after window
- ConcurrencyLimiter: acquire, release, race condition, terminal state
- RateLimiter facade
- Identity resolution
- HTTP 429 responses via FastAPI TestClient
- Per-endpoint rate limits (jobs, chat, auth)
- User isolation (separate counters)
"""

import asyncio
import time
from unittest.mock import patch, MagicMock

import pytest

from shared.rate_limiter import TokenBucket, ConcurrencyLimiter, RateLimiter, RateLimitResult


# ═══════════════════════════════════════════════════════════════════════════════
# TokenBucket Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTokenBucket:
    """Tests for the core token bucket algorithm."""

    @pytest.fixture
    def bucket(self):
        """5 tokens per 10 seconds."""
        return TokenBucket(capacity=5, window_seconds=10)

    @pytest.mark.asyncio
    async def test_below_limit(self, bucket):
        """Requests below capacity should all be allowed."""
        for i in range(3):
            allowed, retry, remaining = await bucket.consume("user1")
            assert allowed is True
            assert retry == 0.0
            assert remaining == 5 - (i + 1)

    @pytest.mark.asyncio
    async def test_exactly_at_limit(self, bucket):
        """Using all tokens should succeed for exactly capacity requests."""
        for _ in range(5):
            allowed, _, _ = await bucket.consume("user1")
            assert allowed is True

    @pytest.mark.asyncio
    async def test_above_limit(self, bucket):
        """Request after exhausting tokens should be denied."""
        # Exhaust all 5 tokens
        for _ in range(5):
            await bucket.consume("user1")

        # 6th request should be denied
        allowed, retry, remaining = await bucket.consume("user1")
        assert allowed is False
        assert retry > 0
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_retry_after_value(self, bucket):
        """Retry-after should indicate when next token is available."""
        for _ in range(5):
            await bucket.consume("user1")

        _, retry, _ = await bucket.consume("user1")
        # Refill rate = 5/10 = 0.5 tokens/sec → 1 token takes 2 seconds
        assert 1.5 <= retry <= 2.5

    @pytest.mark.asyncio
    async def test_reset_after_window(self, bucket):
        """Tokens should refill over time."""
        # Exhaust tokens
        for _ in range(5):
            await bucket.consume("user1")

        # Simulate time passing (monkey-patch time.monotonic)
        original_monotonic = time.monotonic
        offset = 10.0  # Full window
        with patch("time.monotonic", side_effect=lambda: original_monotonic() + offset):
            allowed, _, remaining = await bucket.consume("user1")
            assert allowed is True
            # Should have refilled to capacity - 1 (after consuming one)
            assert remaining == 4

    @pytest.mark.asyncio
    async def test_separate_keys(self, bucket):
        """Different keys should have independent buckets."""
        # Exhaust user1
        for _ in range(5):
            await bucket.consume("user1")
        allowed, _, _ = await bucket.consume("user1")
        assert allowed is False

        # user2 should still have full capacity
        allowed, _, remaining = await bucket.consume("user2")
        assert allowed is True
        assert remaining == 4

    @pytest.mark.asyncio
    async def test_partial_refill(self, bucket):
        """Partial time should partially refill tokens."""
        # Use 3 tokens
        for _ in range(3):
            await bucket.consume("user1")

        # Simulate 4 seconds passing → 2 tokens refilled (0.5/sec * 4s)
        original_monotonic = time.monotonic
        offset = 4.0
        with patch("time.monotonic", side_effect=lambda: original_monotonic() + offset):
            allowed, _, remaining = await bucket.consume("user1")
            assert allowed is True
            # Had 2 remaining + 2 refilled - 1 consumed = 3
            assert remaining == 3

    @pytest.mark.asyncio
    async def test_peek_does_not_consume(self, bucket):
        """Peek should return remaining without consuming."""
        remaining = await bucket.peek("user1")
        assert remaining == 5

        await bucket.consume("user1")
        remaining = await bucket.peek("user1")
        assert remaining == 4

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, bucket):
        """Concurrent requests should not exceed capacity due to locking."""
        # Fire 10 concurrent requests with capacity 5
        results = await asyncio.gather(*[bucket.consume("user1") for _ in range(10)])
        allowed_count = sum(1 for allowed, _, _ in results if allowed)
        denied_count = sum(1 for allowed, _, _ in results if not allowed)
        assert allowed_count == 5
        assert denied_count == 5

    @pytest.mark.asyncio
    async def test_reset(self, bucket):
        """Reset should clear a key's state."""
        for _ in range(5):
            await bucket.consume("user1")
        allowed, _, _ = await bucket.consume("user1")
        assert allowed is False

        await bucket.reset("user1")
        allowed, _, _ = await bucket.consume("user1")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_cleanup_stale_entries(self):
        """Stale entries should be cleaned up after threshold."""
        bucket = TokenBucket(capacity=5, window_seconds=10, cleanup_interval=0)

        await bucket.consume("stale_user")

        # Simulate time far in the future
        original_monotonic = time.monotonic
        offset = 100.0
        with patch("time.monotonic", side_effect=lambda: original_monotonic() + offset):
            # Trigger cleanup via another consume
            await bucket.consume("active_user")
            # stale_user should have been cleaned
            remaining = await bucket.peek("stale_user")
            assert remaining == 5  # Fresh bucket = full capacity


# ═══════════════════════════════════════════════════════════════════════════════
# ConcurrencyLimiter Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestConcurrencyLimiter:
    """Tests for the concurrent slot limiter."""

    @pytest.fixture
    def limiter(self):
        return ConcurrencyLimiter(max_concurrent=3)

    @pytest.mark.asyncio
    async def test_acquire_below_limit(self, limiter):
        """Should allow acquisition below max."""
        acquired, count = await limiter.acquire("user1")
        assert acquired is True
        assert count == 1

    @pytest.mark.asyncio
    async def test_acquire_at_limit(self, limiter):
        """Should allow exactly max_concurrent slots."""
        for i in range(3):
            acquired, count = await limiter.acquire("user1")
            assert acquired is True
            assert count == i + 1

    @pytest.mark.asyncio
    async def test_acquire_above_limit(self, limiter):
        """Should deny acquisition above max."""
        for _ in range(3):
            await limiter.acquire("user1")

        acquired, count = await limiter.acquire("user1")
        assert acquired is False
        assert count == 3

    @pytest.mark.asyncio
    async def test_release_frees_slot(self, limiter):
        """Releasing a slot should allow new acquisition."""
        for _ in range(3):
            await limiter.acquire("user1")

        # Full — denied
        acquired, _ = await limiter.acquire("user1")
        assert acquired is False

        # Release one
        await limiter.release("user1")

        # Should now succeed
        acquired, count = await limiter.acquire("user1")
        assert acquired is True
        assert count == 3

    @pytest.mark.asyncio
    async def test_release_below_zero(self, limiter):
        """Releasing when nothing is acquired should not go negative."""
        await limiter.release("user1")
        count = await limiter.active_count("user1")
        assert count == 0

    @pytest.mark.asyncio
    async def test_concurrent_race_condition(self, limiter):
        """Concurrent acquires should not exceed max due to locking."""
        results = await asyncio.gather(*[limiter.acquire("user1") for _ in range(10)])
        acquired_count = sum(1 for acquired, _ in results if acquired)
        assert acquired_count == 3

    @pytest.mark.asyncio
    async def test_separate_users(self, limiter):
        """Different users should have independent slots."""
        for _ in range(3):
            await limiter.acquire("user1")

        # user1 full
        acquired, _ = await limiter.acquire("user1")
        assert acquired is False

        # user2 should be fine
        acquired, count = await limiter.acquire("user2")
        assert acquired is True
        assert count == 1

    @pytest.mark.asyncio
    async def test_active_count(self, limiter):
        """active_count should reflect current state."""
        assert await limiter.active_count("user1") == 0
        await limiter.acquire("user1")
        assert await limiter.active_count("user1") == 1
        await limiter.acquire("user1")
        assert await limiter.active_count("user1") == 2
        await limiter.release("user1")
        assert await limiter.active_count("user1") == 1


# ═══════════════════════════════════════════════════════════════════════════════
# RateLimiter Facade Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRateLimiter:
    """Tests for the high-level RateLimiter facade."""

    @pytest.fixture
    def limiter(self):
        return RateLimiter(
            name="test",
            capacity=3,
            window_seconds=60,
            error_type="test_limit_exceeded",
            message="Test limit reached.",
        )

    @pytest.mark.asyncio
    async def test_check_allowed(self, limiter):
        """Should return allowed=True below limit."""
        result = await limiter.check("user1")
        assert result.allowed is True
        assert result.retry_after == 0.0
        assert result.remaining == 2

    @pytest.mark.asyncio
    async def test_check_denied(self, limiter):
        """Should return allowed=False and error info above limit."""
        for _ in range(3):
            await limiter.check("user1")

        result = await limiter.check("user1")
        assert result.allowed is False
        assert result.retry_after > 0
        assert result.error_type == "test_limit_exceeded"
        assert result.message == "Test limit reached."

    @pytest.mark.asyncio
    async def test_remaining(self, limiter):
        """remaining() should peek without consuming."""
        assert await limiter.remaining("user1") == 3
        await limiter.check("user1")
        assert await limiter.remaining("user1") == 2


# ═══════════════════════════════════════════════════════════════════════════════
# Identity Resolution Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestIdentityResolution:
    """Tests for identity resolution logic."""

    def test_resolve_with_user_id(self):
        """Should prefer user_id when available."""
        from shared.identity import resolve_identity

        request = MagicMock()
        request.state.user_id = "user-123"
        request.client.host = "192.168.1.1"

        result = resolve_identity(request)
        assert result == "user:user-123"

    def test_resolve_with_ip_only(self):
        """Should fall back to IP when no user_id."""
        from shared.identity import resolve_identity

        request = MagicMock()
        request.state.user_id = None
        request.client.host = "10.0.0.5"

        result = resolve_identity(request)
        assert result == "ip:10.0.0.5"

    def test_resolve_ip_identity(self):
        """resolve_ip_identity should always use IP."""
        from shared.identity import resolve_ip_identity

        request = MagicMock()
        request.state.user_id = "user-999"
        request.client.host = "172.16.0.1"

        result = resolve_ip_identity(request)
        assert result == "ip:172.16.0.1"

    def test_resolve_no_client(self):
        """Should handle missing client gracefully."""
        from shared.identity import resolve_identity

        request = MagicMock()
        request.state.user_id = None
        request.client = None

        result = resolve_identity(request)
        assert result == "ip:unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# HTTP 429 Integration Tests (FastAPI TestClient)
# ═══════════════════════════════════════════════════════════════════════════════


class TestHTTP429Integration:
    """Integration tests verifying actual HTTP 429 responses via TestClient."""

    @pytest.fixture
    async def client(self):
        """Create a fresh test client with isolated rate limiters."""
        # Clear cached settings and limiters for isolated tests
        from cortex.config import get_settings
        from shared.rate_limiters import (
            get_global_limiter,
            get_jobs_limiter,
            get_jobs_concurrency_limiter,
            get_chat_limiter,
            get_login_limiter,
            get_password_reset_limiter,
            get_verify_resend_limiter,
        )

        # Clear all caches
        get_settings.cache_clear()
        get_global_limiter.cache_clear()
        get_jobs_limiter.cache_clear()
        get_jobs_concurrency_limiter.cache_clear()
        get_chat_limiter.cache_clear()
        get_login_limiter.cache_clear()
        get_password_reset_limiter.cache_clear()
        get_verify_resend_limiter.cache_clear()

        # Patch settings for tight test limits
        import os
        os.environ["RATE_LIMIT_GLOBAL_REQUESTS"] = "100"
        os.environ["RATE_LIMIT_GLOBAL_WINDOW_SECONDS"] = "60"
        os.environ["RATE_LIMIT_JOBS_REQUESTS"] = "2"
        os.environ["RATE_LIMIT_JOBS_WINDOW_SECONDS"] = "60"
        os.environ["RATE_LIMIT_JOBS_CONCURRENT"] = "2"
        os.environ["RATE_LIMIT_CHAT_REQUESTS"] = "3"
        os.environ["RATE_LIMIT_CHAT_WINDOW_SECONDS"] = "60"
        os.environ["RATE_LIMIT_LOGIN_REQUESTS"] = "2"
        os.environ["RATE_LIMIT_LOGIN_WINDOW_SECONDS"] = "60"
        os.environ["RATE_LIMIT_PASSWORD_RESET_REQUESTS"] = "2"
        os.environ["RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS"] = "60"
        os.environ["RATE_LIMIT_VERIFY_RESEND_REQUESTS"] = "2"
        os.environ["RATE_LIMIT_VERIFY_RESEND_WINDOW_SECONDS"] = "60"
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_rate_limit.db"

        get_settings.cache_clear()

        from httpx import AsyncClient, ASGITransport
        from cortex.main import create_app

        app = create_app()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Trigger lifespan manually to create tables
            async with app.router.lifespan_context(app):
                yield client

        # Cleanup env vars and test db
        import pathlib
        pathlib.Path("test_rate_limit.db").unlink(missing_ok=True)
        for key in list(os.environ.keys()):
            if key.startswith("RATE_LIMIT_") or key == "DATABASE_URL":
                del os.environ[key]
        get_settings.cache_clear()
        get_global_limiter.cache_clear()
        get_jobs_limiter.cache_clear()
        get_jobs_concurrency_limiter.cache_clear()
        get_chat_limiter.cache_clear()
        get_login_limiter.cache_clear()
        get_password_reset_limiter.cache_clear()
        get_verify_resend_limiter.cache_clear()

    @pytest.mark.asyncio
    async def test_login_rate_limit(self, client):
        """Login should be rate-limited after configured attempts."""
        payload = {"email": "test@example.com", "password": "wrongpassword"}

        # First 2 attempts should get through (even if auth fails)
        for _ in range(2):
            resp = await client.post("/api/v1/auth/login", json=payload)
            assert resp.status_code in (401, 403)  # Auth failure, not rate limit

        # 3rd attempt should be rate-limited
        resp = await client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] == "rate_limit_exceeded"
        assert "retry_after" in body
        assert "Retry-After" in resp.headers

    @pytest.mark.asyncio
    async def test_password_reset_rate_limit(self, client):
        """Password reset should be rate-limited."""
        payload = {"email": "test@example.com"}

        for _ in range(2):
            resp = await client.post("/api/v1/auth/forgot-password", json=payload)
            assert resp.status_code == 200

        resp = await client.post("/api/v1/auth/forgot-password", json=payload)
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] == "rate_limit_exceeded"

    @pytest.mark.asyncio
    async def test_verify_resend_rate_limit(self, client):
        """Verification resend should be rate-limited."""
        payload = {"email": "test@example.com"}

        for _ in range(2):
            resp = await client.post("/api/v1/auth/resend-verification", json=payload)
            # Might fail with 400 (no such user) — that's fine, we're testing rate limit
            assert resp.status_code in (200, 400)

        resp = await client.post("/api/v1/auth/resend-verification", json=payload)
        assert resp.status_code == 429

    @pytest.mark.asyncio
    async def test_chat_rate_limit(self, client):
        """Chat should be rate-limited after configured messages."""
        payload = {"job_id": "fake-job-id", "message": "hello"}

        for _ in range(3):
            resp = await client.post("/api/v1/chat/stream", json=payload)
            # May get 404 (no session) — that's fine, rate limit is checked first
            assert resp.status_code != 429

        resp = await client.post("/api/v1/chat/stream", json=payload)
        assert resp.status_code == 429
        body = resp.json()
        assert body["error"] == "rate_limit_exceeded"
        assert "chat" in body["message"].lower() or "request" in body["message"].lower()

    @pytest.mark.asyncio
    async def test_jobs_rate_limit(self, client):
        """Job submission should be rate-limited."""
        payload = {
            "repo_url": "https://github.com/test/unique-repo-1",
            "artifact_type": "folder_structure",
        }

        for i in range(2):
            payload["repo_url"] = f"https://github.com/test/repo-{i}"
            resp = await client.post("/api/v1/jobs", json=payload)
            # Job may succeed (201) or hit existing duplicate (200) — both fine
            assert resp.status_code in (201, 200)

        # 3rd should be rate limited
        payload["repo_url"] = "https://github.com/test/repo-extra"
        resp = await client.post("/api/v1/jobs", json=payload)
        assert resp.status_code == 429

    @pytest.mark.asyncio
    async def test_429_response_structure(self, client):
        """429 responses should have correct JSON structure and headers."""
        payload = {"email": "test@example.com", "password": "wrong"}

        # Exhaust login limit
        for _ in range(2):
            await client.post("/api/v1/auth/login", json=payload)

        resp = await client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 429

        body = resp.json()
        assert "error" in body
        assert "message" in body
        assert "retry_after" in body
        assert isinstance(body["retry_after"], int)
        assert body["retry_after"] >= 1
        assert "Retry-After" in resp.headers
        assert int(resp.headers["Retry-After"]) >= 1

    @pytest.mark.asyncio
    async def test_health_excluded_from_rate_limit(self, client):
        """Health endpoint should never be rate-limited."""
        # Even after many requests, health should respond
        for _ in range(110):
            resp = await client.get("/api/v1/health")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_global_rate_limit_x_ratelimit_remaining_header(self, client):
        """Successful responses should include X-RateLimit-Remaining header."""
        resp = await client.get("/api/v1/health")
        # Health is excluded from rate limiting, so no header
        # Try a non-excluded endpoint
        resp = await client.get("/api/v1/jobs")
        if resp.status_code == 200:
            assert "X-RateLimit-Remaining" in resp.headers
