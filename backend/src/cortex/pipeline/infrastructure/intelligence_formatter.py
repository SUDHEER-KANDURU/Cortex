"""Intelligence Formatter — structured FACT → RELATIONSHIP → MEANING → RECOMMENDATION.

Every engineering finding in Cortex artifacts should follow this pattern:

  1. FACT: What is objectively true (from AST, graph, metrics)
  2. RELATIONSHIP: How it connects to other parts of the system
  3. MEANING: What this implies for engineering quality
  4. RECOMMENDATION: What should be done about it

This module provides data structures and formatters that all artifact
generators can use to produce consistently structured output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FindingSeverity(str, Enum):
    """Severity of an engineering finding."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    """Category of an engineering finding."""
    ARCHITECTURE = "Architecture"
    COMPLEXITY = "Complexity"
    COUPLING = "Coupling"
    DESIGN = "Design"
    TESTING = "Testing"
    DOCUMENTATION = "Documentation"
    PERFORMANCE = "Performance"
    SECURITY = "Security"


@dataclass
class EngineeringFinding:
    """A structured engineering finding with full evidence chain.

    This is the atomic unit of Cortex intelligence — every artifact
    should express its insights as a list of these.
    """
    # What is objectively true
    fact: str
    # How it connects to other system components
    relationship: str
    # What it means for engineering quality
    meaning: str
    # What should be done
    recommendation: str

    # Evidence metadata
    category: FindingCategory = FindingCategory.ARCHITECTURE
    severity: FindingSeverity = FindingSeverity.MEDIUM
    affected_symbol: str = ""
    source_file: str = ""
    evidence: dict = field(default_factory=dict)
    confidence: float = 0.8

    # Related symbols
    related_symbols: list[str] = field(default_factory=list)
    related_files: list[str] = field(default_factory=list)


@dataclass
class IntelligenceSection:
    """A section of an artifact with structured findings."""
    title: str
    summary: str
    findings: list[EngineeringFinding] = field(default_factory=list)


def render_finding_markdown(finding: EngineeringFinding, index: int = 0) -> str:
    """Render a single finding as structured Markdown."""
    severity_icon = {
        FindingSeverity.CRITICAL: "🔴",
        FindingSeverity.HIGH: "🟠",
        FindingSeverity.MEDIUM: "🟡",
        FindingSeverity.LOW: "🟢",
        FindingSeverity.INFO: "ℹ️",
    }.get(finding.severity, "")

    lines = []
    if index > 0:
        lines.append("")

    header = f"#### {severity_icon} {finding.category.value}"
    if finding.affected_symbol:
        header += f" — `{finding.affected_symbol}`"
    lines.append(header)
    lines.append("")

    # FACT
    lines.append(f"**Fact:** {finding.fact}")
    lines.append("")

    # RELATIONSHIP
    lines.append(f"**Relationship:** {finding.relationship}")
    lines.append("")

    # MEANING
    lines.append(f"**Meaning:** {finding.meaning}")
    lines.append("")

    # RECOMMENDATION
    lines.append(f"**Recommendation:** {finding.recommendation}")
    lines.append("")

    # Evidence details
    if finding.source_file:
        lines.append(f"*Source:* `{finding.source_file}`")
    if finding.related_symbols:
        lines.append(f"*Related:* {', '.join(f'`{s}`' for s in finding.related_symbols[:5])}")
    if finding.confidence < 0.8:
        lines.append(f"*Confidence:* {finding.confidence:.0%}")

    return "\n".join(lines)


def render_section_markdown(section: IntelligenceSection) -> str:
    """Render a full section with its findings."""
    lines = [f"## {section.title}", "", section.summary, ""]

    for i, finding in enumerate(section.findings):
        lines.append(render_finding_markdown(finding, i))
        lines.append("")

    return "\n".join(lines)


def render_findings_summary(findings: list[EngineeringFinding]) -> str:
    """Render a compact summary table of all findings."""
    if not findings:
        return ""

    lines = [
        "## Findings Summary",
        "",
        "| # | Severity | Category | Symbol | Key Insight |",
        "|---|----------|----------|--------|-------------|",
    ]

    for i, f in enumerate(findings[:20], 1):
        severity_icon = {
            FindingSeverity.CRITICAL: "🔴",
            FindingSeverity.HIGH: "🟠",
            FindingSeverity.MEDIUM: "🟡",
            FindingSeverity.LOW: "🟢",
            FindingSeverity.INFO: "ℹ️",
        }.get(f.severity, "")
        symbol = f"`{f.affected_symbol}`" if f.affected_symbol else "—"
        insight = f.meaning[:60] + "…" if len(f.meaning) > 60 else f.meaning
        lines.append(f"| {i} | {severity_icon} | {f.category.value} | {symbol} | {insight} |")

    lines.append("")
    return "\n".join(lines)
