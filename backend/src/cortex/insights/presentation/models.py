"""Pydantic response models for the Insights API."""

from pydantic import BaseModel
from cortex.insights.domain.entities import (
    CodeIssue,
    HealthDimension,
    InsightsReport,
    IssueSeverity,
    IssueCategory,
    MetricScore,
)


class MetricScoreResponse(BaseModel):
    label: str
    score: int
    raw_value: float
    unit: str
    description: str

    @classmethod
    def from_metric(cls, m: MetricScore) -> "MetricScoreResponse":
        return cls(
            label=m.label,
            score=m.score,
            raw_value=m.raw_value,
            unit=m.unit,
            description=m.description,
        )


class HealthDimensionResponse(BaseModel):
    name: str
    score: int
    grade: str
    summary: str
    metrics: list[MetricScoreResponse]

    @classmethod
    def from_dimension(cls, d: HealthDimension) -> "HealthDimensionResponse":
        return cls(
            name=d.name,
            score=d.score,
            grade=d.grade,
            summary=d.summary,
            metrics=[MetricScoreResponse.from_metric(m) for m in d.metrics],
        )


class CodeIssueResponse(BaseModel):
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    suggestion: str
    file_path: str
    line: int
    affected_symbol: str

    @classmethod
    def from_issue(cls, i: CodeIssue) -> "CodeIssueResponse":
        return cls(
            category=i.category,
            severity=i.severity,
            title=i.title,
            description=i.description,
            suggestion=i.suggestion,
            file_path=i.file_path,
            line=i.line,
            affected_symbol=i.affected_symbol,
        )


class InsightsReportResponse(BaseModel):
    job_id: str
    repo_url: str
    repo_name: str
    overall_score: int
    overall_grade: str
    dimensions: list[HealthDimensionResponse]
    issues: list[CodeIssueResponse]
    stats: dict

    @classmethod
    def from_report(cls, r: InsightsReport) -> "InsightsReportResponse":
        return cls(
            job_id=r.job_id,
            repo_url=r.repo_url,
            repo_name=r.repo_name,
            overall_score=r.overall_score,
            overall_grade=r.overall_grade,
            dimensions=[HealthDimensionResponse.from_dimension(d) for d in r.dimensions],
            issues=[CodeIssueResponse.from_issue(i) for i in r.issues],
            stats=r.stats,
        )
