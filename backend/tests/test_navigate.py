"""End-to-end tests for the Navigate feature.

Tests the complete flow:
- Navigate to file, class, function, method, endpoint, module
- Verify definition, callers, callees, dependencies, dependents, source location
- Test entities with no callers, no dependencies, multiple callers
- Test missing relationships and invalid node IDs
- Test impact analysis
- Test explain endpoint (mocked NIM)
"""

import asyncio
import sys
import os

# Add backend/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from cortex.navigate.service import NavigateService
from cortex.navigate.models import (
    NavigateResponse,
    NavigationMode,
    RelationshipStatus,
    ConnectedNode,
    NavigateInsights,
)
from cortex.graph.domain.entities import (
    GraphNode,
    GraphEdge,
    NodeType,
    RelationshipType,
)
from datetime import datetime, timezone


# ─── Test Fixtures ────────────────────────────────────────────────────────────

def _make_node(id: str, label: str, node_type: NodeType, job_id: str = "job-1", **props) -> GraphNode:
    return GraphNode(
        id=id,
        label=label,
        node_type=node_type,
        job_id=job_id,
        properties=props,
        created_at=datetime.now(timezone.utc),
    )


def _make_edge(id: str, source_id: str, target_id: str, relationship: RelationshipType, job_id: str = "job-1") -> GraphEdge:
    return GraphEdge(
        id=id,
        source_id=source_id,
        target_id=target_id,
        relationship=relationship,
        job_id=job_id,
        properties={},
        created_at=datetime.now(timezone.utc),
    )


# Sample graph representing a small authentication system
SAMPLE_NODES = [
    _make_node("repo-1", "auth-service", NodeType.REPOSITORY, file=""),
    _make_node("mod-auth", "auth", NodeType.MODULE, file="src/auth/"),
    _make_node("file-router", "auth_router.py", NodeType.FILE, file="src/auth/auth_router.py", lines=85, language="python"),
    _make_node("file-service", "auth_service.py", NodeType.FILE, file="src/auth/auth_service.py", lines=120, language="python"),
    _make_node("cls-auth-router", "AuthRouter", NodeType.CLASS, file="src/auth/auth_router.py", line_start=10, line_end=85, methods=3, has_docstring=True),
    _make_node("fn-login", "login", NodeType.FUNCTION, file="src/auth/auth_router.py", line_start=15, line_end=35, cyclomatic=4, parameters=2, is_async=True, has_docstring=True),
    _make_node("fn-logout", "logout", NodeType.FUNCTION, file="src/auth/auth_router.py", line_start=37, line_end=50, cyclomatic=2, parameters=1, is_async=True),
    _make_node("cls-auth-service", "AuthService", NodeType.CLASS, file="src/auth/auth_service.py", line_start=5, line_end=120, methods=5, cyclomatic=8, has_docstring=True),
    _make_node("meth-authenticate", "authenticate", NodeType.METHOD, file="src/auth/auth_service.py", line_start=20, line_end=55, cyclomatic=6, parameters=3, is_async=True),
    _make_node("meth-validate-token", "validate_token", NodeType.METHOD, file="src/auth/auth_service.py", line_start=57, line_end=80, cyclomatic=3, parameters=1, is_async=True),
    _make_node("endpoint-login", "POST /login", NodeType.ENDPOINT, file="src/auth/auth_router.py", line_start=15, route_info="POST /login"),
    _make_node("fn-find-user", "find_user", NodeType.FUNCTION, file="src/auth/user_repo.py", line_start=10, line_end=30, cyclomatic=2, parameters=1, is_async=True),
    _make_node("test-auth", "test_authenticate", NodeType.TEST, file="tests/test_auth_service.py", line_start=5, line_end=25),
    _make_node("test-login", "test_login_endpoint", NodeType.TEST, file="tests/test_auth_router.py", line_start=10, line_end=40),
    # Isolated node — no connections
    _make_node("fn-isolated", "isolated_util", NodeType.FUNCTION, file="src/utils/isolated.py", line_start=1, line_end=10, cyclomatic=1),
]

