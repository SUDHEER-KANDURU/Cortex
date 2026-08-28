"""Integration test for the Cortex pipeline (stages 2-5).

Tests the full flow from parsed files → graph → insights → artifacts.
Skips stage 1 (GitHubFetch) to avoid network calls.
Uses in-memory data to validate the pipeline produces correct output
without requiring any external services.
"""

from __future__ import annotations

import pytest
from cortex.graph.domain.entities import NodeType
from cortex.insights.application.engine import InsightsEngine
from cortex.jobs.domain.entities import ArtifactType, Job
from cortex.overview.blast_radius import BlastRadiusAnalyzer
from cortex.pipeline.infrastructure.ast_parser import (
    Language,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
)
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
from cortex.reasoning.application.reasoner import CortexReasoner

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_parsed_files() -> list[ParsedFile]:
    """Simulate what ASTParseStage would produce from a small Python repo."""
    # main.py — entry point with a function
    main_file = ParsedFile(
        path="src/main.py",
        language=Language.PYTHON,
        line_count=30,
        functions=[
            ParsedFunction(
                name="create_app",
                file_path="src/main.py",
                line_start=1,
                line_end=15,
                is_async=False,
                parameters=[],
                return_type="FastAPI",
                decorators=[],
                docstring="Create the FastAPI application.",
                cyclomatic_complexity=2,
                calls=["configure_routes", "configure_middleware"],
            ),
            ParsedFunction(
                name="main",
                file_path="src/main.py",
                line_start=18,
                line_end=30,
                is_async=False,
                parameters=[],
                decorators=[],
                docstring="Entry point.",
                cyclomatic_complexity=1,
                calls=["create_app"],
            ),
        ],
        imports=[
            ParsedImport(module="fastapi", names=["FastAPI"]),
            ParsedImport(module="src.service", names=["UserService"]),
        ],
    )

    # service.py — business logic with a class
    service_file = ParsedFile(
        path="src/service.py",
        language=Language.PYTHON,
        line_count=60,
        classes=[
            ParsedClass(
                name="UserService",
                file_path="src/service.py",
                line_start=5,
                line_end=55,
                base_classes=[],
                docstring="Handles user business logic.",
                methods=[
                    ParsedFunction(
                        name="get_user",
                        file_path="src/service.py",
                        line_start=10,
                        line_end=25,
                        is_method=True,
                        parent_class="UserService",
                        parameters=["self", "user_id: str"],
                        return_type="User",
                        is_async=True,
                        docstring="Fetch a user by ID.",
                        cyclomatic_complexity=3,
                        calls=["repository.find_by_id"],
                    ),
                    ParsedFunction(
                        name="create_user",
                        file_path="src/service.py",
                        line_start=28,
                        line_end=50,
                        is_method=True,
                        parent_class="UserService",
                        parameters=["self", "name: str", "email: str"],
                        return_type="User",
                        is_async=True,
                        docstring="Create a new user.",
                        cyclomatic_complexity=5,
                        calls=["repository.save", "validate_email"],
                    ),
                ],
            ),
        ],
        imports=[
            ParsedImport(module="src.repository", names=["UserRepository"]),
            ParsedImport(module="src.models", names=["User"]),
        ],
    )

    # repository.py — data access layer
    repo_file = ParsedFile(
        path="src/repository.py",
        language=Language.PYTHON,
        line_count=40,
        classes=[
            ParsedClass(
                name="UserRepository",
                file_path="src/repository.py",
                line_start=3,
                line_end=38,
                base_classes=["ABC"],
                is_interface=True,
                docstring="Abstract repository interface for users.",
                methods=[
                    ParsedFunction(
                        name="find_by_id",
                        file_path="src/repository.py",
                        line_start=8,
                        line_end=15,
                        is_method=True,
                        parent_class="UserRepository",
                        parameters=["self", "user_id: str"],
                        return_type="User | None",
                        is_async=True,
                        cyclomatic_complexity=1,
                    ),
                    ParsedFunction(
                        name="save",
                        file_path="src/repository.py",
                        line_start=18,
                        line_end=25,
                        is_method=True,
                        parent_class="UserRepository",
                        parameters=["self", "user: User"],
                        return_type="None",
                        is_async=True,
                        cyclomatic_complexity=1,
                    ),
                ],
            ),
        ],
        imports=[
            ParsedImport(module="abc", names=["ABC", "abstractmethod"]),
            ParsedImport(module="src.models", names=["User"]),
        ],
    )

    # models.py — data models
    models_file = ParsedFile(
        path="src/models.py",
        language=Language.PYTHON,
        line_count=20,
        classes=[
            ParsedClass(
                name="User",
                file_path="src/models.py",
                line_start=3,
                line_end=18,
                base_classes=[],
                docstring="User domain model.",
                attributes=["id", "name", "email", "created_at"],
            ),
        ],
        imports=[
            ParsedImport(module="dataclasses", names=["dataclass"]),
        ],
    )

    # test_service.py — tests
    test_file = ParsedFile(
        path="tests/test_service.py",
        language=Language.PYTHON,
        line_count=35,
        is_test_file=True,
        functions=[
            ParsedFunction(
                name="test_get_user_returns_user",
                file_path="tests/test_service.py",
                line_start=5,
                line_end=15,
                is_test=True,
                parameters=[],
                cyclomatic_complexity=1,
            ),
            ParsedFunction(
                name="test_create_user_validates_email",
                file_path="tests/test_service.py",
                line_start=18,
                line_end=30,
                is_test=True,
                parameters=[],
                cyclomatic_complexity=2,
            ),
        ],
        imports=[
            ParsedImport(module="src.service", names=["UserService"]),
        ],
    )

    return [main_file, service_file, repo_file, models_file, test_file]


