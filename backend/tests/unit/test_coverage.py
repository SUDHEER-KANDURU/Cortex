"""Tests for coverage-gap capture and Coverage computation (Req 1.4, Req 6.1)."""

import asyncio

from cortex.graph.domain.entities import GraphNode, NodeType
from cortex.jobs.domain.entities import ArtifactType, Job
from cortex.pipeline.application.orchestrator import PipelineContext
from cortex.pipeline.domain.entities import Coverage, CoverageGap
from cortex.pipeline.infrastructure.ast_parser import Language, ParsedFile
from cortex.pipeline.infrastructure.coverage import (
    collect_coverage_gaps,
    compute_coverage,
)
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult
from cortex.pipeline.infrastructure.stages import ASTParseStage, GraphBuildStage

# ── CoverageGap capture (Req 1.4) ─────────────────────────────────────────────


def test_parse_failure_records_gap_with_path_and_reason() -> None:
    parsed_files = [
        ParsedFile(path="ok.py", language=Language.PYTHON, line_count=5),
        ParsedFile(
            path="broken.py",
            language=Language.PYTHON,
            parse_errors=["SyntaxError at line 3: invalid syntax"],
        ),
    ]

    gaps = collect_coverage_gaps(parsed_files)

    assert gaps == [
        CoverageGap(
            file_path="broken.py",
            reason="SyntaxError at line 3: invalid syntax",
        )
    ]


def test_gap_reason_is_never_empty() -> None:
    parsed_files = [
        ParsedFile(path="mystery.py", language=Language.PYTHON, parse_errors=[""]),
    ]

    gaps = collect_coverage_gaps(parsed_files)

    assert len(gaps) == 1
    assert gaps[0].reason == "Unknown parse error"


def test_failed_files_are_not_silently_dropped() -> None:
    # Three files, two of which failed — every failure must surface as a gap.
    parsed_files = [
        ParsedFile(path="a.py", language=Language.PYTHON, line_count=1),
        ParsedFile(path="b.py", language=Language.PYTHON, parse_errors=["boom"]),
        ParsedFile(path="c.go", language=Language.GO, parse_errors=["No parser available for go"]),
    ]

    coverage = compute_coverage(parsed_files)

    gap_paths = {g.file_path for g in coverage.gaps}
    assert gap_paths == {"b.py", "c.go"}
    assert coverage.gap_count() == 2


def test_multiple_parse_errors_join_into_one_reason() -> None:
    parsed_files = [
        ParsedFile(
            path="messy.py",
            language=Language.PYTHON,
            parse_errors=["error one", "error two"],
        )
    ]

    gaps = collect_coverage_gaps(parsed_files)

    assert gaps[0].reason == "error one; error two"


# ── File coverage (Req 6.1) ───────────────────────────────────────────────────


def test_file_coverage_counts_analyzed_vs_total() -> None:
    parsed_files = [
        ParsedFile(path="a.py", language=Language.PYTHON, line_count=1),
        ParsedFile(path="b.py", language=Language.PYTHON, line_count=1),
        ParsedFile(path="c.py", language=Language.PYTHON, parse_errors=["boom"]),
    ]

    coverage = compute_coverage(parsed_files)

    assert coverage.total_files == 3
    assert coverage.analyzed_files == 2
    assert coverage.file_coverage_ratio() == 2 / 3


def test_empty_repo_has_full_coverage() -> None:
    coverage = compute_coverage([])

    assert coverage.total_files == 0
    assert coverage.analyzed_files == 0
    assert coverage.file_coverage_ratio() == 1.0
    assert coverage.reference_coverage_ratio() == 1.0
    assert coverage.gap_count() == 0


# ── Reference coverage (Req 6.1) ──────────────────────────────────────────────


def _node(node_id: str, node_type: NodeType, **props: object) -> GraphNode:
    return GraphNode(
        id=node_id,
        label=node_id,
        node_type=node_type,
        job_id="job-1",
        properties=dict(props),
    )


