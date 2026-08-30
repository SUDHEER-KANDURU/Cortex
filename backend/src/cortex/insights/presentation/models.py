"""Pydantic response models for the Insights API.

Exposes: confidence, coverage, evidence on every issue.
Backwards-compatible: all new fields have defaults.
"""

from __future__ import annotations

from typing import Any

from cortex.insights.domain.entities import (
    AnalysisCoverage,
    CodeIssue,
    EngineeringConcern,
    HealthDimension,
    InsightsReport,
    IssueCategory,
    IssueSeverity,
    MetricScore,
)
from pydantic import BaseModel


class AnalysisCoverageResponse(BaseModel):
    total_files_in_repo: int = 0
    source_files:        int = 0
    test_files:          int = 0
    generated_files:     int = 0
    vendor_files:        int = 0
    config_files:        int = 0
    unsupported_files:   int = 0
    analyzed_files:      int = 0
    skipped_files:       int = 0
    coverage_pct:        float = 0.0
    languages_detected:  list[str] = []

    @classmethod
    def from_coverage(cls, c: AnalysisCoverage) -> AnalysisCoverageResponse:
        return cls(**c.to_dict())


class MetricScoreResponse(BaseModel):
    label:       str
    score:       int
    raw_value:   float
    unit:        str
    description: str
    denominator: float = 0.0
    confidence:  float = 1.0

    @classmethod
    def from_metric(cls, m: MetricScore) -> MetricScoreResponse:
        return cls(
            label=m.label, score=m.score, raw_value=m.raw_value,
            unit=m.unit, description=m.description,
            denominator=m.denominator, confidence=m.confidence,
        )


class HealthDimensionResponse(BaseModel):
    name:        str
    score:       int
    grade:       str
    summary:     str
    confidence:  float = 1.0
    issue_count: int   = 0
    metrics:     list[MetricScoreResponse] = []

    @classmethod
    def from_dimension(cls, d: HealthDimension) -> HealthDimensionResponse:
        return cls(
            name=d.name, score=d.score, grade=d.grade,
            summary=d.summary, confidence=d.confidence,
            issue_count=d.issue_count,
            metrics=[MetricScoreResponse.from_metric(m) for m in d.metrics],
        )


class CodeIssueResponse(BaseModel):
    category:        IssueCategory
    severity:        IssueSeverity
    title:           str
    description:     str
    suggestion:      str       # = recommendation (backwards compat)
    recommendation:  str       # explicit field
    file_path:       str  = ""
    line:            int  = 0   # backwards compat = line_start
    line_start:      int  = 0
    line_end:        int  = 0
    affected_symbol: str  = ""
    evidence:        dict[str, Any] = {}
    confidence:      float = 1.0
    # ── Context-aware severity metadata (additive; safe defaults) ────────────
    architectural_role: str = "ordinary"
    context_factors:    list[str] = []
    signal:             str = ""

    @classmethod
    def from_issue(cls, i: CodeIssue) -> CodeIssueResponse:
        return cls(
            category=i.category, severity=i.severity,
            title=i.title, description=i.description,
            suggestion=i.recommendation,
            recommendation=i.recommendation,
            file_path=i.file_path,
            line=i.line_start, line_start=i.line_start, line_end=i.line_end,
            affected_symbol=i.affected_symbol,
            evidence=i.evidence,
            confidence=i.confidence,
            architectural_role=i.architectural_role,
            context_factors=list(i.context_factors),
            signal=i.signal,
        )


class EngineeringConcernResponse(BaseModel):
    """A coherent engineering concern backed by one or more issue signals.

    This is the primary, de-noised view: related signals on the same symbol
    (e.g. high complexity + long function + god function) are presented as ONE
    concern, with the individual signals kept as supporting evidence.
    """
    title:              str
    severity:           IssueSeverity
    category:           IssueCategory
    file_path:          str = ""
    affected_symbol:    str = ""
    architectural_role: str = "ordinary"
    summary:            str = ""
    recommendation:     str = ""
    context_factors:    list[str] = []
    confidence:         float = 1.0
    signal_count:       int = 0
    signals:            list[CodeIssueResponse] = []

    @classmethod
    def from_concern(cls, c: EngineeringConcern) -> EngineeringConcernResponse:
        return cls(
            title=c.title, severity=c.severity, category=c.category,
            file_path=c.file_path, affected_symbol=c.affected_symbol,
            architectural_role=c.architectural_role,
            summary=c.summary, recommendation=c.recommendation,
            context_factors=list(c.context_factors),
            confidence=c.confidence, signal_count=c.signal_count,
            signals=[CodeIssueResponse.from_issue(s) for s in c.signals],
        )


class InsightsReportResponse(BaseModel):
    job_id:             str
    repo_url:           str
    repo_name:          str
    overall_score:      int
    overall_grade:      str
    overall_confidence: float = 1.0
    dimensions:         list[HealthDimensionResponse] = []
    issues:             list[CodeIssueResponse]       = []
    concerns:           list[EngineeringConcernResponse] = []
    stats:              dict = {}
    coverage:           AnalysisCoverageResponse = AnalysisCoverageResponse()

    @classmethod
    def from_report(cls, r: InsightsReport) -> InsightsReportResponse:
        return cls(
            job_id=r.job_id, repo_url=r.repo_url, repo_name=r.repo_name,
            overall_score=r.overall_score, overall_grade=r.overall_grade,
            overall_confidence=r.overall_confidence,
            dimensions=[HealthDimensionResponse.from_dimension(d) for d in r.dimensions],
            issues=[CodeIssueResponse.from_issue(i) for i in r.issues],
            concerns=[EngineeringConcernResponse.from_concern(c) for c in r.concerns],
            stats=r.stats,
            coverage=AnalysisCoverageResponse.from_coverage(r.coverage),
        )
