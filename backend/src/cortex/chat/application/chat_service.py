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
from cortex.jobs.infrastructure.dependencies import job_repository

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are Cortex, an AI Engineering Copilot that deeply understands codebases. You have analyzed this repository and built a complete knowledge graph of its structure, relationships, and engineering health.

You answer like an engineer who has already studied this codebase. Your responses are grounded in evidence from the knowledge graph.

Response Structure (use when appropriate):
1. **Answer** — Direct answer to the question
2. **Evidence** — Specific files, symbols, and relationships backing the answer
3. **Related Context** — Connected components, callers, dependencies
4. **Issues/Metrics** — Relevant engineering health data if applicable
5. **Suggested Next Action** — What to explore or do next

Rules:
- Always reference specific class names, file paths, and methods from the context
- If the context doesn't contain enough information, say so clearly
- Trace actual execution flows through real classes — never fabricate paths
- Use code formatting for class names, file paths, and symbols
- Distinguish between DIRECT evidence (proven from graph) and INFERRED relationships
- When explaining architecture, show the actual module boundaries and dependencies
- When discussing impact, reference the real dependency chain
- Never make up class names or file paths that aren't in the context
- If the context includes prior analysis history, use it for temporal questions
  but clearly distinguish current state from historical state
- For debugging questions, always show the relevant callers and callees
- For refactoring questions, always note the blast radius and affected tests
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
        """Intelligent rule-based fallback when NIM is not available.

        Uses the Cortex Reasoning Layer to provide structured answers
        directly from the knowledge graph — no AI generation needed.
        """
        from cortex.chat.infrastructure.context_retriever import detect_intent, QueryIntent
        from cortex.reasoning.application.reasoner import CortexReasoner
        from cortex.graph.infrastructure.dependencies import graph_repository

        q_lower = question.lower()
        intent = detect_intent(question)

        # Try to produce a reasoner-backed answer
        try:
            nodes = await graph_repository.get_nodes_by_job(job_id)
            edges = await graph_repository.get_edges_by_job(job_id)

            if nodes:
                repo_url = await self._resolve_repo_url(job_id) or ""
                reasoner = CortexReasoner()
                understanding = reasoner.understand(
                    job_id=job_id, repo_url=repo_url, nodes=nodes, edges=edges
                )

                # Generate intent-specific structured response
                if intent == QueryIntent.ARCHITECTURE:
                    return self._format_architecture_answer(understanding)
                elif intent == QueryIntent.METRICS:
                    return self._format_metrics_answer(understanding)
                elif intent in (QueryIntent.ENTRY_POINT, QueryIntent.DATA_FLOW):
                    return self._format_flow_answer(understanding)
                elif intent == QueryIntent.LEARNING:
                    return self._format_learning_answer(understanding)
                elif intent == QueryIntent.COMPLEXITY:
                    return self._format_complexity_answer(understanding)
                elif intent in (QueryIntent.EXPLANATION, QueryIntent.GENERAL):
                    return self._format_general_answer(understanding, context)
                elif intent == QueryIntent.NAVIGATION:
                    return self._format_navigation_answer(understanding, context)
                elif intent == QueryIntent.DEPENDENCY:
                    return self._format_dependency_answer(understanding)
        except Exception as e:
            logger.debug("fallback_reasoner_failed", error=str(e))

        # Final fallback: return raw context
        return (
            f"**Answer** (from repository analysis):\n\n{context}\n\n"
            f"---\n*For conversational AI answers, add a NIM API key to "
            f"backend/.env: `NIM_API_KEY=your_key_here`*"
        )

    def _format_architecture_answer(self, u) -> str:
        """Format an architecture answer from understanding."""
        lines = [
            f"**Answer:** {u.repo_name} uses a {u.architecture_style.value.replace('_', ' ')} architecture.",
            "",
            f"{u.architecture_description}",
            "",
            "**Evidence:**",
        ]
        for ev in u.architecture_evidence[:4]:
            lines.append(f"- {ev}")
        if u.modules:
            lines.append(f"\n**Key Modules ({len(u.modules)}):**")
            for m in u.modules[:5]:
                role = f" ({m.architecture_role})" if m.architecture_role else ""
                lines.append(f"- `{m.name}`{role} — {m.file_count} files, deps: {', '.join(m.dependencies[:3]) or 'none'}")
        if u.frameworks:
            lines.append(f"\n**Frameworks:** {', '.join(u.frameworks)}")
        lines.append(f"\n**Suggested next:** Ask about a specific module or the data flow.")
        return "\n".join(lines)

    def _format_metrics_answer(self, u) -> str:
        """Format a metrics answer."""
        lines = [
            f"**Answer:** Repository metrics for `{u.repo_name}`:",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Files | {u.total_files} |",
            f"| Lines of code | {u.total_lines:,} |",
            f"| Modules | {u.total_modules} |",
            f"| Classes | {u.total_classes} |",
            f"| Functions | {u.total_functions} |",
            f"| Endpoints | {u.total_endpoints} |",
            f"| Tests | {u.total_tests} |",
            f"| Health Score | {u.overall_score}/100 (Grade {u.overall_grade}) |",
            f"| Languages | {', '.join(u.languages)} |",
            "",
            f"**Suggested next:** Ask about complexity hotspots or engineering risks.",
        ]
        return "\n".join(lines)

    def _format_flow_answer(self, u) -> str:
        """Format an entry point / data flow answer."""
        lines = [f"**Answer:** {u.repo_name} has {len(u.entry_points)} entry points.\n"]
        if u.entry_points:
            lines.append("**Entry Points:**")
            for ep in u.entry_points[:8]:
                detail = f"- `{ep.label}` ({ep.kind})"
                if ep.route:
                    detail += f" — {ep.method} {ep.route}"
                if ep.file_path:
                    detail += f" in `{ep.file_path}`"
                lines.append(detail)
        if u.data_flows:
            lines.append(f"\n**Execution Flows ({len(u.data_flows)} traced):**")
            for flow in u.data_flows[:3]:
                path = " → ".join(f"`{s.symbol}`" for s in flow.steps)
                lines.append(f"- **{flow.name}:** {path}")
        lines.append(f"\n**Suggested next:** Ask about a specific endpoint or what calls what.")
        return "\n".join(lines)

    def _format_learning_answer(self, u) -> str:
        """Format a learning path answer."""
        lines = [f"**Answer:** Here's where to start learning `{u.repo_name}`:\n"]
        if u.start_here:
            lines.append(f"**Start Here:** `{u.start_here}` in `{u.start_here_file}`")
            lines.append(f"- *Why:* {u.start_here_reason}")
        if u.modules:
            lines.append(f"\n**Recommended reading order:**")
            for i, m in enumerate(u.modules[:5], 1):
                lines.append(f"{i}. `{m.name}` — {m.file_count} files, role: {m.architecture_role or 'feature'}")
        lines.append(f"\n**Suggested next:** Use the `/reasoning/{{job_id}}/learning-path` endpoint for the full guided path.")
        return "\n".join(lines)

    def _format_complexity_answer(self, u) -> str:
        """Format a complexity/risk answer."""
        lines = [f"**Answer:** Complexity analysis for `{u.repo_name}` (Score: {u.overall_score}/100):\n"]
        if u.complexity_hotspots:
            lines.append("**Complexity Hotspots:**")
            for h in u.complexity_hotspots[:5]:
                lines.append(f"- `{h['symbol']}` in `{h.get('file', '?')}` — cyclomatic: {h['cyclomatic']}, lines: {h.get('lines', '?')}")
        if u.architectural_risks:
            lines.append(f"\n**Architectural Risks:**")
            for risk in u.architectural_risks[:5]:
                lines.append(f"- {risk}")
        god_modules = [m for m in u.modules if m.is_god_module]
        if god_modules:
            lines.append(f"\n**Over-sized modules:**")
            for m in god_modules[:3]:
                lines.append(f"- `{m.name}` ({m.function_count} functions, {m.class_count} classes)")
        lines.append(f"\n**Suggested next:** Ask about the blast radius of a specific hotspot.")
        return "\n".join(lines)

    def _format_general_answer(self, u, context: str) -> str:
        """Format a general/explanation answer."""
        lines = [
            f"**Answer:** `{u.repo_name}` — {u.purpose}\n",
            f"**Architecture:** {u.architecture_style.value.replace('_', ' ')} ({u.overall_grade} grade, {u.overall_score}/100)",
            f"**Structure:** {u.total_files} files, {u.total_modules} modules, {u.total_classes} classes, {u.total_functions} functions",
            f"**Languages:** {', '.join(u.languages)}",
        ]
        if u.frameworks:
            lines.append(f"**Frameworks:** {', '.join(u.frameworks)}")
        if u.start_here:
            lines.append(f"\n**Start here:** `{u.start_here}` — {u.start_here_reason}")
        lines.append(f"\n**Suggested next:** Ask about the architecture, a specific module, or the main execution flow.")
        return "\n".join(lines)

    def _format_navigation_answer(self, u, context: str) -> str:
        """Format a navigation answer."""
        lines = [f"**Answer:** Here's the module map for `{u.repo_name}`:\n"]
        for m in u.modules[:10]:
            role = f" ({m.architecture_role})" if m.architecture_role else ""
            classes = f", key: {', '.join(m.key_classes[:2])}" if m.key_classes else ""
            lines.append(f"- `{m.name}`{role} at `{m.path}` — {m.file_count} files{classes}")
        lines.append(f"\n**Suggested next:** Ask about a specific module name to get its full details.")
        return "\n".join(lines)

    def _format_dependency_answer(self, u) -> str:
        """Format a dependency answer."""
        lines = [f"**Answer:** Dependency analysis for `{u.repo_name}`:\n"]
        if u.top_dependencies:
            lines.append("**Most depended-on components:**")
            for dep in u.top_dependencies[:8]:
                lines.append(f"- {dep}")
        if u.modules:
            lines.append(f"\n**Module dependency map:**")
            for m in u.modules[:6]:
                if m.dependencies or m.dependents:
                    deps = ', '.join(m.dependencies[:3]) if m.dependencies else 'none'
                    lines.append(f"- `{m.name}` → depends on: {deps}")
        lines.append(f"\n**Suggested next:** Ask about blast radius for a specific component.")
        return "\n".join(lines)