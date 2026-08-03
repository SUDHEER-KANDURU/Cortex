"""Insights domain entities — engineering health metrics computed from graph data."""

from dataclasses import dataclass, field
from enum import Enum


class IssueSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    COMPLEXITY = "complexity"
    COUPLING = "coupling"
    DUPLICATION = "duplication"
    NAMING = "naming"
    DOCUMENTATION = "documentation"
    ERROR_HANDLING = "error_handling"
    ARCHITECTURE = "architecture"
    SIZE = "size"


@dataclass
class CodeIssue:
    """A single detected engineering issue."""
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    suggestion: str
    file_path: str = ""
    line: int = 0
    affected_symbol: str = ""


@dataclass
class MetricScore:
    """A single scored metric with label and context."""
    label: str
    score: int          # 0–100
    raw_value: float    # the underlying measurement
    unit: str           # "classes", "lines", "ratio", etc.
    description: str


@dataclass
class HealthDimension:
    """One dimension of the engineering health report."""
    name: str
    score: int          # 0–100
    grade: str          # A / B / C / D / F
    summary: str
    metrics: list[MetricScore] = field(default_factory=list)

    @staticmethod
    def grade_from_score(score: int) -> str:
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 65: return "C"
        if score >= 50: return "D"
        return "F"


@dataclass
class InsightsReport:
    """Complete engineering health report for a repository."""
    job_id: str
    repo_url: str
    repo_name: str
    overall_score: int
    overall_grade: str
    dimensions: list[HealthDimension] = field(default_factory=list)
    issues: list[CodeIssue] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def high_issues(self) -> list[CodeIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.HIGH]

    def medium_issues(self) -> list[CodeIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.MEDIUM]

    def issues_by_category(self, category: IssueCategory) -> list[CodeIssue]:
        return [i for i in self.issues if i.category == category]
