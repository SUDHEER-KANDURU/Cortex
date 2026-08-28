"""Context Retriever — Cortex's own intelligence for finding relevant code.

This is Cortex's RETRIEVAL BRAIN — not NIM. It finds the most relevant
code context for a user's question using:
  1. Intent detection (classify what the user wants)
  2. CortexReasoner intelligence (architecture, data flows, modules, entry points)
  3. Intent-driven graph retrieval (focus on relevant node types)
  4. Blast radius (on-demand "what would break?" analysis)
  5. FTS5 full-text search (BM25 ranking) over facts and graph nodes
  6. 1-hop graph expansion (find connected nodes for richer context)
  7. Stacktrace parsing (detect pasted traces and retrieve matching code)
  8. Repository Memory (durable facts from prior analyses)

The context is then formatted and provided to the chat as grounded evidence.
NIM explains/synthesizes — Cortex finds and structures.

Context budget: max ~5000 tokens of context per query to avoid overwhelming
the LLM. Quality over quantity.
"""

from __future__ import annotations

import re
from collections import defaultdict
from enum import Enum

import structlog
from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.graph.infrastructure.dependencies import graph_repository
from cortex.memory.infrastructure.dependencies import memory_repository
from cortex.search.fts_engine import FTSEngine

logger = structlog.get_logger()

# ── Context budget ────────────────────────────────────────────────────────────
MAX_CONTEXT_CHARS = 16000  # ~4000 tokens budget for context


# ── Intent Detection ──────────────────────────────────────────────────────────

class QueryIntent(str, Enum):
    """Classified intent of a user question."""
    ARCHITECTURE = "architecture"       # System design, layers, patterns
    NAVIGATION = "navigation"           # Where is X? How to find X?
    DATA_FLOW = "data_flow"             # How does request/data flow?
    DEPENDENCY = "dependency"           # What depends on what?
    COMPLEXITY = "complexity"           # What's complex/risky?
    DEBUGGING = "debugging"            # Stacktrace, error, bug
    EXPLANATION = "explanation"         # What does X do? Why is X?
    METRICS = "metrics"                # How many? Stats? Score?
    ENTRY_POINT = "entry_point"        # Where does it start?
    LEARNING = "learning"              # What should I learn first?
    GENERAL = "general"                # Catch-all


# Intent keywords — deterministic classification
_INTENT_PATTERNS: dict[QueryIntent, list[str]] = {
    QueryIntent.ARCHITECTURE: [
        "architecture", "design", "pattern", "layer", "structure",
        "organized", "module", "separation", "concern", "abstraction",
    ],
    QueryIntent.NAVIGATION: [
        "where", "find", "locate", "file", "path", "which file",
        "defined", "located", "look for",
    ],
    QueryIntent.DATA_FLOW: [
        "flow", "request", "pipeline", "process", "chain",
        "step", "sequence", "lifecycle", "journey", "through",
    ],
    QueryIntent.DEPENDENCY: [
        "depend", "import", "require", "coupled", "coupling",
        "uses", "needs", "relies", "connected", "relationship",
    ],
    QueryIntent.COMPLEXITY: [
        "complex", "complicated", "risk", "dangerous", "god class",
        "god function", "debt", "smell", "refactor", "improve",
        "worst", "biggest", "hardest",
    ],
    QueryIntent.DEBUGGING: [
        "error", "bug", "traceback", "exception", "stack",
        "crash", "fail", "break", "fix", "wrong",
    ],
    QueryIntent.EXPLANATION: [
        "what does", "explain", "purpose", "responsibility",
        "why", "reason", "how does", "mean", "role",
    ],
    QueryIntent.METRICS: [
        "how many", "count", "total", "number", "stats",
        "score", "grade", "metric", "size",
    ],
    QueryIntent.ENTRY_POINT: [
        "entry point", "start", "main", "bootstrap", "init",
        "begin", "launch", "run",
    ],
    QueryIntent.LEARNING: [
        "learn", "understand", "onboard", "first", "beginner",
        "study", "read first", "start with", "recommend",
    ],
}