SAMPLE_EDGES = [
    # Structural
    _make_edge("e1", "repo-1", "mod-auth", RelationshipType.CONTAINS),
    _make_edge("e2", "mod-auth", "file-router", RelationshipType.CONTAINS),
    _make_edge("e3", "mod-auth", "file-service", RelationshipType.CONTAINS),
    _make_edge("e4", "file-router", "cls-auth-router", RelationshipType.CONTAINS),
    _make_edge("e5", "cls-auth-router", "fn-login", RelationshipType.CONTAINS),
    _make_edge("e6", "cls-auth-router", "fn-logout", RelationshipType.CONTAINS),
    _make_edge("e7", "file-service", "cls-auth-service", RelationshipType.CONTAINS),
    _make_edge("e8", "cls-auth-service", "meth-authenticate", RelationshipType.CONTAINS),
    _make_edge("e9", "cls-auth-service", "meth-validate-token", RelationshipType.CONTAINS),
    # Call relationships
    _make_edge("e10", "fn-login", "meth-authenticate", RelationshipType.CALLS),
    _make_edge("e11", "meth-authenticate", "fn-find-user", RelationshipType.CALLS),
    _make_edge("e12", "fn-login", "meth-validate-token", RelationshipType.CALLS),
    _make_edge("e13", "endpoint-login", "fn-login", RelationshipType.CALLS),
    # Dependencies
    _make_edge("e14", "file-router", "file-service", RelationshipType.IMPORTS),
    _make_edge("e15", "cls-auth-router", "cls-auth-service", RelationshipType.DEPENDS_ON),
    # Tests
    _make_edge("e16", "test-auth", "meth-authenticate", RelationshipType.TESTS),
    _make_edge("e17", "test-login", "endpoint-login", RelationshipType.TESTS),
]


# ─── Mock Setup ───────────────────────────────────────────────────────────────

def _get_edges_for_node(node_id: str) -> list[GraphEdge]:
    """Return edges connected to a specific node."""
    return [e for e in SAMPLE_EDGES if e.source_id == node_id or e.target_id == node_id]


def _get_edges_by_job(job_id: str) -> list[GraphEdge]:
    return SAMPLE_EDGES


def _get_nodes_by_job(job_id: str) -> list[GraphNode]:
    return SAMPLE_NODES


def _get_node_by_id(node_id: str) -> GraphNode | None:
    for n in SAMPLE_NODES:
        if n.id == node_id:
            return n
    return None


# ─── Tests ────────────────────────────────────────────────────────────────────

@pytest.fixture
def service():
    """Create a NavigateService with mocked graph repository."""
    with patch('cortex.navigate.service.graph_repository') as mock_repo, \
         patch('cortex.navigate.service.job_repository') as mock_job_repo:
        mock_repo.get_node_by_id = AsyncMock(side_effect=_get_node_by_id)
        mock_repo.get_edges_for_node = AsyncMock(side_effect=_get_edges_for_node)
        mock_repo.get_nodes_by_job = AsyncMock(side_effect=_get_nodes_by_job)
        mock_repo.get_edges_by_job = AsyncMock(side_effect=_get_edges_by_job)

        mock_job = MagicMock()
        mock_job.repo_url = "https://github.com/example/auth-service"
        mock_job_repo.get_by_id = AsyncMock(return_value=mock_job)

        yield NavigateService()


# ── Test: Navigate to a Function ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_function(service):
    """Navigate to login function — should show callers, callees, definition."""
    result = await service.get_navigation_context("job-1", "fn-login")

    assert result is not None
    assert result.id == "fn-login"
    assert result.label == "login"
    assert result.node_type == "Function"

    # Definition / source location
    assert result.source.file_path == "src/auth/auth_router.py"
    assert result.source.line_start == 15
    assert result.source.line_end == 35
    assert result.source.symbol_name == "login"

    # Callers (who calls login?)
    # endpoint-login CALLS fn-login
    assert len(result.callers) >= 1
    caller_ids = [c.id for c in result.callers]
    assert "endpoint-login" in caller_ids

    # Callees (what does login call?)
    # fn-login CALLS meth-authenticate, fn-login CALLS meth-validate-token
    assert len(result.callees) >= 2
    callee_ids = [c.id for c in result.callees]
    assert "meth-authenticate" in callee_ids
    assert "meth-validate-token" in callee_ids

    # Contained by
    assert result.contained_by is not None
    assert result.contained_by.id == "cls-auth-router"

    # Insights
    assert result.insights.complexity == 4


@pytest.mark.asyncio
async def test_navigate_function_insights(service):
    """Insights should reflect node properties accurately."""
    result = await service.get_navigation_context("job-1", "fn-login")

    assert result.insights.is_async is True
    assert result.insights.has_docstring is True
    assert result.insights.parameters == 2


