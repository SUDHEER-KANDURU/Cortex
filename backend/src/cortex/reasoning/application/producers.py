"""Core Answer Producers — turn `RepositoryUnderstanding` + graph into `CortexAnswer`s.

An Answer Producer is a **pure** function-object over the reasoning layer's
output (`RepositoryUnderstanding`, `ModuleIntelligence`) and the knowledge graph
(`GraphNode`/`GraphEdge`). Each producer emits a single `CortexAnswer` (Req 4.2)
that always passes `assert_valid_answer` — every claim carries `Evidence` and no
INFERENCE/PREDICTION is ever emitted as a FACT (Req 4.3, Req 5.5).

Three producers live here (Task 7):

* :class:`ArchitectureOverviewProducer` — architecture style + evidence + modules.
* :class:`ModuleBreakdownProducer` — MODULE nodes → `ModuleIntelligence` → sections.
* :class:`ApiSpecProducer` — ENDPOINT nodes → route/method/params/handler sections.

Two cross-cutting rules are applied by every producer:

1. **Language Capability Profiles drive section composition** (Req 2.2, Req 2.3).
   A section is emitted only when its machine key appears in the applicable
   answer sections of at least one detected language's
   `LanguageCapabilityProfile`. A Go service and a TypeScript app therefore get
   different sections for the same intent (e.g. TS exposes ``interfaces``, Go
   exposes ``packages``), and neither shows a section its stack does not support.

2. **Epistemic tagging follows a fixed rule set** (Req 5.2, Req 5.3, Req 5.4):
     - directly-extracted structure (symbols, files, metrics, relationships
       read straight from the graph) → :attr:`Epistemic.FACT`
     - heuristic conclusions (architectural role, purpose, architecture style)
       → :attr:`Epistemic.INFERENCE`
     - forward-looking / impact statements (what a change would do) →
       :attr:`Epistemic.PREDICTION`

Zero framework dependencies — pure computation over domain objects, consistent
with the reasoner and the `graph/domain` style.
"""

from __future__ import annotations

import structlog
from cortex.graph.domain.entities import GraphEdge, GraphNode, NodeType
from cortex.pipeline.domain.entities import Coverage, LanguageCapabilityProfile
from cortex.reasoning.domain.answer import (
    AnswerSection,
    Claim,
    CortexAnswer,
    Epistemic,
    Evidence,
    NextAction,
    NextActionKind,
    assert_valid_answer,
)
from cortex.reasoning.domain.entities import (
    ModuleIntelligence,
    RepositoryUnderstanding,
)

logger = structlog.get_logger()

# ── Confidence / coverage caveat thresholds (Req 6.2, Req 6.3) ────────────────
# When an answer's own computed confidence falls below this, or when the
# analysis Coverage falls below the ratios below, the producer surfaces a plain
# caveat on the answer so the reader knows the result rests on thin evidence.
LOW_CONFIDENCE_THRESHOLD: float = 0.5
LOW_FILE_COVERAGE_THRESHOLD: float = 0.75
LOW_REFERENCE_COVERAGE_THRESHOLD: float = 0.6


# ═══════════════════════════════════════════════════════════════════════════════
# Language Capability Profile lookup
# ═══════════════════════════════════════════════════════════════════════════════


def _load_language_profiles() -> dict[str, LanguageCapabilityProfile]:
    """Build ``{language_name: profile}`` for every supported language.

    Profiles are static declarations (Task 3); reading them never requires a
    tree-sitter grammar to be installed, so this is safe in any environment.
    The Python profile comes from ``PythonASTParser``; the rest come from the
    per-language ``LanguageSpec`` objects via a grammar-free ``TreeSitterParser``
    (matching how ``tests/unit/test_language_profiles.py`` reads them).
    """
    profiles: dict[str, LanguageCapabilityProfile] = {}

    from cortex.pipeline.infrastructure.ast_parser import PythonASTParser

    py = PythonASTParser().profile()
    profiles[py.language] = py

    try:
        from cortex.pipeline.infrastructure import tree_sitter_parser as ts

        specs = [
            ts._JS_SPEC,
            ts._TS_SPEC,
            ts._JAVA_SPEC,
            ts._GO_SPEC,
            ts._RUST_SPEC,
            ts._CSHARP_SPEC,
            ts._RUBY_SPEC,
        ]
        for spec in specs:
            profile = ts.TreeSitterParser(spec, ()).profile()
            profiles[profile.language] = profile
    except Exception as exc:  # pragma: no cover - defensive: profiles are static
        # If the tree-sitter module cannot be imported for any reason, the
        # producers still work with whatever profiles are available (at least
        # Python); section composition simply falls back to a permissive set.
        logger.warning("language_profiles_partial", error=repr(exc))

    return profiles


# Loaded once; profiles are frozen, immutable, deterministic.
_LANGUAGE_PROFILES: dict[str, LanguageCapabilityProfile] = _load_language_profiles()

# When no detected language matches a known profile, allow this broad, stack
# neutral set so a producer never emits an empty answer purely for lack of a
# profile. These keys are the intersection of the common section keys.
_FALLBACK_SECTIONS: frozenset[str] = frozenset(
    {"overview", "modules", "classes", "functions", "endpoints", "dependencies"}
)


