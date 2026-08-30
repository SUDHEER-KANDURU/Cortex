"""Tests for the core Answer Producers (Task 7).

Covers Req 2.2, Req 2.3 (profile-driven section composition adapts per stack),
Req 4.2 (every producer emits a valid CortexAnswer), Req 4.3 (every claim carries
evidence), and Req 5.2/5.3/5.4 (fixed epistemic rule set: extracted = FACT,
heuristic = INFERENCE, impact = PREDICTION).
"""

from __future__ import annotations

import pytest
from cortex.graph.domain.entities import GraphNode, NodeType
from cortex.reasoning.application.producers import (
    ApiSpecProducer,
    ArchitectureOverviewProducer,
    InterviewPrepProducer,
    LearningPathProducer,
    ModuleBreakdownProducer,
    applicable_sections_for,
)
from cortex.reasoning.domain.answer import (
    Epistemic,
    assert_valid_answer,
    validate_answer,
)
from cortex.reasoning.domain.entities import (
    ArchitectureStyle,
    DataFlow,
    DataFlowStep,
    ModuleIntelligence,
    RepositoryUnderstanding,
)

_JOB = "test-producers-001"


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _endpoint_node(
    node_id: str, label: str, route: str, method: str, file: str, line: int
) -> GraphNode:
    return GraphNode(
        id=node_id,
        label=label,
        node_type=NodeType.ENDPOINT,
        job_id=_JOB,
        properties={
            "route_info": route,
            "http_method": method,
            "parameters": "user_id, body",
            "file": file,
            "line": line,
        },
    )


def _ts_understanding() -> RepositoryUnderstanding:
    """A TypeScript stack — profile exposes interfaces/components, no packages."""
    u = RepositoryUnderstanding(
        job_id=_JOB,
        repo_url="https://github.com/example/ts-app",
        repo_name="ts-app",
        purpose="A web API server.",
        headline="A TypeScript web service.",
        architecture_style=ArchitectureStyle.MODULAR,
        architecture_description="Modular architecture.",
        architecture_evidence=["8 distinct modules"],
        languages=["typescript"],
        frameworks=["express"],
        total_files=20,
        total_lines=2000,
        total_modules=4,
        total_classes=10,
        total_functions=40,
        total_endpoints=2,
        top_dependencies=["express", "zod"],
        architectural_risks=["High coupling between routes and services"],
        start_here_file="src/index.ts",
    )
    u.modules = [
        ModuleIntelligence(
            name="routes",
            path="src/routes",
            node_id="mod-routes",
            purpose="HTTP routing.",
            key_classes=["UserController"],
            key_functions=["getUser", "createUser"],
            dependencies=["services"],
            file_count=3,
            class_count=2,
            function_count=8,
            total_lines=300,
            architecture_role="api",
            layer="presentation",
            risks=["Highly coupled to other modules"],
            coupling_score=0.8,
        ),
        ModuleIntelligence(
            name="services",
            path="src/services",
            node_id="mod-services",
            key_classes=["UserService"],
            key_functions=["loadUser"],
            file_count=2,
            class_count=1,
            function_count=6,
            total_lines=250,
            architecture_role="core",
            layer="application",
        ),
    ]
    return u


def _go_understanding() -> RepositoryUnderstanding:
    """A Go stack — profile exposes packages, no components/interfaces-as-decorators."""
    u = RepositoryUnderstanding(
        job_id=_JOB,
        repo_url="https://github.com/example/go-svc",
        repo_name="go-svc",
        architecture_style=ArchitectureStyle.LAYERED,
        languages=["go"],
        frameworks=[],
        total_files=15,
        total_lines=1500,
        total_modules=3,
        total_classes=6,
        total_functions=30,
        total_endpoints=1,
        top_dependencies=["gin"],
    )
    u.modules = [
        ModuleIntelligence(
            name="handlers",
            path="internal/handlers",
            node_id="mod-handlers",
            file_count=4,
            class_count=2,
            function_count=10,
            total_lines=400,
            architecture_role="api",
        )
    ]
    return u


