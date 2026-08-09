"""Centralized insight thresholds — single source of truth.

Every threshold is documented with:
  - metric name
  - value
  - rationale / source
  - severity applied
  - language applicability

References:
  - Clean Code (Martin, 2008)
  - Code Complete 2 (McConnell, 2004)
  - SonarQube default quality profile (2024)
  - Google Python Style Guide
  - Google Java Style Guide
  - Airbnb JavaScript Style Guide
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

Language = Literal["python", "java", "typescript", "javascript", "unknown"]


@dataclass(frozen=True)
class Threshold:
    metric: str
    value: float
    reason: str
    severity: Literal["low", "medium", "high", "critical"]
    languages: tuple[str, ...] = ("python", "java", "typescript", "javascript")


# ── Function / method size ────────────────────────────────────────────────────
FN_LINES_CRITICAL = Threshold(
    metric="function_lines",
    value=60,
    reason="SonarQube default; Clean Code ch.3 — functions should do one thing. >60 lines almost always violates SRP.",
    severity="high",
)
FN_LINES_HIGH = Threshold(
    metric="function_lines",
    value=40,
    reason="Code Complete 2 §7.4 — ideal function length is one screen (~40 lines).",
    severity="medium",
)
FN_LINES_MEDIUM = Threshold(
    metric="function_lines",
    value=25,
    reason="Google Python Style Guide recommends ~20–25 lines for clarity.",
    severity="low",
)

# ── Parameter count ───────────────────────────────────────────────────────────
FN_PARAMS_CRITICAL = Threshold(
    metric="param_count",
    value=7,
    reason="Clean Code ch.3 — no function should have more than 3 params ideally; >7 is universally flagged.",
    severity="high",
)
FN_PARAMS_HIGH = Threshold(
    metric="param_count",
    value=5,
    reason="Clean Code ch.3 — triadic functions acceptable but anything >5 needs a parameter object.",
    severity="medium",
)

# ── Class size ────────────────────────────────────────────────────────────────
CLASS_METHODS_CRITICAL = Threshold(
    metric="class_method_count",
    value=20,
    reason="SonarQube S2176; God Class anti-pattern. >20 methods almost always indicates multiple responsibilities.",
    severity="high",
)
CLASS_METHODS_HIGH = Threshold(
    metric="class_method_count",
    value=12,
    reason="Clean Code ch.10 — classes should be small. >12 public methods is a warning sign.",
    severity="medium",
)
CLASS_LINES_CRITICAL = Threshold(
    metric="class_lines",
    value=400,
    reason="SonarQube S1200 — class should not exceed 200 statements. 400 LOC is a practical proxy.",
    severity="high",
)

# ── File size ─────────────────────────────────────────────────────────────────
FILE_LINES_CRITICAL = Threshold(
    metric="file_lines",
    value=500,
    reason="SonarQube S104 default. A 500-line file typically contains multiple concerns.",
    severity="high",
)
FILE_LINES_HIGH = Threshold(
    metric="file_lines",
    value=300,
    reason="Google Python Style Guide — 300 lines is the soft limit before splitting is recommended.",
    severity="medium",
)

# ── Coupling ──────────────────────────────────────────────────────────────────
FANOUT_CRITICAL = Threshold(
    metric="efferent_coupling",
    value=10,
    reason="Martin's Stable Dependencies Principle. Ce>10 indicates an unstable, change-prone module.",
    severity="high",
)
FANOUT_HIGH = Threshold(
    metric="efferent_coupling",
    value=7,
    reason="Pragmatic Programmer — a module should not depend on more than 7 distinct modules.",
    severity="medium",
)
FANIN_CRITICAL = Threshold(
    metric="afferent_coupling",
    value=20,
    reason="High Ca means changes here break many things. >20 dependents = fragile hub.",
    severity="medium",
)

# ── Documentation ─────────────────────────────────────────────────────────────
DOC_COVERAGE_CRITICAL = Threshold(
    metric="public_api_doc_coverage",
    value=0.30,
    reason="Below 30% documented public APIs means most consumers have no contract to rely on.",
    severity="high",
)
DOC_COVERAGE_HIGH = Threshold(
    metric="public_api_doc_coverage",
    value=0.50,
    reason="Below 50% is below the minimum acceptable for a maintained project.",
    severity="medium",
)
DOC_COVERAGE_MEDIUM = Threshold(
    metric="public_api_doc_coverage",
    value=0.70,
    reason="Below 70% is below the recommended threshold for production code.",
    severity="low",
)

# ── Inheritance depth ─────────────────────────────────────────────────────────
INHERIT_DEPTH_CRITICAL = Threshold(
    metric="inheritance_depth",
    value=5,
    reason="Clean Code ch.6 — deep hierarchies become incomprehensible. >5 levels is universally problematic.",
    severity="high",
)
INHERIT_DEPTH_HIGH = Threshold(
    metric="inheritance_depth",
    value=3,
    reason="Google Java Style Guide — prefer composition. Depth >3 warrants review.",
    severity="medium",
)

# ── Naming (Python-specific) ──────────────────────────────────────────────────
NAMING_MIN_LENGTH = Threshold(
    metric="symbol_name_length",
    value=2,
    reason="Names of 1-2 chars are rarely self-documenting outside of math/loops/generics.",
    severity="low",
    languages=("python",),
)

# ── Analysis coverage ─────────────────────────────────────────────────────────
COVERAGE_WARN = Threshold(
    metric="analysis_coverage_pct",
    value=0.60,
    reason="Below 60% coverage means more than 40% of the codebase was not analyzed. Scores are unreliable.",
    severity="medium",
)
COVERAGE_CRITICAL = Threshold(
    metric="analysis_coverage_pct",
    value=0.30,
    reason="Below 30% coverage means scores are not representative of the repository.",
    severity="high",
)

# ── God Function composite score ──────────────────────────────────────────────
# Weighted signals for god-function detection.
#
# Weights and rationale:
#   lines       0.20 — size is a signal but not the whole story (Clean Code ch.3)
#   cyclomatic  0.30 — McCabe complexity is the strongest single predictor of defect
#                       density (Watson & McCabe, 1996 NASA study)
#   param_count 0.20 — interface complexity; hard to call and test correctly
#   nesting     0.15 — deep nesting → cognitive complexity; correlates with bugs
#   branches    0.00 — already captured by cyclomatic; avoid double-counting
#   calls       0.15 — high call count = broad responsibility = SRP violation
#
# Note: branches weight is 0 because cyclomatic = 1 + branches,
# so including both would double-count the same signal.
GOD_FUNCTION_WEIGHTS: dict[str, float] = {
    "lines":       0.20,
    "cyclomatic":  0.30,
    "param_count": 0.20,
    "nesting":     0.15,
    "branches":    0.00,
    "calls":       0.15,
}
GOD_FUNCTION_SCORE_THRESHOLD = 0.55   # composite score >= this → god function
GOD_FUNCTION_SCORE_HIGH      = 0.35   # composite score >= this → large/complex

# ── Cyclomatic complexity thresholds ─────────────────────────────────────────
# Based on: Watson & McCabe (1996), NIST Special Publication 500-235
# McCabe's original thresholds, widely adopted by SonarQube, CodeClimate, etc.
CYCLOMATIC_CRITICAL = Threshold(
    metric="cyclomatic_complexity",
    value=15,
    reason="McCabe (1976): complexity >15 is untestable without heroic effort. SonarQube critical threshold.",
    severity="critical",
)
CYCLOMATIC_HIGH = Threshold(
    metric="cyclomatic_complexity",
    value=10,
    reason="McCabe (1976): complexity >10 is high risk. Original paper's recommended upper limit.",
    severity="high",
)
CYCLOMATIC_MEDIUM = Threshold(
    metric="cyclomatic_complexity",
    value=5,
    reason="SonarQube medium threshold; functions above this benefit from refactoring.",
    severity="medium",
)

# ── Nesting depth thresholds ──────────────────────────────────────────────────
NESTING_CRITICAL = Threshold(
    metric="nesting_depth",
    value=5,
    reason="Cognitive complexity grows exponentially with nesting. >5 is unmaintainable.",
    severity="high",
)
NESTING_HIGH = Threshold(
    metric="nesting_depth",
    value=3,
    reason="Google style guides recommend max 3 levels of nesting.",
    severity="medium",
)

# ── Classes per file ──────────────────────────────────────────────────────────
CLASSES_PER_FILE_CRITICAL = Threshold(
    metric="classes_per_file",
    value=5,
    reason="One primary class per file is the standard in all major style guides. >5 = mixed concerns.",
    severity="medium",
)

# ── Percentile-based anomaly detection ───────────────────────────────────────
# Functions in the top N% of size for the repo are flagged as outliers
# regardless of absolute threshold — catches repo-relative anomalies
FUNCTION_SIZE_TOP_PERCENTILE = 0.95   # top 5% = outlier
CLASS_SIZE_TOP_PERCENTILE    = 0.95
