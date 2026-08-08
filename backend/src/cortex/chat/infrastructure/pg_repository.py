"""SQLite/PostgreSQL chat repository using SQLAlchemy async engine.

Persists chat sessions and messages so conversation history survives a
server restart. Works with both SQLite (dev) and PostgreSQL (production)
via DATABASE_URL — same pattern as jobs/artifacts repositories.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from cortex.chat.domain.entities import ChatSession, ChatMessage, MessageRole
from cortex.chat.domain.interfaces import AbstractChatRepository
from cortex.schema.models import ChatSessionModel, ChatMessageModel
from shared.exceptions import InfrastructureError
import structlog

logger = structlog.get_logger()


def _message_model_to_entity(model: ChatMessageModel) -> ChatMessage:
    return ChatMessage(
        id=model.id,
        role=MessageRole(model.role),
        content=model.content,
        created_at=model.created_at,
    )


def _session_model_to_entity(model: ChatSessionModel) -> ChatSession:
    return ChatSession(
        id=model.id,
        job_id=model.job_id,
        messages=[_message_model_to_entity(m) for m in model.messages],
        created_at=model.created_at,
    )


class PostgresChatRepository(AbstractChatRepository):
    """Works with both SQLite (dev) and PostgreSQL (production).
    Set DATABASE_URL in .env to switch backends."""

    def __init__(self, database_url: str) -> None:
        connect_args: dict = {}
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}

        self._engine = create_async_engine(
            database_url,
            echo=False,
            connect_args=connect_args,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def save_session(self, session: ChatSession) -> ChatSession:
        async with self._session_factory() as db:
            try:
                model = ChatSessionModel(
                    id=session.id,
                    job_id=session.job_id,
                    created_at=session.created_at,
                )
                db.add(model)
                await db.commit()
                logger.info(
                    "chat_session_saved",
                    session_id=session.id,
                    job_id=session.job_id,
                )
                return session
            except Exception as e:
                await db.rollback()
                raise InfrastructureError(
                    f"Failed to save chat session {session.id}: {e}"
                ) from e

    async def get_session(self, session_id: str) -> ChatSession | None:
        async with self._session_factory() as db:
            result = await db.execute(
                select(ChatSessionModel)
                .options(selectinload(ChatSessionModel.messages))
                .where(ChatSessionModel.id == session_id)
            )
            model = result.scalar_one_or_none()
            return _session_model_to_entity(model) if model else None

    async def add_message(self, session_id: str, message: ChatMessage) -> ChatMessage:
        async with self._session_factory() as db:
            try:
                model = ChatMessageModel(
                    id=message.id,
                    session_id=session_id,
                    role=message.role.value,
                    content=message.content,
                    created_at=message.created_at,
                )
                db.add(model)
                await db.commit()
                return message
            except Exception as e:
                await db.rollback()
                raise InfrastructureError(
                    f"Failed to save message for session {session_id}: {e}"
                ) from e

    async def get_sessions_for_job(self, job_id: str) -> list[ChatSession]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(ChatSessionModel)
                .where(ChatSessionModel.job_id == job_id)
                .order_by(ChatSessionModel.created_at.desc())
            )
            return [
                ChatSession(id=m.id, job_id=m.job_id, messages=[], created_at=m.created_at)
                for m in result.scalars().all()
            ]