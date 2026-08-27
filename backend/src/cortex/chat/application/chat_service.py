"""Chat service — orchestrates context retrieval and NIM streaming."""

import uuid
from collections.abc import AsyncGenerator

import structlog

from cortex.chat.domain.entities import (
    ChatSession,
    MessageRole,
)
from cortex.chat.infrastructure.context_retriever import ContextRetriever
from cortex.chat.infrastructure.dependencies import chat_repository
from cortex.chat.infrastructure.nim_client import NIMClient
from cortex.config import get_settings
from cortex.graph.infrastructure.sqlite_repository import SQLiteGraphRepository
from cortex.jobs.infrastructure.dependencies import job_repository

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are Cortex, an expert code analysis assistant. You have analyzed a GitHub repository and built a complete knowledge graph of its structure. You answer questions about the codebase based on the provided context.

Rules:
- Always reference specific class names, file paths, and methods from the context
- If the context doesn't contain enough information, say so clearly
- Be concise — 2-4 sentences for simple questions, more for complex ones
- Use code formatting for class names and file paths
- When explaining architecture, trace the actual flow through real classes
- Never make up class names or file paths that aren't in the context
- If the context includes a "What's known from prior analyses" section, treat
  that as history from earlier runs of this same repo — useful for questions
  about how the codebase has changed, but don't confuse it with the current
  state unless the question is explicitly about history
"""


class ChatService:
    """Manages chat sessions and streams AI responses.

    Sessions and messages are persisted via `chat_repository` (SQLite by
    default) instead of an in-memory dict, so history survives a restart.

    Context retrieval now blends the live graph with durable facts from
    Repository Memory (prior analyses of the same repo_url), so chat can
    answer questions like "has this always been a god class?" — not just
    what's true of the current job alone.
    """

    def __init__(self) -> None:
        self._retriever = ContextRetriever()
        settings = get_settings()
        self._nim = NIMClient(settings.nim_api_key)
        self._use_nim = bool(settings.nim_api_key)
        self._repo = chat_repository
        # Use the shared singleton from jobs/infrastructure/dependencies
        # instead of constructing a new engine per ChatService instance.
        self._job_repo = job_repository

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
        2. Resolve the session's job to a repo_url (for memory lookup)
        3. Retrieve relevant context from the live graph + repository memory
        4. Build prompt with context + history
        5. Stream response from NIM or fallback
        6. Collect full response and save to session (persisted)
        """
        # Add user message to history
        user_msg = session.add_message(MessageRole.USER, user_message)
        await self._repo.add_message(session.id, user_msg)

        # Resolve repo_url for this job so memory can be searched.
        # Never let this block the conversation — if the job lookup fails
        # for any reason, chat still works from the live graph alone.
        repo_url = await self._resolve_repo_url(session.job_id)

        # Retrieve relevant context (graph + memory)
        context = await self._retriever.retrieve(
            session.job_id, user_message, repo_url=repo_url
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
            used_memory=bool(repo_url),
        )

    async def _resolve_repo_url(self, job_id: str) -> str | None:
        """Look up the repo_url for a job, for repository-memory retrieval.
        Returns None (never raises) if the job can't be found — memory
        lookup is an enhancement, not a hard dependency for chat."""
        try:
            job = await self._job_repo.get_by_id(job_id)
            return job.repo_url if job else None
        except Exception as e:
            logger.warning("chat_job_lookup_failed", job_id=job_id, error=str(e))
            return None

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
            # SQLiteGraphRepository now uses the shared engine singleton via
            # get_engine(). Do NOT dispose it — that would shut down the shared
            # pool. The repo object itself is ephemeral; the engine it references
            # is not.
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