def test_reference_coverage_aggregates_calls_and_imports() -> None:
    graph = GraphBuildResult(job_id="job-1", repo_url="https://example.com/repo")
    graph.nodes.extend(
        [
            _node("f1", NodeType.FILE, resolved_imports=3, unresolved_imports=1),
            _node("f2", NodeType.FILE, resolved_imports=0, unresolved_imports=2),
            _node("fn1", NodeType.FUNCTION, resolved_calls=5, unresolved_calls=4),
            # A node without resolution props contributes nothing.
            _node("m1", NodeType.MODULE, path="src"),
        ]
    )
    parsed_files = [ParsedFile(path="a.py", language=Language.PYTHON, line_count=1)]

    coverage = compute_coverage(parsed_files, graph)

    assert coverage.resolved_references == 3 + 0 + 5
    assert coverage.unresolved_references == 1 + 2 + 4
    assert coverage.reference_coverage_ratio() == 8 / (8 + 7)


def test_reference_counts_zero_without_graph() -> None:
    parsed_files = [ParsedFile(path="a.py", language=Language.PYTHON, line_count=1)]

    coverage = compute_coverage(parsed_files, None)

    assert coverage.resolved_references == 0
    assert coverage.unresolved_references == 0
    assert coverage.reference_coverage_ratio() == 1.0


def test_summary_is_serializable_and_complete() -> None:
    coverage = Coverage(
        total_files=2,
        analyzed_files=1,
        resolved_references=4,
        unresolved_references=1,
        gaps=(CoverageGap(file_path="bad.py", reason="boom"),),
    )

    summary = coverage.summary()

    assert summary["total_files"] == 2
    assert summary["analyzed_files"] == 1
    assert summary["resolved_references"] == 4
    assert summary["unresolved_references"] == 1
    assert summary["gap_count"] == 1
    assert summary["gaps"] == [{"file_path": "bad.py", "reason": "boom"}]
    assert summary["file_coverage_ratio"] == 0.5
    assert round(summary["reference_coverage_ratio"], 4) == 0.8


# ── Determinism (Req 6.1) ─────────────────────────────────────────────────────


def test_compute_coverage_is_deterministic() -> None:
    parsed_files = [
        ParsedFile(path="a.py", language=Language.PYTHON, line_count=1),
        ParsedFile(path="b.py", language=Language.PYTHON, parse_errors=["boom"]),
    ]
    graph = GraphBuildResult(job_id="job-1", repo_url="https://example.com/repo")
    graph.nodes.append(
        _node("fn1", NodeType.FUNCTION, resolved_calls=2, unresolved_calls=1)
    )

    first = compute_coverage(parsed_files, graph)
    second = compute_coverage(parsed_files, graph)

    assert first == second


# ── Pipeline wiring (Req 1.4, Req 6.1) ────────────────────────────────────────


def _context(parsed_files: list[ParsedFile]) -> PipelineContext:
    job = Job(
        repo_url="https://github.com/example/repo",
        artifact_type=ArtifactType.FOLDER_STRUCTURE,
    )
    context = PipelineContext(
        job=job,
        repo_url=job.repo_url,
        artifact_type=job.artifact_type,
    )
    context.parsed_files = parsed_files
    return context


def test_ast_parse_stage_populates_coverage_gaps() -> None:
    # ASTParseStage parses raw contents; feed it one valid and one broken file.
    job = Job(
        repo_url="https://github.com/example/repo",
        artifact_type=ArtifactType.FOLDER_STRUCTURE,
    )
    context = PipelineContext(
        job=job,
        repo_url=job.repo_url,
        artifact_type=job.artifact_type,
    )
    context.file_contents = {
        "good.py": "def f():\n    return 1\n",
        "bad.py": "def f(:\n",  # syntax error
    }

    result = asyncio.run(ASTParseStage().execute(context))

    assert result.coverage is not None
    assert result.coverage.total_files == 2
    assert result.coverage.analyzed_files == 1
    assert result.coverage.gap_count() == 1
    assert result.coverage.gaps[0].file_path == "bad.py"
    assert result.coverage.gaps[0].reason  # non-empty reason


def test_graph_build_stage_folds_reference_counts_into_coverage() -> None:
    context = _context(
        [
            ParsedFile(path="a.py", language=Language.PYTHON, line_count=3),
        ]
    )

    result = asyncio.run(GraphBuildStage().execute(context))

    assert result.coverage is not None
    # File coverage still reflects the parsed files.
    assert result.coverage.total_files == 1
    assert result.coverage.analyzed_files == 1
    # Reference counts are integers aggregated from the graph.
    assert isinstance(result.coverage.resolved_references, int)
    assert isinstance(result.coverage.unresolved_references, int)