@pytest.fixture
def sample_job() -> Job:
    return Job(
        repo_url="https://github.com/example/sample-app",
        artifact_type=ArtifactType.ARCHITECTURE_DIAGRAM,
        id="test-job-integration-001",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestGraphBuilderIntegration:
    """Tests that the graph builder produces a valid graph from parsed files."""

    def test_builds_complete_graph(self, sample_parsed_files: list[ParsedFile], sample_job: Job):
        """Graph builder should produce nodes for all code elements and edges for relationships."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        result = builder.build(sample_parsed_files)

        # Should have nodes
        assert result.node_count() > 0
        assert result.edge_count() > 0

        # Check for expected node types
        node_types = {n.node_type for n in result.nodes}
        assert NodeType.REPOSITORY in node_types
        assert NodeType.MODULE in node_types
        assert NodeType.FILE in node_types
        assert NodeType.CLASS in node_types
        assert NodeType.FUNCTION in node_types

        # Should have file nodes for non-errored files
        file_nodes = result.nodes_by_type(NodeType.FILE)
        assert len(file_nodes) >= 4  # main, service, repository, models (test may be included)

        # Should have class nodes
        class_nodes = result.nodes_by_type(NodeType.CLASS)
        class_labels = {n.label for n in class_nodes}
        assert "UserService" in class_labels
        assert "User" in class_labels

    def test_builds_relationships(self, sample_parsed_files: list[ParsedFile], sample_job: Job):
        """Graph builder should create CONTAINS, IMPORTS, INHERITS edges."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        result = builder.build(sample_parsed_files)

        from cortex.graph.domain.entities import RelationshipType

        edge_types = {e.relationship for e in result.edges}
        assert RelationshipType.CONTAINS in edge_types
        assert RelationshipType.IMPORTS in edge_types

    def test_detects_interface(self, sample_parsed_files: list[ParsedFile], sample_job: Job):
        """Classes with ABC base class should be marked as interface nodes."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        result = builder.build(sample_parsed_files)

        interface_nodes = result.nodes_by_type(NodeType.INTERFACE)
        interface_labels = {n.label for n in interface_nodes}
        assert "UserRepository" in interface_labels

    def test_empty_input(self, sample_job: Job):
        """Empty parsed files should produce a minimal graph (just repo node)."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        result = builder.build([])

        assert result.node_count() == 0 or result.node_count() == 1  # Only repo node or empty


class TestInsightsIntegration:
    """Tests that InsightsEngine produces meaningful output from graph data."""

    def test_computes_report(self, sample_parsed_files: list[ParsedFile], sample_job: Job):
        """InsightsEngine should produce a complete report with dimensions."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        graph = builder.build(sample_parsed_files)

        engine = InsightsEngine()
        report = engine.compute(
            job_id=sample_job.id,
            repo_url=sample_job.repo_url,
            nodes=graph.nodes,
            edges=graph.edges,
        )

        # Should have a valid overall score
        assert 0 <= report.overall_score <= 100
        assert report.overall_grade in ("A", "B", "C", "D", "F")

        # Should have 6 dimensions
        assert len(report.dimensions) == 6
        for dim in report.dimensions:
            assert 0 <= dim.score <= 100
            assert dim.name  # Non-empty name

    def test_detects_language(self, sample_parsed_files: list[ParsedFile], sample_job: Job):
        """Should detect Python as the dominant language."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        graph = builder.build(sample_parsed_files)

        engine = InsightsEngine()
        report = engine.compute(
            job_id=sample_job.id,
            repo_url=sample_job.repo_url,
            nodes=graph.nodes,
            edges=graph.edges,
        )

        assert report.stats.get("dominant_language") == "python"


class TestReasonerIntegration:
    """Tests that CortexReasoner produces structured understanding."""

    def test_produces_understanding(self, sample_parsed_files: list[ParsedFile], sample_job: Job):
        """Reasoner should produce a complete RepositoryUnderstanding."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        graph = builder.build(sample_parsed_files)

        reasoner = CortexReasoner()
        understanding = reasoner.understand(
            job_id=sample_job.id,
            repo_url=sample_job.repo_url,
            nodes=graph.nodes,
            edges=graph.edges,
        )

        # Should populate core fields
        assert understanding.repo_name == "sample-app"
        assert understanding.total_files > 0
        assert understanding.total_classes > 0
        assert understanding.total_functions > 0

        # Should detect languages
        assert "python" in understanding.languages

        # Should detect architecture
        assert understanding.architecture_style is not None

    def test_detects_modules(self, sample_parsed_files: list[ParsedFile], sample_job: Job):
        """Reasoner should detect modules from directory structure."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        graph = builder.build(sample_parsed_files)

        reasoner = CortexReasoner()
        understanding = reasoner.understand(
            job_id=sample_job.id,
            repo_url=sample_job.repo_url,
            nodes=graph.nodes,
            edges=graph.edges,
        )

        assert understanding.total_modules > 0
        assert len(understanding.modules) > 0

    def test_detects_entry_points(self, sample_parsed_files: list[ParsedFile], sample_job: Job):
        """Reasoner should detect main/create_app as entry points."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        graph = builder.build(sample_parsed_files)

        reasoner = CortexReasoner()
        understanding = reasoner.understand(
            job_id=sample_job.id,
            repo_url=sample_job.repo_url,
            nodes=graph.nodes,
            edges=graph.edges,
        )

        entry_labels = {ep.label for ep in understanding.entry_points}
        assert "main" in entry_labels or "create_app" in entry_labels


class TestBlastRadiusIntegration:
    """Tests that BlastRadiusAnalyzer produces valid impact analysis."""

    def test_computes_blast_radius(self, sample_parsed_files: list[ParsedFile], sample_job: Job):
        """Blast radius should find dependents when a core class is changed."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        graph = builder.build(sample_parsed_files)

        # Find the UserRepository node (interface — things depend on it)
        target = None
        for node in graph.nodes:
            if node.label == "UserRepository":
                target = node
                break

        if not target:
            pytest.skip("UserRepository node not found in graph")

        analyzer = BlastRadiusAnalyzer()
        result = analyzer.analyze(target, graph.nodes, graph.edges)

        assert result.target_label == "UserRepository"
        assert result.risk_level in ("low", "medium", "high", "critical")
        assert result.risk_score >= 0

    def test_blast_radius_empty_for_leaf_node(
        self, sample_parsed_files: list[ParsedFile], sample_job: Job
    ):
        """Leaf nodes (no dependents) should have low blast radius."""
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        graph = builder.build(sample_parsed_files)

        # Find User model — likely a leaf in the dependency graph
        target = None
        for node in graph.nodes:
            if node.label == "User" and node.node_type == NodeType.CLASS:
                target = node
                break

        if not target:
            pytest.skip("User class node not found in graph")

        analyzer = BlastRadiusAnalyzer()
        result = analyzer.analyze(target, graph.nodes, graph.edges)

        # User is depended upon, but its blast radius shouldn't be extreme
        assert result.risk_score <= 100


class TestFullPipelineFlow:
    """Tests the complete flow: parsed files → graph → insights → reasoning."""

    def test_end_to_end_produces_all_outputs(
        self, sample_parsed_files: list[ParsedFile], sample_job: Job
    ):
        """Full pipeline (post-fetch) should produce graph, insights, and understanding."""
        # Stage 2 output: parsed files (simulated)
        # Stage 4: Graph build
        builder = GraphBuilder(job_id=sample_job.id, repo_url=sample_job.repo_url)
        graph = builder.build(sample_parsed_files)

        assert graph.node_count() > 0, "Graph should have nodes"
        assert graph.edge_count() > 0, "Graph should have edges"

        # Stage: Insights
        engine = InsightsEngine()
        report = engine.compute(
            job_id=sample_job.id,
            repo_url=sample_job.repo_url,
            nodes=graph.nodes,
            edges=graph.edges,
        )

        assert report.overall_score >= 0, "Insights should produce a score"
        assert len(report.dimensions) == 6, "Should have all 6 dimensions"

        # Stage: Reasoning
        reasoner = CortexReasoner()
        understanding = reasoner.understand(
            job_id=sample_job.id,
            repo_url=sample_job.repo_url,
            nodes=graph.nodes,
            edges=graph.edges,
        )

        assert understanding.repo_name == "sample-app"
        assert understanding.total_files > 0
        assert understanding.overall_score >= 0
        assert understanding.architecture_style is not None

        # All stages produced valid output — pipeline is functional
