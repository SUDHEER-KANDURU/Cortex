"""GitHub analyzer — high-level wrapper combining fetch, parse, detect.
Makes the pipeline stages cleaner by hiding the coordination logic."""

from dataclasses import dataclass, field
from cortex.pipeline.infrastructure.github_client import (
    GitHubClient,
    GitHubFile,
    MAX_ANALYSIS_FILES,
)
from cortex.pipeline.infrastructure.ast_parser import (
    ASTParser,
    ParsedFile,
)
from cortex.pipeline.infrastructure.vibe_detector import (
    VibeDetector,
    VibeReport,
)
import structlog

logger = structlog.get_logger()


@dataclass
class AnalysisResult:
    """Complete analysis result for a repository."""
    repo_url: str
    owner: str
    repo_name: str
    language: str | None
    stars: int
    fetched_files: list[GitHubFile] = field(default_factory=list)
    parsed_files: list[ParsedFile] = field(default_factory=list)
    vibe_report: VibeReport | None = None
    # Candidate code files that exceeded the analysis cap and were not fetched.
    # Recorded as coverage gaps so Coverage reflects partial analysis (Req 10.3).
    skipped_files: list[str] = field(default_factory=list)

    def code_file_count(self) -> int:
        return len(self.fetched_files)

    def parsed_file_count(self) -> int:
        return len(
            [f for f in self.parsed_files if not f.has_errors()]
        )

    def total_classes(self) -> int:
        return sum(
            len(f.classes)
            for f in self.parsed_files
            if not f.has_errors()
        )

    def total_functions(self) -> int:
        return sum(
            len(f.all_functions())
            for f in self.parsed_files
            if not f.has_errors()
        )

    def summary(self) -> dict:
        return {
            "repo": f"{self.owner}/{self.repo_name}",
            "language": self.language,
            "stars": self.stars,
            "files_fetched": self.code_file_count(),
            "files_parsed": self.parsed_file_count(),
            "total_classes": self.total_classes(),
            "total_functions": self.total_functions(),
            "vibe_flags": (
                len(self.vibe_report.flags)
                if self.vibe_report
                else 0
            ),
            "health_score": (
                self.vibe_report.health_score
                if self.vibe_report
                else 100
            ),
        }


class GitHubAnalyzer:
    """Orchestrates fetching, parsing, and vibe detection.

    Usage:
        analyzer = GitHubAnalyzer()
        result = await analyzer.analyze(
            "https://github.com/SUDHEER-KANDURU/DoseBuddy"
        )
        print(result.summary())
    """

    def __init__(self) -> None:
        self._github = GitHubClient()
        self._parser = ASTParser()
        self._detector = VibeDetector()

    async def close(self) -> None:
        """Close the underlying httpx.AsyncClient connection pool.

        Must be called when the analyzer is no longer needed to prevent
        connection-pool leaks. GitHubFetchStage calls this in its
        finally block.
        """
        await self._github.close()

    async def analyze(
        self,
        repo_url: str,
        max_files: int = MAX_ANALYSIS_FILES,
        run_vibe_detection: bool = True,
    ) -> AnalysisResult:
        """Run full analysis on a repository.

        Steps:
        1. Fetch repo metadata and file tree
        2. Download code files
        3. Parse each file with AST parser
        4. Run vibe detection on parsed files
        """
        owner, repo_name = self._github.parse_repo_url(repo_url)

        logger.info(
            "github_analyzer_started",
            owner=owner,
            repo=repo_name,
        )

        # Fetch repo info
        repo_info = await self._github.get_repo_info(owner, repo_name)

        result = AnalysisResult(
            repo_url=repo_url,
            owner=owner,
            repo_name=repo_name,
            language=repo_info.language,
            stars=repo_info.stars,
        )

        # Fetch code files
        result.fetched_files = await self._github.get_code_files(
            owner, repo_name, max_files=max_files
        )
        result.skipped_files = list(self._github.last_skipped_files)

        logger.info(
            "github_analyzer_files_fetched",
            count=len(result.fetched_files),
            skipped=len(result.skipped_files),
        )

        # Parse each file
        files_to_parse = [
            (f.content, f.path)
            for f in result.fetched_files
        ]
        result.parsed_files = self._parser.parse_many(files_to_parse)

        logger.info(
            "github_analyzer_files_parsed",
            total=len(result.parsed_files),
            successful=result.parsed_file_count(),
            classes=result.total_classes(),
            functions=result.total_functions(),
        )

        # Run vibe detection
        if run_vibe_detection and result.parsed_files:
            result.vibe_report = self._detector.analyze(
                result.parsed_files,
                repo_url,
            )
            logger.info(
                "github_analyzer_vibe_complete",
                flags=len(result.vibe_report.flags),
                health_score=result.vibe_report.health_score,
            )

        logger.info(
            "github_analyzer_complete",
            **result.summary(),
        )

        return result

    async def fetch(
        self,
        repo_url: str,
        max_files: int = MAX_ANALYSIS_FILES,
    ) -> AnalysisResult:
        """Fetch repo metadata and file contents only — no parse, no vibe.

        Used by GitHubFetchStage so that ASTParseStage and
        VibeDetectStage remain separate, single-purpose pipeline stages.
        Populates: result.fetched_files (and repo metadata fields).
        """
        owner, repo_name = self._github.parse_repo_url(repo_url)

        logger.info(
            "github_analyzer_fetch_started",
            owner=owner,
            repo=repo_name,
        )

        repo_info = await self._github.get_repo_info(owner, repo_name)

        result = AnalysisResult(
            repo_url=repo_url,
            owner=owner,
            repo_name=repo_name,
            language=repo_info.language,
            stars=repo_info.stars,
        )

        result.fetched_files = await self._github.get_code_files(
            owner, repo_name, max_files=max_files
        )
        result.skipped_files = list(self._github.last_skipped_files)

        logger.info(
            "github_analyzer_fetch_completed",
            owner=owner,
            repo=repo_name,
            files=len(result.fetched_files),
            skipped=len(result.skipped_files),
        )

        return result