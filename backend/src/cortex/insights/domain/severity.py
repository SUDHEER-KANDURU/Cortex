"""Context-aware severity model for engineering insights.

The core idea: a raw metric crossing a threshold is a *signal*, not a
verdict. Whether that signal is a genuine HIGH/CRITICAL engineering risk
depends on context:

    severity  =  magnitude  +  context  +  impact  +  confidence
                              (+ reinforcing signals)

This module centralises:
  1. ArchitecturalRole — what a file *is* (router, orchestrator,
     repository, entry-point, generator/parser, ordinary module).
     A legitimate central orchestrator is *expected* to have high fan-out;
     a router is *expected* to import many collaborators. These roles must
     not be treated as architectural defects just because a metric is large.
  2. adjust_severity() — a single, testable function that takes a base
     (magnitude-derived) severity and returns the context-adjusted severity,
     recording *why* it was adjusted so the evidence trail stays honest.

Deterministic, dependency-free, no NIM. Cortex evidence decides severity.
"""

from __future__ import annotations

import re
from enum import Enum

from cortex.insights.domain.entities import IssueSeverity

# ── Severity ordering helpers ─────────────────────────────────────────────────
_ORDER: dict[IssueSeverity, int] = {
    IssueSeverity.INFO: 0,
    IssueSeverity.LOW: 1,
    IssueSeverity.MEDIUM: 2,
    IssueSeverity.HIGH: 3,
    IssueSeverity.CRITICAL: 4,
}
_BY_RANK: dict[int, IssueSeverity] = {v: k for k, v in _ORDER.items()}


def severity_rank(sev: IssueSeverity) -> int:
    return _ORDER[sev]


def max_severity(a: IssueSeverity, b: IssueSeverity) -> IssueSeverity:
    return a if _ORDER[a] >= _ORDER[b] else b


def _shift(sev: IssueSeverity, delta: int) -> IssueSeverity:
    """Move a severity up (+) or down (-) the ladder, clamped."""
    rank = max(0, min(4, _ORDER[sev] + delta))
    return _BY_RANK[rank]


def downgrade(sev: IssueSeverity, steps: int = 1) -> IssueSeverity:
    return _shift(sev, -abs(steps))


def escalate(sev: IssueSeverity, steps: int = 1) -> IssueSeverity:
    return _shift(sev, abs(steps))


# ── Architectural role ────────────────────────────────────────────────────────
class ArchitecturalRole(str, Enum):
    """What a source file *is*, inferred from path + graph shape.

    Roles carry expectations. A ROUTER legitimately wires many
    dependencies; an ORCHESTRATOR legitimately coordinates many modules;
    a REPOSITORY legitimately imports many models/entities. Metrics that
    are normal *for the role* should not be reported as top-severity risks.
    """

    ENTRY_POINT  = "entry_point"    # app factory / main / wsgi / asgi
    ROUTER       = "router"         # HTTP route layer (presentation)
    ORCHESTRATOR = "orchestrator"   # pipeline / stages / coordinator
    REPOSITORY   = "repository"     # persistence / DB adapters
    GENERATOR    = "generator"      # artifact/report/diagram generators
    PARSER       = "parser"         # AST / language parsers
    ORDINARY     = "ordinary"       # normal business/domain module

    def expects_high_fanout(self) -> bool:
        """Roles for which many outgoing dependencies is normal wiring."""
        return self in {
            ArchitecturalRole.ENTRY_POINT,
            ArchitecturalRole.ROUTER,
            ArchitecturalRole.ORCHESTRATOR,
            ArchitecturalRole.REPOSITORY,
        }

    def expects_large_procedural_body(self) -> bool:
        """Roles where a big file with FEW methods is a legitimate pattern.

        Generators and parsers concentrate long, mostly-linear procedures
        (string building, big match/dispatch) into a handful of methods.
        A 500-line file with 3 methods here is 'large', not a 'god class'.
        """
        return self in {ArchitecturalRole.GENERATOR, ArchitecturalRole.PARSER}


# ── Role classification (path + light graph signals) ──────────────────────────
_ENTRY_RE       = re.compile(r"(^|/)(main|app|wsgi|asgi|__main__|manage|server)\.py$", re.I)
_ROUTER_RE      = re.compile(r"(^|/)(router|routes|controller|endpoints?|views|api)\.py$", re.I)
_ROUTER_DIR_RE  = re.compile(r"(^|/)(presentation|routers?|controllers?|api|views)(/|$)", re.I)
_ORCH_RE        = re.compile(
    r"(^|/)(orchestrat\w*|stages?|pipeline|coordinator|workflow|scheduler|runner)\.py$", re.I
)
_REPO_RE        = re.compile(r"(^|/)(\w*repository|\w*_repo|dao|persistence|store)\.py$", re.I)
_REPO_DIR_RE    = re.compile(r"(^|/)(infrastructure|persistence|adapters?|repositories)(/|$)", re.I)
_GEN_RE         = re.compile(
    r"(^|/)(\w*generator|\w*_gen|\w*builder|\w*renderer|\w*exporter|\w*formatter)\.py$", re.I
)
_PARSER_RE      = re.compile(r"(^|/)(\w*parser|\w*_ast|lexer|tokenizer|ast_\w*)\.py$", re.I)


