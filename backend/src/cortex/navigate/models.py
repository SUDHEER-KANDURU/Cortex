"""Navigate response models — rich navigation data for the frontend."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class NavigationMode(str, Enum):
    """The lens through which the user is exploring."""
    UPSTREAM = "upstream"         # What leads to this?
    DOWNSTREAM = "downstream"    # What does this affect?
    CALL_PATH = "call_path"      # How does execution reach this?
    DEPENDENCIES = "dependencies" # What does this rely on?
    IMPACT = "impact"            # What might break if this changes?
    SOURCE = "source"            # Show the actual code


class RelationshipStatus(str, Enum):
    """How confident we are about a relationship."""
    DETECTED = "detected"       # Directly found in graph
    INFERRED = "inferred"       # Derived from multi-hop traversal
    UNAVAILABLE = "unavailable" # Could not determine


# ─── Sub-models ───────────────────────────────────────────────────────────────

class SourceLocation(BaseModel):
    """Exact source location of a symbol."""
    repository: str = ""
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    symbol_name: str = ""


class ConnectedNode(BaseModel):
    """A node connected to the navigation target."""
    id: str
    label: str
    node_type: str
    relationship: str
    relationship_status: RelationshipStatus = RelationshipStatus.DETECTED
    file_path: str = ""
    line_start: int = 0


class NavigateIssue(BaseModel):
    """An engineering issue related to the navigation target."""
    title: str
    severity: str
    category: str
    description: str
    recommendation: str
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    confidence: float = 1.0


class NavigateInsights(BaseModel):
    """Engineering insights for the navigated entity."""
    complexity: int = 0
    lines: int = 0
    methods: int = 0
    parameters: int = 0
    is_async: bool = False
    has_docstring: bool = False
    coupling_in: int = 0   # number of incoming dependencies
    coupling_out: int = 0  # number of outgoing dependencies
    issues: list[NavigateIssue] = []
    risk_factors: list[str] = []


class CallPathNode(BaseModel):
    """A node in a call/execution path."""
    id: str
    label: str
    node_type: str
    file_path: str = ""
    depth: int = 0


class CallPath(BaseModel):
    """An execution path to or from the target."""
    nodes: list[CallPathNode] = []
    direction: str = "upstream"  # upstream or downstream


# ─── Main Response ────────────────────────────────────────────────────────────

class NavigateResponse(BaseModel):
    """Complete navigation context for a single entity."""

    # 1. Definition
    id: str
    label: str
    node_type: str
    source: SourceLocation

    # 2. Callers — who calls this?
    callers: list[ConnectedNode] = []

    # 3. Callees — what does this call?
    callees: list[ConnectedNode] = []

    # 4. Dependencies — what does this depend on? (IMPORTS, DEPENDS_ON, INHERITS)
    dependencies: list[ConnectedNode] = []

    # 5. Dependents — what depends on this?
    dependents: list[ConnectedNode] = []

    # 6. Related modules — nearby architectural components
    related_modules: list[ConnectedNode] = []

    # 7. Tests — related test nodes
    tests: list[ConnectedNode] = []

    # 8. Insights — complexity, coupling, issues, risks
    insights: NavigateInsights = NavigateInsights()

    # 9. Source snippet — relevant code context
    source_snippet: str = ""

    # 10. Contained by / Contains
    contained_by: ConnectedNode | None = None
    contains: list[ConnectedNode] = []

    # Navigation context
    breadcrumb: list[ConnectedNode] = []

    # Mode-specific data
    call_paths_upstream: list[CallPath] = []
    call_paths_downstream: list[CallPath] = []


class NavigateExplainRequest(BaseModel):
    """Request body for AI explanation."""
    node_id: str
    question: str = ""  # optional specific question


class ExplanationSectionResponse(BaseModel):
    """One section of a Cortex explanation."""
    key:      str
    heading:  str
    body:     str
    evidence: list[str] = []


class NavigateExplainResponse(BaseModel):
    """Cortex explanation of an entity, grounded in graph evidence.

    `explanation` is the full markdown text (backwards compatible).
    `sections` is the structured 12-part breakdown.
    `source` is "cortex" (deterministic only) or "cortex+nim" (NIM refined
    the wording; the facts remain Cortex's).
    """
    explanation:   str
    sections:      list[ExplanationSectionResponse] = []
    headline:      str = ""
    architectural_role: str = "ordinary"
    read_next:     list[str] = []
    evidence_used: list[str] = []
    confidence:    float = 0.0
    source:        str = "cortex"


# ─── Scoped Explanation (CortexAnswer over a file + line range) ───────────────


class ScopedExplainRequest(BaseModel):
    """Request body for a scoped explanation (Req 7.3).

    A file + line range plus an optional free-text question. The ``job_id`` is
    supplied as a path parameter (every navigate route is job-scoped), so it is
    not part of the body.
    """
    file_path: str
    line_start: int
    line_end: int
    question: str = ""


class EvidenceResponse(BaseModel):
    """A traceable pointer back into the repository backing a claim."""
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    node_id: str | None = None


class ClaimResponse(BaseModel):
    """A single assertion tagged with its epistemic status (fact/inference/prediction)."""
    text: str
    epistemic: str
    evidence: list[EvidenceResponse] = []


class AnswerSectionResponse(BaseModel):
    """An ordered, headed group of claims within an answer."""
    heading: str
    claims: list[ClaimResponse] = []


class NextActionResponse(BaseModel):
    """A suggested follow-up rendered as a next-action button."""
    label: str
    kind: str
    target: str = ""
    line_start: int | None = None
    line_end: int | None = None


class CortexAnswerResponse(BaseModel):
    """Serialized `CortexAnswer` — the unified answer contract over HTTP (Req 4.1)."""
    intent: str
    title: str
    summary: str
    sections: list[AnswerSectionResponse] = []
    confidence: float = 0.0
    coverage_note: str | None = None
    next_actions: list[NextActionResponse] = []
