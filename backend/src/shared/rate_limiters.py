"""Singleton rate limiter instances for Cortex.

All limiters are created lazily on first access so they pick up the
current Settings values. The instances live for the process lifetime.

Rate limiting state is process-local and is not shared across multiple workers.
"""

from functools import lru_cache

from cortex.config import get_settings
from shared.rate_limiter import ConcurrencyLimiter, RateLimiter


@lru_cache
def get_global_limiter() -> RateLimiter:
    """Global API rate limiter — broad protection against flooding."""
    s = get_settings()
    return RateLimiter(
        name="global",
        capacity=s.rate_limit_global_requests,
        window_seconds=s.rate_limit_global_window_seconds,
        error_type="rate_limit_exceeded",
        message="Too many requests. Please try again shortly.",
    )


@lru_cache
def get_jobs_limiter() -> RateLimiter:
    """Job submission rate limiter."""
    s = get_settings()
    return RateLimiter(
        name="jobs",
        capacity=s.rate_limit_jobs_requests,
        window_seconds=s.rate_limit_jobs_window_seconds,
        error_type="rate_limit_exceeded",
        message="Too many analysis requests. Please wait before submitting another.",
    )


@lru_cache
def get_jobs_concurrency_limiter() -> ConcurrencyLimiter:
    """Concurrent analysis jobs limiter."""
    s = get_settings()
    return ConcurrencyLimiter(max_concurrent=s.rate_limit_jobs_concurrent)


@lru_cache
def get_chat_limiter() -> RateLimiter:
    """Chat message rate limiter."""
    s = get_settings()
    return RateLimiter(
        name="chat",
        capacity=s.rate_limit_chat_requests,
        window_seconds=s.rate_limit_chat_window_seconds,
        error_type="rate_limit_exceeded",
        message="Too many chat messages. Please wait a moment.",
    )


@lru_cache
def get_login_limiter() -> RateLimiter:
    """Login attempt rate limiter (IP-based)."""
    s = get_settings()
    return RateLimiter(
        name="login",
        capacity=s.rate_limit_login_requests,
        window_seconds=s.rate_limit_login_window_seconds,
        error_type="rate_limit_exceeded",
        message="Too many login attempts. Please try again later.",
    )


@lru_cache
def get_password_reset_limiter() -> RateLimiter:
    """Password reset rate limiter (IP-based)."""
    s = get_settings()
    return RateLimiter(
        name="password_reset",
        capacity=s.rate_limit_password_reset_requests,
        window_seconds=s.rate_limit_password_reset_window_seconds,
        error_type="rate_limit_exceeded",
        message="Too many password reset requests. Please try again later.",
    )


@lru_cache
def get_verify_resend_limiter() -> RateLimiter:
    """Email verification resend rate limiter (IP-based)."""
    s = get_settings()
    return RateLimiter(
        name="verify_resend",
        capacity=s.rate_limit_verify_resend_requests,
        window_seconds=s.rate_limit_verify_resend_window_seconds,
        error_type="rate_limit_exceeded",
        message="Too many verification requests. Please try again later.",
    )
