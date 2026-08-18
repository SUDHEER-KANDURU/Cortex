"""Repository memory summarizer — turns a completed analysis into
durable, searchable knowledge.

This is deliberately NOT a raw dump of the graph or the full insights
report. Repository Memory exists so that the next time someone asks
"what do we know about this repo?" (via chat, via a new job, via the
memory API), the answer comes from a handful of durable facts instead
of re-querying the entire graph. Facts are short, self-contained, and
traceable back to the job that produced them.
"""

from cortex.insights.domain.entities import InsightsReport
from cortex.memory.domain.entities import RepositorySummary, RepositoryFact


class RepositoryMemorySummarizer:
    """Extracts a RepositorySummary and a list of RepositoryFacts from
    a completed InsightsReport. Pure function of its inputs — no I/O."""

    MAX_ISSUE_FACTS = 8

    def summarize(
        self,
        report: InsightsReport,
        existing_summary: RepositorySummary | None,
    ) -> tuple[RepositorySummary, list[RepositoryFact]]:
        """Build (or refresh) a RepositorySummary and extract facts from
        this job's report. If existing_summary is provided, it is
        refreshed in place rather than replaced, so analysis_count and
        history accumulate across repeat runs of the same repo."""

        headline = self._build_headline(report)

        if existing_summary is not None:
            summary = existing_summary
            summary.refresh(
                job_id=report.job_id,
                overall_score=report.overall_score,
                overall_grade=report.overall_grade,
                dominant_language=report.stats.get("dominant_language"),
                total_files=int(report.stats.get("files", 0) or 0),
                total_classes=int(report.stats.get("classes", 0) or 0),
                total_functions=int(report.stats.get("functions", 0) or 0),
                headline=headline,
            )
        else:
            summary = RepositorySummary.new(
                repo_url=report.repo_url,
                repo_name=report.repo_name,
                job_id=report.job_id,
            )
            summary.overall_score = report.overall_score
            summary.overall_grade = report.overall_grade
            summary.dominant_language = report.stats.get("dominant_language")
            summary.total_files = int(report.stats.get("files", 0) or 0)
            summary.total_classes = int(report.stats.get("classes", 0) or 0)
            summary.total_functions = int(report.stats.get("functions", 0) or 0)
            summary.headline = headline

        facts = self._extract_facts(report)
        return summary, facts

    def _build_headline(self, report: InsightsReport) -> str:
        """One-sentence, human-readable summary of the whole report —
        the first thing shown when someone asks about this repo."""
        top_dim = min(report.dimensions, key=lambda d: d.score, default=None)
        weak_spot = f", weakest dimension is {top_dim.name} ({top_dim.score}/100)" if top_dim else ""
        return (
            f"{report.repo_name} scored {report.overall_score}/100 "
            f"({report.overall_grade}) across {len(report.dimensions)} dimensions "
            f"with {len(report.issues)} issues found{weak_spot}."
        )

    def _extract_facts(self, report: InsightsReport) -> list[RepositoryFact]:
        facts: list[RepositoryFact] = []

        # Overview fact — always recorded, one per job
        facts.append(
            RepositoryFact(
                id=self._fact_id(),
                repo_url=report.repo_url,
                job_id=report.job_id,
                category="overview",
                text=self._build_headline(report),
            )
        )

        # One fact per dimension — durable, comparable across jobs
        for dim in report.dimensions:
            facts.append(
                RepositoryFact(
                    id=self._fact_id(),
                    repo_url=report.repo_url,
                    job_id=report.job_id,
                    category=dim.name.lower().replace(" ", "_"),
                    text=f"{dim.name}: {dim.score}/100 ({dim.grade}) — {dim.summary}",
                )
            )

        # High/critical issues become individually searchable facts —
        # these are what someone is most likely to search for later
        # ("does this repo have a god class?", "any circular deps?")
        high_priority = report.high_issues()[: self.MAX_ISSUE_FACTS]
        for issue in high_priority:
            location = f" in {issue.file_path}" if issue.file_path else ""
            symbol = f" (`{issue.affected_symbol}`)" if issue.affected_symbol else ""
            facts.append(
                RepositoryFact(
                    id=self._fact_id(),
                    repo_url=report.repo_url,
                    job_id=report.job_id,
                    category=f"issue_{issue.category.value}",
                    text=f"{issue.title}{symbol}{location}: {issue.description}",
                    source_symbol=issue.affected_symbol or None,
                    source_file=issue.file_path or None,
                )
            )

        return facts

    def _fact_id(self) -> str:
        import uuid
        return str(uuid.uuid4())