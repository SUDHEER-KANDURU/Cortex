"""Group related issue signals into coherent engineering concerns.

The problem this solves: one oversized, over-complex function or file
trips several detectors at once (cyclomatic, long-function, god-function,
oversized-file, god-class). Reported as separate issues, that is five
scary-looking HIGH labels for what a human reads as *one* concern:
"this thing does too much."

Grouping keeps every individual `CodeIssue` (evidence is never discarded)
but presents them under one `EngineeringConcern` whose severity is the
strongest of its signals. Only signals that describe the SAME underlying
concern on the SAME symbol are merged — unrelated problems stay separate.

Deterministic, dependency-free, no NIM.
"""

from __future__ import annotations

from collections import defaultdict

from cortex.insights.domain.entities import (
    CodeIssue,
    EngineeringConcern,
    IssueCategory,
)
from cortex.insights.domain.severity import max_severity, severity_rank

# Signals that describe "this unit does too much / is too big" — these
# co-occur on the same symbol and represent one concern, not many.
_SIZE_COMPLEXITY_SIGNALS = {
    "cyclomatic", "nesting", "god_function", "large_function",
    "god_class", "large_class", "oversized_file", "large_file",
    "too_many_params",
}


def _concern_key(issue: CodeIssue) -> tuple[str, str, str]:
    """Group by (category-family, file, symbol).

    Size and complexity signals share a family so a function's CC + length
    + god-function signals collapse into one concern. Other categories
    (coupling, architecture, docs, naming) group only within their own
    category on the same symbol.
    """
    if issue.signal in _SIZE_COMPLEXITY_SIGNALS or issue.category in (
        IssueCategory.COMPLEXITY,
        IssueCategory.SIZE,
    ):
        family = "size_complexity"
    else:
        family = issue.category.value
    return (family, issue.file_path, issue.affected_symbol)


def _title_for(family: str, primary: CodeIssue, n_signals: int) -> str:
    """A concern-level title framed as an engineering concern, not a metric."""
    if n_signals == 1:
        return primary.title
    if family == "size_complexity":
        sym = primary.affected_symbol or "This unit"
        return f"{sym} is doing too much"
    return primary.title


def group_into_concerns(issues: list[CodeIssue]) -> list[EngineeringConcern]:
    """Collapse related issue signals into engineering concerns.

    The strongest signal becomes the concern's primary framing; all signals
    are retained as evidence. Concern severity = max signal severity.
    """
    buckets: dict[tuple[str, str, str], list[CodeIssue]] = defaultdict(list)
    for i in issues:
        buckets[_concern_key(i)].append(i)

    concerns: list[EngineeringConcern] = []
    for (family, _file, _sym), group in buckets.items():
        # Primary = highest severity, then highest confidence, stable.
        primary = max(
            group,
            key=lambda i: (severity_rank(i.severity), i.confidence),
        )
        sev = primary.severity
        for i in group:
            sev = max_severity(sev, i.severity)

        factors: list[str] = []
        for i in group:
            for f in i.context_factors:
                if f not in factors:
                    factors.append(f)

        # Merge evidence signal names for the summary.
        signal_titles = []
        for i in sorted(group, key=lambda x: -severity_rank(x.severity)):
            if i.title not in signal_titles:
                signal_titles.append(i.title)

        if len(group) > 1:
            summary = (
                f"{len(group)} reinforcing signals point to one concern: "
                + "; ".join(signal_titles[:4])
                + (primary.description and f". {primary.description}" or "")
            )
        else:
            summary = primary.description

        concerns.append(EngineeringConcern(
            title=_title_for(family, primary, len(group)),
            severity=sev,
            category=primary.category,
            file_path=primary.file_path,
            affected_symbol=primary.affected_symbol,
            architectural_role=primary.architectural_role,
            summary=summary,
            recommendation=primary.recommendation,
            signals=list(group),
            context_factors=factors,
            confidence=round(max(i.confidence for i in group), 3),
        ))

    concerns.sort(
        key=lambda c: (
            -severity_rank(c.severity),
            -c.signal_count,
            c.file_path,
            c.affected_symbol,
        )
    )
    return concerns
