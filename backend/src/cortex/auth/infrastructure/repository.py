"""Auth infrastructure — SQLAlchemy repository implementations."""

from datetime import datetime, timezone

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from cortex.auth.domain.entities import EmailVerificationToken, PasswordResetToken, User
from cortex.auth.domain.interfaces import (
    PasswordResetTokenRepository,
    UserRepository,
    VerificationTokenRepository,
)
from cortex.db import get_async_session
from cortex.schema.models import (
    EmailVerificationTokenModel,
    PasswordResetTokenModel,
    UserModel,
)


class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy user repository using shared session factory."""

    async def create(self, user: User) -> User:
        async with get_async_session() as session:
            model = UserModel(
                id=user.id,
                name=user.name,
                email=user.email,
                hashed_password=user.hashed_password,
                is_active=user.is_active,
                is_verified=user.is_verified,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return self._to_entity(model)

    async def get_by_id(self, user_id: str) -> User | None:
        async with get_async_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        async with get_async_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.email == email)
            )
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None

    async def update(self, user: User) -> User:
        async with get_async_session() as session:
            await session.execute(
                sa_update(UserModel)
                .where(UserModel.id == user.id)
                .values(
                    name=user.name,
                    email=user.email,
                    hashed_password=user.hashed_password,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
            return user

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            name=model.name,
            email=model.email,
            hashed_password=model.hashed_password,
            is_active=model.is_active,
            is_verified=model.is_verified,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyVerificationTokenRepository(VerificationTokenRepository):
    async def create(self, token: EmailVerificationToken) -> EmailVerificationToken:
        async with get_async_session() as session:
            model = EmailVerificationTokenModel(
                id=token.id,
                user_id=token.user_id,
                token=token.token,
                expires_at=token.expires_at,
                used=token.used,
            )
            session.add(model)
            await session.commit()
            return token

    async def get_by_token(self, token_str: str) -> EmailVerificationToken | None:
        async with get_async_session() as session:
            result = await session.execute(
                select(EmailVerificationTokenModel).where(
                    EmailVerificationTokenModel.token == token_str
                )
            )
            model = result.scalar_one_or_none()
            if not model:
                return None
            return EmailVerificationToken(
                id=model.id,
                user_id=model.user_id,
                token=model.token,
                expires_at=model.expires_at,
                used=model.used,
            )

    async def mark_used(self, token_id: str) -> None:
        async with get_async_session() as session:
            await session.execute(
                sa_update(EmailVerificationTokenModel)
                .where(EmailVerificationTokenModel.id == token_id)
                .values(used=True)
            )
            await session.commit()

    async def invalidate_for_user(self, user_id: str) -> None:
        async with get_async_session() as session:
            await session.execute(
                sa_update(EmailVerificationTokenModel)
                .where(EmailVerificationTokenModel.user_id == user_id)
                .where(EmailVerificationTokenModel.used == False)  # noqa: E712
                .values(used=True)
            )
            await session.commit()


class SqlAlchemyPasswordResetTokenRepository(PasswordResetTokenRepository):
    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        async with get_async_session() as session:
            model = PasswordResetTokenModel(
                id=token.id,
                user_id=token.user_id,
                token=token.token,
                expires_at=token.expires_at,
                used=token.used,
            )
            session.add(model)
            await session.commit()
            return token

    async def get_by_token(self, token_str: str) -> PasswordResetToken | None:
        async with get_async_session() as session:
            result = await session.execute(
                select(PasswordResetTokenModel).where(
                    PasswordResetTokenModel.token == token_str
                )
            )
            model = result.scalar_one_or_none()
            if not model:
                return None
            return PasswordResetToken(
                id=model.id,
                user_id=model.user_id,
                token=model.token,
                expires_at=model.expires_at,
                used=model.used,
            )

    async def mark_used(self, token_id: str) -> None:
        async with get_async_session() as session:
            await session.execute(
                sa_update(PasswordResetTokenModel)
                .where(PasswordResetTokenModel.id == token_id)
                .values(used=True)
            )
            await session.commit()

    async def invalidate_for_user(self, user_id: str) -> None:
        async with get_async_session() as session:
            await session.execute(
                sa_update(PasswordResetTokenModel)
                .where(PasswordResetTokenModel.user_id == user_id)
                .where(PasswordResetTokenModel.used == False)  # noqa: E712
                .values(used=True)
            )
            await session.commit()
