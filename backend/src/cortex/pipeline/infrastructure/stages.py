"""Pipeline stages — each stage does one job in the analysis pipeline.

Stage order:
  1. GitHubFetchStage    — fetches file tree + raw file contents
  2. ASTParseStage       — parses fetched files → context.parsed_files
  3. VibeDetectStage     — runs vibe detection  → context.vibe_report
  4. GraphBuildStage     — builds knowledge graph → context.graph_result
  5. ArtifactGenerateStage — generates artifact content

Every stage reads from PipelineContext typed fields and writes back
to typed fields. No private _attrs anywhere.
"""

import structlog

from cortex.pipeline.application.orchestrator import PipelineContext
from cortex.pipeline.domain.interfaces import AbstractPipelineStage
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.artifacts.domain.entities import ArtifactContentType

logger = structlog.get_logger()


class GitHubFetchStage(AbstractPipelineStage):
    """Stage 1 — Fetches repository file tree and raw file contents.

    Delegates to GitHubAnalyzer which wraps GitHubClient.
    Populates: context.file_tree, context.file_contents.
    """

    def __init__(self) -> None:
        from cortex.pipeline.infrastructure.github_analyzer import (
            GitHubAnalyzer,
        )
        self._analyzer = GitHubAnalyzer()

    async def execute(self, context: PipelineContext) -> PipelineContext:
        try:
            logger.info(
                "github_fetch_stage_started",
                job_id=context.job.id,
                repo_url=context.repo_url,
            )

            # Use the analyzer only for fetching — parse/vibe are separate stages
            result = await self._analyzer.fetch(
                context.repo_url,
                max_files=60,
            )

            context.file_tree = [
                {"path": f.path, "type": "blob", "size": f.size}
                for f in result.fetched_files
            ]
            context.file_contents = {
                f.path: f.content for f in result.fetched_files
            }

            logger.info(
                "github_fetch_stage_completed",
                job_id=context.job.id,
                tree_files=len(context.file_tree),
                code_files=len(context.file_contents),
            )

        except Exception as e:
            context.mark_error(f"GitHubFetchStage failed: {str(e)}")

        return context


class ASTParseStage(AbstractPipelineStage):
    """Stage 2 — Parses all fetched code files using the AST parser.

    Reads:   context.file_contents
    Writes:  context.parsed_files
    """

    def __init__(self) -> None:
        from cortex.pipeline.infrastructure.ast_parser import ASTParser
        self._parser = ASTParser()

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if not context.file_contents:
            context.mark_error(
                "ASTParseStage: no file contents to parse. "
                "GitHubFetchStage may have failed."
            )
            return context

        try:
            logger.info(
                "ast_parse_stage_started",
                job_id=context.job.id,
                file_count=len(context.file_contents),
            )

            files_to_parse = [
                (content, path)
                for path, content in context.file_contents.items()
            ]

            context.parsed_files = self._parser.parse_many(files_to_parse)

            successful = [p for p in context.parsed_files if not p.has_errors()]
            failed = [p for p in context.parsed_files if p.has_errors()]

            logger.info(
                "ast_parse_stage_completed",
                job_id=context.job.id,
                total=len(context.parsed_files),
                successful=len(successful),
                failed=len(failed),
                total_classes=sum(len(p.classes) for p in successful),
                total_functions=sum(
                    len(p.all_functions()) for p in successful
                ),
            )

        except Exception as e:
            context.mark_error(f"ASTParseStage failed: {str(e)}")

        return context


class VibeDetectStage(AbstractPipelineStage):
    """Stage 3 — Runs vibe code detection on parsed files.

    Reads:   context.parsed_files
    Writes:  context.vibe_report
    Non-fatal — pipeline continues even if this stage fails.
    """

    def __init__(self) -> None:
        from cortex.pipeline.infrastructure.vibe_detector import VibeDetector
        self._detector = VibeDetector()

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if not context.parsed_files:
            # No parsed files — skip silently, not fatal
            return context

        try:
            context.vibe_report = self._detector.analyze(
                context.parsed_files,
                context.repo_url,
            )
            logger.info(
                "vibe_detect_stage_completed",
                job_id=context.job.id,
                flags=len(context.vibe_report.flags),
                health_score=context.vibe_report.health_score,
            )
        except Exception as e:
            # Non-fatal — pipeline continues without vibe data
            logger.warning(
                "vibe_detect_stage_failed",
                job_id=context.job.id,
                error=str(e),
            )

        return context


