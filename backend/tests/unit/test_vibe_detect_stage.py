import asyncio

from cortex.jobs.domain.entities import ArtifactType, Job
from cortex.pipeline.application.orchestrator import PipelineContext
from cortex.pipeline.infrastructure.ast_parser import Language, ParsedFile, ParsedFunction
from cortex.pipeline.infrastructure.stages import VibeDetectStage


def test_vibe_detect_stage_adds_report_to_context() -> None:
    async def run() -> PipelineContext:
        job = Job(
            repo_url="https://github.com/example/repo",
            artifact_type=ArtifactType.FOLDER_STRUCTURE,
        )
        context = PipelineContext(
            job=job,
            repo_url=job.repo_url,
            artifact_type=job.artifact_type,
        )
        context._parsed_files = [
            ParsedFile(
                path="example.py",
                language=Language.PYTHON,
                functions=[
                    ParsedFunction(
                        name="run",
                        file_path="example.py",
                        line_start=1,
                        line_end=20,
                    )
                ],
                line_count=20,
            )
        ]

        return await VibeDetectStage().execute(context)

    updated_context = asyncio.run(run())

    assert getattr(updated_context, "_vibe_report", None) is not None
    assert updated_context._vibe_report.repo_url == "https://github.com/example/repo"