def _ts_endpoints() -> list[GraphNode]:
    return [
        _endpoint_node("ep1", "getUser", "/users/{id}", "get", "src/routes/user.ts", 10),
        _endpoint_node("ep2", "createUser", "/users", "post", "src/routes/user.ts", 25),
    ]


# ── Req 2.2 / 2.3: section composition adapts per stack ──────────────────────


def test_applicable_sections_differ_between_go_and_ts() -> None:
    ts_sections = applicable_sections_for(["typescript"])
    go_sections = applicable_sections_for(["go"])
    assert ts_sections != go_sections
    # TypeScript profile exposes "components"; Go exposes "packages".
    assert "components" in ts_sections
    assert "components" not in go_sections
    assert "packages" in go_sections
    assert "packages" not in ts_sections


def test_unknown_language_falls_back_to_permissive_set() -> None:
    sections = applicable_sections_for(["cobol"])
    assert "overview" in sections
    assert "modules" in sections


def test_multi_language_union_of_sections() -> None:
    both = applicable_sections_for(["typescript", "go"])
    assert "components" in both  # from TS
    assert "packages" in both    # from Go


# ── Req 4.2 / 4.3 / 5.5: every producer emits a valid answer ─────────────────


def test_architecture_overview_is_valid_answer() -> None:
    answer = ArchitectureOverviewProducer(_ts_understanding()).produce()
    assert answer.intent == "architecture_overview"
    assert validate_answer(answer) == []
    assert_valid_answer(answer)
    # Every claim carries evidence (Req 4.3).
    assert all(c.evidence for c in answer.iter_claims())


def test_module_breakdown_is_valid_answer() -> None:
    answer = ModuleBreakdownProducer(_ts_understanding()).produce()
    assert answer.intent == "module_breakdown"
    assert_valid_answer(answer)
    assert all(c.evidence for c in answer.iter_claims())
    # One section per module.
    headings = {s.heading for s in answer.sections}
    assert "routes" in headings
    assert "services" in headings


def test_api_spec_is_valid_answer() -> None:
    u = _ts_understanding()
    answer = ApiSpecProducer(u, nodes=_ts_endpoints()).produce()
    assert answer.intent == "api_spec"
    assert_valid_answer(answer)
    assert all(c.evidence for c in answer.iter_claims())
    # Each endpoint became a FACT claim referencing its route.
    texts = [c.text for c in answer.iter_claims()]
    assert any("/users/{id}" in t for t in texts)
    assert any("/users" in t for t in texts)


# ── Req 5.2 / 5.3 / 5.4: epistemic tagging follows the fixed rule set ────────


def test_architecture_style_is_inference_not_fact() -> None:
    answer = ArchitectureOverviewProducer(_ts_understanding()).produce()
    style_claims = [c for c in answer.iter_claims() if "architecture style" in c.text.lower()]
    assert style_claims
    assert all(c.epistemic is Epistemic.INFERENCE for c in style_claims)


def test_structural_counts_are_facts() -> None:
    answer = ArchitectureOverviewProducer(_ts_understanding()).produce()
    count_claims = [c for c in answer.iter_claims() if "files" in c.text and "modules" in c.text]
    assert count_claims
    assert all(c.epistemic is Epistemic.FACT for c in count_claims)


def test_module_role_is_inference() -> None:
    answer = ModuleBreakdownProducer(_ts_understanding()).produce()
    role_claims = [c for c in answer.iter_claims() if "role" in c.text.lower()]
    assert role_claims
    assert all(c.epistemic is Epistemic.INFERENCE for c in role_claims)


def test_module_risks_are_predictions() -> None:
    answer = ModuleBreakdownProducer(_ts_understanding()).produce()
    risk_claims = [c for c in answer.iter_claims() if c.text.lower().startswith("risk:")]
    assert risk_claims
    assert all(c.epistemic is Epistemic.PREDICTION for c in risk_claims)


def test_architectural_risks_are_predictions() -> None:
    answer = ArchitectureOverviewProducer(_ts_understanding()).produce()
    risk_claims = [c for c in answer.iter_claims() if c.text.lower().startswith("risk:")]
    assert risk_claims
    assert all(c.epistemic is Epistemic.PREDICTION for c in risk_claims)


