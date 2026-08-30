"""Insights domain entities — engineering health metrics computed from graph data.

Every issue carries evidence.
Every score carries confidence.
Every analysis carries coverage.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class IssueCategory(str, Enum):
    COMPLEXITY    = "complexity"
    COUPLING      = "coupling"
    DUPLICATION   = "duplication"
    NAMING        = "naming"
    DOCUMENTATION = "documentation"
    ERROR_HANDLING= "error_handling"
    ARCHITECTURE  = "architecture"
    SIZE          = "size"


@dataclass
class CodeIssue:
    """A single detected engineering issue with full evidence trail."""

    # Identity
    category:  IssueCategory
    severity:  IssueSeverity
    title:     str
    description: str
    recommendation: str

    # Location
    file_path:       str  = ""
    line_start:      int  = 0
    line_end:        int  = 0
    affected_symbol: str  = ""

    # Evidence — every issue must show its work
    evidence: dict[str, Any] = field(default_factory=dict)

    # Confidence 0–1 — how certain we are this is a real issue
    confidence: float = 1.0

    # ── Context-aware severity metadata (additive; safe defaults) ────────────
    # The architectural role of the affected file (router/orchestrator/...).
    architectural_role: str = "ordinary"
    # Human-readable reasons the base severity was adjusted by context.
    context_factors: list[str] = field(default_factory=list)
    # Machine key for grouping related signals into one concern
    # (usually the detector name: "fanout", "god_class", "cyclomatic", ...).
    signal: str = ""

    # Preserved for API compat
    @property
    def line(self) -> int:
        return self.line_start

    @property
    def suggestion(self) -> str:
        return self.recommendation


@dataclass
class MetricScore:
    """A single scored metric with label, value, and denominator."""
    label:       str
    score:       int    # 0–100
    raw_value:   float  # the underlying measurement
    unit:        str    # "classes", "lines", "ratio", "%" etc.
    description: str
    denominator: float = 0.0  # what raw_value is divided by (for normalization)
    confidence:  float = 1.0


@dataclass
class HealthDimension:
    """One dimension of the engineering health report."""
    name:       str
    score:      int    # 0–100
    grade:      str    # A / B / C / D / F
    summary:    str
    confidence: float = 1.0   # 0–1: how reliable is this dimension's data
    metrics:    list[MetricScore] = field(default_factory=list)
    issue_count: int = 0

    @staticmethod
    def grade_from_score(score: int) -> str:
        if score >= 90: return "A"
        if score >= 80: return "B"
        if score >= 65: return "C"
        if score >= 50: return "D"
        return "F"


@dataclass
class AnalysisCoverage:
    """Reports how complete the analysis was."""
    total_files_in_repo:  int   = 0
    source_files:         int   = 0
    test_files:           int   = 0
    generated_files:      int   = 0
    vendor_files:         int   = 0
    config_files:         int   = 0
    unsupported_files:    int   = 0
    analyzed_files:       int   = 0
    skipped_files:        int   = 0
    coverage_pct:         float = 0.0   # analyzed / source_files
    languages_detected:   list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_files_in_repo":  self.total_files_in_repo,
            "source_files":         self.source_files,
            "test_files":           self.test_files,
            "generated_files":      self.generated_files,
            "vendor_files":         self.vendor_files,
            "config_files":         self.config_files,
            "unsupported_files":    self.unsupported_files,
            "analyzed_files":       self.analyzed_files,
            "skipped_files":        self.skipped_files,
            "coverage_pct":         round(self.coverage_pct, 4),
            "languages_detected":   self.languages_detected,
        }


@dataclass
class EngineeringConcern:
    """One coherent engineering concern, backed by one or more signals.

    A single symbol that trips cyclomatic complexity, long-function, and
    god-function detectors is *one* engineering concern ("this function does
    too much"), not three independent problems. This groups the underlying
    `CodeIssue` signals so the user sees the concern first and the supporting
    metrics as evidence — without ever discarding the individual signals.
    """

    title:           str
    severity:        IssueSeverity
    category:        IssueCategory
    file_path:       str = ""
    affected_symbol: str = ""
    architectural_role: str = "ordinary"
    # Why it matters / impact / recommendation — synthesised from the signals.
    summary:         str = ""
    recommendation:  str = ""
    # The individual detector signals that make up this concern (evidence kept).
    signals:         list[CodeIssue] = field(default_factory=list)
    context_factors: list[str] = field(default_factory=list)
    confidence:      float = 1.0

    @property
    def signal_count(self) -> int:
        return len(self.signals)


@dataclass
class InsightsReport:
    """Complete engineering health report for a repository."""
    job_id:         str
    repo_url:       str
    repo_name:      str
    overall_score:  int
    overall_grade:  str
    overall_confidence: float = 1.0
    dimensions:     list[HealthDimension] = field(default_factory=list)
    issues:         list[CodeIssue]       = field(default_factory=list)
    concerns:       list[EngineeringConcern] = field(default_factory=list)
    stats:          dict                  = field(default_factory=dict)
    coverage:       AnalysisCoverage      = field(default_factory=AnalysisCoverage)

    def high_issues(self) -> list[CodeIssue]:
        return [i for i in self.issues if i.severity in (IssueSeverity.HIGH, IssueSeverity.CRITICAL)]

    def medium_issues(self) -> list[CodeIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.MEDIUM]

    def issues_by_category(self, category: IssueCategory) -> list[CodeIssue]:
        return [i for i in self.issues if i.category == category]