class GraphBuildStage(AbstractPipelineStage):
    """Stage 4 — Builds the knowledge graph from parsed files.

    Reads:   context.parsed_files
    Writes:  context.graph_result, context.node_count, context.edge_count
    Also persists nodes and edges to SQLite (non-fatal if it fails).
    """

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if not context.parsed_files:
            context.mark_error(
                "GraphBuildStage: no parsed files found. "
                "ASTParseStage may have failed."
            )
            return context

        try:
            logger.info(
                "graph_build_stage_started",
                job_id=context.job.id,
                parsed_file_count=len(context.parsed_files),
            )

            builder = GraphBuilder(
                job_id=context.job.id,
                repo_url=context.repo_url,
            )
            graph_result = builder.build(context.parsed_files)

            context.graph_result = graph_result
            context.node_count = graph_result.node_count()
            context.edge_count = graph_result.edge_count()

            # Persist to SQLite — non-fatal
            try:
                from cortex.graph.infrastructure.sqlite_repository import (
                    SQLiteGraphRepository,
                )
                from cortex.config import get_settings
                graph_repo = SQLiteGraphRepository(get_settings().database_url)
                for node in graph_result.nodes:
                    await graph_repo.save_node(node)
                for edge in graph_result.edges:
                    await graph_repo.save_edge(edge)
                logger.info(
                    "graph_persisted_to_sqlite",
                    job_id=context.job.id,
                    nodes=context.node_count,
                    edges=context.edge_count,
                )
            except Exception as e:
                logger.warning(
                    "graph_persist_failed",
                    job_id=context.job.id,
                    error=str(e),
                )

            logger.info(
                "graph_build_stage_completed",
                job_id=context.job.id,
                nodes=context.node_count,
                edges=context.edge_count,
            )

        except Exception as e:
            context.mark_error(f"GraphBuildStage failed: {str(e)}")

        return context


class ArtifactGenerateStage(AbstractPipelineStage):
    """Stage 5 — Generates artifact content from the knowledge graph.

    Reads:   context.graph_result, context.vibe_report, context.artifact_type
    Writes:  context.artifact_content, context.artifact_content_type
    """

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if not context.graph_result:
            context.mark_error(
                "ArtifactGenerateStage: no graph result found. "
                "GraphBuildStage may have failed."
            )
            return context

        try:
            from cortex.pipeline.infrastructure.artifact_generator import (
                MermaidGenerator,
                MarkdownReportGenerator,
            )

            graph_result = context.graph_result
            repo_name = context.repo_url.rstrip("/").split("/")[-1]
            artifact_type = context.artifact_type.value
            mermaid_gen = MermaidGenerator()
            markdown_gen = MarkdownReportGenerator()

            if artifact_type == "architecture_diagram":
                content = mermaid_gen.generate(graph_result, repo_name)
                content_type = ArtifactContentType.MERMAID

            elif artifact_type == "module_breakdown":
                content = markdown_gen.generate_module_breakdown(
                    graph_result, repo_name
                )
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "learning_path":
                content = markdown_gen.generate_learning_path(
                    graph_result, repo_name
                )
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "api_spec":
                content = markdown_gen.generate_api_spec(
                    graph_result, repo_name
                )
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "interview_questions":
                content = markdown_gen.generate_interview_questions(
                    graph_result, repo_name
                )
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "vibe_code_detection":
                if context.vibe_report:
                    content = context.vibe_report.to_markdown()
                else:
                    content = "# Vibe Code Detection\n\nNo data available."
                content_type = ArtifactContentType.MARKDOWN

            else:
                content = mermaid_gen.generate(graph_result, repo_name)
                content_type = ArtifactContentType.MERMAID

            context.artifact_content = content
            context.artifact_content_type = content_type

            logger.info(
                "artifact_generate_stage_completed",
                job_id=context.job.id,
                artifact_type=artifact_type,
                content_length=len(content),
            )

        except Exception as e:
            context.mark_error(f"ArtifactGenerateStage failed: {str(e)}")

        return context
