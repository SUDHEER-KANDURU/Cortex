"""Root-Cause Analysis — error/stacktrace → graph context → diagnosis.

Given a stacktrace, error message, or exception:
1. Parse file/symbol references
2. Match them to graph nodes
3. Find callers/callees/dependencies
4. Find relevant insights/issues
5. Build evidence context for synthesis

Always distinguishes:
  USER-PROVIDED RUNTIME EVIDENCE (from the stacktrace)
  from
  CORTEX STATIC EVIDENCE (from the knowledge graph)

Does NOT claim the exact runtime root cause unless evidence supports it.
"""

from __future__ import annotations

import re
from collections import defaultdict

import structlog

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.insights.domain.entities import InsightsReport
from cortex.reasoning.domain.entities import RootCauseAnalysis, RootCauseEvidence

logger = structlog.get_logger()


class RootCauseAnalyzer:
    """Performs root-cause analysis by combining stacktrace parsing with graph intelligence.

    Pure computation — no IO, no NIM. Pass in the error + graph data,
    get back a structured analysis with evidence.
    """

    def analyze(
        self,
        error_input: str,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        insights_report: InsightsReport | None = None,
    ) -> RootCauseAnalysis:
        """Analyze an error/stacktrace against the knowledge graph.

        Returns structured evidence — synthesis/explanation is left to NIM
        at the presentation layer.
        """
        result = RootCauseAnalysis(error_input=error_input)

        # Step 1: Parse symbols from the error
        result.parsed_symbols = self._parse_symbols(error_input)

        if not result.parsed_symbols:
            result.likely_cause = "Could not extract symbols from the error input."
            result.suggested_investigation = [
                "Try pasting a full stacktrace with file paths and line numbers.",
                "Or paste a specific error message with class/function names.",
            ]
            return result

        # Step 2: Match symbols to graph nodes
        node_map = {n.id: n for n in nodes}
        edges_from: dict[str, list[GraphEdge]] = defaultdict(list)
        edges_to: dict[str, list[GraphEdge]] = defaultdict(list)
        for edge in edges:
            edges_from[edge.source_id].append(edge)
            edges_to[edge.target_id].append(edge)

        matched_nodes = self._match_symbols_to_graph(result.parsed_symbols, nodes)
        result.matched_nodes = [
            {
                "id": n.id,
                "label": n.label,
                "type": n.node_type.value,
                "file": str(n.properties.get("file", "")),
                "complexity": n.properties.get("cyclomatic", 0),
                "lines": n.properties.get("lines", 0),
            }
            for n in matched_nodes
        ]

        if not matched_nodes:
            result.likely_cause = (
                f"Symbols [{', '.join(result.parsed_symbols[:5])}] were not found in the "
                f"knowledge graph. They may be from external libraries or dynamically generated."
            )
            result.suggested_investigation = [
                "Check if the symbols belong to third-party dependencies.",
                "Verify the file paths in the stacktrace match the analyzed repository.",
            ]
            return result

        # Step 3: Find callers and callees
        matched_ids = {n.id for n in matched_nodes}

        for edge in edges:
            if edge.target_id in matched_ids and edge.relationship == RelationshipType.CALLS:
                caller = node_map.get(edge.source_id)
                if caller:
                    result.callers.append({
                        "id": caller.id,
                        "label": caller.label,
                        "type": caller.node_type.value,
                        "file": str(caller.properties.get("file", "")),
                        "relationship": "CALLS",
                    })

            if edge.source_id in matched_ids and edge.relationship == RelationshipType.CALLS:
                callee = node_map.get(edge.target_id)
                if callee:
                    result.callees.append({
                        "id": callee.id,
                        "label": callee.label,
                        "type": callee.node_type.value,
                        "file": str(callee.properties.get("file", "")),
                        "relationship": "CALLS",
                    })

        # Step 4: Find related insights/issues
        if insights_report:
            for issue in insights_report.issues:
                # Check if the issue affects any of the matched symbols or files
                matched_files = {
                    str(n.properties.get("file", "")) for n in matched_nodes if n.properties.get("file")
                }
                matched_labels = {n.label.lower() for n in matched_nodes}

                if (
                    issue.file_path in matched_files
                    or issue.affected_symbol.lower() in matched_labels
                ):
                    result.related_issues.append({
                        "title": issue.title,
                        "severity": issue.severity.value,
                        "category": issue.category.value,
                        "file": issue.file_path,
                        "symbol": issue.affected_symbol,
                        "description": issue.description,
                        "recommendation": issue.recommendation,
                    })

        # Step 5: Build evidence
        self._build_evidence(result, matched_nodes, edges_from, edges_to, node_map)

        # Step 6: Build the affected path
        result.affected_path = self._build_affected_path(matched_nodes, edges, node_map)

        # Step 7: Generate investigation suggestions
        result.suggested_investigation = self._generate_suggestions(result)

        # Step 8: Build evidence context for NIM synthesis
        result.evidence_context = self._format_evidence_context(result)

        return result

    def _parse_symbols(self, text: str) -> list[str]:
        """Parse file paths, class names, and function names from error text.

        Supports:
        - Python tracebacks: File "path", line N, in function
        - Java stacktraces: at package.Class.method(File.java:N)
        - JavaScript/TS: at Function (file:line:col)
        - Generic: CamelCase class names, error messages with qualified names
        """
        symbols: list[str] = []

        # Python traceback
        py_pattern = re.compile(r'File "([^"]+)", line \d+, in (\w+)')
        for match in py_pattern.finditer(text):
            file_path = match.group(1)
            fn_name = match.group(2)
            if fn_name not in ("<module>", "<lambda>"):
                symbols.append(fn_name)
            # Extract module name from file path
            filename = file_path.split("/")[-1].split("\\")[-1]
            if filename.endswith(".py"):
                symbols.append(filename[:-3])
            symbols.append(file_path)

        # Java/Kotlin stacktrace
        java_pattern = re.compile(r'at\s+([\w.]+)\.(\w+)\(([^)]+)\)')
        for match in java_pattern.finditer(text):
            qualified = match.group(1)
            method = match.group(2)
            class_name = qualified.split(".")[-1]
            symbols.extend([class_name, method])

        # JavaScript/TS
        js_pattern = re.compile(r'at\s+(\w+)\s+\(([^)]+)\)')
        for match in js_pattern.finditer(text):
            fn_name = match.group(1)
            if fn_name not in ("Object", "Module", "Array", "Promise", "new"):
                symbols.append(fn_name)

        # Generic: extract CamelCase names and qualified identifiers
        camel_pattern = re.compile(r'\b([A-Z][a-zA-Z0-9]{2,})\b')
        for match in camel_pattern.finditer(text):
            name = match.group(1)
            if name not in ("Error", "Exception", "TypeError", "ValueError", "None", "True", "False"):
                symbols.append(name)

        # Extract dotted identifiers (e.g., "cortex.pipeline.orchestrator")
        dot_pattern = re.compile(r'\b([\w]+(?:\.[\w]+){2,})\b')
        for match in dot_pattern.finditer(text):
            parts = match.group(1).split(".")
            symbols.extend(parts[-2:])  # Take last 2 parts

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for s in symbols:
            s_lower = s.lower()
            if s_lower not in seen and len(s) >= 2:
                seen.add(s_lower)
                unique.append(s)

        return unique[:15]

    def _match_symbols_to_graph(
        self, symbols: list[str], nodes: list[GraphNode]
    ) -> list[GraphNode]:
        """Find graph nodes matching the parsed symbols."""
        matched: list[GraphNode] = []
        matched_ids: set[str] = set()

        for node in nodes:
            if node.id in matched_ids:
                continue

            label_lower = node.label.lower()
            file_path = str(node.properties.get("file", "")).lower()
            qualified = str(node.properties.get("qualified_name", "")).lower()

            for symbol in symbols:
                symbol_lower = symbol.lower()
                if (
                    symbol_lower == label_lower
                    or symbol_lower in label_lower
                    or symbol_lower in file_path
                    or symbol_lower in qualified
                ):
                    matched.append(node)
                    matched_ids.add(node.id)
                    break

        # Prioritize: functions/methods > classes > files > modules
        type_priority = {
            NodeType.FUNCTION: 0, NodeType.METHOD: 0,
            NodeType.CLASS: 1, NodeType.INTERFACE: 1,
            NodeType.FILE: 2, NodeType.MODULE: 3,
        }
        matched.sort(key=lambda n: type_priority.get(n.node_type, 5))

        return matched[:20]

    def _build_evidence(
        self,
        result: RootCauseAnalysis,
        matched_nodes: list[GraphNode],
        edges_from: dict[str, list[GraphEdge]],
        edges_to: dict[str, list[GraphEdge]],
        node_map: dict[str, GraphNode],
    ) -> None:
        """Build structured evidence from matched nodes and their context."""
        for node in matched_nodes[:5]:
            # High complexity is a risk factor
            cc = int(node.properties.get("cyclomatic", 0) or 0)
            if cc > 10:
                result.static_evidence.append(RootCauseEvidence(
                    source="graph",
                    description=f"`{node.label}` has high cyclomatic complexity ({cc}) — more paths means more potential failure modes.",
                    symbol=node.label,
                    file_path=str(node.properties.get("file", "")),
                    confidence=0.7,
                ))

            # Many dependencies is a risk factor
            dep_count = len([
                e for e in edges_from.get(node.id, [])
                if e.relationship in (RelationshipType.CALLS, RelationshipType.IMPORTS)
            ])
            if dep_count > 5:
                result.static_evidence.append(RootCauseEvidence(
                    source="graph",
                    description=f"`{node.label}` depends on {dep_count} other components — any of them could be the failure source.",
                    symbol=node.label,
                    file_path=str(node.properties.get("file", "")),
                    confidence=0.5,
                ))

            # Many callers means high impact
            caller_count = len([
                e for e in edges_to.get(node.id, [])
                if e.relationship == RelationshipType.CALLS
            ])
            if caller_count > 3:
                result.static_evidence.append(RootCauseEvidence(
                    source="graph",
                    description=f"`{node.label}` is called by {caller_count} other functions — a failure here impacts many callers.",
                    symbol=node.label,
                    file_path=str(node.properties.get("file", "")),
                    confidence=0.6,
                ))

        # Add evidence from related issues
        for issue in result.related_issues[:3]:
            result.static_evidence.append(RootCauseEvidence(
                source="insight",
                description=f"Known issue: {issue['title']} — {issue['description']}",
                symbol=issue.get("symbol", ""),
                file_path=issue.get("file", ""),
                confidence=0.8,
            ))

    def _build_affected_path(
        self,
        matched_nodes: list[GraphNode],
        edges: list[GraphEdge],
        node_map: dict[str, GraphNode],
    ) -> list[str]:
        """Build the execution path through matched nodes."""
        if not matched_nodes:
            return []

        # Try to order nodes by call relationship
        matched_ids = {n.id for n in matched_nodes}
        call_order: list[str] = []
        visited: set[str] = set()

        # Start from nodes that have no incoming CALLS from other matched nodes
        has_incoming: set[str] = set()
        for edge in edges:
            if (
                edge.relationship == RelationshipType.CALLS
                and edge.source_id in matched_ids
                and edge.target_id in matched_ids
            ):
                has_incoming.add(edge.target_id)

        roots = [n for n in matched_nodes if n.id not in has_incoming]
        if not roots:
            roots = matched_nodes[:1]

        # Simple traversal
        queue = [r.id for r in roots]
        while queue and len(call_order) < 10:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            node = node_map.get(node_id)
            if node:
                file_path = str(node.properties.get("file", ""))
                call_order.append(
                    f"{node.label} ({node.node_type.value})"
                    + (f" in {file_path}" if file_path else "")
                )

        return call_order

    def _generate_suggestions(self, result: RootCauseAnalysis) -> list[str]:
        """Generate actionable investigation suggestions."""
        suggestions: list[str] = []

        if result.matched_nodes:
            # Suggest investigating the most complex matched node
            complex_nodes = sorted(
                result.matched_nodes,
                key=lambda n: int(n.get("complexity", 0) or 0),
                reverse=True,
            )
            if complex_nodes and int(complex_nodes[0].get("complexity", 0) or 0) > 5:
                top = complex_nodes[0]
                suggestions.append(
                    f"Investigate `{top['label']}` — it has complexity {top['complexity']} "
                    f"and is likely where the logic error occurs."
                )

        if result.callers:
            suggestions.append(
                f"Check callers: {', '.join(c['label'] for c in result.callers[:3])} "
                f"— the error may originate from how they invoke the failing code."
            )

        if result.callees:
            suggestions.append(
                f"Check dependencies: {', '.join(c['label'] for c in result.callees[:3])} "
                f"— the failure may propagate from a downstream call."
            )

        if result.related_issues:
            suggestions.append(
                f"Related known issue: \"{result.related_issues[0]['title']}\" — "
                f"this pre-existing problem may be contributing to the failure."
            )

        if not suggestions:
            suggestions.append("Add more context (full stacktrace, error message) for better analysis.")

        return suggestions

    def _format_evidence_context(self, result: RootCauseAnalysis) -> str:
        """Format the evidence into a context string suitable for NIM synthesis."""
        lines: list[str] = []

        lines.append("## Root-Cause Analysis Evidence\n")

        if result.matched_nodes:
            lines.append("### Matched Code Elements")
            for node in result.matched_nodes[:8]:
                detail = f"- `{node['label']}` ({node['type']})"
                if node.get("file"):
                    detail += f" in `{node['file']}`"
                if node.get("complexity") and int(node["complexity"]) > 0:
                    detail += f" [complexity: {node['complexity']}]"
                lines.append(detail)
            lines.append("")

        if result.callers:
            lines.append("### Callers (who invokes the failing code)")
            for c in result.callers[:5]:
                lines.append(f"- `{c['label']}` ({c['type']}) in `{c.get('file', '?')}`")
            lines.append("")

        if result.callees:
            lines.append("### Dependencies (what the failing code calls)")
            for c in result.callees[:5]:
                lines.append(f"- `{c['label']}` ({c['type']}) in `{c.get('file', '?')}`")
            lines.append("")

        if result.static_evidence:
            lines.append("### Static Evidence")
            for ev in result.static_evidence[:5]:
                lines.append(f"- [{ev.source}] {ev.description}")
            lines.append("")

        if result.related_issues:
            lines.append("### Related Known Issues")
            for issue in result.related_issues[:3]:
                lines.append(f"- **{issue['title']}** ({issue['severity']}): {issue['description']}")
            lines.append("")

        return "\n".join(lines)
