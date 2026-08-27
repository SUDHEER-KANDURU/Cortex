"""Auth application service — orchestrates registration, login, verification, password reset."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

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

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


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
    ) -> None:
        self._users = user_repo
        self._verifications = verification_repo
        self._resets = reset_repo
        self._settings = settings

    # ── Registration ─────────────────────────────────────────────────────

    async def register(self, name: str, email: str, password: str) -> tuple[User, str]:
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
        )
        user = await self._users.create(user)

        # Create verification token
        token = await self._create_verification_token(user.id)
        logger.info("user_registered", user_id=user.id, email=user.email)
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

        if datetime.now(timezone.utc) > token.expires_at:
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
        return token.token

    async def reset_password(self, token_str: str, new_password: str) -> User:
        """Reset password using a valid reset token."""
        token = await self._resets.get_by_token(token_str)
        if not token:
            raise InvalidTokenError("Reset token not found.")

        if token.used:
            raise InvalidTokenError("This reset link has already been used.")

        if datetime.now(timezone.utc) > token.expires_at:
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
        token = EmailVerificationToken(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token=secrets.token_urlsafe(48),
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=self._settings.verification_token_expire_hours),
            used=False,
        )
        return await self._verifications.create(token)

    async def _create_reset_token(self, user_id: str) -> PasswordResetToken:
        token = PasswordResetToken(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token=secrets.token_urlsafe(48),
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=self._settings.password_reset_token_expire_hours),
            used=False,
        )
        return await self._resets.create(token)

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self._users.get_by_id(user_id)
