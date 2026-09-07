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
        context.parsed_files = [
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

    assert updated_context.vibe_report is not None
    assert updated_context.vibe_report.repo_url == "https://github.com/example/repo"


# ── Regression: hardcoded-values detector (foundation stabilization) ──────────
# The previous _detect_hardcoded_values implementation wrapped a function-name
# heuristic in a loop over 6 regex patterns while ignoring the patterns. It was
# unreachable (guarded by file_contents_available(), which is always False) and,
# had it run, would have emitted up to 6 DUPLICATE flags for any function whose
# name contained a secret-like keyword. These tests lock in the intended
# behaviour: because raw file content is not stored, the detector emits NO
# HARDCODED_VALUES flags and never false-flags a function by its name alone.

from cortex.pipeline.infrastructure.vibe_detector import VibeDetector, VibePattern


def _hardcoded_flags(report):
    return [f for f in report.flags if f.pattern == VibePattern.HARDCODED_VALUES]


def test_hardcoded_values_emits_no_flags_when_content_unavailable() -> None:
    """With no raw content available, the detector must not emit any
    HARDCODED_VALUES flags (it is a documented no-op today)."""
    parsed = ParsedFile(
        path="secrets.py",
        language=Language.PYTHON,
        functions=[
            ParsedFunction(
                name="get_password",  # secret-like name — must NOT be flagged
                file_path="secrets.py",
                line_start=1,
                line_end=5,
            ),
            ParsedFunction(
                name="load_api_key",  # secret-like name — must NOT be flagged
                file_path="secrets.py",
                line_start=6,
                line_end=10,
            ),
        ],
        line_count=10,
    )

    report = VibeDetector().analyze([parsed], "https://github.com/example/repo")

    assert _hardcoded_flags(report) == [], (
        "hardcoded-values detection must be a no-op while raw file content is "
        "unavailable; function names must not trigger secret flags"
    )


def test_hardcoded_values_no_duplicate_flags_for_secret_named_function() -> None:
    """Explicitly guards against the old duplicate-flag bug: a single
    secret-named function must never yield multiple HARDCODED_VALUES flags."""
    parsed = ParsedFile(
        path="token_store.py",
        language=Language.PYTHON,
        functions=[
            ParsedFunction(
                name="rotate_secret_token",
                file_path="token_store.py",
                line_start=1,
                line_end=8,
            ),
        ],
        line_count=8,
    )

    report = VibeDetector().analyze([parsed], "https://github.com/example/repo")

    assert len(_hardcoded_flags(report)) <= 1, (
        "must never emit duplicate HARDCODED_VALUES flags for one function"
    )