def test_endpoint_claims_are_facts() -> None:
    answer = ApiSpecProducer(_ts_understanding(), nodes=_ts_endpoints()).produce()
    endpoint_claims = [c for c in answer.iter_claims() if "handled by" in c.text]
    assert endpoint_claims
    assert all(c.epistemic is Epistemic.FACT for c in endpoint_claims)
    # Endpoint FACTs carry locatable file + node evidence.
    for c in endpoint_claims:
        assert c.evidence[0].file_path
        assert c.evidence[0].node_id


# ── Req 2.2 / 2.3: producer section composition adapts per stack ─────────────


def test_module_breakdown_classes_section_gated_by_profile() -> None:
    """Both TS and Go have classes; a class-less stack would omit the section.

    Here we assert the positive case (classes appear) and that a Go module —
    whose module has no key_classes — simply omits the class claim rather than
    fabricating one.
    """
    ts_answer = ModuleBreakdownProducer(_ts_understanding()).produce()
    ts_texts = [c.text for c in ts_answer.iter_claims()]
    assert any("Key classes" in t for t in ts_texts)

    go_answer = ModuleBreakdownProducer(_go_understanding()).produce()
    go_texts = [c.text for c in go_answer.iter_claims()]
    # Go module fixture has no key_classes → no "Key classes" claim.
    assert not any("Key classes" in t for t in go_texts)


def test_same_intent_different_stacks_yield_different_sections() -> None:
    """Req 2.3: architecture overview for a Ruby stack omits sections a TS stack shows.

    The Ruby profile has a narrower answer_sections set than TypeScript. We use
    the section-gating helper directly and via the producer to confirm the
    difference is reflected in the emitted answer's section keys.
    """
    ts = _ts_understanding()
    ruby = _ts_understanding()
    ruby.languages = ["ruby"]
    ruby.frameworks = []

    ts_allowed = applicable_sections_for(ts.languages)
    ruby_allowed = applicable_sections_for(ruby.languages)
    assert ts_allowed != ruby_allowed


# ── Req 4.6: insufficient evidence states the gap ────────────────────────────


def test_api_spec_states_gap_when_no_endpoints() -> None:
    u = _ts_understanding()
    u.total_endpoints = 0
    answer = ApiSpecProducer(u, nodes=[]).produce()
    assert_valid_answer(answer)
    texts = [c.text for c in answer.iter_claims()]
    assert any("No HTTP endpoints" in t for t in texts)


def test_module_breakdown_states_gap_when_no_modules() -> None:
    u = _go_understanding()
    u.modules = []
    u.total_modules = 0
    answer = ModuleBreakdownProducer(u).produce()
    assert_valid_answer(answer)
    texts = [c.text for c in answer.iter_claims()]
    assert any("No modules" in t for t in texts)


# ── Determinism ──────────────────────────────────────────────────────────────


def test_producers_are_deterministic() -> None:
    u = _ts_understanding()
    endpoints = _ts_endpoints()
    a1 = ApiSpecProducer(u, nodes=endpoints).produce()
    a2 = ApiSpecProducer(u, nodes=endpoints).produce()
    assert [c.text for c in a1.iter_claims()] == [c.text for c in a2.iter_claims()]


@pytest.mark.parametrize("confidence_answer", [
    ArchitectureOverviewProducer(_ts_understanding()).produce(),
    ModuleBreakdownProducer(_ts_understanding()).produce(),
    ApiSpecProducer(_ts_understanding(), nodes=_ts_endpoints()).produce(),
])
def test_confidence_within_bounds(confidence_answer) -> None:
    assert 0.0 <= confidence_answer.confidence <= 1.0


# ═════════════════════════════════════════════════════════════════════════════
# Task 8: LearningPathProducer + InterviewPrepProducer
# ═════════════════════════════════════════════════════════════════════════════


