"""API Features Generator — evidence-backed API surface analysis.

This is NOT a list of function names from router files. It produces:
  - Detected HTTP endpoints with method, path, and handler
  - Call chain tracing (endpoint → service → repository)
  - Request/response model detection from parameters and return types
  - API quality assessment (documentation, naming consistency, auth detection)
  - Architectural concerns (duplicate routes, high-complexity handlers)

Every endpoint is traced through the graph to show the FULL request flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


@dataclass
class EndpointAnalysis:
    """Analysis of a single API endpoint with evidence."""
    route_info: str  # e.g. "GET /api/v1/users"
    method: str = ""  # GET, POST, PUT, DELETE, etc.
    path: str = ""
    handler_name: str = ""
    handler_file: str = ""
    handler_line: int = 0
    # Parameters and types
    parameters: list[str] = field(default_factory=list)
    return_type: str = ""
    # Call chain (handler → service → repo → ...)
    call_chain: list[str] = field(default_factory=list)
    # Qualities
    has_docstring: bool = False
    is_async: bool = False
    complexity: int = 1
    # Detected patterns
    has_auth_decorator: bool = False
    has_validation: bool = False


@dataclass
class APIAnalysisResult:
    """Full API surface analysis for a repository."""
    repo_name: str
    total_endpoints: int = 0
    # Grouped by HTTP method
    get_count: int = 0
    post_count: int = 0
    put_count: int = 0
    patch_count: int = 0
    delete_count: int = 0
    other_count: int = 0
    # Endpoints organized by file/router
    endpoints_by_file: dict[str, list[EndpointAnalysis]] = field(default_factory=dict)
    # Quality metrics
    documented_ratio: float = 0.0
    avg_complexity: float = 0.0
    async_ratio: float = 0.0
    auth_ratio: float = 0.0
    # Issues detected
    issues: list[str] = field(default_factory=list)


class APIFeaturesGenerator:
    """Generates evidence-backed API surface analysis from the knowledge graph.

    Uses ENDPOINT nodes (detected from route decorators) and CALLS edges
    to trace the full request flow from HTTP handler through services.
    """

    def generate(self, graph: GraphBuildResult, repo_name: str) -> str:
        """Generate full API features analysis as Markdown."""
        result = self.analyze(graph, repo_name)
        return self._render_markdown(result)

    def analyze(self, graph: GraphBuildResult, repo_name: str) -> APIAnalysisResult:
        """Perform full API surface analysis."""
        result = APIAnalysisResult(repo_name=repo_name)

        endpoints = graph.nodes_by_type(NodeType.ENDPOINT)
        if not endpoints:
            # Fallback: look for functions with route_info in properties
            endpoints = [
                n for n in graph.nodes
                if n.node_type in (NodeType.FUNCTION, NodeType.METHOD)
                and n.properties.get("is_endpoint")
            ]

        result.total_endpoints = len(endpoints)
        if not endpoints:
            return result

        # Build CALLS edge index for chain tracing
        calls_from: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.relationship == RelationshipType.CALLS:
                calls_from[edge.source_id].append(edge.target_id)

        # Analyze each endpoint
        all_analyses: list[EndpointAnalysis] = []
        for ep_node in endpoints:
            analysis = self._analyze_endpoint(ep_node, calls_from, graph)
            all_analyses.append(analysis)

            # Group by file
            file_key = analysis.handler_file or "unknown"
            result.endpoints_by_file.setdefault(file_key, []).append(analysis)

        # Count by method
        for ep in all_analyses:
            method = ep.method.upper()
            if method == "GET":
                result.get_count += 1
            elif method == "POST":
                result.post_count += 1
            elif method == "PUT":
                result.put_count += 1
            elif method == "PATCH":
                result.patch_count += 1
            elif method == "DELETE":
                result.delete_count += 1
            else:
                result.other_count += 1

        # Quality metrics
        if all_analyses:
            result.documented_ratio = round(
                sum(1 for ep in all_analyses if ep.has_docstring) / len(all_analyses), 2
            )
            result.avg_complexity = round(
                sum(ep.complexity for ep in all_analyses) / len(all_analyses), 1
            )
            result.async_ratio = round(
                sum(1 for ep in all_analyses if ep.is_async) / len(all_analyses), 2
            )
            result.auth_ratio = round(
                sum(1 for ep in all_analyses if ep.has_auth_decorator) / len(all_analyses), 2
            )

        # Detect issues
        result.issues = self._detect_issues(all_analyses)

        return result

    def _analyze_endpoint(
        self,
        ep_node: GraphNode,
        calls_from: dict[str, list[str]],
        graph: GraphBuildResult,
    ) -> EndpointAnalysis:
        """Analyze a single endpoint node."""
        route_info = str(ep_node.properties.get("route_info", "") or "")

        # Parse method and path from route_info (e.g. "GET /api/v1/users")
        method = ""
        path = ""
        if route_info and " " in route_info:
            parts = route_info.split(" ", 1)
            method = parts[0]
            path = parts[1]
        elif route_info:
            path = route_info

        analysis = EndpointAnalysis(
            route_info=route_info or ep_node.label,
            method=method,
            path=path,
            handler_name=ep_node.properties.get("qualified_name", ep_node.label) or ep_node.label,
            handler_file=str(ep_node.properties.get("file", "") or ""),
            handler_line=int(ep_node.properties.get("line", 0) or 0),
            parameters=self._parse_params(ep_node),
            return_type=str(ep_node.properties.get("return_type", "") or ""),
            has_docstring=bool(ep_node.properties.get("has_docstring")),
            is_async=bool(ep_node.properties.get("is_async")),
            complexity=int(ep_node.properties.get("cyclomatic", 1) or 1),
        )

        # Detect auth/validation from decorators
        decorators = str(ep_node.properties.get("decorators", "") or "").lower()
        analysis.has_auth_decorator = any(
            kw in decorators
            for kw in ("auth", "login_required", "permission", "jwt", "token", "depends")
        )
        analysis.has_validation = any(
            kw in decorators
            for kw in ("validate", "schema", "body", "query")
        )

        # Trace call chain (up to 3 hops)
        analysis.call_chain = self._trace_call_chain(ep_node.id, calls_from, graph, max_depth=3)

        return analysis

    def _parse_params(self, node: GraphNode) -> list[str]:
        """Extract parameters from node properties."""
        params_str = str(node.properties.get("parameters", "") or "")
        if not params_str:
            return []
        return [p.strip() for p in params_str.split(",") if p.strip()]

    def _trace_call_chain(
        self,
        start_id: str,
        calls_from: dict[str, list[str]],
        graph: GraphBuildResult,
        max_depth: int = 3,
    ) -> list[str]:
        """Trace the call chain from an endpoint handler through services."""
        chain: list[str] = []
        visited: set[str] = {start_id}
        current_level = [start_id]

        for _ in range(max_depth):
            next_level: list[str] = []
            for node_id in current_level:
                for target_id in calls_from.get(node_id, []):
                    if target_id not in visited:
                        visited.add(target_id)
                        target_node = graph.node_by_id.get(target_id)
                        if target_node:
                            label = target_node.properties.get("qualified_name", target_node.label) or target_node.label
                            chain.append(str(label))
                            next_level.append(target_id)
            current_level = next_level
            if not current_level:
                break

        return chain[:8]  # Cap chain length

    def _detect_issues(self, endpoints: list[EndpointAnalysis]) -> list[str]:
        """Detect API quality issues from endpoint analysis."""
        issues: list[str] = []

        # Duplicate paths
        paths_seen: dict[str, list[str]] = defaultdict(list)
        for ep in endpoints:
            if ep.path:
                key = f"{ep.method} {ep.path}"
                paths_seen[key].append(ep.handler_name)
        for path_key, handlers in paths_seen.items():
            if len(handlers) > 1:
                issues.append(
                    f"Duplicate route `{path_key}` handled by: "
                    f"{', '.join(f'`{h}`' for h in handlers)}"
                )

        # Undocumented endpoints
        undocumented = [ep for ep in endpoints if not ep.has_docstring]
        if undocumented and len(undocumented) > len(endpoints) * 0.5:
            issues.append(
                f"{len(undocumented)}/{len(endpoints)} endpoints lack documentation"
            )

        # High complexity handlers
        complex_handlers = [ep for ep in endpoints if ep.complexity >= 10]
        for ep in complex_handlers[:3]:
            issues.append(
                f"Complex handler: `{ep.handler_name}` has cyclomatic complexity "
                f"{ep.complexity} — consider extracting logic to a service"
            )

        # No auth on mutation endpoints
        unprotected_mutations = [
            ep for ep in endpoints
            if ep.method in ("POST", "PUT", "PATCH", "DELETE")
            and not ep.has_auth_decorator
        ]
        if unprotected_mutations:
            names = [ep.route_info for ep in unprotected_mutations[:3]]
            issues.append(
                f"{len(unprotected_mutations)} mutation endpoint(s) without detected auth: "
                f"{', '.join(f'`{n}`' for n in names)}"
            )

        # Inconsistent naming (mixed snake_case and camelCase in paths)
        snake_paths = sum(1 for ep in endpoints if "_" in ep.path)
        camel_paths = sum(
            1 for ep in endpoints
            if any(c.isupper() for c in ep.path) and "_" not in ep.path
        )
        if snake_paths > 0 and camel_paths > 0:
            issues.append(
                f"Inconsistent path naming: {snake_paths} snake_case, "
                f"{camel_paths} camelCase paths detected"
            )

        return issues

    def _render_markdown(self, result: APIAnalysisResult) -> str:
        """Render API analysis as structured Markdown."""
        lines: list[str] = []

        lines.append(f"# API Features — {result.repo_name}")
        lines.append("")
        lines.append(
            "> **What is an API?** An API (Application Programming Interface) is how "
            "this software communicates with the outside world. Think of endpoints as "
            "\"doors\" into the application — each one accepts a specific type of request "
            "and returns a specific type of response. Understanding the API tells you "
            "what this system can DO."
        )
        lines.append("")

        if result.total_endpoints == 0:
            lines.append("_No API endpoints detected in this repository._")
            lines.append("")
            lines.append(
                "This may mean the project doesn't expose HTTP endpoints, "
                "or the endpoints use patterns not yet detected by Cortex "
                "(currently supports: FastAPI, Flask, Express, Django, Spring decorators)."
            )
            return "\n".join(lines)

        # ── Summary ──────────────────────────────────────────────────────────
        lines.append("## At a Glance")
        lines.append("")
        lines.append(
            f"This application exposes **{result.total_endpoints} endpoints** — "
            f"that's {result.total_endpoints} different operations the outside world can ask it to perform."
        )
        lines.append("")
        lines.append("| What | Count | Meaning |")
        lines.append("|------|-------|---------|")
        if result.get_count:
            lines.append(f"| GET requests | {result.get_count} | Read/fetch data (like viewing a page) |")
        if result.post_count:
            lines.append(f"| POST requests | {result.post_count} | Create new data (like submitting a form) |")
        if result.put_count:
            lines.append(f"| PUT requests | {result.put_count} | Replace/update existing data |")
        if result.patch_count:
            lines.append(f"| PATCH requests | {result.patch_count} | Partially update existing data |")
        if result.delete_count:
            lines.append(f"| DELETE requests | {result.delete_count} | Remove data |")
        lines.append("")

        # Quality indicators with explanations
        lines.append("### Quality Indicators")
        lines.append("")
        doc_emoji = "✅" if result.documented_ratio >= 0.7 else ("⚠️" if result.documented_ratio >= 0.4 else "❌")
        auth_emoji = "✅" if result.auth_ratio >= 0.7 else ("⚠️" if result.auth_ratio >= 0.3 else "❌")
        lines.append(f"- {doc_emoji} **Documentation:** {result.documented_ratio:.0%} of endpoints have descriptions explaining what they do")
        lines.append(f"- {auth_emoji} **Security:** {result.auth_ratio:.0%} of endpoints require authentication (identity verification)")
        lines.append(f"- **Average Complexity:** {result.avg_complexity} (lower is simpler; above 10 means hard to maintain)")
        if result.async_ratio > 0:
            lines.append(f"- **Async:** {result.async_ratio:.0%} use modern async patterns (better performance under load)")
        lines.append("")

        # ── Issues ───────────────────────────────────────────────────────────
        if result.issues:
            lines.append("## ⚠ Issues Found")
            lines.append("")
            lines.append("These are potential problems Cortex detected in the API design:")
            lines.append("")
            for issue in result.issues:
                lines.append(f"- {issue}")
            lines.append("")

        # ── Endpoints by Router/File ─────────────────────────────────────────
        lines.append("## All Endpoints")
        lines.append("")
        lines.append(
            "> Each row below is one \"door\" into the application. The **Method** tells you "
            "what kind of action it performs. The **Path** is the URL. The **Handler** is "
            "the code function that processes the request."
        )
        lines.append("")

        for file_path, endpoints in sorted(result.endpoints_by_file.items()):
            file_name = file_path.split("/")[-1] if "/" in file_path else file_path
            lines.append(f"### `{file_name}`")
            lines.append("")
            lines.append("| Action | URL Path | Handler Function | Complexity | Protected? |")
            lines.append("|--------|----------|-----------------|-----------|-----------|")

            for ep in sorted(endpoints, key=lambda e: e.path):
                auth_badge = "🔒 Yes" if ep.has_auth_decorator else "🔓 No"
                cc_badge = f"⚠ {ep.complexity}" if ep.complexity >= 10 else str(ep.complexity)
                lines.append(
                    f"| `{ep.method}` | `{ep.path}` | "
                    f"`{ep.handler_name}` | {cc_badge} | {auth_badge} |"
                )

            lines.append("")

            # Show call chains with explanation
            chains_shown = 0
            for ep in endpoints:
                if ep.call_chain and chains_shown < 4:
                    chain_str = " → ".join(f"`{c}`" for c in ep.call_chain[:4])
                    lines.append(
                        f"**Request flow for `{ep.method} {ep.path}`:**"
                    )
                    lines.append(
                        f"When someone calls this endpoint, the request travels through: "
                        f"`{ep.handler_name}` → {chain_str}"
                    )
                    lines.append("")
                    chains_shown += 1

        # ── API Design Assessment ────────────────────────────────────────────
        lines.append("## Overall Assessment")
        lines.append("")
        lines.append(
            "> **What does this mean?** Below is Cortex's assessment of how well "
            "this API is designed. A well-designed API is easier to use, more secure, "
            "and less likely to break when changes are made."
        )
        lines.append("")

        if result.documented_ratio >= 0.8:
            lines.append("✅ **Documentation:** Excellent — most endpoints explain what they do, making it easy for developers to use this API correctly.")
        elif result.documented_ratio >= 0.5:
            lines.append("⚠️ **Documentation:** Partial — some endpoints have descriptions but many don't. New developers may struggle to understand what each endpoint does.")
        else:
            lines.append("❌ **Documentation:** Poor — most endpoints lack any description. This makes the API hard to use without reading the source code.")
        lines.append("")

        if result.async_ratio >= 0.8:
            lines.append("✓ **Async:** Consistently async handlers (good for I/O-bound workloads)")
        elif result.async_ratio > 0 and result.async_ratio < 0.5:
            lines.append("⚠ **Async:** Mixed sync/async handlers — consider standardizing")
        lines.append("")

        if result.auth_ratio >= 0.7:
            lines.append("✓ **Authentication:** Most endpoints are protected")
        elif result.auth_ratio < 0.3 and result.total_endpoints > 3:
            lines.append("⚠ **Authentication:** Few endpoints have auth decorators detected")
        lines.append("")

        return "\n".join(lines)
