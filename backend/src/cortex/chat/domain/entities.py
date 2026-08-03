"""Chat domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ChatMessage:
    role: MessageRole
    content: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatSession:
    id: str
    job_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

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
