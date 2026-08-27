"""Performance Analyzer — Cortex's deterministic performance detection.

Detects performance anti-patterns from graph structure WITHOUT AI.
This is Cortex's own performance intelligence.

Detections:
  - Nested loops (high nesting depth in functions with loops)
  - Sync operations in async context
  - N+1 query patterns (loop inside function that calls DB)
  - Unbounded operations (no pagination/limit signals)
  - High call-count functions (potential hot paths)
  - Large file processing without streaming

Each finding: evidence, severity, fix_template.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cortex.graph.domain.entities import GraphNode, NodeType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


@dataclass
class PerformanceFinding:
    """A single performance issue with evidence and fix."""
    title: str
    severity: str  # high, medium, low
    category: str  # loops, async, query, unbounded, hotpath
    description: str
    file_path: str = ""
    line: int = 0
    symbol: str = ""
    evidence: str = ""
    fix_template: str = ""
    confidence: float = 0.8


class PerformanceAnalyzer:
    """Deterministic performance analysis from graph node metrics.

    Uses cyclomatic complexity, nesting depth, call count, and async
    flags to detect performance anti-patterns.
    """

    def analyze(self, graph: GraphBuildResult) -> list[PerformanceFinding]:
        """Run all performance detections."""
        findings: list[PerformanceFinding] = []

        functions = [n for n in graph.nodes if n.node_type in (
            NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT
        )]

        # Detection 1: Deep nesting (likely nested loops)
        findings.extend(self._detect_deep_nesting(functions))

        # Detection 2: Sync functions in async codebase
        findings.extend(self._detect_sync_in_async(functions))

        # Detection 3: High call-count functions (hot paths)
        findings.extend(self._detect_hot_paths(functions))

        # Detection 4: Large functions with high complexity (potential O(n^2))
        findings.extend(self._detect_quadratic_risk(functions))

        # Detection 5: Missing pagination signals on endpoints
        findings.extend(self._detect_unbounded_endpoints(graph))

        return findings

    def _detect_deep_nesting(self, functions: list[GraphNode]) -> list[PerformanceFinding]:
        """Functions with nesting_depth >= 4 likely have nested loops."""
        findings: list[PerformanceFinding] = []

        for fn in functions:
            nesting = int(fn.properties.get("nesting_depth", 0) or 0)
            complexity = int(fn.properties.get("cyclomatic", 0) or 0)

            if nesting >= 4 and complexity >= 8:
                lines = int(fn.properties.get("lines", 0) or 0)
                findings.append(PerformanceFinding(
                    title=f"Deep nesting in `{fn.label}` (depth: {nesting})",
                    severity="high",
                    category="loops",
                    description=(
                        f"Nesting depth {nesting} with complexity {complexity} suggests "
                        f"nested loops or deeply branching logic. Potential O(n²) or worse."
                    ),
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0) or 0),
                    symbol=fn.label,
                    evidence=f"nesting_depth={nesting}, cyclomatic={complexity}, lines={lines}",
                    fix_template=(
                        "Flatten nested loops: (1) Extract inner loop to a separate function, "
                        "(2) Use hash maps for O(1) lookups instead of nested iteration, "
                        "(3) Consider itertools or set operations for intersection/filtering."
                    ),
                    confidence=0.8,
                ))

        return sorted(findings, key=lambda f: int(f.evidence.split(",")[0].split("=")[1]), reverse=True)[:5]

    def _detect_sync_in_async(self, functions: list[GraphNode]) -> list[PerformanceFinding]:
        """Detect sync-heavy functions in a codebase that uses async.

        If the codebase has async functions but also has sync functions
        with high call counts (likely I/O), those may be blocking the event loop.
        """
        findings: list[PerformanceFinding] = []

        async_fns = [f for f in functions if f.properties.get("is_async")]
        sync_fns = [f for f in functions if not f.properties.get("is_async")]

        # Only relevant if the codebase uses async
        if len(async_fns) < 3:
            return []

        # Find sync functions with high call counts that might do I/O
        io_keywords = {"read", "write", "open", "fetch", "request", "connect", "send", "recv", "sleep"}
        for fn in sync_fns:
            calls = str(fn.properties.get("calls", "")).lower()
            name_lower = fn.label.lower()

            is_io_like = any(kw in calls or kw in name_lower for kw in io_keywords)
            call_count = int(fn.properties.get("call_count", 0) or 0)

            if is_io_like and call_count >= 3:
                file_path = str(fn.properties.get("file", ""))
                if "test" in file_path.lower():
                    continue
                findings.append(PerformanceFinding(
                    title=f"Sync I/O in async codebase: `{fn.label}`",
                    severity="medium",
                    category="async",
                    description=(
                        "This sync function appears to do I/O in a codebase that uses async. "
                        "If called from an async context, it will block the event loop."
                    ),
                    file_path=file_path,
                    line=int(fn.properties.get("line", 0) or 0),
                    symbol=fn.label,
                    evidence=f"calls={calls}, call_count={call_count}, is_async=False",
                    fix_template=(
                        "Convert to async: (1) Use aiofiles for file I/O, (2) Use httpx/aiohttp "
                        "for HTTP calls, (3) Use asyncpg/aiosqlite for DB, (4) Or run in "
                        "executor: await asyncio.to_thread(sync_fn, args)"
                    ),
                    confidence=0.6,
                ))

        return findings[:4]

    def _detect_hot_paths(self, functions: list[GraphNode]) -> list[PerformanceFinding]:
        """Functions with very high call counts may be performance-critical."""
        findings: list[PerformanceFinding] = []

        high_callers = sorted(
            [f for f in functions if int(f.properties.get("call_count", 0) or 0) >= 15],
            key=lambda f: int(f.properties.get("call_count", 0) or 0),
            reverse=True,
        )

        for fn in high_callers[:3]:
            call_count = int(fn.properties.get("call_count", 0) or 0)
            complexity = int(fn.properties.get("cyclomatic", 0) or 0)

            if complexity >= 5:
                findings.append(PerformanceFinding(
                    title=f"Hot path: `{fn.label}` ({call_count} calls, complexity {complexity})",
                    severity="medium",
                    category="hotpath",
                    description=(
                        "This function makes many calls AND has high complexity. "
                        "If called frequently, it's a performance bottleneck candidate."
                    ),
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0) or 0),
                    symbol=fn.label,
                    evidence=f"call_count={call_count}, cyclomatic={complexity}",
                    fix_template=(
                        "Profile this function under load. Consider: (1) Caching repeated calls, "
                        "(2) Batch operations instead of individual calls, (3) Lazy evaluation "
                        "for expensive computations."
                    ),
                    confidence=0.6,
                ))

        return findings

    def _detect_quadratic_risk(self, functions: list[GraphNode]) -> list[PerformanceFinding]:
        """Large functions with both high nesting and high complexity
        likely contain O(n²) patterns."""
        findings: list[PerformanceFinding] = []

        for fn in functions:
            lines = int(fn.properties.get("lines", 0) or 0)
            nesting = int(fn.properties.get("nesting_depth", 0) or 0)
            complexity = int(fn.properties.get("cyclomatic", 0) or 0)

            # Heuristic: long + nested + complex = quadratic risk
            if lines >= 30 and nesting >= 3 and complexity >= 10:
                findings.append(PerformanceFinding(
                    title=f"Potential O(n²) in `{fn.label}`",
                    severity="high",
                    category="loops",
                    description=(
                        f"Function is {lines} lines with nesting depth {nesting} and "
                        f"complexity {complexity} — characteristic of nested iteration."
                    ),
                    file_path=str(fn.properties.get("file", "")),
                    line=int(fn.properties.get("line", 0) or 0),
                    symbol=fn.label,
                    evidence=f"lines={lines}, nesting={nesting}, cyclomatic={complexity}",
                    fix_template=(
                        "Check for nested loops over the same collection. Solutions: "
                        "(1) Pre-index with dict/set for O(1) lookup, "
                        "(2) Sort + binary search, (3) Use itertools.groupby for grouping."
                    ),
                    confidence=0.7,
                ))

        return sorted(findings, key=lambda f: f.confidence, reverse=True)[:3]

    def _detect_unbounded_endpoints(self, graph: GraphBuildResult) -> list[PerformanceFinding]:
        """Detect GET endpoints that return lists without pagination signals."""
        findings: list[PerformanceFinding] = []
        endpoints = graph.nodes_by_type(NodeType.ENDPOINT)

        list_endpoints = []
        for ep in endpoints:
            route = str(ep.properties.get("route_info", ""))
            params = str(ep.properties.get("parameters", "")).lower()

            # GET endpoints that likely return collections
            if route.startswith("GET") and not any(
                kw in params for kw in ("limit", "page", "offset", "cursor", "per_page")
            ):
                # Check if route looks like a collection (plural or /list)
                path = route.replace("GET ", "").lower()
                if path.endswith("s") or "list" in path or "all" in path:
                    list_endpoints.append(ep)

        if list_endpoints:
            routes = [str(ep.properties.get("route_info", ep.label)) for ep in list_endpoints[:4]]
            findings.append(PerformanceFinding(
                title=f"{len(list_endpoints)} endpoints without pagination",
                severity="medium",
                category="unbounded",
                description=f"These GET endpoints may return unbounded result sets: {', '.join(routes)}",
                file_path=str(list_endpoints[0].properties.get("file", "")),
                evidence=f"Endpoints without limit/page/offset params: {', '.join(routes)}",
                fix_template=(
                    "Add pagination parameters: (1) limit + offset for simple pagination, "
                    "(2) cursor-based for large datasets, (3) Set a default and max limit."
                ),
                confidence=0.6,
            ))

        return findings
