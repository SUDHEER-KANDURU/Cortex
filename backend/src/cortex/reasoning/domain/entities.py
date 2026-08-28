"""Reasoning domain entities — outputs of the Cortex intelligence pipeline.

These are the shared data structures that all product features consume.
Every field is grounded in repository evidence — no fabrication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# Architecture & Module Intelligence
# ═══════════════════════════════════════════════════════════════════════════════


class ArchitectureStyle(str, Enum):
    """Detected architecture patterns."""
    LAYERED = "layered"
    MODULAR = "modular"
    MONOLITHIC = "monolithic"
    MICROSERVICE = "microservice"
    HEXAGONAL = "hexagonal"
    MVC = "mvc"
    EVENT_DRIVEN = "event_driven"
    PIPELINE = "pipeline"
    UNKNOWN = "unknown"


@dataclass
class ModuleIntelligence:
    """Rich intelligence about a single module (inferred, not just directory)."""
    name: str
    path: str
    node_id: str
    # Responsibilities
    purpose: str = ""
    responsibilities: list[str] = field(default_factory=list)
    # Surface
    public_symbols: list[str] = field(default_factory=list)
    key_classes: list[str] = field(default_factory=list)
    key_functions: list[str] = field(default_factory=list)
    # Relationships
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    # Metrics
    file_count: int = 0
    class_count: int = 0
    function_count: int = 0
    total_lines: int = 0
    avg_complexity: float = 0.0
    max_complexity: int = 0
    # Architecture role
    architecture_role: str = ""  # "core", "api", "infrastructure", "utility", etc.
    layer: str = ""  # "presentation", "application", "domain", "infrastructure"
    # Health
    coupling_score: float = 0.0  # 0=no coupling, 1=extreme coupling
    cohesion_score: float = 0.0  # 0=incoherent, 1=perfectly cohesive
    # Risks
    risks: list[str] = field(default_factory=list)
    is_god_module: bool = False
    has_circular_deps: bool = False


@dataclass
class EntryPoint:
    """A detected entry point into the system."""
    label: str
    node_id: str
    node_type: str
    file_path: str
    kind: str = ""  # "http_endpoint", "main_function", "cli", "event_handler"
    method: str = ""  # GET, POST, etc.
    route: str = ""  # /api/v1/users
    description: str = ""


@dataclass
class DataFlowStep:
    """One step in a data/request flow through the system."""
    symbol: str
    node_id: str
    node_type: str
    file_path: str
    role: str = ""  # "entry", "controller", "service", "repository", "external"


@dataclass
class DataFlow:
    """A traced data/request flow through the system."""
    name: str
    entry_point: str
    steps: list[DataFlowStep] = field(default_factory=list)
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# Repository Understanding
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RepositoryUnderstanding:
    """Complete Cortex understanding of a repository.

    This is the CENTRAL output of the reasoning layer — every feature
    consumes this rather than independently querying modules.
    """
    # Identity
    job_id: str
    repo_url: str
    repo_name: str

    # ── What is this system? ──────────────────────────────────────────────────
    purpose: str = ""
    headline: str = ""

    # ── Architecture ──────────────────────────────────────────────────────────
    architecture_style: ArchitectureStyle = ArchitectureStyle.UNKNOWN
    architecture_description: str = ""
    architecture_evidence: list[str] = field(default_factory=list)

    # ── Languages & Frameworks ────────────────────────────────────────────────
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)

    # ── Structure ─────────────────────────────────────────────────────────────
    total_files: int = 0
    total_lines: int = 0
    total_modules: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_endpoints: int = 0
    total_tests: int = 0

    # ── Entry Points ──────────────────────────────────────────────────────────
    entry_points: list[EntryPoint] = field(default_factory=list)

    # ── Modules ───────────────────────────────────────────────────────────────
    modules: list[ModuleIntelligence] = field(default_factory=list)

    # ── Data Flows ────────────────────────────────────────────────────────────
    data_flows: list[DataFlow] = field(default_factory=list)

    # ── Health ────────────────────────────────────────────────────────────────
    overall_score: int = 0
    overall_grade: str = "C"
    complexity_hotspots: list[dict[str, Any]] = field(default_factory=list)
    architectural_risks: list[str] = field(default_factory=list)

    # ── Recommended starting point ────────────────────────────────────────────
    start_here: str = ""
    start_here_reason: str = ""
    start_here_file: str = ""

    # ── Key dependencies ──────────────────────────────────────────────────────
    top_dependencies: list[str] = field(default_factory=list)

    # Evidence tracking
    evidence_sources: dict[str, str] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Learning Path
# ═══════════════════════════════════════════════════════════════════════════════


class LearningDifficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class LearningStep:
    """One step in the learning path."""
    order: int
    title: str
    what_to_read: list[str]  # file paths
    why: str
    symbols: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    difficulty: LearningDifficulty = LearningDifficulty.BEGINNER
    what_to_understand: str = ""
    module: str = ""
    estimated_minutes: int = 0


@dataclass
class LearningPath:
    """Repository-specific onboarding path."""
    repo_name: str
    total_steps: int = 0
    estimated_hours: float = 0.0
    # Stages
    start_here: list[LearningStep] = field(default_factory=list)
    foundations: list[LearningStep] = field(default_factory=list)
    core_flow: list[LearningStep] = field(default_factory=list)
    important_modules: list[LearningStep] = field(default_factory=list)
    advanced_areas: list[LearningStep] = field(default_factory=list)
    known_risks: list[LearningStep] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Root-Cause Analysis
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RootCauseEvidence:
    """One piece of evidence for root-cause analysis."""
    source: str  # "stacktrace", "graph", "insight", "memory"
    description: str
    symbol: str = ""
    file_path: str = ""
    confidence: float = 0.0


@dataclass
class RootCauseAnalysis:
    """Result of root-cause analysis for a given error/stacktrace."""
    # Input
    error_input: str
    parsed_symbols: list[str] = field(default_factory=list)
    # Matched context
    matched_nodes: list[dict[str, Any]] = field(default_factory=list)
    callers: list[dict[str, Any]] = field(default_factory=list)
    callees: list[dict[str, Any]] = field(default_factory=list)
    related_issues: list[dict[str, Any]] = field(default_factory=list)
    # Evidence
    static_evidence: list[RootCauseEvidence] = field(default_factory=list)
    # Synthesis (for NIM)
    evidence_context: str = ""
    # Verdict
    likely_cause: str = ""
    affected_path: list[str] = field(default_factory=list)
    suggested_investigation: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Issue → Fix Intelligence
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class FixIntelligence:
    """Intelligence for fixing a detected engineering issue."""
    # The issue itself
    issue_title: str
    issue_category: str
    issue_severity: str
    # Evidence
    problem_description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    # Impact
    affected_code: list[dict[str, str]] = field(default_factory=list)  # [{file, symbol, role}]
    blast_radius_summary: str = ""
    # Fix direction
    recommended_approach: str = ""
    implementation_steps: list[str] = field(default_factory=list)
    # Related context
    related_dependencies: list[str] = field(default_factory=list)
    related_tests: list[str] = field(default_factory=list)
    # Common fix template (deterministic)
    fix_template: str = ""
    estimated_complexity: str = ""  # "trivial", "moderate", "significant", "major"
