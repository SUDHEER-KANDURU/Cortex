"""Auth domain entities — pure data, no framework dependencies."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class User:
    id: str
    name: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass(frozen=True)
class EmailVerificationToken:
    id: str
    user_id: str
    token: str
    expires_at: datetime
    used: bool = False


@dataclass(frozen=True)
class PasswordResetToken:
    id: str
    user_id: str
    token: str
    expires_at: datetime
    used: bool = False