def classify_role(
    path: str,
    *,
    endpoint_count: int = 0,
    has_app_factory: bool = False,
) -> ArchitecturalRole:
    """Infer a file's architectural role from its path and light signals.

    Order matters: entry-point and router (structural signals) win over
    filename-only heuristics. Everything falls back to ORDINARY so an
    unknown module is judged strictly, never leniently.
    """
    p = path.replace("\\", "/")

    if has_app_factory or _ENTRY_RE.search(p):
        return ArchitecturalRole.ENTRY_POINT

    # A file that defines HTTP endpoints, or lives in a presentation layer
    # with a router-like name, is a router regardless of import count.
    if endpoint_count > 0 or _ROUTER_RE.search(p):
        return ArchitecturalRole.ROUTER
    if _ROUTER_DIR_RE.search(p) and _ROUTER_RE.search(p):
        return ArchitecturalRole.ROUTER

    if _ORCH_RE.search(p):
        return ArchitecturalRole.ORCHESTRATOR
    if _PARSER_RE.search(p):
        return ArchitecturalRole.PARSER
    if _GEN_RE.search(p):
        return ArchitecturalRole.GENERATOR
    if _REPO_RE.search(p) or (_REPO_DIR_RE.search(p) and "repositor" in p.lower()):
        return ArchitecturalRole.REPOSITORY

    return ArchitecturalRole.ORDINARY


# ── The severity adjustment core ──────────────────────────────────────────────
class SeverityDecision:
    """Result of a context-aware severity computation.

    Carries the final severity plus a human-readable list of the context
    factors that moved it, so the evidence trail explains the verdict.
    """

    __slots__ = ("severity", "factors")

    def __init__(self, severity: IssueSeverity, factors: list[str]) -> None:
        self.severity = severity
        self.factors = factors


def adjust_severity(
    *,
    base: IssueSeverity,
    role: ArchitecturalRole,
    signal: str,
    magnitude_ratio: float = 1.0,
    dependents: int = 0,
    fan_in_hub: bool = False,
    reinforcing_signals: int = 0,
) -> SeverityDecision:
    """Turn a magnitude-derived base severity into a context-aware one.

    Args:
        base:               severity implied by the raw metric alone.
        role:               architectural role of the affected file.
        signal:             which detector fired ("fanout", "god_class",
                            "oversized_file", "cyclomatic", "god_function"...).
        magnitude_ratio:    metric / threshold. >=2.0 means "extreme",
                            which can pull a downgraded finding back up.
        dependents:         afferent coupling (how many files import this).
        fan_in_hub:         True if this file is also a dependency hub.
        reinforcing_signals: count of *other independent* concern signals on
                            the same symbol (e.g. CC high AND deep nesting).

    Returns:
        SeverityDecision with the adjusted severity and the reasons.
    """
    sev = base
    factors: list[str] = []

    extreme = magnitude_ratio >= 2.0

    # ── 1. Fan-out on wiring roles is expected, not a defect ──────────────────
    # Routers/entry-points/orchestrators/repositories exist precisely to wire
    # many collaborators together, so a high *outgoing* dependency count is the
    # normal shape of the role — not an architectural defect. It only becomes a
    # real risk when this file is ALSO widely depended upon (a fan-in hub),
    # because then its churn ripples outward. Raw magnitude of fan-out, however
    # large, does not by itself override the role: a 30-import router is still a
    # router. So we downgrade unless it is a genuine hub.
    fanout_downgraded = False
    if signal == "fanout" and role.expects_high_fanout():
        if fan_in_hub:
            factors.append(
                f"{role.value} with high fan-out is usually normal wiring, but it is "
                f"also a dependency hub ({dependents} dependents) — its churn ripples "
                f"outward, so the risk is kept elevated"
            )
        else:
            # Very extreme wiring (>=3x) is still worth a MEDIUM note, but never
            # a HIGH purely for composing collaborators.
            steps = 1 if magnitude_ratio < 3.0 else 1
            sev = downgrade(sev, steps)
            fanout_downgraded = True
            factors.append(
                f"high fan-out is expected for a {role.value} that composes many "
                f"collaborators — normal wiring for this role, not an architectural "
                f"defect on its own (downgraded)"
            )

    # ── 2. Large procedural files in generator/parser roles ──────────────────
    if signal == "oversized_file" and role.expects_large_procedural_body():
        if not extreme:
            sev = downgrade(sev, 1)
            factors.append(
                f"a {role.value} concentrates long procedural code in one file by "
                f"design; large size here is expected, not multiple hidden concerns "
                f"(downgraded)"
            )

    # ── 3. Impact amplification via dependents (blast radius) ─────────────────
    if signal in {"cyclomatic", "god_function", "god_class"} and dependents >= 8:
        sev = escalate(sev, 1)
        factors.append(
            f"changes here ripple to {dependents} dependent files — wide blast radius "
            f"raises the risk (escalated)"
        )

    # ── 4. Reinforcing signals turn a single warning into a real concern ──────
    if reinforcing_signals >= 2 and severity_rank(sev) < severity_rank(IssueSeverity.HIGH):
        sev = escalate(sev, 1)
        factors.append(
            f"multiple independent complexity signals ({reinforcing_signals}) fire "
            f"together on this symbol, reinforcing each other (escalated)"
        )

    # ── 5. Extreme magnitude is a risk regardless of role ─────────────────────
    # (Skipped for fan-out we deliberately downgraded: a router composing many
    #  collaborators is expected shape, not a magnitude problem.)
    if (
        extreme
        and not fanout_downgraded
        and severity_rank(sev) < severity_rank(IssueSeverity.HIGH)
    ):
        sev = escalate(sev, 1)
        factors.append(
            f"metric is {magnitude_ratio:.1f}x the threshold — extreme magnitude "
            f"outweighs contextual leniency (escalated)"
        )

    return SeverityDecision(sev, factors)