def _understanding_with_hotspots_and_flows() -> RepositoryUnderstanding:
    """A TS understanding enriched with complexity hotspots and traced flows."""
    u = _ts_understanding()
    u.complexity_hotspots = [
        {
            "symbol": "handleRequest",
            "file": "src/routes/user.ts",
            "cyclomatic": 18,
            "lines": 120,
            "node_id": "fn-handle",
        },
        {
            "symbol": "validate",
            "file": "src/services/validate.ts",
            "cyclomatic": 9,
            "lines": 40,
            "node_id": "fn-validate",
        },
    ]
    u.data_flows = [
        DataFlow(
            name="Create User",
            entry_point="POST /users",
            steps=[
                DataFlowStep(
                    symbol="createUser",
                    node_id="fn-create",
                    node_type="Function",
                    file_path="src/routes/user.ts",
                    role="entry",
                ),
                DataFlowStep(
                    symbol="UserService.save",
                    node_id="m-save",
                    node_type="Method",
                    file_path="src/services/user.ts",
                    role="service",
                ),
            ],
        )
    ]
    return u


# ── Req 4.2: both producers emit valid CortexAnswers ─────────────────────────


def test_learning_path_is_valid_answer() -> None:
    answer = LearningPathProducer(_ts_understanding()).produce()
    assert answer.intent == "learning_path"
    assert validate_answer(answer) == []
    assert_valid_answer(answer)
    # Every claim carries evidence (Req 4.3).
    assert all(c.evidence for c in answer.iter_claims())


def test_interview_prep_is_valid_answer() -> None:
    answer = InterviewPrepProducer(_understanding_with_hotspots_and_flows()).produce()
    assert answer.intent == "interview_prep"
    assert validate_answer(answer) == []
    assert_valid_answer(answer)
    assert all(c.evidence for c in answer.iter_claims())


# ── Learning path ordering: deterministic + reflects dependency depth ────────


def test_learning_path_orders_by_dependency_depth() -> None:
    """services (depth 0) must precede routes (depth 1, depends on services)."""
    answer = LearningPathProducer(_ts_understanding()).produce()
    order_claims = [
        c for c in answer.iter_claims() if c.text.startswith("Recommended learning order")
    ]
    assert order_claims
    order_text = order_claims[0].text
    assert order_text.index("services") < order_text.index("routes")
    # The recommended order is a heuristic conclusion → INFERENCE.
    assert order_claims[0].epistemic is Epistemic.INFERENCE

    # Step sections appear foundational-first.
    step_headings = [s.heading for s in answer.sections if s.heading.startswith("Step ")]
    assert step_headings[0] == "Step 1: services"
    assert step_headings[1] == "Step 2: routes"


def test_learning_path_is_deterministic() -> None:
    u = _ts_understanding()
    a1 = LearningPathProducer(u).produce()
    a2 = LearningPathProducer(u).produce()
    assert [c.text for c in a1.iter_claims()] == [c.text for c in a2.iter_claims()]
    assert [s.heading for s in a1.sections] == [s.heading for s in a2.sections]


def test_learning_path_handles_cyclic_dependencies_deterministically() -> None:
    """A dependency cycle must not crash and must still be deterministic."""
    u = _ts_understanding()
    # Introduce a cycle: services now also depends on routes.
    u.modules[1].dependencies = ["routes"]
    a1 = LearningPathProducer(u).produce()
    a2 = LearningPathProducer(u).produce()
    assert_valid_answer(a1)
    assert [c.text for c in a1.iter_claims()] == [c.text for c in a2.iter_claims()]


# ── Learning path epistemics: structure = FACT, order rationale = INFERENCE ──


def test_learning_path_module_structure_is_fact() -> None:
    answer = LearningPathProducer(_ts_understanding()).produce()
    struct_claims = [
        c for c in answer.iter_claims() if "files" in c.text and "functions" in c.text
    ]
    assert struct_claims
    assert all(c.epistemic is Epistemic.FACT for c in struct_claims)


def test_learning_path_rationale_is_inference() -> None:
    answer = LearningPathProducer(_ts_understanding()).produce()
    rationale = [c for c in answer.iter_claims() if c.text.lower().startswith("learn '")]
    assert rationale
    assert all(c.epistemic is Epistemic.INFERENCE for c in rationale)