# Which node types matter most for each intent
_INTENT_NODE_PRIORITY: dict[QueryIntent, list[NodeType]] = {
    QueryIntent.ARCHITECTURE: [NodeType.MODULE, NodeType.CLASS, NodeType.FILE],
    QueryIntent.NAVIGATION: [NodeType.FILE, NodeType.CLASS, NodeType.FUNCTION],
    QueryIntent.DATA_FLOW: [NodeType.ENDPOINT, NodeType.FUNCTION, NodeType.CLASS],
    QueryIntent.DEPENDENCY: [NodeType.FILE, NodeType.MODULE, NodeType.CLASS],
    QueryIntent.COMPLEXITY: [NodeType.FUNCTION, NodeType.CLASS, NodeType.FILE],
    QueryIntent.DEBUGGING: [NodeType.FUNCTION, NodeType.CLASS, NodeType.FILE],
    QueryIntent.EXPLANATION: [NodeType.CLASS, NodeType.FUNCTION, NodeType.MODULE],
    QueryIntent.METRICS: [NodeType.FILE, NodeType.MODULE, NodeType.REPOSITORY],
    QueryIntent.ENTRY_POINT: [NodeType.ENDPOINT, NodeType.FUNCTION, NodeType.FILE],
    QueryIntent.LEARNING: [NodeType.MODULE, NodeType.CLASS, NodeType.FILE],
    QueryIntent.GENERAL: [NodeType.CLASS, NodeType.FUNCTION, NodeType.FILE],
}

# Which edge types matter most for each intent
_INTENT_EDGE_PRIORITY: dict[QueryIntent, list[RelationshipType]] = {
    QueryIntent.ARCHITECTURE: [RelationshipType.CONTAINS, RelationshipType.IMPORTS],
    QueryIntent.DEPENDENCY: [
        RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON, RelationshipType.CALLS,
    ],
    QueryIntent.DATA_FLOW: [RelationshipType.CALLS, RelationshipType.IMPORTS],
    QueryIntent.COMPLEXITY: [RelationshipType.CALLS, RelationshipType.IMPORTS],
    QueryIntent.DEBUGGING: [RelationshipType.CALLS, RelationshipType.IMPORTS],
    QueryIntent.GENERAL: [
        RelationshipType.IMPORTS, RelationshipType.CALLS, RelationshipType.INHERITS,
    ],
}


def detect_intent(question: str) -> QueryIntent:
    """Classify the user's question into a query intent.

    Uses deterministic keyword matching — no AI required.
    Falls back to GENERAL if no strong signal is found.
    """
    q_lower = question.lower()

    # Check for stacktrace first — always debugging
    if re.search(r'(File ".*", line \d+|at\s+[\w.]+\(|Traceback)', question):
        return QueryIntent.DEBUGGING

    # Score each intent
    scores: dict[QueryIntent, int] = {}
    for intent, patterns in _INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if p in q_lower)
        if score > 0:
            scores[intent] = score

    if not scores:
        return QueryIntent.GENERAL

    # Return highest-scoring intent
    return max(scores, key=lambda k: scores[k])


