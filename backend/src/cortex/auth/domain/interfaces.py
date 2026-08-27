"""Auth domain interfaces — abstract contracts for infrastructure."""

from abc import ABC, abstractmethod
from cortex.auth.domain.entities import User, EmailVerificationToken, PasswordResetToken


class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        ...


class VerificationTokenRepository(ABC):
    @abstractmethod
    async def create(self, token: EmailVerificationToken) -> EmailVerificationToken:
        ...

    @abstractmethod
    async def get_by_token(self, token: str) -> EmailVerificationToken | None:
        ...

    @abstractmethod
    async def mark_used(self, token_id: str) -> None:
        ...

    @abstractmethod
    async def invalidate_for_user(self, user_id: str) -> None:
        ...


class PasswordResetTokenRepository(ABC):
    @abstractmethod
    async def create(self, token: PasswordResetToken) -> PasswordResetToken:
        ...

    @abstractmethod
    async def get_by_token(self, token: str) -> PasswordResetToken | None:
        ...

    @abstractmethod
    async def mark_used(self, token_id: str) -> None:
        ...

    @abstractmethod
    async def invalidate_for_user(self, user_id: str) -> None:
        ...