def applicable_sections_for(languages: list[str]) -> frozenset[str]:
    """Return the union of answer-section keys applicable to ``languages``.

    A section is applicable when its key appears in the ``answer_sections`` of
    at least one detected language's profile (Req 2.2). Different stacks yield
    different sets — this is what makes section composition adapt per stack
    (Req 2.3). Unknown languages contribute nothing; if nothing is known at all
    the permissive fallback set is used so the answer is never empty.
    """
    keys: set[str] = set()
    matched_any = False
    for lang in languages:
        profile = _LANGUAGE_PROFILES.get(lang.lower())
        if profile is not None:
            matched_any = True
            keys.update(profile.applicable_sections())
    if not matched_any:
        return _FALLBACK_SECTIONS
    return frozenset(keys)


# ═══════════════════════════════════════════════════════════════════════════════
# Shared producer base
# ═══════════════════════════════════════════════════════════════════════════════


class _BaseProducer:
    """Common machinery: a graph index, profile-driven section gating, validation.

    Subclasses implement :meth:`_build` returning an unvalidated `CortexAnswer`;
    :meth:`produce` runs the answer through ``assert_valid_answer`` so no
    malformed or epistemically dishonest answer can reach the user (Req 5.5).
    """

    intent: str = "answer"

    def __init__(
        self,
        understanding: RepositoryUnderstanding,
        nodes: list[GraphNode] | None = None,
        edges: list[GraphEdge] | None = None,
        coverage: Coverage | None = None,
    ) -> None:
        self.u = understanding
        self.nodes = nodes or []
        self.edges = edges or []
        # Real analysis coverage, when the caller can thread it through (Req 6.3).
        # Coverage is computed in the pipeline layer (``compute_coverage`` in
        # ``pipeline/infrastructure/coverage.py``) and lives on the pipeline
        # context; the reasoning layer's ``RepositoryUnderstanding`` does not
        # carry it today. This is the seam: when a caller has the ``Coverage``
        # in hand it passes it here and the caveat reflects real coverage; when
        # it does not, the caveat still fires on the answer's own low confidence
        # and on thin structure (Req 6.3).
        self.coverage = coverage
        self.node_by_id: dict[str, GraphNode] = {n.id: n for n in self.nodes}
        self.sections_allowed = applicable_sections_for(understanding.languages)

    # ── section gating (Req 2.2, Req 2.3) ────────────────────────────────────
    def _section_applies(self, key: str) -> bool:
        return key in self.sections_allowed

    def _nodes_of(self, node_type: NodeType) -> list[GraphNode]:
        return [n for n in self.nodes if n.node_type == node_type]

    @staticmethod
    def _prop(node: GraphNode, key: str, default: str = "") -> str:
        return str(node.properties.get(key, default) or default)

    @staticmethod
    def _int_prop(node: GraphNode, key: str) -> int:
        try:
            return int(node.properties.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0

    def produce(self) -> CortexAnswer:
        answer = self._build()
        assert_valid_answer(answer)
        return answer

    # ── caveat surfacing (Req 6.2, Req 6.3) ──────────────────────────────────
    def _coverage_note(self, confidence: float) -> str | None:
        """Return a plain caveat when coverage OR confidence is low (Req 6.3).

        Combines three independent signals so a reader is never left trusting a
        thin answer:

        * **Structure** — an empty graph or a repo with no detected modules is
          called out directly (the historic behaviour).
        * **Coverage** — when real :class:`Coverage` is threaded in and either
          the file-coverage or reference-coverage ratio is low, the caveat
          states exactly how much was analyzed/resolved.
        * **Confidence** — when the answer's own computed confidence falls below
          :data:`LOW_CONFIDENCE_THRESHOLD`, the caveat says the result rests on
          limited evidence, even if structure and coverage look adequate.

        Returns ``None`` when nothing is low, so a high-confidence, well-covered
        answer never shows a spurious caveat.
        """
        return build_coverage_note(self.u, confidence, self.coverage)

    def _build(self) -> CortexAnswer:  # pragma: no cover - abstract
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════════════════════
# ArchitectureOverviewProducer
# ═══════════════════════════════════════════════════════════════════════════════


class ArchitectureOverviewProducer(_BaseProducer):
    """Produce a repository architecture overview as a `CortexAnswer`.

    Section composition:
      - ``overview``     — structural counts (FACT) + architecture style (INFERENCE)
                           + purpose (INFERENCE).
      - ``modules``      — the top modules by importance (FACT), each with an
                           inferred role (INFERENCE).
      - ``dependencies`` — top external dependencies (FACT).

    Only sections whose keys are applicable to the detected stack are emitted.
    """

    intent = "architecture_overview"

    def _build(self) -> CortexAnswer:
        u = self.u
        sections: list[AnswerSection] = []
        repo_evidence = Evidence(file_path=u.repo_name or u.repo_url or "repository")

        # ── overview ──────────────────────────────────────────────────────────
        if self._section_applies("overview"):
            claims: list[Claim] = []

            # Directly-extracted structural counts → FACT (Req 5.2).
            claims.append(
                Claim(
                    text=(
                        f"The repository contains {u.total_files} files, "
                        f"{u.total_modules} modules, {u.total_classes} classes, "
                        f"{u.total_functions} functions, and {u.total_endpoints} "
                        f"endpoints ({u.total_lines} lines total)."
                    ),
                    epistemic=Epistemic.FACT,
                    evidence=[repo_evidence],
                )
            )

            if u.languages:
                claims.append(
                    Claim(
                        text=(
                            "Detected languages: "
                            + ", ".join(u.languages)
                            + (
                                "; frameworks: " + ", ".join(u.frameworks)
                                if u.frameworks
                                else ""
                            )
                            + "."
                        ),
                        epistemic=Epistemic.FACT,
                        evidence=[repo_evidence],
                    )
                )

            # Architecture style is a heuristic conclusion → INFERENCE (Req 5.3).
            claims.append(
                Claim(
                    text=(
                        f"The architecture style appears to be "
                        f"'{u.architecture_style.value}'."
                        + (
                            f" {u.architecture_description}"
                            if u.architecture_description
                            else ""
                        )
                    ),
                    epistemic=Epistemic.INFERENCE,
                    evidence=[repo_evidence],
                )
            )

            # Purpose is inferred → INFERENCE (Req 5.3).
            if u.purpose:
                claims.append(
                    Claim(
                        text=f"Inferred purpose: {u.purpose}",
                        epistemic=Epistemic.INFERENCE,
                        evidence=[repo_evidence],
                    )
                )

            sections.append(AnswerSection(heading="Overview", claims=claims))

        # ── modules ─────────────────────────────────────────────────────────
        if self._section_applies("modules") and u.modules:
            claims = []
            for mi in u.modules[:8]:
                mod_ev = Evidence(file_path=mi.path or mi.name, node_id=mi.node_id)
                # Structure of the module is directly extracted → FACT.
                claims.append(
                    Claim(
                        text=(
                            f"Module '{mi.name}' has {mi.file_count} files, "
                            f"{mi.class_count} classes, and {mi.function_count} "
                            f"functions."
                        ),
                        epistemic=Epistemic.FACT,
                        evidence=[mod_ev],
                    )
                )
                # Architectural role is heuristic → INFERENCE (Req 5.3).
                if mi.architecture_role:
                    claims.append(
                        Claim(
                            text=(
                                f"Module '{mi.name}' plays a "
                                f"'{mi.architecture_role}' role"
                                + (f" in the {mi.layer} layer." if mi.layer else ".")
                            ),
                            epistemic=Epistemic.INFERENCE,
                            evidence=[mod_ev],
                        )
                    )
            sections.append(AnswerSection(heading="Modules", claims=claims))

        # ── dependencies ──────────────────────────────────────────────────────
        if self._section_applies("dependencies") and u.top_dependencies:
            claims = [
                Claim(
                    text="Top external dependencies: "
                    + ", ".join(u.top_dependencies[:15])
                    + ".",
                    epistemic=Epistemic.FACT,
                    evidence=[repo_evidence],
                )
            ]
            sections.append(AnswerSection(heading="Dependencies", claims=claims))

        # ── architectural risks → forward-looking → PREDICTION (Req 5.4) ──────
        if u.architectural_risks:
            claims = [
                Claim(
                    text=f"Risk: {risk}",
                    epistemic=Epistemic.PREDICTION,
                    evidence=[repo_evidence],
                )
                for risk in u.architectural_risks[:8]
            ]
            sections.append(AnswerSection(heading="Architectural Risks", claims=claims))

        next_actions: list[NextAction] = []
        if u.start_here_file:
            next_actions.append(
                NextAction(
                    label=f"Start here: {u.start_here_file}",
                    kind=NextActionKind.OPEN_FILE,
                    target=u.start_here_file,
                )
            )
        next_actions.append(
            NextAction(
                label="View module breakdown",
                kind=NextActionKind.RUN_PRODUCER,
                target="module_breakdown",
            )
        )

        confidence = _confidence_from_counts(u.total_files, len(u.modules))
        return CortexAnswer(
            intent=self.intent,
            title=f"Architecture Overview — {u.repo_name}",
            summary=(
                u.headline
                or u.architecture_description
                or f"A {u.architecture_style.value} system with "
                f"{u.total_modules} modules across {u.total_files} files."
            ),
            sections=sections,
            confidence=confidence,
            coverage_note=self._coverage_note(confidence),
            next_actions=next_actions,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ModuleBreakdownProducer
# ═══════════════════════════════════════════════════════════════════════════════


class ModuleBreakdownProducer(_BaseProducer):
    """Produce a per-module breakdown as a `CortexAnswer`.

    Walks the reasoner's `ModuleIntelligence` (which is derived from MODULE
    nodes in the graph). Each module becomes a section whose claims mix:
      - metrics + key symbols (directly extracted) → FACT (Req 5.2),
      - role / purpose (heuristic) → INFERENCE (Req 5.3),
      - coupling / god-module risks (forward-looking) → PREDICTION (Req 5.4).
    """

    intent = "module_breakdown"

    def _build(self) -> CortexAnswer:
        u = self.u
        sections: list[AnswerSection] = []

        for mi in u.modules[:20]:
            claims = self._claims_for_module(mi)
            if claims:
                sections.append(AnswerSection(heading=mi.name, claims=claims))

        if not sections:
            # Insufficient evidence: state the gap rather than fabricate (Req 4.6).
            repo_ev = Evidence(file_path=u.repo_name or u.repo_url or "repository")
            sections.append(
                AnswerSection(
                    heading="No modules detected",
                    claims=[
                        Claim(
                            text=(
                                "No modules were detected in the analyzed graph, "
                                "so a module breakdown cannot be produced."
                            ),
                            epistemic=Epistemic.FACT,
                            evidence=[repo_ev],
                        )
                    ],
                )
            )

        confidence = _confidence_from_counts(u.total_files, len(u.modules))
        return CortexAnswer(
            intent=self.intent,
            title=f"Module Breakdown — {u.repo_name}",
            summary=(
                f"{len(u.modules)} modules across {u.total_files} files. "
                "Each module is described by its structure, inferred role, and risks."
            ),
            sections=sections,
            confidence=confidence,
            coverage_note=self._coverage_note(confidence),
            next_actions=[
                NextAction(
                    label="View architecture overview",
                    kind=NextActionKind.RUN_PRODUCER,
                    target="architecture_overview",
                )
            ],
        )

    def _claims_for_module(self, mi: ModuleIntelligence) -> list[Claim]:
        mod_ev = Evidence(file_path=mi.path or mi.name, node_id=mi.node_id)
        claims: list[Claim] = []

        # ── structure → FACT (always applicable) ─────────────────────────────
        claims.append(
            Claim(
                text=(
                    f"Contains {mi.file_count} files, {mi.class_count} classes, "
                    f"{mi.function_count} functions, {mi.total_lines} lines."
                ),
                epistemic=Epistemic.FACT,
                evidence=[mod_ev],
            )
        )

        # ── classes section (only where the stack has classes) → FACT ─────────
        if self._section_applies("classes") and mi.key_classes:
            claims.append(
                Claim(
                    text="Key classes: " + ", ".join(mi.key_classes) + ".",
                    epistemic=Epistemic.FACT,
                    evidence=[mod_ev],
                )
            )

        # ── functions section → FACT ──────────────────────────────────────────
        if self._section_applies("functions") and mi.key_functions:
            claims.append(
                Claim(
                    text="Key functions: " + ", ".join(mi.key_functions) + ".",
                    epistemic=Epistemic.FACT,
                    evidence=[mod_ev],
                )
            )

        # ── dependencies → FACT (relationships are extracted) ─────────────────
        if self._section_applies("dependencies") and mi.dependencies:
            claims.append(
                Claim(
                    text="Depends on modules: " + ", ".join(mi.dependencies) + ".",
                    epistemic=Epistemic.FACT,
                    evidence=[mod_ev],
                )
            )

        # ── role / purpose → INFERENCE (Req 5.3) ──────────────────────────────
        if mi.architecture_role:
            claims.append(
                Claim(
                    text=(
                        f"Plays a '{mi.architecture_role}' role"
                        + (f" in the {mi.layer} layer." if mi.layer else ".")
                    ),
                    epistemic=Epistemic.INFERENCE,
                    evidence=[mod_ev],
                )
            )
        if mi.purpose:
            claims.append(
                Claim(
                    text=f"Inferred purpose: {mi.purpose}",
                    epistemic=Epistemic.INFERENCE,
                    evidence=[mod_ev],
                )
            )

        # ── risks / coupling → PREDICTION (Req 5.4) ───────────────────────────
        for risk in mi.risks:
            claims.append(
                Claim(
                    text=f"Risk: {risk}",
                    epistemic=Epistemic.PREDICTION,
                    evidence=[mod_ev],
                )
            )
        if mi.is_god_module:
            claims.append(
                Claim(
                    text=(
                        "Changing this module is likely to have wide-reaching "
                        "impact because it concentrates many responsibilities."
                    ),
                    epistemic=Epistemic.PREDICTION,
                    evidence=[mod_ev],
                )
            )

        return claims


# ═══════════════════════════════════════════════════════════════════════════════
# ApiSpecProducer
# ═══════════════════════════════════════════════════════════════════════════════


class ApiSpecProducer(_BaseProducer):
    """Produce an API specification as a `CortexAnswer`.

    Walks ENDPOINT nodes in the graph, emitting a claim per endpoint carrying
    the route, HTTP method, parameters, and handler — all directly extracted, so
    every endpoint claim is a FACT (Req 5.2). The whole answer is gated on the
    ``endpoints`` section key being applicable to the detected stack (Req 2.2):
    a stack whose profile omits ``endpoints`` (e.g. a Rust crate) produces a
    stated-gap answer instead of fabricated route claims.
    """

    intent = "api_spec"

    def _build(self) -> CortexAnswer:
        u = self.u
        sections: list[AnswerSection] = []
        endpoints = self._nodes_of(NodeType.ENDPOINT)

        endpoints_supported = self._section_applies("endpoints")

        if endpoints_supported and endpoints:
            # Deterministic ordering: by route then method then label.
            endpoints_sorted = sorted(
                endpoints,
                key=lambda n: (
                    self._prop(n, "route_info") or self._prop(n, "route"),
                    self._prop(n, "http_method") or self._prop(n, "method"),
                    n.label,
                ),
            )
            claims: list[Claim] = []
            for ep in endpoints_sorted:
                route = self._prop(ep, "route_info") or self._prop(ep, "route") or "(unknown route)"
                method = (
                    self._prop(ep, "http_method")
                    or self._prop(ep, "method")
                    or "GET"
                ).upper()
                params = self._prop(ep, "parameters")
                handler = ep.label
                file_path = self._prop(ep, "file") or u.repo_name or "repository"
                line = self._int_prop(ep, "line") or None

                text = f"{method} {route} → handled by {handler}()"
                if params:
                    text += f" (params: {params})"
                text += "."

                claims.append(
                    Claim(
                        text=text,
                        epistemic=Epistemic.FACT,
                        evidence=[
                            Evidence(
                                file_path=file_path,
                                line_start=line,
                                line_end=line,
                                node_id=ep.id,
                            )
                        ],
                    )
                )
            sections.append(AnswerSection(heading="Endpoints", claims=claims))
        else:
            # Insufficient / inapplicable: state the gap rather than fabricate
            # (Req 4.6). Distinguish "stack has no API surface concept" from
            # "no endpoints found".
            repo_ev = Evidence(file_path=u.repo_name or u.repo_url or "repository")
            if not endpoints_supported:
                gap = (
                    "The detected stack does not expose an HTTP endpoint concept, "
                    "so no API specification is applicable."
                )
            else:
                gap = "No HTTP endpoints were detected in the analyzed graph."
            sections.append(
                AnswerSection(
                    heading="No API surface",
                    claims=[
                        Claim(text=gap, epistemic=Epistemic.FACT, evidence=[repo_ev])
                    ],
                )
            )

        n_endpoints = len(endpoints) if endpoints_supported else 0
        confidence = _confidence_from_counts(u.total_endpoints, n_endpoints)
        return CortexAnswer(
            intent=self.intent,
            title=f"API Specification — {u.repo_name}",
            summary=(
                f"{n_endpoints} HTTP endpoints detected."
                if n_endpoints
                else "No API surface to describe."
            ),
            sections=sections,
            confidence=confidence,
            coverage_note=self._coverage_note(confidence),
            next_actions=[
                NextAction(
                    label="View architecture overview",
                    kind=NextActionKind.RUN_PRODUCER,
                    target="architecture_overview",
                )
            ],
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LearningPathProducer
# ═══════════════════════════════════════════════════════════════════════════════


def _dependency_depths(modules: list[ModuleIntelligence]) -> dict[str, int]:
    """Compute a deterministic dependency depth for every module.

    Depth is the length of the longest chain of intra-repository dependencies a
    module rests on: a module that depends on nothing has depth 0; a module that
    depends only on depth-0 modules has depth 1; and so on. Modules with a lower
    depth are foundational and should be learned first.

    ``ModuleIntelligence.dependencies`` lists the *names* of modules a module
    depends on (a relationship read straight from the graph). Only dependencies
    that resolve to another module in this repository count toward depth;
    external/unknown names are ignored. Cycles are broken deterministically so
    the computation always terminates and always yields the same result for the
    same input (a hard requirement — the learning order must be deterministic).
    """
    by_name = {m.name: m for m in modules}
    depth: dict[str, int] = {}

    def resolve(name: str, on_stack: frozenset[str]) -> int:
        if name in depth:
            return depth[name]
        module = by_name.get(name)
        if module is None:
            return 0
        # Only intra-repo dependencies that are not currently being resolved
        # (cycle guard) contribute. Sorting makes the walk order deterministic.
        dep_depths = [
            resolve(dep, on_stack | {name}) + 1
            for dep in sorted(set(module.dependencies))
            if dep in by_name and dep != name and dep not in on_stack
        ]
        computed = max(dep_depths, default=0)
        depth[name] = computed
        return computed

    for m in sorted(modules, key=lambda x: x.name):
        resolve(m.name, frozenset())
    return depth


class LearningPathProducer(_BaseProducer):
    """Produce a guided learning path (an onboarding reading order) as a `CortexAnswer`.

    Modules are ordered into a learning sequence by **dependency depth**:
    foundational modules (those depending on little or nothing inside the repo)
    come first, dependent modules later. Ordering is fully deterministic —
    ``(depth, name)`` — so the same repository always yields the same path.

    Epistemic rule set:
      - each module's structure and its dependency relationships are directly
        extracted → :attr:`Epistemic.FACT`;
      - the recommended *order* / "learn this first" rationale is a heuristic
        conclusion → :attr:`Epistemic.INFERENCE`.

    Insufficient evidence (no modules) yields a stated-gap answer (Req 4.6).
    """

    intent = "learning_path"

    def _build(self) -> CortexAnswer:
        u = self.u
        modules = u.modules
        sections: list[AnswerSection] = []

        if not modules:
            repo_ev = Evidence(file_path=u.repo_name or u.repo_url or "repository")
            sections.append(
                AnswerSection(
                    heading="No learning path available",
                    claims=[
                        Claim(
                            text=(
                                "No modules were detected in the analyzed graph, "
                                "so a dependency-ordered learning path cannot be "
                                "produced."
                            ),
                            epistemic=Epistemic.FACT,
                            evidence=[repo_ev],
                        )
                    ],
                )
            )
            return CortexAnswer(
                intent=self.intent,
                title=f"Learning Path — {u.repo_name}",
                summary="No modules were detected, so no learning path is available.",
                sections=sections,
                confidence=_confidence_from_counts(u.total_files, 0),
                coverage_note=self._coverage_note(_confidence_from_counts(u.total_files, 0)),
                next_actions=[
                    NextAction(
                        label="View architecture overview",
                        kind=NextActionKind.RUN_PRODUCER,
                        target="architecture_overview",
                    )
                ],
            )

        depths = _dependency_depths(modules)
        # Deterministic learning order: shallowest dependency depth first, then
        # by name to break ties (Req: ordering must be deterministic).
        ordered = sorted(modules, key=lambda m: (depths.get(m.name, 0), m.name))

        # ── recommended order → INFERENCE (Req 5.3) ──────────────────────────
        repo_ev = Evidence(file_path=u.repo_name or u.repo_url or "repository")
        order_claim = Claim(
            text=(
                "Recommended learning order (foundational modules first): "
                + " → ".join(m.name for m in ordered)
                + "."
            ),
            epistemic=Epistemic.INFERENCE,
            evidence=[repo_ev],
        )
        sections.append(
            AnswerSection(heading="Recommended Order", claims=[order_claim])
        )

        # ── one step per module, in learning order ───────────────────────────
        for step, mi in enumerate(ordered, start=1):
            mod_ev = Evidence(file_path=mi.path or mi.name, node_id=mi.node_id)
            claims: list[Claim] = []

            # Module structure is directly extracted → FACT (Req 5.2).
            claims.append(
                Claim(
                    text=(
                        f"Module '{mi.name}' has {mi.file_count} files, "
                        f"{mi.class_count} classes, and {mi.function_count} "
                        f"functions."
                    ),
                    epistemic=Epistemic.FACT,
                    evidence=[mod_ev],
                )
            )

            # Dependency relationships are directly extracted → FACT (Req 5.2).
            intra_deps = sorted(
                dep for dep in set(mi.dependencies) if dep in depths and dep != mi.name
            )
            if intra_deps:
                claims.append(
                    Claim(
                        text="Depends on: " + ", ".join(intra_deps) + ".",
                        epistemic=Epistemic.FACT,
                        evidence=[mod_ev],
                    )
                )

            # Why to read it here (order rationale) is heuristic → INFERENCE.
            depth = depths.get(mi.name, 0)
            if depth == 0:
                rationale = (
                    f"Learn '{mi.name}' early: it is foundational and does not "
                    "depend on other repository modules."
                )
            else:
                rationale = (
                    f"Learn '{mi.name}' after its {len(intra_deps)} dependency "
                    f"module(s) (dependency depth {depth}), so its context is "
                    "already familiar."
                )
            claims.append(
                Claim(text=rationale, epistemic=Epistemic.INFERENCE, evidence=[mod_ev])
            )

            sections.append(
                AnswerSection(heading=f"Step {step}: {mi.name}", claims=claims)
            )

        learning_confidence = _confidence_from_counts(u.total_files, len(modules))
        next_actions: list[NextAction] = []
        first = ordered[0]
        first_target = first.path or first.name
        next_actions.append(
            NextAction(
                label=f"Start with {first.name}",
                kind=NextActionKind.OPEN_FILE,
                target=first_target,
            )
        )
        next_actions.append(
            NextAction(
                label="View module breakdown",
                kind=NextActionKind.RUN_PRODUCER,
                target="module_breakdown",
            )
        )

        return CortexAnswer(
            intent=self.intent,
            title=f"Learning Path — {u.repo_name}",
            summary=(
                f"A guided reading order across {len(modules)} modules, sequenced "
                "by dependency depth so you learn foundations before the code that "
                "builds on them."
            ),
            sections=sections,
            confidence=learning_confidence,
            coverage_note=self._coverage_note(learning_confidence),
            next_actions=next_actions,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# InterviewPrepProducer
# ═══════════════════════════════════════════════════════════════════════════════


class InterviewPrepProducer(_BaseProducer):
    """Produce interview-prep material as a `CortexAnswer`.

    Combines three evidence sources into Q&A-style sections:
      - **Hotspots** — the most complex functions (``complexity_hotspots``): the
        metrics (cyclomatic complexity, line counts) are directly extracted →
        :attr:`Epistemic.FACT`; the "why it matters" / likely-question framing is
        heuristic → :attr:`Epistemic.INFERENCE`; the change-impact of touching a
        hotspot is forward-looking → :attr:`Epistemic.PREDICTION`.
      - **Architecture** — the detected style is heuristic → INFERENCE; its
        structural evidence (counts) is FACT.
      - **Key flows** — traced request/data flows (``data_flows``): the steps are
        directly extracted → FACT; the "expect to be asked to trace this" framing
        is INFERENCE.

    Insufficient evidence (no hotspots, no flows, and no architecture signal)
    yields a stated-gap answer (Req 4.6).
    """

    intent = "interview_prep"

    def _build(self) -> CortexAnswer:
        u = self.u
        sections: list[AnswerSection] = []
        repo_ev = Evidence(file_path=u.repo_name or u.repo_url or "repository")

        has_arch = u.architecture_style is not None and (
            u.architecture_style.value != "unknown" or u.total_modules > 0
        )
        has_hotspots = bool(u.complexity_hotspots)
        has_flows = bool(u.data_flows)

        if not (has_arch or has_hotspots or has_flows):
            # Insufficient evidence: state the gap rather than fabricate (Req 4.6).
            sections.append(
                AnswerSection(
                    heading="Insufficient evidence for interview prep",
                    claims=[
                        Claim(
                            text=(
                                "No architecture signal, complexity hotspots, or "
                                "traced flows were detected, so interview-prep "
                                "questions cannot be produced."
                            ),
                            epistemic=Epistemic.FACT,
                            evidence=[repo_ev],
                        )
                    ],
                )
            )
            return CortexAnswer(
                intent=self.intent,
                title=f"Interview Prep — {u.repo_name}",
                summary="Not enough analyzed evidence to build interview questions.",
                sections=sections,
                confidence=_confidence_from_counts(u.total_files, 0),
                coverage_note=self._coverage_note(_confidence_from_counts(u.total_files, 0)),
                next_actions=[
                    NextAction(
                        label="View architecture overview",
                        kind=NextActionKind.RUN_PRODUCER,
                        target="architecture_overview",
                    )
                ],
            )

        # ── Architecture Q&A ─────────────────────────────────────────────────
        if has_arch:
            arch_claims: list[Claim] = [
                Claim(
                    text=(
                        "Q: How is this system structured, and what architecture "
                        "style does it follow?"
                    ),
                    epistemic=Epistemic.INFERENCE,
                    evidence=[repo_ev],
                ),
                Claim(
                    text=(
                        f"The system spans {u.total_modules} modules across "
                        f"{u.total_files} files ({u.total_classes} classes, "
                        f"{u.total_functions} functions)."
                    ),
                    epistemic=Epistemic.FACT,
                    evidence=[repo_ev],
                ),
                Claim(
                    text=(
                        f"It appears to follow a '{u.architecture_style.value}' "
                        "architecture"
                        + (
                            f": {u.architecture_description}"
                            if u.architecture_description
                            else "."
                        )
                    ),
                    epistemic=Epistemic.INFERENCE,
                    evidence=[repo_ev],
                ),
            ]
            sections.append(
                AnswerSection(heading="Architecture", claims=arch_claims)
            )

        # ── Hotspots Q&A (deterministic order) ───────────────────────────────
        if has_hotspots:
            hot_claims: list[Claim] = [
                Claim(
                    text=(
                        "Q: Which parts of this codebase are the most complex, and "
                        "how would you approach changing them?"
                    ),
                    epistemic=Epistemic.INFERENCE,
                    evidence=[repo_ev],
                )
            ]
            # Deterministic ordering: by cyclomatic desc, then symbol, then file.
            hotspots = sorted(
                u.complexity_hotspots,
                key=lambda h: (
                    -int(h.get("cyclomatic", 0) or 0),
                    str(h.get("symbol", "")),
                    str(h.get("file", "")),
                ),
            )
            for h in hotspots[:8]:
                symbol = str(h.get("symbol", "") or "(unknown symbol)")
                file_path = str(h.get("file", "") or "").strip()
                cyclomatic = int(h.get("cyclomatic", 0) or 0)
                lines = int(h.get("lines", 0) or 0)
                node_id = h.get("node_id")
                hot_ev = Evidence(
                    file_path=file_path or (u.repo_name or "repository"),
                    node_id=str(node_id) if node_id else None,
                )

                # Metrics are directly extracted → FACT (Req 5.2).
                metric_text = (
                    f"'{symbol}'"
                    + (f" in {file_path}" if file_path else "")
                    + f" has cyclomatic complexity {cyclomatic}"
                    + (f" across {lines} lines" if lines else "")
                    + "."
                )
                hot_claims.append(
                    Claim(
                        text=metric_text,
                        epistemic=Epistemic.FACT,
                        evidence=[hot_ev],
                    )
                )
                # Why it matters / likely question → INFERENCE (Req 5.3).
                hot_claims.append(
                    Claim(
                        text=(
                            f"Expect questions about '{symbol}': its high branching "
                            "makes it a likely source of bugs and a common review "
                            "focus."
                        ),
                        epistemic=Epistemic.INFERENCE,
                        evidence=[hot_ev],
                    )
                )
                # Change-impact → PREDICTION (Req 5.4).
                hot_claims.append(
                    Claim(
                        text=(
                            f"Changing '{symbol}' is likely to require careful "
                            "testing because its complexity raises the chance of "
                            "regressions."
                        ),
                        epistemic=Epistemic.PREDICTION,
                        evidence=[hot_ev],
                    )
                )
            sections.append(
                AnswerSection(heading="Complexity Hotspots", claims=hot_claims)
            )

        # ── Key Flows Q&A (deterministic order) ──────────────────────────────
        if has_flows:
            flow_claims: list[Claim] = [
                Claim(
                    text=(
                        "Q: Walk me through a key request/data flow through the "
                        "system."
                    ),
                    epistemic=Epistemic.INFERENCE,
                    evidence=[repo_ev],
                )
            ]
            flows = sorted(u.data_flows, key=lambda f: f.name)
            for flow in flows[:6]:
                # Prefer a locatable file from the flow's first step, else repo.
                flow_file = ""
                if flow.steps:
                    flow_file = (flow.steps[0].file_path or "").strip()
                flow_ev = Evidence(
                    file_path=flow_file or (u.repo_name or "repository")
                )
                step_labels = [s.symbol for s in flow.steps]
                trace = " → ".join(step_labels) if step_labels else "(no steps traced)"
                # The traced steps are directly extracted → FACT (Req 5.2).
                flow_claims.append(
                    Claim(
                        text=(
                            f"Flow '{flow.name}' (entry: {flow.entry_point}) "
                            f"traces: {trace}."
                        ),
                        epistemic=Epistemic.FACT,
                        evidence=[flow_ev],
                    )
                )
                # Likely-question framing → INFERENCE (Req 5.3).
                flow_claims.append(
                    Claim(
                        text=(
                            f"Be ready to explain how '{flow.name}' moves data "
                            "from entry to persistence and where responsibilities "
                            "are separated."
                        ),
                        epistemic=Epistemic.INFERENCE,
                        evidence=[flow_ev],
                    )
                )
            sections.append(AnswerSection(heading="Key Flows", claims=flow_claims))

        present = len(u.complexity_hotspots) + len(u.data_flows) + (1 if has_arch else 0)
        confidence = _confidence_from_counts(max(u.total_files, present), present)
        return CortexAnswer(
            intent=self.intent,
            title=f"Interview Prep — {u.repo_name}",
            summary=(
                "Q&A-style preparation drawn from this repository's architecture, "
                "complexity hotspots, and key flows."
            ),
            sections=sections,
            confidence=confidence,
            coverage_note=self._coverage_note(confidence),
            next_actions=[
                NextAction(
                    label="View architecture overview",
                    kind=NextActionKind.RUN_PRODUCER,
                    target="architecture_overview",
                ),
                NextAction(
                    label="View module breakdown",
                    kind=NextActionKind.RUN_PRODUCER,
                    target="module_breakdown",
                ),
            ],
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _confidence_from_counts(total: int, present: int) -> float:
    """A conservative confidence in 0..1 based on how much evidence backs the answer.

    More detected structure → higher confidence, capped so a deterministic
    producer never claims certainty it cannot justify.
    """
    if total <= 0:
        return 0.3
    ratio = min(present / total, 1.0) if total else 0.0
    # Blend a base floor with the coverage ratio; keep within [0.3, 0.95].
    return round(min(0.95, 0.3 + 0.65 * ratio), 2)


def build_coverage_note(
    u: RepositoryUnderstanding,
    confidence: float | None = None,
    coverage: Coverage | None = None,
) -> str | None:
    """Surface a plain caveat when coverage OR confidence is low (Req 6.3).

    A single answer can trip more than one signal; every applicable caveat is
    collected so the reader sees the full picture, joined into one note. Returns
    ``None`` when the answer is well-grounded — a high-confidence, well-covered
    answer never shows a spurious caveat.

    The signals, in priority order:

    1. **Empty / thin structure** — an empty graph or a repo with no detected
       modules (the historic behaviour). This short-circuits: if there is
       nothing to analyze, that is the only caveat worth stating.
    2. **Low real coverage** — when a :class:`Coverage` is supplied and either
       ratio is below its threshold, the caveat states how much was
       analyzed/resolved (Req 6.1, Req 6.3).
    3. **Low confidence** — when ``confidence`` is below
       :data:`LOW_CONFIDENCE_THRESHOLD`, the caveat says the answer rests on
       limited evidence (Req 6.2, Req 6.3).
    """
    if u.total_files == 0:
        return "No files were analyzed; this answer is based on an empty graph."
    if u.total_modules == 0:
        return "No modules were detected; module-level detail is unavailable."

    notes: list[str] = []

    if coverage is not None:
        file_ratio = coverage.file_coverage_ratio()
        ref_ratio = coverage.reference_coverage_ratio()
        if file_ratio < LOW_FILE_COVERAGE_THRESHOLD:
            notes.append(
                f"Only {file_ratio:.0%} of files were analyzed "
                f"({coverage.analyzed_files}/{coverage.total_files}); "
                f"{coverage.gap_count()} file(s) could not be parsed, so this "
                "answer may be incomplete."
            )
        if ref_ratio < LOW_REFERENCE_COVERAGE_THRESHOLD:
            notes.append(
                f"Only {ref_ratio:.0%} of references were resolved, so some "
                "relationships may be missing from this answer."
            )

    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        notes.append(
            f"Confidence is low ({confidence:.0%}); this answer rests on limited "
            "analyzed evidence and should be treated as provisional."
        )

    if not notes:
        return None
    return " ".join(notes)


def _coverage_note(u: RepositoryUnderstanding) -> str | None:
    """Backward-compatible structural caveat (no confidence/coverage signals).

    Retained so existing call sites and tests keep working; new code should use
    :func:`build_coverage_note` or ``_BaseProducer._coverage_note`` which also
    fire on low confidence and low coverage (Req 6.3).
    """
    return build_coverage_note(u)
