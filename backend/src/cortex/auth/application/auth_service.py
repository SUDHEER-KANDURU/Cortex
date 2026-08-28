"""Auth application service — orchestrates registration, login, verification, password reset."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import structlog
from jose import JWTError, jwt
import bcrypt

if TYPE_CHECKING:
    from cortex.auth.infrastructure.email_service import EmailService

from cortex.auth.domain.entities import (
    EmailVerificationToken,
    PasswordResetToken,
    TokenPair,
    User,
)
from cortex.auth.domain.interfaces import (
    PasswordResetTokenRepository,
    UserRepository,
    VerificationTokenRepository,
)
from cortex.config import Settings
from shared.exceptions import CortexError

logger = structlog.get_logger()

# ── Password hashing ────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── Custom Exceptions ────────────────────────────────────────────────────────


class AuthError(CortexError):
    """Base auth error."""


class EmailAlreadyRegisteredError(AuthError):
    def __init__(self) -> None:
        super().__init__("An account with this email already exists.")


class InvalidCredentialsError(AuthError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password.")


class AccountNotVerifiedError(AuthError):
    def __init__(self) -> None:
        super().__init__("Please verify your email before logging in.")


class InvalidTokenError(AuthError):
    def __init__(self, detail: str = "Token is invalid or has expired.") -> None:
        super().__init__(detail)


class AccountDisabledError(AuthError):
    def __init__(self) -> None:
        super().__init__("This account has been disabled.")


# ── Auth Service ─────────────────────────────────────────────────────────────


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        verification_repo: VerificationTokenRepository,
        reset_repo: PasswordResetTokenRepository,
        settings: Settings,
        email_service: "EmailService | None" = None,
    ) -> None:
        self._users = user_repo
        self._verifications = verification_repo
        self._resets = reset_repo
        self._settings = settings
        self._email = email_service

    # ── Registration ─────────────────────────────────────────────────────

    async def register(
        self,
        name: str,
        email: str,
        password: str,
        organization: str | None = None,
        role: str | None = None,
        phone: str | None = None,
        date_of_birth: str | None = None,
        gender: str | None = None,
    ) -> tuple[User, str]:
        """Register a new user. Returns (user, verification_token)."""
        email_lower = email.lower().strip()
        existing = await self._users.get_by_email(email_lower)
        if existing:
            raise EmailAlreadyRegisteredError()

        user = User(
            id=str(uuid.uuid4()),
            name=name.strip(),
            email=email_lower,
            hashed_password=hash_password(password),
            is_active=True,
            is_verified=False,
            organization=organization.strip() if organization else None,
            role=role.strip() if role else None,
            phone=phone.strip() if phone else None,
            date_of_birth=date_of_birth.strip() if date_of_birth else None,
            gender=gender.strip() if gender else None,
        )
        user = await self._users.create(user)

        # Create verification token
        token = await self._create_verification_token(user.id)
        logger.info("user_registered", user_id=user.id, email=user.email)

        # Send verification email (non-blocking — don't fail registration if email fails)
        if self._email:
            await self._email.send_verification_email(
                to_email=user.email, name=user.name, token=token.token
            )

        return user, token.token

    # ── Login ────────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> TokenPair:
        """Authenticate user and return JWT token pair."""
        email_lower = email.lower().strip()
        user = await self._users.get_by_email(email_lower)

        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise AccountDisabledError()

        if not user.is_verified:
            raise AccountNotVerifiedError()

        tokens = self._create_token_pair(user.id, user.email)
        logger.info("user_logged_in", user_id=user.id)
        return tokens

    # ── Email Verification ───────────────────────────────────────────────

    async def verify_email(self, token_str: str) -> User:
        """Verify user email with the provided token."""
        token = await self._verifications.get_by_token(token_str)
        if not token:
            raise InvalidTokenError("Verification token not found.")

        if token.used:
            raise InvalidTokenError("This verification link has already been used.")

        now = datetime.now(timezone.utc)
        expires = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=timezone.utc)
        if now > expires:
            raise InvalidTokenError("Verification link has expired. Please request a new one.")

        # Mark token used
        await self._verifications.mark_used(token.id)

        # Activate user
        user = await self._users.get_by_id(token.user_id)
        if not user:
            raise InvalidTokenError("User not found.")

        updated_user = User(
            id=user.id,
            name=user.name,
            email=user.email,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
            is_verified=True,
            organization=user.organization,
            role=user.role,
            phone=user.phone,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        updated_user = await self._users.update(updated_user)
        logger.info("email_verified", user_id=user.id)
        return updated_user

    async def resend_verification(self, email: str) -> str:
        """Resend verification email. Returns new token."""
        email_lower = email.lower().strip()
        user = await self._users.get_by_email(email_lower)
        if not user:
            # Don't reveal if email exists
            raise InvalidTokenError("If this email is registered, a verification link will be sent.")

        if user.is_verified:
            raise InvalidTokenError("Email is already verified.")

        # Invalidate old tokens and create new
        await self._verifications.invalidate_for_user(user.id)
        token = await self._create_verification_token(user.id)
        logger.info("verification_resent", user_id=user.id)

        # Send verification email
        if self._email:
            await self._email.send_verification_email(
                to_email=user.email, name=user.name, token=token.token
            )

        return token.token

    # ── Forgot / Reset Password ──────────────────────────────────────────

    async def forgot_password(self, email: str) -> str | None:
        """Create a password reset token. Returns token or None if email not found."""
        email_lower = email.lower().strip()
        user = await self._users.get_by_email(email_lower)
        if not user:
            # Don't reveal if email exists — return None silently
            return None

        await self._resets.invalidate_for_user(user.id)
        token = await self._create_reset_token(user.id)
        logger.info("password_reset_requested", user_id=user.id)

        # Send password reset email
        if self._email:
            await self._email.send_password_reset_email(
                to_email=user.email, name=user.name, token=token.token
            )

        return token.token

    async def reset_password(self, token_str: str, new_password: str) -> User:
        """Reset password using a valid reset token."""
        token = await self._resets.get_by_token(token_str)
        if not token:
            raise InvalidTokenError("Reset token not found.")

        if token.used:
            raise InvalidTokenError("This reset link has already been used.")

        now = datetime.now(timezone.utc)
        expires = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=timezone.utc)
        if now > expires:
            raise InvalidTokenError("Reset link has expired. Please request a new one.")

        await self._resets.mark_used(token.id)

        user = await self._users.get_by_id(token.user_id)
        if not user:
            raise InvalidTokenError("User not found.")

        updated_user = User(
            id=user.id,
            name=user.name,
            email=user.email,
            hashed_password=hash_password(new_password),
            is_active=user.is_active,
            is_verified=user.is_verified,
            organization=user.organization,
            role=user.role,
            phone=user.phone,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        updated_user = await self._users.update(updated_user)
        logger.info("password_reset_completed", user_id=user.id)
        return updated_user

    # ── Token Utilities ──────────────────────────────────────────────────

    def _create_token_pair(self, user_id: str, email: str) -> TokenPair:
        now = datetime.now(timezone.utc)

        access_payload = {
            "sub": user_id,
            "email": email,
            "type": "access",
            "exp": now + timedelta(minutes=self._settings.access_token_expire_minutes),
            "iat": now,
        }
        refresh_payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": now + timedelta(days=self._settings.refresh_token_expire_days),
            "iat": now,
        }

        access_token = jwt.encode(
            access_payload, self._settings.jwt_secret, algorithm=self._settings.jwt_algorithm
        )
        refresh_token = jwt.encode(
            refresh_payload, self._settings.jwt_secret, algorithm=self._settings.jwt_algorithm
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def decode_access_token(self, token: str) -> dict:
        """Decode and validate an access token. Raises InvalidTokenError on failure."""
        try:
            payload = jwt.decode(
                token, self._settings.jwt_secret, algorithms=[self._settings.jwt_algorithm]
            )
            if payload.get("type") != "access":
                raise InvalidTokenError("Invalid token type.")
            return payload
        except JWTError:
            raise InvalidTokenError("Token is invalid or has expired.")

    def refresh_tokens(self, refresh_token_str: str) -> TokenPair:
        """Use a refresh token to get a new token pair."""
        try:
            payload = jwt.decode(
                refresh_token_str,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
            )
            if payload.get("type") != "refresh":
                raise InvalidTokenError("Invalid token type.")
            user_id = payload["sub"]
            # Generate new pair (email not in refresh token, use empty)
            return self._create_token_pair(user_id, payload.get("email", ""))
        except JWTError:
            raise InvalidTokenError("Refresh token is invalid or has expired.")

    async def _create_verification_token(self, user_id: str) -> EmailVerificationToken:
        # Generate a 6-digit OTP code
        otp_code = f"{secrets.randbelow(1000000):06d}"
        token = EmailVerificationToken(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token=otp_code,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=self._settings.verification_token_expire_hours),
            used=False,
        )
        return await self._verifications.create(token)

    async def _create_reset_token(self, user_id: str) -> PasswordResetToken:
        # Generate a 6-digit OTP code
        otp_code = f"{secrets.randbelow(1000000):06d}"
        token = PasswordResetToken(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token=otp_code,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=self._settings.password_reset_token_expire_hours),
            used=False,
        )
        return await self._resets.create(token)

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self._users.get_by_id(user_id)

    async def delete_account(self, user_id: str) -> None:
        """Permanently delete a user account from the database."""
        await self._users.delete(user_id)

    # ── Profile Update ───────────────────────────────────────────────────

    async def update_profile(
        self,
        user_id: str,
        name: str | None = None,
        organization: str | None = None,
        role: str | None = None,
        phone: str | None = None,
        date_of_birth: str | None = None,
        gender: str | None = None,
    ) -> User:
        """Update user profile fields. Only updates non-None values."""
        user = await self._users.get_by_id(user_id)
        if not user:
            raise InvalidTokenError("User not found.")

        updated_user = User(
            id=user.id,
            name=name.strip() if name else user.name,
            email=user.email,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
            is_verified=user.is_verified,
            organization=organization.strip() if organization is not None else user.organization,
            role=role.strip() if role is not None else user.role,
            phone=phone.strip() if phone is not None else user.phone,
            date_of_birth=date_of_birth.strip() if date_of_birth is not None else user.date_of_birth,
            gender=gender.strip() if gender is not None else user.gender,
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        updated_user = await self._users.update(updated_user)
        logger.info("profile_updated", user_id=user.id)
        return updated_user

    # ── Change Password (OTP-secured) ────────────────────────────────────

    async def request_password_change(self, user_id: str) -> None:
        """Send OTP to user's email for password change authorization."""
        user = await self._users.get_by_id(user_id)
        if not user:
            raise InvalidTokenError("User not found.")

        # Reuse the password reset token infrastructure
        await self._resets.invalidate_for_user(user.id)
        token = await self._create_reset_token(user.id)

        if self._email:
            await self._email.send_verification_email(
                to_email=user.email, name=user.name, token=token.token
            )
        logger.info("password_change_otp_sent", user_id=user.id)

    async def change_password(self, user_id: str, code: str, new_password: str) -> User:
        """Verify OTP and change password for the authenticated user."""
        token = await self._resets.get_by_token(code)
        if not token:
            raise InvalidTokenError("Invalid verification code.")

        if token.used:
            raise InvalidTokenError("This code has already been used.")

        if token.user_id != user_id:
            raise InvalidTokenError("Invalid verification code.")

        now = datetime.now(timezone.utc)
        expires = token.expires_at if token.expires_at.tzinfo else token.expires_at.replace(tzinfo=timezone.utc)
        if now > expires:
            raise InvalidTokenError("Code has expired. Please request a new one.")

        await self._resets.mark_used(token.id)

        user = await self._users.get_by_id(user_id)
        if not user:
            raise InvalidTokenError("User not found.")

        updated_user = User(
            id=user.id,
            name=user.name,
            email=user.email,
            hashed_password=hash_password(new_password),
            is_active=user.is_active,
            is_verified=user.is_verified,
            organization=user.organization,
            role=user.role,
            phone=user.phone,
            date_of_birth=user.date_of_birth,
            gender=user.gender,
            created_at=user.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        updated_user = await self._users.update(updated_user)
        logger.info("password_changed", user_id=user.id)
        return updated_user
