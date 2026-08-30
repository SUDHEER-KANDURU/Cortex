"""Chat service — orchestrates context retrieval and NIM streaming."""

import uuid
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from cortex.chat.infrastructure.context_retriever import QueryIntent
    from cortex.reasoning.application.producers import _BaseProducer
    from cortex.reasoning.domain.answer import CortexAnswer
    from cortex.reasoning.domain.entities import RepositoryUnderstanding
from cortex.chat.domain.entities import (
    ChatSession,
    MessageRole,
)
from cortex.chat.infrastructure.context_retriever import ContextRetriever
from cortex.chat.infrastructure.dependencies import chat_repository
from cortex.chat.infrastructure.nim_client import NIMClient
from cortex.config import get_settings
from cortex.jobs.infrastructure.dependencies import job_repository

logger = structlog.get_logger()

# NIM's role in chat is to REFINE Cortex's grounded draft answer, not to author
# facts. Cortex assembles the answer from the knowledge graph first; NIM only
# improves clarity and flow and must not introduce facts absent from the context.
REFINE_SYSTEM_PROMPT = """You are the natural-language layer of Cortex, an Engineering Copilot. Cortex has already analysed this repository, built a knowledge graph, and produced a grounded DRAFT ANSWER plus the CODE CONTEXT it was derived from.

Your job is to refine the draft into a clear, conversational reply.

STRICT RULES:
- The DRAFT ANSWER's facts are authoritative. Do NOT change any file path, class name, method, metric, or relationship.
- Do NOT add files, symbols, or claims that are not in the CODE CONTEXT or DRAFT.
- You MAY improve wording, structure, and flow, and answer the user's exact question using only the given facts.
- If the context lacks the answer, say so plainly rather than inventing.
- Keep code formatting for class names, file paths, and symbols.
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

    async def create_session(
        self, job_id: str, user_id: str | None = None
    ) -> ChatSession:
        """Create and persist a new chat session for a job, owned by user_id."""
        session = ChatSession(
            id=str(uuid.uuid4()),
            job_id=job_id,
            user_id=user_id,
        )
        await self._repo.save_session(session)
        logger.info(
            "chat_session_created",
            session_id=session.id,
            job_id=job_id,
            user_id=user_id,
        )
        return session

    async def get_session(
        self, session_id: str, owner_id: str | None = None
    ) -> ChatSession | None:
        """Get an existing session by ID, with full message history loaded.

        When owner_id is provided, a session owned by a different user is
        treated as not found — prevents reading another account's history."""
        session = await self._repo.get_session(session_id)
        if session is None:
            return None
        if owner_id is not None and session.user_id is not None and session.user_id != owner_id:
            return None
        return session

    async def get_or_create_session(
        self, job_id: str, session_id: str | None = None, user_id: str | None = None
    ) -> ChatSession:
        """Get existing session or create new one.

        A provided session_id is only reused if it belongs to the requesting
        user; otherwise a fresh session is created for this user."""
        if session_id:
            existing = await self._repo.get_session(session_id)
            if existing and (
                user_id is None
                or existing.user_id is None
                or existing.user_id == user_id
            ):
                return existing
        return await self.create_session(job_id, user_id=user_id)

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

        # ── Cortex authors a grounded DRAFT answer FIRST (deterministic) ──────
        # This is the source of truth. It is a validated CortexAnswer built from
        # the knowledge graph via an Answer Producer, and is always available,
        # with or without NIM (Req 9.1). `cortex_answer` holds the authoritative
        # facts/evidence/epistemic tags; `cortex_draft` is its rendered markdown.
        cortex_answer, cortex_draft = await self._generate_answer(
            session.job_id, user_message, context
        )

        # Stream response
        full_response = []

        if self._use_nim:
            # NIM REFINES the Cortex draft — it does not author facts.
            messages = [
                {"role": "system", "content": REFINE_SYSTEM_PROMPT},
                {"role": "system", "content": f"## CODE CONTEXT\n\n{context}"},
            ]
            # Conversation history for continuity (last 6 messages)
            recent = session.messages[-6:]
            for msg in recent[:-1]:  # Skip the user msg we just added
                messages.append({"role": msg.role.value, "content": msg.content})
            messages.append({
                "role": "user",
                "content": (
                    f"User question:\n{user_message}\n\n"
                    f"## DRAFT ANSWER (Cortex, authoritative facts)\n{cortex_draft}\n\n"
                    "Refine this into a clear reply to the question, keeping all facts."
                ),
            })
            nim_failed = False
            async for chunk in self._nim.stream(messages):
                # NIMClient yields a canned error string on total failure — detect
                # it and fall back to the trustworthy Cortex draft instead.
                if chunk.startswith("Sorry — I couldn't connect"):
                    nim_failed = True
                    break
                full_response.append(chunk)
                yield chunk
            if nim_failed or not "".join(full_response).strip():
                full_response = []
                for word in cortex_draft.split(" "):
                    full_response.append(word + " ")
                    yield word + " "
        else:
            # No NIM key — stream Cortex's own grounded answer directly.
            for word in cortex_draft.split(" "):
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

    def _try_entity_explanation(
        self,
        question: str,
        nodes: list,
        edges: list,
    ) -> str | None:
        """If the question targets a specific file/class/function, explain it
        with the SAME CortexExplainer that Navigate uses.

        Returns the explanation markdown, or None if no confident entity match —
        in which case the caller falls back to repository-level answers.
        """
        from cortex.graph.domain.entities import NodeType
        from cortex.reasoning.application.explainer import CortexExplainer

        q = question.lower()
        target = None
        best_score = 0

        for n in nodes:
            label = str(n.label or "")
            if not label:
                continue
            path = str(n.properties.get("path", "") or "")
            file_name = path.split("/")[-1] if path else ""
            score = 0
            # Strongest: the exact FILE name (must contain a dot, so we never
            # match a bare directory segment as a stray substring) appears.
            if (
                n.node_type == NodeType.FILE
                and file_name
                and "." in file_name
                and file_name.lower() in q
            ):
                score = 100 + len(file_name)
            # Next: a class/function name (>=4 chars to avoid noise) mentioned.
            elif (
                n.node_type in (
                    NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM,
                    NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT,
                )
                and len(label) >= 4
                and label.lower() in q
            ):
                score = 50 + len(label)
            if score > best_score:
                best_score, target = score, n

        if target is None:
            return None

        explanation = CortexExplainer().explain_node(target.id, nodes, edges)
        if explanation is None:
            return None
        return explanation.to_markdown()

    def _select_producer(
        self,
        intent: "QueryIntent",
        understanding: "RepositoryUnderstanding",
        nodes: list,
        edges: list,
    ) -> "_BaseProducer":
        """Map a detected `QueryIntent` to the Answer Producer that best serves it.

        This replaces the old ad-hoc `_format_*` formatters (Req 4.5). Every
        intent now resolves to a deterministic producer that emits a
        `CortexAnswer` — one shape for every output. Producers that need graph
        structure (e.g. `ApiSpecProducer` reads ENDPOINT nodes) are handed the
        nodes/edges already fetched from the graph repository.
        """
        from cortex.chat.infrastructure.context_retriever import QueryIntent
        from cortex.reasoning.application.producers import (
            ApiSpecProducer,
            ArchitectureOverviewProducer,
            InterviewPrepProducer,
            LearningPathProducer,
            ModuleBreakdownProducer,
        )

        # Intent → producer class. Every existing intent maps to the closest
        # producer; unmapped/GENERAL falls through to the architecture overview,
        # which is the most complete stack-agnostic answer.
        mapping = {
            QueryIntent.ARCHITECTURE: ArchitectureOverviewProducer,
            QueryIntent.METRICS: ArchitectureOverviewProducer,
            QueryIntent.ENTRY_POINT: ApiSpecProducer,
            QueryIntent.DATA_FLOW: ApiSpecProducer,
            QueryIntent.LEARNING: LearningPathProducer,
            QueryIntent.COMPLEXITY: InterviewPrepProducer,
            QueryIntent.EXPLANATION: ArchitectureOverviewProducer,
            QueryIntent.GENERAL: ArchitectureOverviewProducer,
            QueryIntent.NAVIGATION: ModuleBreakdownProducer,
            QueryIntent.DEPENDENCY: ModuleBreakdownProducer,
            QueryIntent.DEBUGGING: InterviewPrepProducer,
        }
        producer_cls = mapping.get(intent, ArchitectureOverviewProducer)
        return producer_cls(understanding, nodes=nodes, edges=edges)

    def _build_cortex_answer(
        self,
        job_id: str,
        question: str,
        nodes: list,
        edges: list,
        repo_url: str,
    ) -> "CortexAnswer":
        """Build a `CortexAnswer` for a question from the deterministic layer.

        Returns the validated `CortexAnswer`, or None if no producer-backed
        answer can be built (caller then falls back to the raw graph context).
        This is the sole source of facts/evidence/epistemic tags — NIM only
        rewords the rendered form later (Req 9.1, Req 9.2).
        """
        from cortex.chat.infrastructure.context_retriever import detect_intent
        from cortex.reasoning.application.reasoner import CortexReasoner

        intent = detect_intent(question)
        reasoner = CortexReasoner()
        understanding = reasoner.understand(
            job_id=job_id, repo_url=repo_url, nodes=nodes, edges=edges
        )
        producer = self._select_producer(intent, understanding, nodes, edges)
        return producer.produce()

    async def _generate_answer(
        self,
        job_id: str,
        question: str,
        context: str,
    ) -> tuple[object | None, str]:
        """Produce the grounded draft for a question.

        Returns ``(cortex_answer, draft_markdown)``:
          - ``cortex_answer`` is the authoritative `CortexAnswer` (or None when
            the answer came from the entity explainer or the raw-context
            fallback and no producer answer was built).
          - ``draft_markdown`` is the text to stream / hand to NIM.

        Entity-targeted questions keep the deep `CortexExplainer` path so Chat
        and Navigate share one understanding. All repository-level intents route
        through Answer Producers (Req 4.5). On any failure the raw graph context
        is returned so chat always answers.
        """
        from cortex.graph.infrastructure.dependencies import graph_repository
        from cortex.reasoning.application.answer_serializer import (
            render_answer_markdown,
        )

        try:
            nodes = await graph_repository.get_nodes_by_job(job_id)
            edges = await graph_repository.get_edges_by_job(job_id)

            if nodes:
                # ── Entity-specific questions use the SAME deep explainer that
                # Navigate uses, so Chat and Navigate share one understanding
                # foundation rather than Chat giving a shallower answer. ──────
                entity_answer = self._try_entity_explanation(question, nodes, edges)
                if entity_answer:
                    return None, entity_answer

                repo_url = await self._resolve_repo_url(job_id) or ""
                answer = self._build_cortex_answer(
                    job_id, question, nodes, edges, repo_url
                )
                if answer is not None:
                    return answer, render_answer_markdown(answer)
        except Exception as e:
            logger.debug("answer_producer_failed", error=str(e))

        # Final fallback: return the grounded repository context directly.
        return None, f"**Answer** (from Cortex repository analysis):\n\n{context}"