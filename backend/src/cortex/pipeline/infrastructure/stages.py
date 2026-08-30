"""Pipeline stages — each stage does one job in the analysis pipeline.

Stage order:
  1. GitHubFetchStage       — fetches file tree + raw file contents
  2. ASTParseStage          — parses fetched files → context.parsed_files
  3. VibeDetectStage        — runs vibe detection  → context.vibe_report
  4. GraphBuildStage        — builds knowledge graph → context.graph_result
  5. ArtifactGenerateStage  — generates artifact content

Every stage reads from and writes to typed PipelineContext fields only.
"""

import structlog

from cortex.pipeline.application.orchestrator import PipelineContext
from cortex.pipeline.domain.interfaces import AbstractPipelineStage
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
from cortex.artifacts.domain.entities import ArtifactContentType

logger = structlog.get_logger()


class GitHubFetchStage(AbstractPipelineStage):
    """Stage 1 — Fetches repository file tree and raw file contents."""

    def __init__(self) -> None:
        from cortex.pipeline.infrastructure.github_analyzer import GitHubAnalyzer
        self._analyzer = GitHubAnalyzer()

    async def execute(self, context: PipelineContext) -> PipelineContext:
        try:
            logger.info(
                "github_fetch_stage_started",
                job_id=context.job.id,
                repo_url=context.repo_url,
            )

            # No explicit max_files — the analyzer defaults to MAX_ANALYSIS_FILES
            # so large repos are handled (Req 10.1). Files beyond the cap come
            # back as result.skipped_files and are recorded as coverage gaps.
            result = await self._analyzer.fetch(context.repo_url)

            context.file_tree = [
                {"path": f.path, "type": "blob", "size": f.size}
                for f in result.fetched_files
            ]
            context.file_contents = {
                f.path: f.content for f in result.fetched_files
            }
            context.skipped_files = list(result.skipped_files)

            logger.info(
                "github_fetch_stage_completed",
                job_id=context.job.id,
                tree_files=len(context.file_tree),
                code_files=len(context.file_contents),
                skipped_files=len(context.skipped_files),
            )

            # Store file hashes for incremental analysis on next run
            try:
                from cortex.pipeline.infrastructure.incremental_analyzer import IncrementalAnalyzer
                incremental = IncrementalAnalyzer()
                await incremental.store_hashes(
                    repo_url=context.repo_url,
                    job_id=context.job.id,
                    file_contents=context.file_contents,
                )
            except Exception as hash_err:
                logger.warning("file_hash_storage_failed", error=str(hash_err))

        except Exception as e:
            context.mark_error(f"GitHubFetchStage failed: {str(e)}")

        finally:
            # Always close the underlying httpx.AsyncClient connection pool.
            # Call the public close() method — never access _github directly.
            await self._analyzer.close()

        return context


class ASTParseStage(AbstractPipelineStage):
    """Stage 2 — Parses all fetched code files using the AST parser."""

    def __init__(self) -> None:
        from cortex.pipeline.infrastructure.ast_parser import ASTParser
        self._parser = ASTParser()

    async def _incremental_parse(self, context: PipelineContext) -> list:
        """Parse files, reusing cached results for unchanged files.

        Uses the IncrementalAnalyzer's persisted parsed-result cache: unchanged
        files (matching content hash) are reused, only changed/added files are
        re-parsed. The CPU-bound re-parse is offloaded to a worker thread so the
        event loop stays responsive. Any failure degrades to a full parse so the
        pipeline never fails just because the cache is unavailable.
        """
        import asyncio

        file_contents = context.file_contents

        async def _full_parse() -> list:
            files_to_parse = [
                (content, path) for path, content in sorted(file_contents.items())
            ]
            return await asyncio.to_thread(self._parser.parse_many, files_to_parse)

        try:
            from cortex.pipeline.infrastructure.incremental_analyzer import (
                IncrementalAnalyzer,
            )

            analyzer = IncrementalAnalyzer()
            await analyzer.ensure_table()

            # Offload the CPU-bound re-parse to a worker thread so the event
            # loop stays responsive. incremental_parse awaits this coroutine.
            def _parse_offloaded(files: list[tuple[str, str]]):
                return asyncio.to_thread(self._parser.parse_many, files)

            result = await analyzer.incremental_parse(
                context.repo_url, file_contents, _parse_offloaded
            )

            logger.info(
                "ast_incremental_parse",
                job_id=context.job.id,
                reused=len(result.reused_paths),
                reparsed=len(result.reparsed_paths),
                total=len(result.parsed_files),
            )
            return result.parsed_files
        except Exception as inc_err:
            logger.warning(
                "ast_incremental_parse_fallback",
                job_id=context.job.id,
                error=str(inc_err),
            )
            return await _full_parse()

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

            # Incremental, hash-based parse: reuse cached ParsedFile results for
            # unchanged files and re-parse ONLY changed/added files. Falls back
            # to a full parse if the incremental path is unavailable (Req 10.1,
            # 10.2, 10.4).
            context.parsed_files = await self._incremental_parse(context)

            successful = [p for p in context.parsed_files if not p.has_errors()]
            failed = [p for p in context.parsed_files if p.has_errors()]

            # Record coverage gaps for every file that failed to parse, and
            # capture preliminary file coverage. Reference counts are folded in
            # later by GraphBuildStage once the graph exists (Req 1.4, Req 6.1).
            from cortex.pipeline.infrastructure.coverage import compute_coverage
            context.coverage = compute_coverage(
                context.parsed_files, skipped_files=context.skipped_files
            )

            logger.info(
                "ast_parse_stage_completed",
                job_id=context.job.id,
                total=len(context.parsed_files),
                successful=len(successful),
                failed=len(failed),
                coverage_gaps=context.coverage.gap_count(),
                total_classes=sum(len(p.classes) for p in successful),
                total_functions=sum(len(p.all_functions()) for p in successful),
            )

        except Exception as e:
            context.mark_error(f"ASTParseStage failed: {str(e)}")

        return context


