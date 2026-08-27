"""Context Retriever — Cortex's own intelligence for finding relevant code.

This is Cortex's RETRIEVAL BRAIN — not NIM. It finds the most relevant
code context for a user's question using:
  1. FTS5 full-text search (BM25 ranking) over facts and graph nodes
  2. 1-hop graph expansion (find connected nodes for richer context)
  3. Stacktrace parsing (detect pasted traces and retrieve matching code)
  4. Repository Memory (durable facts from prior analyses)

The context is then formatted and provided to the chat as grounded evidence.
NIM explains/synthesizes — Cortex finds and structures.
"""

from __future__ import annotations

import re
from collections import defaultdict

from cortex.graph.infrastructure.dependencies import graph_repository
from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.memory.infrastructure.dependencies import memory_repository
from cortex.search.fts_engine import FTSEngine
import structlog

logger = structlog.get_logger()


class ContextRetriever:
    """Retrieves relevant code context for a user question.

    Intelligence pipeline:
      1. Detect if the message contains a stacktrace → parse symbols
      2. FTS5 search across facts and graph nodes
      3. 1-hop graph expansion on matched nodes (callers, callees, dependencies)
      4. Memory facts from prior analyses
      5. Format as structured context for the AI prompt
    """

    def __init__(self) -> None:
        self._graph_repo = graph_repository
        self._fts = FTSEngine()

    async def retrieve(
        self,
        job_id: str,
        question: str,
        max_results: int = 12,
        repo_url: str | None = None,
    ) -> str:
        """Find the most relevant context for a question.

        Combines FTS5 search, graph traversal, stacktrace parsing,
        and repository memory into a unified context string.
        """
        try:
            sections: list[str] = []

            # Step 1: Detect stacktrace
            stacktrace_symbols = self._parse_stacktrace(question)
            if stacktrace_symbols:
                trace_context = await self._retrieve_stacktrace_context(
                    job_id, stacktrace_symbols
                )
                if trace_context:
                    sections.append(trace_context)

            # Step 2: FTS5 search (Cortex's own search brain)
            fts_context = await self._retrieve_fts_context(
                question, job_id, repo_url, max_results
            )
            if fts_context:
                sections.append(fts_context)

            # Step 3: Graph keyword matching + 1-hop expansion
            graph_context = await self._retrieve_graph_context(
                job_id, question, max_results
            )
            if graph_context:
                sections.append(graph_context)

            # Step 4: Repository memory (prior analyses)
            memory_context = await self._retrieve_memory_context(
                repo_url, question
            )
            if memory_context:
                sections.append(memory_context)

            if not sections:
                return "No code context available for this repository."

            return "\n\n---\n\n".join(sections)

        except Exception as e:
            logger.warning(
                "context_retrieval_failed",
                job_id=job_id,
                error=str(e),
            )
            return "Context retrieval encountered an error — answering from general knowledge."

    def _parse_stacktrace(self, text: str) -> list[str]:
        """Detect and parse a stacktrace to extract class/method symbols.

        Detects:
          - Python tracebacks (File "path", line N, in function)
          - Java/Kotlin stacktraces (at package.Class.method(File.java:N))
          - JavaScript/TS stacktraces (at Function (file:line:col))
        """
        symbols: list[str] = []

        # Python traceback pattern
        py_pattern = re.compile(r'File "([^"]+)", line \d+, in (\w+)')
        for match in py_pattern.finditer(text):
            file_path = match.group(1)
            function_name = match.group(2)
            if function_name not in ("<module>", "<lambda>"):
                symbols.append(function_name)
            # Extract filename
            filename = file_path.split("/")[-1].split("\\")[-1]
            if filename.endswith(".py"):
                symbols.append(filename[:-3])  # module name

        # Java stacktrace pattern
        java_pattern = re.compile(r'at\s+([\w.]+)\.(\w+)\(([^)]+)\)')
        for match in java_pattern.finditer(text):
            class_name = match.group(1).split(".")[-1]
            method_name = match.group(2)
            symbols.extend([class_name, method_name])

        # JavaScript/TS pattern
        js_pattern = re.compile(r'at\s+(\w+)\s+\(([^)]+)\)')
        for match in js_pattern.finditer(text):
            fn_name = match.group(1)
            if fn_name not in ("Object", "Module", "Array", "Promise"):
                symbols.append(fn_name)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for s in symbols:
            if s.lower() not in seen and len(s) >= 2:
                seen.add(s.lower())
                unique.append(s)

        return unique[:10]

    async def _retrieve_stacktrace_context(
        self, job_id: str, symbols: list[str]
    ) -> str:
        """Find graph nodes matching stacktrace symbols."""
        nodes = await self._graph_repo.get_nodes_by_job(job_id)
        if not nodes:
            return ""

        matched: list[tuple[str, str, str]] = []  # (label, type, file)
        for node in nodes:
            label_lower = node.label.lower()
            for symbol in symbols:
                if symbol.lower() == label_lower or symbol.lower() in label_lower:
                    file_path = str(node.properties.get("file", ""))
                    matched.append((node.label, node.node_type.value, file_path))
                    break

        if not matched:
            return ""

        lines = ["## Stacktrace Context (matched symbols from your trace):\n"]
        for label, ntype, fpath in matched[:8]:
            detail = f"- `{label}` ({ntype})"
            if fpath:
                detail += f" in `{fpath}`"
            lines.append(detail)

        return "\n".join(lines)

    async def _retrieve_fts_context(
        self,
        question: str,
        job_id: str | None,
        repo_url: str | None,
        max_results: int,
    ) -> str:
        """Use FTS5 to find relevant facts and nodes."""
        try:
            results = await self._fts.search(
                query=question,
                job_id=job_id,
                repo_url=repo_url,
                limit=max_results,
            )
        except Exception as e:
            logger.debug("fts_search_failed_in_context", error=str(e))
            return ""

        if not results:
            return ""

        lines = ["## Search Results (ranked by relevance):\n"]
        for r in results[:8]:
            if r.source == "fact":
                lines.append(f"- **[Fact]** {r.text}")
            else:
                detail = f"- **[{r.category}]** `{r.text}`"
                if r.source_file:
                    detail += f" in `{r.source_file.split('/')[-1]}`"
                lines.append(detail)

        return "\n".join(lines)

    async def _retrieve_graph_context(
        self,
        job_id: str,
        question: str,
        max_nodes: int,
    ) -> str:
        """Score graph nodes by keyword relevance + 1-hop expansion."""
        nodes = await self._graph_repo.get_nodes_by_job(job_id)
        if not nodes:
            return ""

        keywords = self._extract_keywords(question)
        if not keywords:
            return ""

        # Score nodes
        scored: list[tuple[int, object]] = []
        for node in nodes:
            score = self._score_node(node.label, node.properties, keywords)
            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_nodes = [n for _, n in scored[:max_nodes]]

        if not top_nodes:
            return ""

        # 1-hop expansion: get edges for top nodes to show connections
        edges = await self._graph_repo.get_edges_by_job(job_id)
        node_ids = {n.id for n in top_nodes}
        node_map = {n.id: n for n in nodes}

        connections: list[str] = []
        for edge in edges:
            if edge.source_id in node_ids or edge.target_id in node_ids:
                src = node_map.get(edge.source_id)
                tgt = node_map.get(edge.target_id)
                if src and tgt and edge.relationship != RelationshipType.CONTAINS:
                    connections.append(
                        f"  `{src.label}` —[{edge.relationship.value}]→ `{tgt.label}`"
                    )

        # Format
        lines = ["## Graph Context (relevant nodes + relationships):\n"]

        by_type: dict[str, list] = defaultdict(list)
        for node in top_nodes:
            by_type[node.node_type.value].append(node)

        for type_name, type_nodes in by_type.items():
            for node in type_nodes:
                file_path = node.properties.get("file", "") or node.properties.get("path", "")
                methods = node.properties.get("methods", "")
                complexity = node.properties.get("cyclomatic", "")

                detail = f"- **{type_name}:** `{node.label}`"
                if file_path:
                    detail += f" in `{str(file_path).split('/')[-1]}`"
                if methods:
                    detail += f" ({methods} methods)"
                if complexity and int(complexity or 0) > 5:
                    detail += f" [complexity: {complexity}]"
                lines.append(detail)

        if connections:
            lines.append("\n**Relationships:**")
            for conn in connections[:6]:
                lines.append(conn)

        return "\n".join(lines)

    async def _retrieve_memory_context(
        self, repo_url: str | None, question: str
    ) -> str:
        """Search durable facts from prior analyses."""
        if not repo_url:
            return ""

        keywords = self._extract_keywords(question)
        if not keywords:
            return ""

        try:
            facts = await memory_repository.search_facts(
                keywords, repo_url=repo_url, limit=4
            )
        except Exception:
            return ""

        if not facts:
            return ""

        lines = ["## Repository Memory (from prior analyses):\n"]
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
            "please", "could", "would", "should", "which", "have",
            "has", "had", "be", "been", "being", "my", "your",
        }
        words = question.lower().replace("?", "").replace(",", "").replace(".", "").split()
        return [w for w in words if w not in stopwords and len(w) >= 2]

    def _score_node(self, label: str, properties: dict, keywords: list[str]) -> int:
        """Score a node's relevance to the keywords."""
        score = 0
        label_lower = label.lower()
        file_path = str(properties.get("file", "")).lower()
        path = str(properties.get("path", "")).lower()
        route = str(properties.get("route_info", "")).lower()
        qualified = str(properties.get("qualified_name", "")).lower()

        for kw in keywords:
            if kw in label_lower:
                score += 4
            if kw in qualified:
                score += 3
            if kw in route:
                score += 3
            if kw in file_path:
                score += 2
            if kw in path:
                score += 1

        return score