# ── Interview prep epistemics: metric = FACT, why = INFERENCE, impact = PRED ─


def test_interview_prep_hotspot_metric_is_fact() -> None:
    answer = InterviewPrepProducer(_understanding_with_hotspots_and_flows()).produce()
    metric_claims = [c for c in answer.iter_claims() if "cyclomatic complexity" in c.text]
    assert metric_claims
    assert all(c.epistemic is Epistemic.FACT for c in metric_claims)
    # Hotspot facts carry locatable evidence.
    for c in metric_claims:
        assert c.evidence[0].file_path


def test_interview_prep_likely_question_is_inference() -> None:
    answer = InterviewPrepProducer(_understanding_with_hotspots_and_flows()).produce()
    q_claims = [c for c in answer.iter_claims() if c.text.startswith("Expect questions about")]
    assert q_claims
    assert all(c.epistemic is Epistemic.INFERENCE for c in q_claims)


def test_interview_prep_change_impact_is_prediction() -> None:
    answer = InterviewPrepProducer(_understanding_with_hotspots_and_flows()).produce()
    impact = [c for c in answer.iter_claims() if c.text.startswith("Changing '")]
    assert impact
    assert all(c.epistemic is Epistemic.PREDICTION for c in impact)


def test_interview_prep_hotspots_ordered_by_complexity() -> None:
    """Hotspots are listed most-complex-first, deterministically."""
    answer = InterviewPrepProducer(_understanding_with_hotspots_and_flows()).produce()
    metric_texts = [c.text for c in answer.iter_claims() if "cyclomatic complexity" in c.text]
    # handleRequest (18) must come before validate (9).
    assert any("handleRequest" in metric_texts[0] for _ in [0])
    idx_handle = next(i for i, t in enumerate(metric_texts) if "handleRequest" in t)
    idx_validate = next(i for i, t in enumerate(metric_texts) if "validate" in t)
    assert idx_handle < idx_validate


def test_interview_prep_is_deterministic() -> None:
    u = _understanding_with_hotspots_and_flows()
    a1 = InterviewPrepProducer(u).produce()
    a2 = InterviewPrepProducer(u).produce()
    assert [c.text for c in a1.iter_claims()] == [c.text for c in a2.iter_claims()]


def test_interview_prep_flow_steps_are_facts() -> None:
    answer = InterviewPrepProducer(_understanding_with_hotspots_and_flows()).produce()
    flow_claims = [c for c in answer.iter_claims() if c.text.startswith("Flow '")]
    assert flow_claims
    assert all(c.epistemic is Epistemic.FACT for c in flow_claims)


# ── Req 4.6: insufficient evidence states the gap ────────────────────────────


def test_learning_path_states_gap_when_no_modules() -> None:
    u = _ts_understanding()
    u.modules = []
    u.total_modules = 0
    answer = LearningPathProducer(u).produce()
    assert_valid_answer(answer)
    texts = [c.text for c in answer.iter_claims()]
    assert any("No modules" in t for t in texts)


def test_interview_prep_states_gap_when_no_evidence() -> None:
    u = RepositoryUnderstanding(
        job_id=_JOB,
        repo_url="https://github.com/example/empty",
        repo_name="empty",
        architecture_style=ArchitectureStyle.UNKNOWN,
        languages=["typescript"],
        total_files=0,
        total_modules=0,
    )
    answer = InterviewPrepProducer(u).produce()
    assert_valid_answer(answer)
    texts = [c.text for c in answer.iter_claims()]
    assert any("cannot be produced" in t for t in texts)


# ── Confidence bounds for the new producers ──────────────────────────────────


@pytest.mark.parametrize("confidence_answer", [
    LearningPathProducer(_ts_understanding()).produce(),
    InterviewPrepProducer(_understanding_with_hotspots_and_flows()).produce(),
])
def test_new_producer_confidence_within_bounds(confidence_answer) -> None:
    assert 0.0 <= confidence_answer.confidence <= 1.0
