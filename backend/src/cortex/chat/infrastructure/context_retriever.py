"""Context retriever — finds relevant code context for a question.

Searches the graph and parsed files to find what's relevant before
sending to NIM. This is the RAG layer.

NEW: also searches Repository Memory's durable facts, so chat can draw
on prior analyses of the same repo (e.g. "has this always been a god
class?") — not just whatever the current job's live graph contains.
"""

from cortex.graph.infrastructure.sqlite_repository import (
    SQLiteGraphRepository,
)
from cortex.graph.domain.entities import NodeType
from cortex.memory.infrastructure.dependencies import memory_repository
from cortex.config import get_settings
import structlog

logger = structlog.get_logger()


class ContextRetriever:
    """Retrieves relevant code context for a user question.

    Searches graph nodes by label matching the question keywords, and
    blends in durable facts from Repository Memory when a repo_url is
    available. Returns a formatted context string to include in the
    NIM prompt.
    """

    def __init__(self) -> None:
        self._repo = SQLiteGraphRepository(get_settings().database_url)

    async def retrieve(
        self,
        job_id: str,
        question: str,
        max_nodes: int = 8,
        repo_url: str | None = None,
        max_facts: int = 4,
    ) -> str:
        """Find relevant graph nodes (and, if repo_url is known, relevant
        stored facts from prior analyses) for a question."""
        try:
            nodes = await self._repo.get_nodes_by_job(job_id)
            keywords = self._extract_keywords(question)

            graph_section = await self._retrieve_graph_context(
                job_id, nodes, keywords, max_nodes
            )
            memory_section = await self._retrieve_memory_context(
                repo_url, keywords, max_facts
            )

            sections = [s for s in (graph_section, memory_section) if s]
            if not sections:
                return "No code context available for this repository."
            return "\n\n".join(sections)

        except Exception as e:
            logger.warning(
                "context_retrieval_failed",
                job_id=job_id,
                error=str(e),
            )
            return "Context retrieval failed — answering from general knowledge."

    async def _retrieve_graph_context(
        self,
        job_id: str,
        nodes: list,
        keywords: list[str],
        max_nodes: int,
    ) -> str:
        """Unchanged behavior — score and format live graph nodes."""
        if not nodes:
            return ""

        scored = []
        for node in nodes:
            score = self._score_node(node.label, node.properties, keywords)
            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_nodes = [n for _, n in scored[:max_nodes]]

        if not top_nodes:
            repo_nodes = [n for n in nodes if n.node_type == NodeType.REPOSITORY]
            module_nodes = [n for n in nodes if n.node_type == NodeType.MODULE]
            top_nodes = repo_nodes + module_nodes[:6]

        if not top_nodes:
            return ""

        return self._format_graph_context(top_nodes)

    async def _retrieve_memory_context(
        self,
        repo_url: str | None,
        keywords: list[str],
        max_facts: int,
    ) -> str:
        """NEW — search durable facts from prior analyses of this repo.
        Silently returns nothing if repo_url is unknown or memory has
        nothing on this repo yet; chat should never break because memory
        is empty."""
        if not repo_url or not keywords:
            return ""

        try:
            facts = await memory_repository.search_facts(
                keywords, repo_url=repo_url, limit=max_facts
            )
        except Exception as e:
            logger.warning("memory_context_retrieval_failed", repo_url=repo_url, error=str(e))
            return ""

        if not facts:
            return ""

        lines = ["## What's known from prior analyses of this repository:\n"]
        for fact in facts:
            lines.append(f"- {fact.text}")
        return "\n".join(lines)

    def _extract_keywords(self, question: str) -> list[str]:
        """Extract meaningful keywords from a question."""
        stopwords = {
            "what", "how", "why", "where", "when", "does", "do",
            "is", "are", "the", "a", "an", "in", "of", "to", "and",
            "or", "for", "with", "this", "that", "it", "can", "you",
            "me", "about", "tell", "explain", "describe", "show",
        }
        words = question.lower().replace("?", "").replace(",", "").split()
        return [w for w in words if w not in stopwords and len(w) > 2]

    def _score_node(
        self,
        label: str,
        properties: dict,
        keywords: list[str],
    ) -> int:
        """Score a node's relevance to the keywords."""
        score = 0
        label_lower = label.lower()
        file_path = str(properties.get("file", "")).lower()
        path = str(properties.get("path", "")).lower()

        for kw in keywords:
            if kw in label_lower:
                score += 3  # Direct label match — high relevance
            if kw in file_path:
                score += 2  # File path match
            if kw in path:
                score += 1  # Module path match

        return score

    def _format_graph_context(
        self,
        nodes: list,
    ) -> str:
        """Format nodes as readable context for the LLM."""
        lines = ["## Relevant code context from the repository:\n"]

        by_type: dict[str, list] = {}
        for node in nodes:
            type_name = node.node_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(node)

        for type_name, type_nodes in by_type.items():
            lines.append(f"### {type_name} nodes:")
            for node in type_nodes:
                file_path = node.properties.get("file", "")
                methods = node.properties.get("methods", "")
                lines_count = node.properties.get("lines", "")

                detail = f"- `{node.label}`"
                if file_path:
                    detail += f" in `{file_path}`"
                if methods:
                    detail += f" ({methods} methods)"
                if lines_count:
                    detail += f" — {lines_count} lines"
                lines.append(detail)
            lines.append("")

        return "\n".join(lines)