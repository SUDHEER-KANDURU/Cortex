import asyncio

from cortex.graph.domain.entities import (
    GraphEdge,
    GraphNode,
    NodeType,
    RelationshipType,
)
from cortex.jobs.domain.entities import ArtifactType, Job
from cortex.pipeline.application.orchestrator import PipelineContext
from cortex.pipeline.infrastructure.artifact_generator import MermaidGenerator
from cortex.pipeline.infrastructure.ast_parser import Language, ParsedFile
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult, GraphBuilder
from cortex.pipeline.infrastructure.stages import GraphBuildStage


def test_build_creates_hierarchical_module_nodes_for_repo_paths() -> None:
    builder = GraphBuilder(
        job_id="job-123",
        repo_url="https://github.com/example/cortex",
    )

    parsed_files = [
        ParsedFile(
            path="backend/src/cortex/pipeline/infrastructure/graph_builder.py",
            language=Language.PYTHON,
            line_count=10,
        ),
        ParsedFile(
            path="frontend/src/app/page.tsx",
            language=Language.TYPESCRIPT,
            line_count=8,
        ),
    ]

    result = builder.build(parsed_files)

    module_paths = {
        node.properties.get("path")
        for node in result.nodes
        if node.node_type == NodeType.MODULE
    }

    assert "backend" in module_paths
    assert "frontend" in module_paths
    assert "backend/src" in module_paths
    assert "frontend/src" in module_paths

    module_edges = [
        edge for edge in result.edges
        if any(
            node.node_type == NodeType.MODULE and node.id == edge.source_id
            for node in result.nodes
        )
        and any(
            node.node_type == NodeType.MODULE and node.id == edge.target_id
            for node in result.nodes
        )
    ]

    assert module_edges


def test_graph_build_stage_execute_handles_debug_summary() -> None:
    stage = GraphBuildStage()
    job = Job(
        repo_url="https://github.com/example/cortex",
        artifact_type=ArtifactType.ARCHITECTURE_DIAGRAM,
    )
    context = PipelineContext(
        job=job,
        repo_url=job.repo_url,
        artifact_type=job.artifact_type,
    )
    context._parsed_files = [
        ParsedFile(
            path="backend/src/cortex/pipeline/infrastructure/graph_builder.py",
            language=Language.PYTHON,
            line_count=10,
        )
    ]  # type: ignore[attr-defined]

    result_context = asyncio.run(stage.execute(context))

    assert result_context.node_count > 0
    assert result_context.edge_count > 0


def test_mermaid_generator_renders_all_modules_and_classes() -> None:
    graph = GraphBuildResult(job_id="job-123", repo_url="https://example.com/repo")

    repo = GraphNode(
        id="repo_root",
        label="repo",
        node_type=NodeType.REPOSITORY,
        job_id="job-123",
    )
    graph.nodes.append(repo)

    module_paths = [
        "backend",
        "backend/jobs",
        "backend/pipeline",
        "backend/graph",
        "backend/shared",
        "frontend",
        "frontend/app",
        "frontend/components",
        "frontend/hooks",
        "shared",
    ]

    modules = []
    for module_path in module_paths:
        module = GraphNode(
            id=f"module_{module_path.replace('/', '_')}",
            label=f"{module_path}/",
            node_type=NodeType.MODULE,
            job_id="job-123",
            properties={"path": module_path},
        )
        graph.nodes.append(module)
        modules.append(module)
        graph.edges.append(
            GraphEdge(
                id=f"edge_{module_path}",
                source_id=repo.id,
                target_id=module.id,
                relationship=RelationshipType.CONTAINS,
                job_id="job-123",
            )
        )

    file_node = GraphNode(
        id="file_config",
        label="config.py",
        node_type=NodeType.FILE,
        job_id="job-123",
        properties={"path": "backend/config.py"},
    )
    graph.nodes.append(file_node)
    graph.edges.append(
        GraphEdge(
            id="edge_file",
            source_id=modules[0].id,
            target_id=file_node.id,
            relationship=RelationshipType.CONTAINS,
            job_id="job-123",
        )
    )

    class_node = GraphNode(
        id="class_app",
        label="AppConfig",
        node_type=NodeType.CLASS,
        job_id="job-123",
        properties={"file": "backend/config.py", "methods": 2},
    )
    graph.nodes.append(class_node)
    graph.edges.append(
        GraphEdge(
            id="edge_class",
            source_id=file_node.id,
            target_id=class_node.id,
            relationship=RelationshipType.CONTAINS,
            job_id="job-123",
        )
    )

    output = MermaidGenerator().generate(graph, "repo")

    assert "backend/" in output
    assert "frontend/" in output
    assert "shared/" in output
    assert "frontend/components/" in output
    assert "AppConfig" in output
