"""Auth dependency injection — singleton instances for FastAPI Depends."""

from functools import lru_cache

from cortex.auth.application.auth_service import AuthService
from cortex.auth.infrastructure.email_service import EmailService
from cortex.auth.infrastructure.repository import (
    SqlAlchemyPasswordResetTokenRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyVerificationTokenRepository,
)
from cortex.config import get_settings


@lru_cache
def _get_user_repo() -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository()


@lru_cache
def _get_verification_repo() -> SqlAlchemyVerificationTokenRepository:
    return SqlAlchemyVerificationTokenRepository()


@lru_cache
def _get_reset_repo() -> SqlAlchemyPasswordResetTokenRepository:
    return SqlAlchemyPasswordResetTokenRepository()


def get_auth_service() -> AuthService:
    settings = get_settings()
    return AuthService(
        user_repo=_get_user_repo(),
        verification_repo=_get_verification_repo(),
        reset_repo=_get_reset_repo(),
        settings=settings,
        email_service=EmailService(settings=settings),
    )
