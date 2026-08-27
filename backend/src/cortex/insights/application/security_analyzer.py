"""Security Analyzer — Cortex's deterministic security detection.

Detects security issues from AST/graph data WITHOUT calling any AI.
This is Cortex's own security intelligence layer.

Detections:
  - Hardcoded secrets (API keys, passwords, tokens in source)
  - SQL injection patterns (string concatenation in queries)
  - Unsafe deserialization (pickle, eval, exec)
  - Hardcoded credentials in config
  - Missing input validation on endpoints
  - Exposed debug/admin endpoints

Each finding includes: evidence (file, line, symbol), severity,
and a fix_template (actionable recommendation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from cortex.graph.domain.entities import GraphNode, NodeType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


@dataclass
class SecurityFinding:
    """A single security issue with evidence and fix."""
    title: str
    severity: str  # critical, high, medium, low
    category: str  # secrets, injection, unsafe_api, auth, exposure
    description: str
    file_path: str = ""
    line: int = 0
    symbol: str = ""
    evidence: str = ""
    fix_template: str = ""
    confidence: float = 0.9


class SecurityAnalyzer:
    """Deterministic security analysis from graph node properties.

    Uses the enriched graph properties (decorators, parameters, file paths,
    function names) to detect security anti-patterns without reading raw
    source code. This means detections are based on structural patterns,
    not string scanning of file contents.
    """

    # Patterns that suggest hardcoded secrets in symbol names/properties
    _SECRET_PATTERNS = re.compile(
        r'(api_key|api_secret|secret_key|password|passwd|token|auth_token'
        r'|private_key|access_key|secret|credential)',
        re.IGNORECASE,
    )

    # Patterns in function names suggesting unsafe operations
    _UNSAFE_FUNCTION_PATTERNS = {
        "eval": ("Unsafe eval() usage", "critical", "Avoid eval(). Use ast.literal_eval() for safe parsing or a dedicated parser."),
        "exec": ("Unsafe exec() usage", "critical", "Avoid exec(). Refactor to use function dispatch or strategy pattern."),
        "pickle": ("Unsafe pickle deserialization", "high", "Use JSON or msgpack instead. Pickle can execute arbitrary code on load."),
        "loads": ("Potential unsafe deserialization", "medium", "Ensure input is validated before deserialization. Prefer JSON for untrusted data."),
        "system": ("OS command execution", "high", "Use subprocess with shell=False and explicit argument lists."),
        "popen": ("OS command execution via popen", "high", "Use subprocess.run() with explicit args instead of popen."),
    }

    # Endpoint patterns that shouldn't be public
    _DANGEROUS_ROUTES = re.compile(
        r'(debug|admin|internal|secret|backdoor|test_only|dev_only)',
        re.IGNORECASE,
    )

    def analyze(self, graph: GraphBuildResult) -> list[SecurityFinding]:
        """Run all security detections on the graph."""
        findings: list[SecurityFinding] = []

        functions = [n for n in graph.nodes if n.node_type in (
            NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT
        )]
        endpoints = graph.nodes_by_type(NodeType.ENDPOINT)
        files = graph.nodes_by_type(NodeType.FILE)

        # Detection 1: Hardcoded secrets in symbol names
        findings.extend(self._detect_hardcoded_secrets(functions, files))

        # Detection 2: Unsafe function usage
        findings.extend(self._detect_unsafe_functions(functions))

        # Detection 3: Exposed debug/admin endpoints
        findings.extend(self._detect_dangerous_endpoints(endpoints))

        # Detection 4: Endpoints without auth
        findings.extend(self._detect_unprotected_endpoints(endpoints))

        # Detection 5: SQL injection potential (functions with 'query' + high complexity)
        findings.extend(self._detect_sql_injection_risk(functions))

        return findings

    def _detect_hardcoded_secrets(
        self, functions: list[GraphNode], files: list[GraphNode]
    ) -> list[SecurityFinding]:
        """Detect parameters or symbols that suggest hardcoded secrets."""
        findings: list[SecurityFinding] = []

        for fn in functions:
            params = str(fn.properties.get("parameters", ""))
            # Check if default values contain secret-like names
            if self._SECRET_PATTERNS.search(fn.label):
                # Function named like a secret handler — lower concern
                continue

            # Check parameters for secret-like defaults
            if self._SECRET_PATTERNS.search(params):
                file_path = str(fn.properties.get("file", ""))
                # Skip test files
                if "test" in file_path.lower():
                    continue
                findings.append(SecurityFinding(
                    title=f"Potential hardcoded secret in `{fn.label}`",
                    severity="medium",
                    category="secrets",
                    description=f"Parameter names suggest secret handling: {params}",
                    file_path=file_path,
                    line=int(fn.properties.get("line", 0) or 0),
                    symbol=fn.label,
                    evidence=f"Parameters: {params}",
                    fix_template="Move secrets to environment variables. Use pydantic-settings or python-dotenv for configuration.",
                    confidence=0.6,
                ))

        # Check for config files with secret-like names
        for f in files:
            path = str(f.properties.get("path", f.label)).lower()
            if any(kw in path for kw in (".env", "secret", "credential", "key")):
                if not path.endswith((".env.example", ".env.template", ".env.sample")):
                    findings.append(SecurityFinding(
                        title=f"Secret file detected: `{f.label}`",
                        severity="high",
                        category="secrets",
                        description="File likely contains secrets. Ensure it's in .gitignore.",
                        file_path=path,
                        symbol=f.label,
                        fix_template="Add to .gitignore. Use environment variables or a secrets manager instead of files.",
                        confidence=0.8,
                    ))

        return findings[:5]

    def _detect_unsafe_functions(self, functions: list[GraphNode]) -> list[SecurityFinding]:
        """Detect calls to dangerous functions."""
        findings: list[SecurityFinding] = []

        for fn in functions:
            calls = str(fn.properties.get("calls", "")).lower()
            fn_name = fn.label.lower()

            for pattern, (title, severity, fix) in self._UNSAFE_FUNCTION_PATTERNS.items():
                if pattern in calls or pattern in fn_name:
                    file_path = str(fn.properties.get("file", ""))
                    if "test" in file_path.lower():
                        continue
                    findings.append(SecurityFinding(
                        title=f"{title} in `{fn.label}`",
                        severity=severity,
                        category="unsafe_api",
                        description=f"Function uses or is named after an unsafe pattern: {pattern}",
                        file_path=file_path,
                        line=int(fn.properties.get("line", 0) or 0),
                        symbol=fn.label,
                        evidence=f"Calls: {calls}" if calls else f"Function name: {fn.label}",
                        fix_template=fix,
                        confidence=0.7,
                    ))
                    break

        return findings[:5]

    def _detect_dangerous_endpoints(self, endpoints: list[GraphNode]) -> list[SecurityFinding]:
        """Detect debug/admin endpoints that shouldn't be publicly accessible."""
        findings: list[SecurityFinding] = []

        for ep in endpoints:
            route = str(ep.properties.get("route_info", ""))
            if self._DANGEROUS_ROUTES.search(route):
                decorators = str(ep.properties.get("decorators", "")).lower()
                has_auth = any(kw in decorators for kw in ("auth", "permission", "admin", "internal"))

                if not has_auth:
                    findings.append(SecurityFinding(
                        title=f"Exposed sensitive endpoint: `{route}`",
                        severity="high",
                        category="exposure",
                        description="This endpoint appears to be debug/admin and lacks authentication.",
                        file_path=str(ep.properties.get("file", "")),
                        line=int(ep.properties.get("line", 0) or 0),
                        symbol=ep.label,
                        evidence=f"Route: {route}, Decorators: {decorators}",
                        fix_template="Add authentication decorator or move to an internal-only router with IP restrictions.",
                        confidence=0.8,
                    ))

        return findings[:3]

    def _detect_unprotected_endpoints(self, endpoints: list[GraphNode]) -> list[SecurityFinding]:
        """Detect mutation endpoints without any auth decorator."""
        findings: list[SecurityFinding] = []
        mutation_methods = ("POST", "PUT", "PATCH", "DELETE")

        unprotected_mutations = []
        for ep in endpoints:
            route = str(ep.properties.get("route_info", ""))
            if any(route.startswith(m) for m in mutation_methods):
                decorators = str(ep.properties.get("decorators", "")).lower()
                if not any(kw in decorators for kw in ("auth", "login", "permission", "token", "depends", "jwt")):
                    unprotected_mutations.append(ep)

        if len(unprotected_mutations) >= 2:
            routes = [str(ep.properties.get("route_info", ep.label)) for ep in unprotected_mutations[:4]]
            findings.append(SecurityFinding(
                title=f"{len(unprotected_mutations)} mutation endpoints without detected auth",
                severity="medium",
                category="auth",
                description=f"Endpoints: {', '.join(routes)}",
                file_path=str(unprotected_mutations[0].properties.get("file", "")),
                evidence=f"Routes without auth decorators: {', '.join(routes)}",
                fix_template="Add authentication middleware/decorator to mutation endpoints. Use Depends() in FastAPI or @login_required in Django.",
                confidence=0.7,
            ))

        return findings

    def _detect_sql_injection_risk(self, functions: list[GraphNode]) -> list[SecurityFinding]:
        """Detect functions that might be vulnerable to SQL injection.

        Heuristic: functions with 'query' or 'sql' in name + high complexity
        + string parameters suggest dynamic query construction.
        """
        findings: list[SecurityFinding] = []

        for fn in functions:
            name_lower = fn.label.lower()
            if any(kw in name_lower for kw in ("query", "sql", "execute", "raw_sql")):
                params = str(fn.properties.get("parameters", ""))
                complexity = int(fn.properties.get("cyclomatic", 0) or 0)
                # High complexity + query function + string params = risk
                if complexity >= 5 or "str" in params or "query" in params:
                    file_path = str(fn.properties.get("file", ""))
                    if "test" in file_path.lower():
                        continue
                    findings.append(SecurityFinding(
                        title=f"Potential SQL injection risk in `{fn.label}`",
                        severity="high",
                        category="injection",
                        description="Function constructs queries with dynamic parameters.",
                        file_path=file_path,
                        line=int(fn.properties.get("line", 0) or 0),
                        symbol=fn.label,
                        evidence=f"Parameters: {params}, Complexity: {complexity}",
                        fix_template="Use parameterized queries (?, :param) instead of string formatting. Never concatenate user input into SQL.",
                        confidence=0.5,
                    ))

        return findings[:3]
