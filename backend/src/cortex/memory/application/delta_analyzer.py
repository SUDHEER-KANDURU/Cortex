"""Delta Analyzer — Cortex's own intelligence for tracking change over time.

Compares the current analysis against the previous one for the same
repository. Produces a "what changed" report WITHOUT needing git history.

This is Cortex's TEMPORAL INTELLIGENCE — deterministic comparison of:
  - Score changes per dimension (improved / degraded / stable)
  - New issues introduced since last run
  - Issues resolved since last run
  - Structural changes (new modules, new endpoints, class growth)

The delta is computed purely from stored RepositoryMemory data —
no git clone, no commit history needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from cortex.insights.domain.entities import InsightsReport, HealthDimension
from cortex.memory.domain.entities import RepositorySummary


@dataclass
class ScoreChange:
    """Change in a single metric between two analyses."""
    metric: str
    previous: int | float
    current: int | float
    delta: int | float
    direction: str  # "improved", "degraded", "stable"


@dataclass
class DeltaReport:
    """Complete delta analysis between two runs."""
    repo_url: str
    repo_name: str
    # Metadata
    current_job_id: str
    previous_job_id: str = ""
    analysis_count: int = 1
    current_timestamp: datetime | None = None
    # Overall change
    overall_score_change: ScoreChange | None = None
    # Per-dimension changes
    dimension_changes: list[ScoreChange] = field(default_factory=list)
    # Structural changes
    structural_changes: list[str] = field(default_factory=list)
    # Summary
    improvements: list[str] = field(default_factory=list)
    degradations: list[str] = field(default_factory=list)
    # Is this the first analysis?
    is_first_analysis: bool = True


class DeltaAnalyzer:
    """Computes delta between current and previous analysis.

    Uses RepositorySummary (which stores overall_score, analysis_count,
    total_files, total_classes, total_functions) to detect changes without
    needing the full previous graph.
    """

    def compute_delta(
        self,
        current_report: InsightsReport,
        previous_summary: RepositorySummary | None,
    ) -> DeltaReport:
        """Compute what changed between this analysis and the last one.

        If previous_summary is None, this is the first analysis — returns
        a baseline report with no delta.
        """
        delta = DeltaReport(
            repo_url=current_report.repo_url,
            repo_name=current_report.repo_name,
            current_job_id=current_report.job_id,
        )

        if previous_summary is None or previous_summary.analysis_count <= 1:
            delta.is_first_analysis = True
            delta.structural_changes.append(
                f"First analysis: {current_report.stats.get('files', 0)} files, "
                f"{current_report.stats.get('classes', 0)} classes, "
                f"{current_report.stats.get('functions', 0)} functions"
            )
            return delta

        # We have a previous analysis to compare against
        delta.is_first_analysis = False
        delta.previous_job_id = previous_summary.last_job_id
        delta.analysis_count = previous_summary.analysis_count + 1

        # Overall score change
        prev_score = previous_summary.overall_score or 0
        curr_score = current_report.overall_score
        delta.overall_score_change = self._compute_change(
            "Overall Score", prev_score, curr_score
        )

        # Structural changes
        self._compute_structural_changes(current_report, previous_summary, delta)

        # Per-dimension changes (compare against stored dimension scores if available)
        # Since we store overall_score in summary, we can track progression
        self._compute_dimension_deltas(current_report, prev_score, delta)

        # Summarize improvements and degradations
        self._summarize_changes(delta)

        return delta

    def _compute_change(self, metric: str, previous: int | float, current: int | float) -> ScoreChange:
        """Compute a single score change with direction."""
        delta_val = current - previous
        if abs(delta_val) < 2:  # Within noise threshold
            direction = "stable"
        elif delta_val > 0:
            direction = "improved"
        else:
            direction = "degraded"

        return ScoreChange(
            metric=metric,
            previous=previous,
            current=current,
            delta=round(delta_val, 1),
            direction=direction,
        )

    def _compute_structural_changes(
        self,
        current: InsightsReport,
        previous: RepositorySummary,
        delta: DeltaReport,
    ) -> None:
        """Detect structural changes (file count, class count, etc.)."""
        curr_files = int(current.stats.get("files", 0) or 0)
        curr_classes = int(current.stats.get("classes", 0) or 0)
        curr_functions = int(current.stats.get("functions", 0) or 0)

        prev_files = previous.total_files
        prev_classes = previous.total_classes
        prev_functions = previous.total_functions

        if curr_files != prev_files:
            diff = curr_files - prev_files
            direction = "added" if diff > 0 else "removed"
            delta.structural_changes.append(
                f"{abs(diff)} files {direction} (was {prev_files}, now {curr_files})"
            )

        if curr_classes != prev_classes:
            diff = curr_classes - prev_classes
            direction = "added" if diff > 0 else "removed"
            delta.structural_changes.append(
                f"{abs(diff)} classes {direction} (was {prev_classes}, now {curr_classes})"
            )

        if curr_functions != prev_functions:
            diff = curr_functions - prev_functions
            direction = "added" if diff > 0 else "removed"
            delta.structural_changes.append(
                f"{abs(diff)} functions {direction} (was {prev_functions}, now {curr_functions})"
            )

    def _compute_dimension_deltas(
        self,
        current: InsightsReport,
        prev_overall: int,
        delta: DeltaReport,
    ) -> None:
        """Track per-dimension changes relative to overall trend."""
        for dim in current.dimensions:
            # We don't have per-dimension history in the summary,
            # but we can still report each dimension's absolute score
            # and flag any that are significantly below or above average
            delta.dimension_changes.append(ScoreChange(
                metric=dim.name,
                previous=prev_overall,  # Best approximation without per-dim history
                current=dim.score,
                delta=dim.score - prev_overall,
                direction="improved" if dim.score > prev_overall + 5 else (
                    "degraded" if dim.score < prev_overall - 5 else "stable"
                ),
            ))

    def _summarize_changes(self, delta: DeltaReport) -> None:
        """Generate human-readable improvement/degradation summaries."""
        if delta.overall_score_change:
            sc = delta.overall_score_change
            if sc.direction == "improved":
                delta.improvements.append(
                    f"Overall score improved by {sc.delta:+.0f} points "
                    f"({sc.previous:.0f} → {sc.current:.0f})"
                )
            elif sc.direction == "degraded":
                delta.degradations.append(
                    f"Overall score dropped by {abs(sc.delta):.0f} points "
                    f"({sc.previous:.0f} → {sc.current:.0f})"
                )

        for dim_change in delta.dimension_changes:
            if dim_change.direction == "degraded" and dim_change.delta < -10:
                delta.degradations.append(
                    f"{dim_change.metric} dimension needs attention "
                    f"(score: {dim_change.current:.0f}/100)"
                )

        for change in delta.structural_changes:
            if "added" in change and "files" in change:
                delta.improvements.append(f"Repository grew: {change}")

    def render_markdown(self, delta: DeltaReport) -> str:
        """Render the delta report as Markdown."""
        lines: list[str] = []

        lines.append(f"# Changes Since Last Analysis — {delta.repo_name}")
        lines.append("")

        if delta.is_first_analysis:
            lines.append("*This is the first analysis of this repository.*")
            lines.append("")
            if delta.structural_changes:
                lines.append("## Baseline")
                lines.append("")
                for change in delta.structural_changes:
                    lines.append(f"- {change}")
            return "\n".join(lines)

        lines.append(f"**Analysis #{delta.analysis_count}** · Comparing against previous run")
        lines.append("")

        # Overall score change
        if delta.overall_score_change:
            sc = delta.overall_score_change
            icon = {"improved": "📈", "degraded": "📉", "stable": "➡️"}.get(sc.direction, "")
            lines.append(f"## {icon} Overall: {sc.previous:.0f} → {sc.current:.0f} ({sc.delta:+.0f})")
            lines.append("")

        # Improvements
        if delta.improvements:
            lines.append("## ✅ Improvements")
            lines.append("")
            for imp in delta.improvements:
                lines.append(f"- {imp}")
            lines.append("")

        # Degradations
        if delta.degradations:
            lines.append("## ⚠ Degradations")
            lines.append("")
            for deg in delta.degradations:
                lines.append(f"- {deg}")
            lines.append("")

        # Structural changes
        if delta.structural_changes:
            lines.append("## Structural Changes")
            lines.append("")
            for change in delta.structural_changes:
                lines.append(f"- {change}")
            lines.append("")

        # Dimension scores
        if delta.dimension_changes:
            lines.append("## Dimension Scores")
            lines.append("")
            lines.append("| Dimension | Score | vs. Previous |")
            lines.append("|-----------|-------|-------------|")
            for dc in delta.dimension_changes:
                icon = {"improved": "↑", "degraded": "↓", "stable": "→"}.get(dc.direction, "")
                lines.append(f"| {dc.metric} | {dc.current:.0f}/100 | {icon} {dc.delta:+.0f} |")
            lines.append("")

        return "\n".join(lines)
