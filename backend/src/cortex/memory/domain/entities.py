"""Repository Memory domain entities — zero dependencies on frameworks,
databases, or HTTP.

A RepositorySummary is durable, cross-job knowledge about a repository
(keyed by repo_url, not job_id) that accumulates across repeated analyses.
Unlike a Job or Artifact — which describe a single pipeline run — a
summary is meant to answer "what do we already know about this repo?"
before a fresh analysis even starts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RepositoryFact:
    """One durable, searchable fact extracted from a completed analysis.

    Facts are the unit of semantic search — short, self-contained
    statements like "UserManager is a god class with 12 methods in
    core/a.py" rather than raw graph dumps. Each fact remembers which
    job produced it so results can be traced back to their source.
    """
    id: str
    repo_url: str
    job_id: str
    category: str  # "architecture" | "complexity" | "coupling" | "overview" | "issue"
    text: str
    source_symbol: str | None = None
    source_file: str | None = None
    created_at: datetime = field(default_factory=_now)


@dataclass
class RepositorySummary:
    """Accumulated knowledge about one repository across all its analyses.

    One RepositorySummary per repo_url. Each new completed job refreshes
    the headline stats and appends new facts, so repeat analyses of the
    same repo build up a history instead of starting from zero.
    """
    id: str
    repo_url: str
    repo_name: str
    last_job_id: str
    analysis_count: int = 1
    overall_score: int | None = None
    overall_grade: str | None = None
    dominant_language: str | None = None
    total_files: int = 0
    total_classes: int = 0
    total_functions: int = 0
    headline: str = ""
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @staticmethod
    def new(
        repo_url: str,
        repo_name: str,
        job_id: str,
    ) -> "RepositorySummary":
        return RepositorySummary(
            id=_uuid(),
            repo_url=repo_url,
            repo_name=repo_name,
            last_job_id=job_id,
        )

    def refresh(
        self,
        job_id: str,
        overall_score: int,
        overall_grade: str,
        dominant_language: str | None,
        total_files: int,
        total_classes: int,
        total_functions: int,
        headline: str,
    ) -> None:
        """Update headline stats from a newly completed analysis."""
        self.last_job_id = job_id
        self.analysis_count += 1
        self.overall_score = overall_score
        self.overall_grade = overall_grade
        self.dominant_language = dominant_language
        self.total_files = total_files
        self.total_classes = total_classes
        self.total_functions = total_functions
        self.headline = headline
        self.updated_at = _now()s