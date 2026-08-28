"""Unit tests for the CortexReasoner.

Covers:
  - Structure counting (files, classes, functions, endpoints, tests)
  - Language and framework detection
  - Architecture style detection (layered, hexagonal, modular, etc.)
  - Entry point detection (main functions, HTTP endpoints)
  - Module intelligence (role classification, dependencies, risks)
  - Starting point determination
  - Edge cases (empty graph, single node)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from cortex.graph.domain.entities import GraphEdge, GraphNode, NodeType, RelationshipType
from cortex.reasoning.application.reasoner import CortexReasoner
from cortex.reasoning.domain.entities import ArchitectureStyle

# ── Helpers ───────────────────────────────────────────────────────────────────

_NOW = datetime.now(timezone.utc)
_JOB = "test-reasoner-001"
_REPO = "https://github.com/example/test-repo"


def _node(id: str, label: str, ntype: NodeType, props: dict | None = None) -> GraphNode:
    return GraphNode(
        id=id, label=label, node_type=ntype, job_id=_JOB,
        properties=props or {}, created_at=_NOW,
    )


def _edge(sid: str, tid: str, rel: RelationshipType) -> GraphEdge:
    return GraphEdge(
        id=f"{sid}-{tid}-{rel.value}", source_id=sid, target_id=tid,
        relationship=rel, job_id=_JOB, created_at=_NOW,
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def reasoner() -> CortexReasoner:
    return CortexReasoner()


@pytest.fixture
def layered_architecture_graph() -> tuple[list[GraphNode], list[GraphEdge]]:
    """Build a graph that looks like a layered architecture (domain/application/infrastructure)."""
    nodes = [
        _node("repo", "test-repo", NodeType.REPOSITORY),
        # Modules
        _node("mod-domain", "domain", NodeType.MODULE, {"path": "domain"}),
        _node("mod-application", "application", NodeType.MODULE, {"path": "application"}),
        _node("mod-infrastructure", "infrastructure", NodeType.MODULE, {"path": "infrastructure"}),
        _node("mod-presentation", "presentation", NodeType.MODULE, {"path": "presentation"}),
        # Files
        _node("f1", "entities.py", NodeType.FILE, {
            "path": "domain/entities.py", "language": "python", "lines": 50,
        }),
        _node("f2", "use_cases.py", NodeType.FILE, {
            "path": "application/use_cases.py", "language": "python", "lines": 80,
        }),
        _node("f3", "repository.py", NodeType.FILE, {
            "path": "infrastructure/repository.py", "language": "python", "lines": 60,
        }),
        _node("f4", "router.py", NodeType.FILE, {
            "path": "presentation/router.py", "language": "python", "lines": 40,
        }),
        # Classes
        _node("c1", "User", NodeType.CLASS, {
            "file": "domain/entities.py", "lines": 20, "methods": 3,
        }),
        _node("c2", "CreateUser", NodeType.CLASS, {
            "file": "application/use_cases.py", "lines": 30, "methods": 2,
        }),
        _node("c3", "SQLRepository", NodeType.CLASS, {
            "file": "infrastructure/repository.py", "lines": 40, "methods": 4,
        }),
        # Functions
        _node("fn1", "main", NodeType.FUNCTION, {
            "file": "main.py", "lines": 10, "cyclomatic": 2,
        }),
        _node("fn2", "create_app", NodeType.FUNCTION, {
            "file": "main.py", "lines": 15, "cyclomatic": 3,
        }),
        # Endpoint
        _node("ep1", "create_user_endpoint", NodeType.ENDPOINT, {
            "file": "presentation/router.py", "route_info": "POST /api/users",
            "http_method": "POST", "lines": 12,
        }),
    ]

    edges = [
        # Repo contains modules
        _edge("repo", "mod-domain", RelationshipType.CONTAINS),
        _edge("repo", "mod-application", RelationshipType.CONTAINS),
        _edge("repo", "mod-infrastructure", RelationshipType.CONTAINS),
        _edge("repo", "mod-presentation", RelationshipType.CONTAINS),
        # Modules contain files
        _edge("mod-domain", "f1", RelationshipType.CONTAINS),
        _edge("mod-application", "f2", RelationshipType.CONTAINS),
        _edge("mod-infrastructure", "f3", RelationshipType.CONTAINS),
        _edge("mod-presentation", "f4", RelationshipType.CONTAINS),
        # Files contain classes
        _edge("f1", "c1", RelationshipType.CONTAINS),
        _edge("f2", "c2", RelationshipType.CONTAINS),
        _edge("f3", "c3", RelationshipType.CONTAINS),
        _edge("f4", "ep1", RelationshipType.CONTAINS),
        # Imports
        _edge("f2", "f1", RelationshipType.IMPORTS),  # application imports domain
        _edge("f3", "f1", RelationshipType.IMPORTS),  # infrastructure imports domain
        _edge("f4", "f2", RelationshipType.IMPORTS),  # presentation imports application
    ]

    return nodes, edges


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestReasonerStructure:
    """Tests for structure counting."""

    def test_counts_files(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        assert u.total_files == 4

    def test_counts_classes(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        assert u.total_classes == 3

    def test_counts_functions(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        # 2 top-level functions + the endpoint
        assert u.total_functions >= 2

    def test_counts_modules(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        assert u.total_modules == 4

    def test_counts_endpoints(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        assert u.total_endpoints == 1


class TestReasonerLanguageDetection:
    """Tests for language and framework detection."""

    def test_detects_python(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        assert "python" in u.languages

    def test_detects_multiple_languages(self, reasoner: CortexReasoner):
        nodes = [
            _node("f1", "app.py", NodeType.FILE, {"language": "python", "lines": 100}),
            _node("f2", "app.ts", NodeType.FILE, {"language": "typescript", "lines": 200}),
            _node("f3", "Main.java", NodeType.FILE, {"language": "java", "lines": 150}),
        ]
        u = reasoner.understand(_JOB, _REPO, nodes, [])
        assert len(u.languages) >= 2


class TestReasonerArchitecture:
    """Tests for architecture style detection."""

    def test_detects_layered(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        # With domain/application/infrastructure/presentation, should detect layered or hexagonal
        assert u.architecture_style in (
            ArchitectureStyle.LAYERED,
            ArchitectureStyle.HEXAGONAL,
            ArchitectureStyle.MODULAR,
        )

    def test_monolithic_for_few_modules(self, reasoner: CortexReasoner):
        """A repo with very few modules should be detected as monolithic."""
        nodes = [
            _node("repo", "mono-app", NodeType.REPOSITORY),
            _node("mod1", "src", NodeType.MODULE, {"path": "src"}),
            _node("f1", "app.py", NodeType.FILE, {"language": "python", "lines": 500}),
        ]
        edges = [
            _edge("repo", "mod1", RelationshipType.CONTAINS),
            _edge("mod1", "f1", RelationshipType.CONTAINS),
        ]
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        # With only 1 module, should be monolithic or unknown
        assert u.architecture_style in (
            ArchitectureStyle.MONOLITHIC,
            ArchitectureStyle.UNKNOWN,
        )


class TestReasonerEntryPoints:
    """Tests for entry point detection."""

    def test_detects_main_function(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        entry_labels = {ep.label for ep in u.entry_points}
        assert "main" in entry_labels or "create_app" in entry_labels

    def test_detects_http_endpoints(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        endpoint_entries = [ep for ep in u.entry_points if ep.kind == "http_endpoint"]
        assert len(endpoint_entries) >= 1


class TestReasonerModuleIntelligence:
    """Tests for module intelligence."""

    def test_populates_modules(self, reasoner: CortexReasoner, layered_architecture_graph):
        nodes, edges = layered_architecture_graph
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        assert len(u.modules) > 0
        module_names = {m.name for m in u.modules}
        assert "domain" in module_names or "application" in module_names


class TestReasonerEdgeCases:
    """Edge case handling."""

    def test_empty_graph(self, reasoner: CortexReasoner):
        """Empty graph should produce a valid but empty understanding."""
        u = reasoner.understand(_JOB, _REPO, [], [])
        assert u.repo_name == "test-repo"
        assert u.total_files == 0
        assert u.total_classes == 0

    def test_single_file(self, reasoner: CortexReasoner):
        """A single file should still produce valid output."""
        nodes = [
            _node("f1", "main.py", NodeType.FILE, {"language": "python", "lines": 10}),
            _node("fn1", "main", NodeType.FUNCTION, {"file": "main.py", "lines": 5}),
        ]
        edges = [_edge("f1", "fn1", RelationshipType.CONTAINS)]
        u = reasoner.understand(_JOB, _REPO, nodes, edges)
        assert u.total_files == 1
        assert u.total_functions >= 1