class VibeDetectStage(AbstractPipelineStage):
    """Stage 3 — Runs vibe code detection. Non-fatal."""

    def __init__(self) -> None:
        from cortex.pipeline.infrastructure.vibe_detector import VibeDetector
        self._detector = VibeDetector()

    async def execute(self, context: PipelineContext) -> PipelineContext:
        if not context.parsed_files:
            return context  # skip silently — not fatal

        try:
            context.vibe_report = self._detector.analyze(
                context.parsed_files, context.repo_url
            )
            logger.info(
                "vibe_detect_stage_completed",
                job_id=context.job.id,
                flags=len(context.vibe_report.flags),
                health_score=context.vibe_report.health_score,
            )
        except Exception as e:
            logger.warning(
                "vibe_detect_stage_failed",
                job_id=context.job.id,
                error=str(e),
            )

        return context


class GraphBuildStage(AbstractPipelineStage):
    """Stage 4 — Builds the knowledge graph from parsed files."""

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

            builder = GraphBuilder(job_id=context.job.id, repo_url=context.repo_url)
            graph_result = builder.build(context.parsed_files)

            context.graph_result = graph_result
            context.node_count = graph_result.node_count()
            context.edge_count = graph_result.edge_count()

            # Recompute coverage now that the graph exists so resolved vs.
            # unresolved reference counts are included alongside the parse-time
            # file coverage and gaps (Req 6.1).
            from cortex.pipeline.infrastructure.coverage import compute_coverage
            context.coverage = compute_coverage(
                context.parsed_files, graph_result, skipped_files=context.skipped_files
            )

            # Persist graph to SQLite using bulk inserts — one transaction
            # for all nodes, one for all edges. This replaces the previous
            # per-node/per-edge loop that issued thousands of round-trips.
            try:
                from cortex.graph.infrastructure.sqlite_repository import SQLiteGraphRepository
                from cortex.config import get_settings
                graph_repo = SQLiteGraphRepository(get_settings().database_url)
                await graph_repo.save_nodes_bulk(graph_result.nodes)
                await graph_repo.save_edges_bulk(graph_result.edges)
                # Do NOT call graph_repo._engine.dispose() here.
                # SQLiteGraphRepository now uses the shared get_engine() singleton;
                # disposing it would close the connection pool for every other
                # repository in the process.
                logger.info(
                    "graph_persisted_to_sqlite",
                    job_id=context.job.id,
                    nodes=context.node_count,
                    edges=context.edge_count,
                )
            except Exception as e:
                logger.error(
                    "graph_persist_failed",
                    job_id=context.job.id,
                    error=str(e),
                )
                context.mark_error(f"GraphBuildStage: failed to persist graph — {e}")
                return context

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
    """Stage 5 — Generates artifact content from the knowledge graph."""

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
                from cortex.pipeline.infrastructure.architecture_diagram_generator import (
                    ArchitectureDiagramGenerator,
                )
                content = ArchitectureDiagramGenerator().generate(graph_result, repo_name)
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "module_breakdown":
                content = markdown_gen.generate_module_breakdown(graph_result, repo_name)
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "learning_path":
                content = markdown_gen.generate_learning_path(graph_result, repo_name)
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "api_spec":
                content = markdown_gen.generate_api_spec(graph_result, repo_name)
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "interview_questions":
                content = markdown_gen.generate_interview_questions(graph_result, repo_name)
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "vibe_code_detection":
                from cortex.pipeline.infrastructure.code_quality_generator import (
                    CodeQualityGenerator,
                )
                content = CodeQualityGenerator().generate(
                    graph_result, repo_name, vibe_report=context.vibe_report
                )
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "folder_structure":
                content = markdown_gen.generate_module_breakdown(graph_result, repo_name)
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "engineering_report":
                from cortex.pipeline.infrastructure.engineering_report_generator import (
                    EngineeringReportGenerator,
                )
                content = EngineeringReportGenerator().generate(graph_result, repo_name)
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "database_schema":
                from cortex.pipeline.infrastructure.database_schema_generator import (
                    DatabaseSchemaGenerator,
                )
                schema_gen = DatabaseSchemaGenerator()
                content = schema_gen.generate(
                    context.parsed_files or [],
                    graph_result,
                    repo_name,
                )
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
