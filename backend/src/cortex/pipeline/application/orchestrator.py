"""Pipeline orchestrator — coordinates the full repo analysis workflow.
This is the brain that connects GitHub fetching, graph building,
and artifact generation into one end-to-end pipeline."""

from dataclasses import dataclass
from cortex.jobs.domain.entities import Job, JobStatus, ArtifactType
from cortex.pipeline.domain.interfaces import AbstractPipelineStage
from shared.exceptions import CortexError
import structlog

logger = structlog.get_logger()


class PipelineError(CortexError):
    """Raised when any pipeline stage fails."""


@dataclass
class PipelineContext:
    """Carries state through every stage of the pipeline.
    Each stage reads from and writes to this context."""

    job: Job
    repo_url: str
    artifact_type: ArtifactType

    # Populated by GitHubFetchStage
    file_tree: list[dict] = None
    file_contents: dict[str, str] = None

    # Populated by GraphBuildStage
    node_count: int = 0
    edge_count: int = 0

    # Populated by ArtifactGenerateStage
    artifact_id: str | None = None
    artifact_content: str | None = None

    # Error tracking
    error: str | None = None

    def __post_init__(self) -> None:
        self.file_tree = self.file_tree or []
        self.file_contents = self.file_contents or {}

    def has_error(self) -> bool:
        return self.error is not None

    def mark_error(self, message: str) -> None:
        self.error = message
        logger.error(
            "pipeline_context_error",
            job_id=self.job.id,
            error=message,
        )


class PipelineOrchestrator:
    """Runs each pipeline stage in sequence.
    If any stage fails, the pipeline stops and marks the job failed.
    Stages are injected — the orchestrator never creates them directly."""

    def __init__(self, stages: list[AbstractPipelineStage]) -> None:
        self._stages = stages

    async def run(self, job: Job) -> PipelineContext:
        """Execute all pipeline stages for a job.
        Returns the final context with all results populated."""

        context = PipelineContext(
            job=job,
            repo_url=job.repo_url,
            artifact_type=job.artifact_type,
        )

        logger.info(
            "pipeline_started",
            job_id=job.id,
            repo_url=job.repo_url,
            artifact_type=job.artifact_type.value,
            stage_count=len(self._stages),
        )

        for stage in self._stages:
            stage_name = stage.__class__.__name__

            logger.info(
                "pipeline_stage_started",
                job_id=job.id,
                stage=stage_name,
            )

            try:
                context = await stage.execute(context)

                if context.has_error():
                    logger.error(
                        "pipeline_stage_failed",
                        job_id=job.id,
                        stage=stage_name,
                        error=context.error,
                    )
                    raise PipelineError(
                        f"Stage {stage_name} failed: {context.error}"
                    )

                logger.info(
                    "pipeline_stage_completed",
                    job_id=job.id,
                    stage=stage_name,
                )

            except PipelineError:
                raise
            except Exception as e:
                error_msg = f"Unexpected error in {stage_name}: {str(e)}"
                context.mark_error(error_msg)
                raise PipelineError(error_msg) from e

        logger.info(
            "pipeline_completed",
            job_id=job.id,
            node_count=context.node_count,
            edge_count=context.edge_count,
            artifact_id=context.artifact_id,
        )

        return context


def build_default_pipeline() -> "PipelineOrchestrator":
    """Build the default pipeline with all four stages in order.
    Import here to avoid circular imports."""

    from cortex.pipeline.infrastructure.stages import (
        GitHubFetchStage,
        ASTParseStage,
        GraphBuildStage,
        ArtifactGenerateStage,
    )
    from cortex.artifacts.infrastructure.dependencies import (
        artifact_repository,
    )
    from cortex.artifacts.application.use_cases import ArtifactService

    artifact_service = ArtifactService(artifact_repository)

    return PipelineOrchestrator(
        stages=[
            GitHubFetchStage(),
            ASTParseStage(),
            GraphBuildStage(),
            ArtifactGenerateStage(artifact_service),
        ]
    )