class ContextRetriever:
    """Retrieves relevant code context for a user question.

    Enhanced intelligence pipeline:
      1. Classify intent (architecture, navigation, debugging, etc.)
      2. Detect if the message contains a stacktrace → parse symbols
      3. Query CortexReasoner for deep intelligence (architecture, flows, modules)
      4. On-demand blast radius (when user asks "what breaks if I change X?")
      5. Intent-driven graph retrieval (prioritize relevant node types)
      6. FTS5 search across facts and graph nodes
      7. 1-hop graph expansion (callers, callees, dependencies)
      8. Repository memory (durable facts from prior analyses)
      9. Assemble bounded context within token budget
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

        Bounded retrieval: total context stays within MAX_CONTEXT_CHARS.
        Intent-driven: different question types prioritize different data.
        Reasoner-enriched: uses CortexReasoner for deep structural understanding.
        """
        try:
            # Step 1: Detect intent
            intent = detect_intent(question)
            logger.debug(
                "chat_intent_detected",
                job_id=job_id,
                intent=intent.value,
                question_preview=question[:60],
            )

            sections: list[str] = []
            budget_remaining = MAX_CONTEXT_CHARS

            # Step 2: Stacktrace detection (highest priority for debugging)
            stacktrace_symbols = self._parse_stacktrace(question)
            if stacktrace_symbols:
                trace_context = await self._retrieve_stacktrace_context(
                    job_id, stacktrace_symbols
                )
                if trace_context:
                    sections.append(trace_context)
                    budget_remaining -= len(trace_context)

            # Step 3: CortexReasoner intelligence (architecture, flows, modules)
            # This is the KEY differentiator — gives chat deep structural understanding
            if budget_remaining > 3000:
                reasoner_context = await self._retrieve_reasoner_context(
                    job_id, question, intent, repo_url
                )
                if reasoner_context:
                    truncated = reasoner_context[:budget_remaining // 2]
                    sections.append(truncated)
                    budget_remaining -= len(truncated)

            # Step 4: Blast radius (if user asks "what breaks / what's affected?")
            if budget_remaining > 2000 and self._wants_blast_radius(question):
                blast_context = await self._retrieve_blast_radius_context(
                    job_id, question
                )
                if blast_context:
                    truncated = blast_context[:budget_remaining // 3]
                    sections.append(truncated)
                    budget_remaining -= len(truncated)

            # Step 5: Intent-driven graph retrieval
            if budget_remaining > 2000:
                graph_context = await self._retrieve_intent_graph_context(
                    job_id, question, intent, min(max_results, 10)
                )
                if graph_context:
                    truncated = graph_context[:budget_remaining // 2]
                    sections.append(truncated)
                    budget_remaining -= len(truncated)

            # Step 6: FTS5 search
            if budget_remaining > 1000:
                fts_context = await self._retrieve_fts_context(
                    question, job_id, repo_url, min(max_results, 8)
                )
                if fts_context:
                    truncated = fts_context[:budget_remaining // 2]
                    sections.append(truncated)
                    budget_remaining -= len(truncated)

            # Step 7: Repository memory
            if budget_remaining > 500:
                memory_context = await self._retrieve_memory_context(
                    repo_url, question
                )
                if memory_context:
                    truncated = memory_context[:budget_remaining]
                    sections.append(truncated)

            if not sections:
                return "No code context available for this repository."

            # Add intent hint for NIM
            intent_hint = f"[Query intent: {intent.value}]\n\n"
            return intent_hint + "\n\n---\n\n".join(sections)

        except Exception as e:
            logger.warning(
                "context_retrieval_failed",
                job_id=job_id,
                error=str(e),
            )
            return "Context retrieval encountered an error — answering from general knowledge."

    # ══════════════════════════════════════════════════════════════════════════
    # Reasoner Intelligence (NEW — deep structural understanding)
    # ══════════════════════════════════════════════════════════════════════════

    async def _retrieve_reasoner_context(
        self,
        job_id: str,
        question: str,
        intent: QueryIntent,
        repo_url: str | None,
    ) -> str:
        """Query the CortexReasoner for deep structural intelligence.

        Depending on intent, surfaces:
        - Architecture style and evidence
        - Data flows (how requests move through the system)
        - Module intelligence (roles, dependencies, risks)
        - Entry points
        - Starting point and learning recommendations
        - Complexity hotspots
        """
        try:
            from cortex.reasoning.application.reasoner import CortexReasoner

            nodes = await self._graph_repo.get_nodes_by_job(job_id)
            edges = await self._graph_repo.get_edges_by_job(job_id)

            if not nodes:
                return ""

            reasoner = CortexReasoner()
            understanding = reasoner.understand(
                job_id=job_id,
                repo_url=repo_url or "",
                nodes=nodes,
                edges=edges,
            )

            lines: list[str] = []

            # Always include the high-level purpose and architecture
            if understanding.purpose:
                lines.append(f"## Repository Purpose\n{understanding.purpose}")
            if understanding.headline:
                lines.append(f"**Summary:** {understanding.headline}")

            # Intent-specific intelligence
            if intent in (QueryIntent.ARCHITECTURE, QueryIntent.GENERAL):
                lines.append(self._format_architecture(understanding))

            if intent in (QueryIntent.DATA_FLOW, QueryIntent.ENTRY_POINT, QueryIntent.GENERAL):
                lines.append(self._format_data_flows(understanding))

            if intent in (QueryIntent.LEARNING, QueryIntent.GENERAL):
                lines.append(self._format_start_here(understanding))

            if intent in (QueryIntent.COMPLEXITY, QueryIntent.GENERAL):
                lines.append(self._format_complexity_hotspots(understanding))

            if intent in (QueryIntent.DEPENDENCY, QueryIntent.ARCHITECTURE):
                lines.append(self._format_module_intelligence(understanding, question))

            if intent == QueryIntent.ENTRY_POINT:
                lines.append(self._format_entry_points(understanding))

            if intent == QueryIntent.NAVIGATION:
                lines.append(self._format_module_navigation(understanding, question))

            if intent == QueryIntent.EXPLANATION:
                lines.append(self._format_module_intelligence(understanding, question))

            if intent == QueryIntent.METRICS:
                lines.append(self._format_metrics(understanding))

            return "\n\n".join(line for line in lines if line)

        except Exception as e:
            logger.debug("reasoner_context_failed", error=str(e))
            return ""

    def _format_architecture(self, u) -> str:
        """Format architecture intelligence."""
        lines = [f"## Architecture: {u.architecture_style.value.replace('_', ' ').title()}"]
        lines.append(u.architecture_description)
        if u.architecture_evidence:
            lines.append("**Evidence:**")
            for ev in u.architecture_evidence[:4]:
                lines.append(f"  - {ev}")
        if u.frameworks:
            lines.append(f"**Frameworks:** {', '.join(u.frameworks)}")
        if u.languages:
            lines.append(f"**Languages:** {', '.join(u.languages)}")
        return "\n".join(lines)

    def _format_data_flows(self, u) -> str:
        """Format data flow traces."""
        if not u.data_flows:
            return ""
        lines = ["## Data Flows (request paths through the system):"]
        for flow in u.data_flows[:5]:
            path_str = " → ".join(
                f"`{s.symbol}` ({s.role})" for s in flow.steps
            )
            lines.append(f"- **{flow.name}:** {path_str}")
        return "\n".join(lines)

    def _format_start_here(self, u) -> str:
        """Format learning/starting point recommendation."""
        if not u.start_here:
            return ""
        lines = ["## Where to Start"]
        lines.append(f"**Start with:** `{u.start_here}` in `{u.start_here_file}`")
        lines.append(f"**Why:** {u.start_here_reason}")
        return "\n".join(lines)

    def _format_complexity_hotspots(self, u) -> str:
        """Format complexity hotspots."""
        if not u.complexity_hotspots:
            return ""
        lines = ["## Complexity Hotspots (highest risk):"]
        for h in u.complexity_hotspots[:5]:
            symbol = h.get("symbol", "unknown")
            file = h.get("file", "")
            cyclo = h.get("cyclomatic", 0)
            loc = h.get("lines", 0)
            lines.append(f"- `{symbol}` in `{file}` — cyclomatic: {cyclo}, lines: {loc}")
        if u.architectural_risks:
            lines.append("\n**Architectural risks:**")
            for risk in u.architectural_risks[:3]:
                lines.append(f"  - {risk}")
        return "\n".join(lines)

    def _format_module_intelligence(self, u, question: str) -> str:
        """Format module intelligence, focusing on modules matching the question."""
        if not u.modules:
            return ""
        keywords = self._extract_keywords(question)
        # Find the most relevant modules
        relevant = []
        for m in u.modules:
            score = 0
            for kw in keywords:
                if kw in m.name.lower():
                    score += 5
                if kw in m.purpose.lower():
                    score += 3
                if any(kw in cls.lower() for cls in m.key_classes):
                    score += 2
            relevant.append((score, m))
        relevant.sort(key=lambda x: x[0], reverse=True)

        # If no keyword match, show the top modules by size/importance
        top = [m for _, m in relevant[:5]] if relevant[0][0] > 0 else u.modules[:5]

        lines = ["## Module Intelligence:"]
        for m in top:
            detail = f"- **{m.name}**"
            if m.architecture_role:
                detail += f" ({m.architecture_role})"
            if m.purpose:
                detail += f" — {m.purpose}"
            extras = []
            if m.file_count:
                extras.append(f"{m.file_count} files")
            if m.key_classes:
                extras.append(f"key: {', '.join(m.key_classes[:3])}")
            if m.dependencies:
                extras.append(f"deps: {', '.join(m.dependencies[:3])}")
            if m.risks:
                extras.append(f"risks: {'; '.join(m.risks[:2])}")
            if extras:
                detail += f" [{', '.join(extras)}]"
            lines.append(detail)
        return "\n".join(lines)

    def _format_entry_points(self, u) -> str:
        """Format entry points."""
        if not u.entry_points:
            return ""
        lines = ["## Entry Points:"]
        for ep in u.entry_points[:10]:
            detail = f"- `{ep.label}` ({ep.kind})"
            if ep.route:
                detail += f" — {ep.method} {ep.route}"
            if ep.file_path:
                detail += f" in `{ep.file_path.split('/')[-1]}`"
            lines.append(detail)
        return "\n".join(lines)

    def _format_module_navigation(self, u, question: str) -> str:
        """Help user navigate to specific code."""
        keywords = self._extract_keywords(question)
        lines = ["## Navigation (matching modules and symbols):"]
        for m in u.modules:
            matched = any(kw in m.name.lower() for kw in keywords)
            if matched:
                lines.append(f"- Module `{m.name}` at `{m.path}`")
                for cls in m.key_classes[:3]:
                    lines.append(f"  - Class: `{cls}`")
                for fn in m.key_functions[:3]:
                    lines.append(f"  - Function: `{fn}`")
        return "\n".join(lines) if len(lines) > 1 else ""

    def _format_metrics(self, u) -> str:
        """Format metrics/stats."""
        lines = ["## Repository Metrics:"]
        lines.append(f"- Files: {u.total_files} | Lines: {u.total_lines}")
        lines.append(f"- Modules: {u.total_modules} | Classes: {u.total_classes}")
        lines.append(f"- Functions: {u.total_functions} | Endpoints: {u.total_endpoints}")
        lines.append(f"- Tests: {u.total_tests}")
        lines.append(f"- Health: {u.overall_score}/100 (Grade {u.overall_grade})")
        lines.append(f"- Architecture: {u.architecture_style.value}")
        lines.append(f"- Languages: {', '.join(u.languages)}")
        return "\n".join(lines)

    # ══════════════════════════════════════════════════════════════════════════
    # Blast Radius (on-demand)
    # ══════════════════════════════════════════════════════════════════════════

    def _wants_blast_radius(self, question: str) -> bool:
        """Detect if the user is asking about change impact."""
        q_lower = question.lower()
        blast_signals = [
            "what would break", "what breaks", "impact", "blast radius",
            "what happens if i change", "what depends on", "affect",
            "safe to change", "safe to modify", "safe to remove",
            "who uses", "what uses",
        ]
        return any(signal in q_lower for signal in blast_signals)

    async def _retrieve_blast_radius_context(
        self, job_id: str, question: str
    ) -> str:
        """Perform on-demand blast radius analysis for a symbol mentioned in the question."""
        try:
            from cortex.overview.blast_radius import BlastRadiusAnalyzer

            nodes = await self._graph_repo.get_nodes_by_job(job_id)
            edges = await self._graph_repo.get_edges_by_job(job_id)
            if not nodes:
                return ""

            # Find the target node from the question
            keywords = self._extract_keywords(question)
            target_node = None
            best_score = 0
            for node in nodes:
                if node.node_type in (NodeType.REPOSITORY, NodeType.MODULE):
                    continue  # Too broad
                score = 0
                for kw in keywords:
                    if kw in node.label.lower():
                        score += 4
                    if kw in str(node.properties.get("file", "")).lower():
                        score += 2
                if score > best_score:
                    best_score = score
                    target_node = node

            if not target_node or best_score < 4:
                return ""

            analyzer = BlastRadiusAnalyzer()
            result = analyzer.analyze(target_node, nodes, edges)

            lines = [f"## Blast Radius for `{result.target_label}`:"]
            lines.append(f"**Risk level:** {result.risk_level} (score: {result.risk_score}/100)")
            if result.risk_factors:
                for rf in result.risk_factors[:3]:
                    lines.append(f"  - {rf}")
            if result.direct_dependents:
                lines.append(f"\n**Direct dependents ({len(result.direct_dependents)}):**")
                for dep in result.direct_dependents[:5]:
                    lines.append(f"  - `{dep.label}` ({dep.node_type}) via {dep.relationship}")
            if result.transitive_dependents:
                trans_count = len(result.transitive_dependents)
                lines.append(
                    f"\n**Transitive impact:** {trans_count} additional nodes affected"
                )
            if result.affected_modules:
                lines.append(f"**Affected modules:** {', '.join(result.affected_modules)}")
            if result.affected_tests:
                lines.append(f"**Tests to verify:** {len(result.affected_tests)}")
            return "\n".join(lines)

        except Exception as e:
            logger.debug("blast_radius_context_failed", error=str(e))
            return ""

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
            filename = file_path.split("/")[-1].split("\\")[-1]
            if filename.endswith(".py"):
                symbols.append(filename[:-3])

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
        """Find graph nodes matching stacktrace symbols + their callers."""
        nodes = await self._graph_repo.get_nodes_by_job(job_id)
        if not nodes:
            return ""

        matched: list[tuple[str, str, str, dict]] = []
        for node in nodes:
            label_lower = node.label.lower()
            for symbol in symbols:
                if symbol.lower() == label_lower or symbol.lower() in label_lower:
                    file_path = str(node.properties.get("file", ""))
                    matched.append((node.label, node.node_type.value, file_path, node.properties))
                    break

        if not matched:
            return ""

        lines = ["## Stacktrace Context (matched symbols from your trace):\n"]
        for label, ntype, fpath, props in matched[:8]:
            detail = f"- `{label}` ({ntype})"
            if fpath:
                detail += f" in `{fpath}`"
            complexity = props.get("cyclomatic", "")
            if complexity and int(complexity or 0) > 5:
                detail += f" [complexity: {complexity}]"
            lines.append(detail)

        # Also find callers of the matched symbols for debugging context
        edges = await self._graph_repo.get_edges_by_job(job_id)
        node_map = {n.id: n for n in nodes}
        matched_labels = {m[0].lower() for m in matched}
        matched_ids = {
            n.id for n in nodes if n.label.lower() in matched_labels
        }

        callers: list[str] = []
        for edge in edges:
            if edge.target_id in matched_ids and edge.relationship == RelationshipType.CALLS:
                src = node_map.get(edge.source_id)
                if src:
                    callers.append(f"  `{src.label}` calls into the trace")

        if callers:
            lines.append("\n**Callers of traced symbols:**")
            for c in callers[:4]:
                lines.append(c)

        return "\n".join(lines)

    async def _retrieve_intent_graph_context(
        self,
        job_id: str,
        question: str,
        intent: QueryIntent,
        max_nodes: int,
    ) -> str:
        """Intent-driven graph retrieval — prioritizes node types and edges
        based on what the user is actually asking about."""
        nodes = await self._graph_repo.get_nodes_by_job(job_id)
        if not nodes:
            return ""

        keywords = self._extract_keywords(question)
        priority_types = _INTENT_NODE_PRIORITY.get(
            intent, _INTENT_NODE_PRIORITY[QueryIntent.GENERAL]
        )

        # Score nodes with intent-aware boosting
        scored: list[tuple[float, object]] = []
        for node in nodes:
            base_score = self._score_node(node.label, node.properties, keywords)

            # Boost nodes whose type matches the intent priority
            type_boost = 0
            if node.node_type in priority_types:
                rank = priority_types.index(node.node_type)
                type_boost = (len(priority_types) - rank) * 2

            # Intent-specific boosting
            intent_boost = self._intent_boost(node, intent)

            total = base_score + type_boost + intent_boost
            if total > 0:
                scored.append((total, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_nodes = [n for _, n in scored[:max_nodes]]

        if not top_nodes:
            # Fallback: for broad questions, show high-level structure
            if intent in (QueryIntent.ARCHITECTURE, QueryIntent.LEARNING, QueryIntent.ENTRY_POINT):
                top_nodes = [
                    n for n in nodes
                    if n.node_type in (NodeType.MODULE, NodeType.ENDPOINT)
                ][:max_nodes]

        if not top_nodes:
            return ""

        # 1-hop expansion with intent-relevant edge filtering
        edges = await self._graph_repo.get_edges_by_job(job_id)
        node_ids = {n.id for n in top_nodes}
        node_map = {n.id: n for n in nodes}
        priority_edges = _INTENT_EDGE_PRIORITY.get(
            intent, _INTENT_EDGE_PRIORITY[QueryIntent.GENERAL]
        )

        connections: list[str] = []
        for edge in edges:
            if edge.source_id in node_ids or edge.target_id in node_ids:
                # Filter to intent-relevant edge types
                if edge.relationship in priority_edges:
                    src = node_map.get(edge.source_id)
                    tgt = node_map.get(edge.target_id)
                    if src and tgt:
                        connections.append(
                            f"  `{src.label}` —[{edge.relationship.value}]→ `{tgt.label}`"
                        )

        # Format with rich properties
        lines = [f"## Graph Context ({intent.value} focus):\n"]

        by_type: dict[str, list] = defaultdict(list)
        for node in top_nodes:
            by_type[node.node_type.value].append(node)

        for type_name, type_nodes in by_type.items():
            for node in type_nodes:
                detail = self._format_node_detail(node)
                lines.append(detail)

        if connections:
            lines.append("\n**Key relationships:**")
            # Deduplicate connections
            seen_conns: set[str] = set()
            for conn in connections[:10]:
                if conn not in seen_conns:
                    seen_conns.add(conn)
                    lines.append(conn)

        return "\n".join(lines)

    def _intent_boost(self, node, intent: QueryIntent) -> int:
        """Give extra points to nodes that are especially relevant to the intent."""
        boost = 0
        props = node.properties

        if intent == QueryIntent.ENTRY_POINT:
            if props.get("is_entry_point") or props.get("route_info"):
                boost += 8
            if node.label.lower() in ("main", "app", "server", "index"):
                boost += 5

        elif intent == QueryIntent.COMPLEXITY:
            cyclo = int(props.get("cyclomatic", 0) or 0)
            lines = int(props.get("lines", 0) or 0)
            methods = int(props.get("methods", 0) or 0)
            if cyclo > 10:
                boost += 6
            if lines > 100:
                boost += 4
            if methods > 10:
                boost += 5

        elif intent == QueryIntent.DATA_FLOW:
            if props.get("route_info"):
                boost += 6
            if node.node_type == NodeType.ENDPOINT:
                boost += 8

        elif intent == QueryIntent.ARCHITECTURE:
            if node.node_type == NodeType.MODULE:
                boost += 4
            if "abstract" in str(props.get("decorators", "")).lower():
                boost += 3
            if any(
                p in node.label.lower()
                for p in ["service", "repository", "controller", "handler"]
            ):
                boost += 4

        elif intent == QueryIntent.DEPENDENCY:
            # Prefer nodes with high fan-in or fan-out
            if node.node_type == NodeType.FILE:
                boost += 2

        elif intent == QueryIntent.LEARNING:
            # Prefer simpler, foundational nodes
            cyclo = int(props.get("cyclomatic", 0) or 0)
            if cyclo < 5:
                boost += 2
            if props.get("has_docstring"):
                boost += 3

        return boost

    def _format_node_detail(self, node) -> str:
        """Format a node with rich property information."""
        props = node.properties
        detail = f"- **{node.node_type.value}:** `{node.label}`"

        file_path = props.get("file", "") or props.get("path", "")
        if file_path:
            detail += f" in `{str(file_path).split('/')[-1]}`"

        # Add relevant properties based on node type
        extras: list[str] = []
        methods = props.get("methods", "")
        if methods and int(methods or 0) > 0:
            extras.append(f"{methods} methods")

        complexity = props.get("cyclomatic", "")
        if complexity and int(complexity or 0) > 3:
            extras.append(f"complexity: {complexity}")

        lines = props.get("lines", "")
        if lines and int(lines or 0) > 50:
            extras.append(f"{lines} lines")

        route = props.get("route_info", "")
        if route:
            extras.append(f"route: {route}")

        params = props.get("parameters", "")
        if params and int(params or 0) > 4:
            extras.append(f"{params} params")

        if props.get("is_async"):
            extras.append("async")

        if props.get("has_docstring"):
            extras.append("documented")

        if extras:
            detail += f" [{', '.join(extras)}]"

        return detail

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

        lines = ["## What's known from prior analyses:\n"]
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
            "i", "we", "they", "them", "its", "from", "at", "on",
            "there", "here", "all", "any", "some", "each", "every",
            "much", "many", "more", "most", "very", "just", "also",
        }
        words = re.findall(r'\b\w+\b', question.lower())
        return [w for w in words if w not in stopwords and len(w) >= 2][:15]

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