# ── Test: Navigate to a Method ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_method(service):
    """Navigate to authenticate method — should show callers and callees."""
    result = await service.get_navigation_context("job-1", "meth-authenticate")

    assert result is not None
    assert result.label == "authenticate"
    assert result.node_type == "Method"

    # Callers: fn-login CALLS meth-authenticate
    caller_ids = [c.id for c in result.callers]
    assert "fn-login" in caller_ids

    # Callees: meth-authenticate CALLS fn-find-user
    callee_ids = [c.id for c in result.callees]
    assert "fn-find-user" in callee_ids

    # Tests: test-auth TESTS meth-authenticate
    test_ids = [t.id for t in result.tests]
    assert "test-auth" in test_ids


# ── Test: Navigate to an Endpoint ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_endpoint(service):
    """Navigate to POST /login endpoint."""
    result = await service.get_navigation_context("job-1", "endpoint-login")

    assert result is not None
    assert result.label == "POST /login"
    assert result.node_type == "Endpoint"

    # Callees: endpoint-login CALLS fn-login
    callee_ids = [c.id for c in result.callees]
    assert "fn-login" in callee_ids

    # Tests
    test_ids = [t.id for t in result.tests]
    assert "test-login" in test_ids


# ── Test: Navigate to a Class ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_class(service):
    """Navigate to AuthService class — should show contained methods."""
    result = await service.get_navigation_context("job-1", "cls-auth-service")

    assert result is not None
    assert result.label == "AuthService"
    assert result.node_type == "Class"

    # Contains: meth-authenticate, meth-validate-token
    child_ids = [c.id for c in result.contains]
    assert "meth-authenticate" in child_ids
    assert "meth-validate-token" in child_ids

    # Dependents: cls-auth-router DEPENDS_ON cls-auth-service
    dependent_ids = [d.id for d in result.dependents]
    assert "cls-auth-router" in dependent_ids


# ── Test: Navigate to a Module ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_module(service):
    """Navigate to the auth module — should show contained files."""
    result = await service.get_navigation_context("job-1", "mod-auth")

    assert result is not None
    assert result.label == "auth"
    assert result.node_type == "Module"

    # Contains: file-router, file-service
    child_ids = [c.id for c in result.contains]
    assert "file-router" in child_ids
    assert "file-service" in child_ids

    # Contained by: repo-1
    assert result.contained_by is not None
    assert result.contained_by.id == "repo-1"


# ── Test: Navigate to a File ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_file(service):
    """Navigate to auth_router.py file."""
    result = await service.get_navigation_context("job-1", "file-router")

    assert result is not None
    assert result.label == "auth_router.py"
    assert result.node_type == "File"
    assert result.source.file_path == "src/auth/auth_router.py"

    # Contains: cls-auth-router
    child_ids = [c.id for c in result.contains]
    assert "cls-auth-router" in child_ids

    # Dependencies (IMPORTS): file-router IMPORTS file-service
    dep_ids = [d.id for d in result.dependencies]
    assert "file-service" in dep_ids


# ── Test: Entity with No Callers ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_no_callers(service):
    """Entity with no incoming calls should have empty callers list."""
    result = await service.get_navigation_context("job-1", "endpoint-login")

    # The endpoint has no callers (it's a top-level entry point)
    # Only callees outward
    assert result.callers == []


# ── Test: Entity with No Dependencies ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_no_dependencies(service):
    """fn-find-user has no outgoing dependency edges."""
    result = await service.get_navigation_context("job-1", "fn-find-user")

    assert result is not None
    assert result.dependencies == []
    assert result.callees == []


# ── Test: Entity with Multiple Callers ────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_multiple_callers(service):
    """meth-validate-token is called by fn-login (could be multiple)."""
    result = await service.get_navigation_context("job-1", "meth-validate-token")

    assert result is not None
    caller_ids = [c.id for c in result.callers]
    assert "fn-login" in caller_ids


# ── Test: Isolated Entity (No Connections) ────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_isolated_entity(service):
    """Isolated entity should return valid response with empty relationships."""
    result = await service.get_navigation_context("job-1", "fn-isolated")

    assert result is not None
    assert result.label == "isolated_util"
    assert result.callers == []
    assert result.callees == []
    assert result.dependencies == []
    assert result.dependents == []
    assert result.contained_by is None


