"""Abstract repository interface for the chat domain.
Nothing in this file knows about databases, HTTP, or frameworks."""

from abc import ABC, abstractmethod
from cortex.chat.domain.entities import ChatSession, ChatMessage


class AbstractChatRepository(ABC):
    """Defines every storage operation the chat domain needs.
    The infrastructure layer implements this against SQLite/PostgreSQL."""

    @abstractmethod
    async def save_session(self, session: ChatSession) -> ChatSession:
        """Persist a new chat session (no messages yet). Returns the saved session."""
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> ChatSession | None:
        """Return a session with its full message history, ordered oldest first.
        Returns None if not found — never raises."""
        ...

    @abstractmethod
    async def add_message(self, session_id: str, message: ChatMessage) -> ChatMessage:
        """Persist a new message onto an existing session. Returns the saved message."""
        ...

    @abstractmethod
    async def get_sessions_for_job(self, job_id: str) -> list[ChatSession]:
        """Return all sessions for a given job (metadata only, no messages loaded),
        newest first. Used to show conversation history for a repo analysis."""
        ...