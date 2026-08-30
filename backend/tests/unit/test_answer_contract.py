"""Tests for the CortexAnswer domain contract (Req 4.1, Req 4.3, Req 5.1, Req 5.5)."""

import pytest
from cortex.reasoning.domain.answer import (
    AnswerSection,
    AnswerValidationError,
    Claim,
    CortexAnswer,
    Epistemic,
    Evidence,
    NextAction,
    NextActionKind,
    assert_valid_answer,
    validate_answer,
)


def _fact_evidence() -> Evidence:
    return Evidence(file_path="src/app/service.py", line_start=10, line_end=20, node_id="n1")


def _valid_answer() -> CortexAnswer:
    """A well-formed answer with one FACT, one INFERENCE, one PREDICTION."""
    return CortexAnswer(
        intent="module_breakdown",
        title="Module Breakdown",
        summary="The service layer coordinates repositories and controllers.",
        sections=[
            AnswerSection(
                heading="Structure",
                claims=[
                    Claim(
                        text="service.py defines UserService.",
                        epistemic=Epistemic.FACT,
                        evidence=[_fact_evidence()],
                    ),
                    Claim(
                        text="This module plays a core application role.",
                        epistemic=Epistemic.INFERENCE,
                        evidence=[Evidence(file_path="src/app/service.py")],
                    ),
                    Claim(
                        text="Changing it would ripple into the API layer.",
                        epistemic=Epistemic.PREDICTION,
                        evidence=[Evidence(file_path="src/app/service.py")],
                    ),
                ],
            )
        ],
        confidence=0.8,
        coverage_note=None,
        next_actions=[
            NextAction(
                label="Open service.py",
                kind=NextActionKind.OPEN_FILE,
                target="src/app/service.py",
                line_start=10,
                line_end=20,
            )
        ],
    )


# ── Dataclass shape ──────────────────────────────────────────────────────────


def test_epistemic_enum_has_three_members() -> None:
    assert {e.name for e in Epistemic} == {"FACT", "INFERENCE", "PREDICTION"}


def test_cortex_answer_holds_full_shape() -> None:
    answer = _valid_answer()
    assert answer.intent == "module_breakdown"
    assert answer.title == "Module Breakdown"
    assert answer.summary
    assert isinstance(answer.sections[0], AnswerSection)
    assert 0.0 <= answer.confidence <= 1.0
    assert answer.coverage_note is None
    assert isinstance(answer.next_actions[0], NextAction)


def test_defaults_are_independent_lists() -> None:
    a = CortexAnswer(intent="x", title="t", summary="s")
    b = CortexAnswer(intent="x", title="t", summary="s")
    a.sections.append(AnswerSection(heading="h"))
    assert b.sections == []  # default_factory, not shared mutable default


def test_iter_claims_flattens_in_order() -> None:
    answer = CortexAnswer(
        intent="x",
        title="t",
        summary="s",
        sections=[
            AnswerSection(heading="A", claims=[Claim("1", Epistemic.FACT, [_fact_evidence()])]),
            AnswerSection(
                heading="B",
                claims=[Claim("2", Epistemic.INFERENCE, [_fact_evidence()])],
            ),
        ],
    )
    assert [c.text for c in answer.iter_claims()] == ["1", "2"]


# ── Validation: valid answer passes ──────────────────────────────────────────


def test_valid_answer_has_no_violations() -> None:
    assert validate_answer(_valid_answer()) == []


def test_assert_valid_answer_does_not_raise_on_valid() -> None:
    assert_valid_answer(_valid_answer())  # must not raise


# ── Validation: claim without evidence fails (Req 4.3) ───────────────────────


def test_claim_without_evidence_is_a_violation() -> None:
    answer = _valid_answer()
    answer.sections[0].claims[0].evidence = []
    errors = validate_answer(answer)
    assert errors
    assert any("no evidence" in e for e in errors)


def test_assert_valid_answer_raises_on_missing_evidence() -> None:
    answer = _valid_answer()
    answer.sections[0].claims[1].evidence = []
    with pytest.raises(AnswerValidationError):
        assert_valid_answer(answer)


# ── Validation: FACT masquerading as INFERENCE/PREDICTION rejected (Req 5.5) ──


def test_fact_with_ungrounded_evidence_is_rejected() -> None:
    """A FACT whose evidence lacks a file path is really an inference/prediction."""
    answer = _valid_answer()
    answer.sections[0].claims[0] = Claim(
        text="This is claimed as fact but only heuristically supported.",
        epistemic=Epistemic.FACT,
        evidence=[Evidence(file_path="")],  # no locatable evidence
    )
    errors = validate_answer(answer)
    assert any("tagged FACT" in e for e in errors)


def test_inference_and_prediction_may_use_file_only_evidence() -> None:
    """Non-FACT claims are not held to the strict directly-extracted standard."""
    answer = CortexAnswer(
        intent="x",
        title="t",
        summary="s",
        sections=[
            AnswerSection(
                heading="H",
                claims=[
                    Claim("role", Epistemic.INFERENCE, [Evidence(file_path="a.py")]),
                    Claim("impact", Epistemic.PREDICTION, [Evidence(file_path="a.py")]),
                ],
            )
        ],
        confidence=0.5,
    )
    assert validate_answer(answer) == []


def test_multiple_violations_are_all_reported() -> None:
    answer = CortexAnswer(
        intent="x",
        title="t",
        summary="s",
        sections=[
            AnswerSection(
                heading="H",
                claims=[
                    Claim("no evidence", Epistemic.FACT, []),
                    Claim("bad fact", Epistemic.FACT, [Evidence(file_path="")]),
                ],
            )
        ],
        confidence=0.5,
    )
    errors = validate_answer(answer)
    assert len(errors) == 2


# ── Validation: confidence bounds ────────────────────────────────────────────


@pytest.mark.parametrize("bad", [-0.1, 1.1, 2.0])
def test_confidence_out_of_range_is_a_violation(bad: float) -> None:
    answer = _valid_answer()
    answer.confidence = bad
    assert any("out of range" in e for e in validate_answer(answer))


@pytest.mark.parametrize("ok", [0.0, 0.5, 1.0])
def test_confidence_within_range_is_ok(ok: float) -> None:
    answer = _valid_answer()
    answer.confidence = ok
    assert validate_answer(answer) == []
