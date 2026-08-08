"""Chat service — orchestrates context retrieval and NIM streaming."""

import uuid
from typing import AsyncGenerator
from cortex.chat.domain.entities import (
    ChatSession,
    ChatMessage,
    MessageRole,
)
from cortex.chat.infrastructure.context_retriever import ContextRetriever
from cortex.chat.infrastructure.nim_client import NIMClient
from cortex.chat.infrastructure.dependencies import chat_repository
from cortex.graph.infrastructure.sqlite_repository import SQLiteGraphRepository
from cortex.config import get_settings
import structlog

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are Cortex, an expert code analysis assistant. You have analyzed a GitHub repository and built a complete knowledge graph of its structure. You answer questions about the codebase based on the provided context.

Rules:
- Always reference specific class names, file paths, and methods from the context
- If the context doesn't contain enough information, say so clearly
- Be concise — 2-4 sentences for simple questions, more for complex ones
- Use code formatting for class names and file paths
- When explaining architecture, trace the actual flow through real classes
- Never make up class names or file paths that aren't in the context
"""


class ChatService:
    """Manages chat sessions and streams AI responses.

    Sessions and messages are persisted via `chat_repository` (SQLite by
    default) instead of an in-memory dict, so history survives a restart.
    """

    def __init__(self) -> None:
        self._retriever = ContextRetriever()
        settings = get_settings()
        self._nim = NIMClient(settings.nim_api_key)
        self._use_nim = bool(settings.nim_api_key)
        self._repo = chat_repository

    async def create_session(self, job_id: str) -> ChatSession:
        """Create and persist a new chat session for a job."""
        session = ChatSession(
            id=str(uuid.uuid4()),
            job_id=job_id,
        )
        await self._repo.save_session(session)
        logger.info(
            "chat_session_created",
            session_id=session.id,
            job_id=job_id,
        )
        return session

    async def get_session(self, session_id: str) -> ChatSession | None:
        """Get an existing session by ID, with full message history loaded."""
        return await self._repo.get_session(session_id)

    async def get_or_create_session(
        self, job_id: str, session_id: str | None = None
    ) -> ChatSession:
        """Get existing session or create new one."""
        if session_id:
            existing = await self._repo.get_session(session_id)
            if existing:
                return existing
        return await self.create_session(job_id)

    async def stream_response(
        self,
        session: ChatSession,
        user_message: str,
    ) -> AsyncGenerator[str, None]:
        """Stream an AI response for a user message.

        Flow:
        1. Add user message to session history (persisted immediately)
        2. Retrieve relevant code context from graph
        3. Build prompt with context + history
        4. Stream response from NIM or fallback
        5. Collect full response and save to session (persisted)
        """
        # Add user message to history
        user_msg = session.add_message(MessageRole.USER, user_message)
        await self._repo.add_message(session.id, user_msg)

        # Retrieve relevant context
        context = await self._retriever.retrieve(
            session.job_id, user_message
        )

        # Build messages for NIM
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"Here is the code context:\n\n{context}",
            },
        ]

        # Add conversation history (last 6 messages)
        recent = session.messages[-6:]
        for msg in recent[:-1]:  # Skip the last one we just added
            messages.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        messages.append({
            "role": "user",
            "content": user_message,
        })

        # Stream response
        full_response = []

        if self._use_nim:
            async for chunk in self._nim.stream(messages):
                full_response.append(chunk)
                yield chunk
        else:
            # Fallback — rule-based response when no NIM key
            response = await self._generate_fallback(
                session.job_id, user_message, context
            )
            for word in response.split(" "):
                full_response.append(word + " ")
                yield word + " "
                import asyncio
                await asyncio.sleep(0.03)  # Simulate streaming

        # Save complete response to session
        complete = "".join(full_response)
        assistant_msg = session.add_message(MessageRole.ASSISTANT, complete)
        await self._repo.add_message(session.id, assistant_msg)

        logger.info(
            "chat_response_complete",
            session_id=session.id,
            job_id=session.job_id,
            response_length=len(complete),
            used_nim=self._use_nim,
        )

    async def _generate_fallback(
        self,
        job_id: str,
        question: str,
        context: str,
    ) -> str:
        """Rule-based fallback when NIM is not available.
        Extracts answers directly from the graph context."""
        q_lower = question.lower()

        if any(w in q_lower for w in ["what", "describe", "explain"]):
            return (
                f"Based on the repository analysis:\n\n{context}\n\n"
                f"This codebase follows a structured architecture with "
                f"the modules and classes shown above. Add your NIM API "
                f"key to get detailed AI-powered answers."
            )
        elif any(w in q_lower for w in ["how many", "count", "total"]):
            repo = SQLiteGraphRepository(get_settings().database_url)
            counts = await repo.count_by_job(job_id)
            return (
                f"The repository has {counts.get('nodes', 0)} "
                f"code elements (nodes) and {counts.get('edges', 0)} "
                f"relationships between them."
            )
        else:
            return (
                f"Here's what I found in the codebase:\n\n{context}\n\n"
                f"For more detailed answers, add a NIM API key to your "
                f"backend/.env file: `NIM_API_KEY=your_key_here`"
            )