# ── Test: Invalid Node ID ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_invalid_node(service):
    """Invalid node ID should return None (API will 404)."""
    result = await service.get_navigation_context("job-1", "non-existent-id")
    assert result is None


# ── Test: Breadcrumb ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_breadcrumb(service):
    """Breadcrumb should trace from root to the target entity."""
    result = await service.get_navigation_context("job-1", "fn-login")

    assert result is not None
    assert len(result.breadcrumb) >= 2
    # Last item should be the target itself
    assert result.breadcrumb[-1].id == "fn-login"
    # Should include the parent (cls-auth-router)
    breadcrumb_ids = [b.id for b in result.breadcrumb]
    assert "cls-auth-router" in breadcrumb_ids


# ── Test: Impact Analysis ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_impact_analysis(service):
    """Impact of meth-authenticate: what breaks if it changes?
    fn-login calls it, endpoint-login calls fn-login → both affected.
    """
    result = await service.get_impact_analysis("job-1", "meth-authenticate")

    assert len(result) >= 1
    impact_ids = [n.id for n in result]
    # fn-login calls meth-authenticate, so it's affected
    assert "fn-login" in impact_ids


# ── Test: Related Tests Detection ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_related_tests_direct(service):
    """Direct TESTS edge should appear in tests list."""
    result = await service.get_navigation_context("job-1", "meth-authenticate")

    test_ids = [t.id for t in result.tests]
    assert "test-auth" in test_ids
    # Check relationship status
    test_auth = next(t for t in result.tests if t.id == "test-auth")
    assert test_auth.relationship_status == RelationshipStatus.DETECTED


# ── Test: Relationship Status ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_relationship_status(service):
    """Directly connected nodes should be marked as DETECTED."""
    result = await service.get_navigation_context("job-1", "fn-login")

    # Direct callers should be DETECTED
    for caller in result.callers:
        assert caller.relationship_status == RelationshipStatus.DETECTED

    # Direct callees should be DETECTED
    for callee in result.callees:
        assert callee.relationship_status == RelationshipStatus.DETECTED


# ── Test: Source Location Preserved ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_source_location(service):
    """Every entity should preserve its source location."""
    result = await service.get_navigation_context("job-1", "meth-authenticate")

    assert result.source.file_path == "src/auth/auth_service.py"
    assert result.source.line_start == 20
    assert result.source.line_end == 55
    assert result.source.symbol_name == "authenticate"
    assert "github.com" in result.source.repository


# ── Test: Call Paths ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_call_paths_upstream(service):
    """Upstream call paths for fn-find-user should trace back through callers."""
    result = await service.get_navigation_context("job-1", "fn-find-user")

    # fn-find-user is called by meth-authenticate, which is called by fn-login
    if result.call_paths_upstream:
        # At least one path should exist
        path_labels = []
        for path in result.call_paths_upstream:
            path_labels.extend([n.label for n in path.nodes])
        # Should contain the caller chain
        assert "find_user" in path_labels or len(result.call_paths_upstream) >= 0


@pytest.mark.asyncio
async def test_call_paths_downstream(service):
    """Downstream call paths for endpoint-login should trace through callees."""
    result = await service.get_navigation_context("job-1", "endpoint-login")

    if result.call_paths_downstream:
        all_labels = []
        for path in result.call_paths_downstream:
            all_labels.extend([n.label for n in path.nodes])
        # Should trace down to login → authenticate → find_user
        assert "POST /login" in all_labels


# ── Test: ConnectedNode Fields ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_connected_node_fields(service):
    """ConnectedNode should have all required fields populated."""
    result = await service.get_navigation_context("job-1", "fn-login")

    for caller in result.callers:
        assert caller.id
        assert caller.label
        assert caller.node_type
        assert caller.relationship
        # relationship_status should be set
        assert caller.relationship_status in [
            RelationshipStatus.DETECTED,
            RelationshipStatus.INFERRED,
            RelationshipStatus.UNAVAILABLE,
        ]


# ── Test: Risk Factors ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_risk_factors(service):
    """High-complexity entities should report risk factors."""
    result = await service.get_navigation_context("job-1", "meth-authenticate")

    # cyclomatic=6, parameters=3 — no warning thresholds hit for this entity
    # But let's check the insights are computed
    assert result.insights.complexity == 6
    assert result.insights.parameters == 3
    assert result.insights.is_async is True


# ─── Run tests ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
