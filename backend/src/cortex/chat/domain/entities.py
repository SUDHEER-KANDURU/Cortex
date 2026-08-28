"""Chat domain entities."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


def _now() -> datetime:
    return datetime.now(timezone.utc)  # Fix — was datetime.utcnow() (deprecated)


@dataclass
class ChatMessage:
    role: MessageRole
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))  # NEW — needed as DB primary key
    created_at: datetime = field(default_factory=_now)


@dataclass
class ChatSession:
    id: str
    job_id: str
    user_id: str | None = None  # Owner — scopes history to a single account.
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)

    def add_message(
        self, role: MessageRole, content: str
    ) -> ChatMessage:
        msg = ChatMessage(role=role, content=content)
        self.messages.append(msg)
        return msg

    def to_nim_messages(self) -> list[dict]:
        """Convert to NIM/OpenAI message format."""
        return [
            {"role": m.role.value, "content": m.content}
            for m in self.messages
        ]