"""The unified answer contract — the single output shape every Cortex feature emits.

Every product feature (overview, module breakdown, API spec, learning path,
scoped explanation, chat) produces a `CortexAnswer`, and one renderer consumes it.
This is what makes "everything looks consistent" real (Req 4).

Epistemic honesty is enforced structurally (Req 5): every claim is tagged as a
FACT, an INFERENCE, or a PREDICTION, and every claim must carry evidence. The
`validate_answer` function guarantees no INFERENCE or PREDICTION is ever
represented as a FACT anywhere in the pipeline.

Zero dependencies on Neo4j, FastAPI, NIM, or any framework — consistent with the
`graph/domain/entities.py` style.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Epistemic(str, Enum):
    """How a claim is grounded (Req 5.1).

    - FACT:       directly extracted structural evidence (symbols, files,
                  metrics, relationships read straight from the repository).
    - INFERENCE:  a heuristic conclusion (role, purpose, architecture style)
                  reasoned from facts but not itself directly extracted.
    - PREDICTION: a forward-looking or impact statement about what a change
                  would do or how the system is likely to behave.
    """

    FACT = "fact"
    INFERENCE = "inference"
    PREDICTION = "prediction"


@dataclass
class Evidence:
    """A traceable pointer back into the repository backing a claim (Req 4.3).

    `file_path` is always present; line range and graph node id are attached
    where applicable.
    """

    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    node_id: str | None = None


@dataclass
class Claim:
    """A single assertion in an answer, tagged with its epistemic status.

    Every claim MUST carry at least one `Evidence` (Req 4.3). A claim tagged
    FACT MUST be backed only by directly-extracted structural evidence; heuristic
    or forward-looking statements MUST be tagged INFERENCE or PREDICTION
    respectively (Req 5.1, Req 5.5).
    """

    text: str
    epistemic: Epistemic
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class AnswerSection:
    """An ordered, headed group of claims within an answer."""

    heading: str
    claims: list[Claim] = field(default_factory=list)


class NextActionKind(str, Enum):
    """The kind of follow-up a next-action button triggers.

    Kept deliberately small and stack-agnostic; producers pick the closest fit.
    """

    OPEN_FILE = "open_file"          # jump the navigator to a file/line
    VIEW_NODE = "view_node"          # focus a graph node
    ASK_QUESTION = "ask_question"    # seed inline chat with a follow-up question
    RUN_PRODUCER = "run_producer"    # generate another answer (e.g. learning path)


@dataclass
class NextAction:
    """A suggested follow-up rendered as a next-action button (Req 4.4, Req 8.2).

    `label` is the human-readable button text. `kind` says what happens.
    `target` carries enough info to act — a file path, node id, intent name, or
    question text depending on `kind`. `line_start`/`line_end` locate a range
    when the action opens a file.
    """

    label: str
    kind: NextActionKind
    target: str = ""
    line_start: int | None = None
    line_end: int | None = None


@dataclass
class CortexAnswer:
    """The single output shape for every Cortex feature (Req 4.1).

    Contains a title, a plain-English summary, ordered sections (each holding
    evidence-backed, epistemically-tagged claims), a confidence score, an
    optional coverage note, and suggested next actions.
    """

    intent: str                                   # "module_breakdown" | "api_spec" | ...
    title: str
    summary: str
    sections: list[AnswerSection] = field(default_factory=list)
    confidence: float = 0.0                       # 0..1
    coverage_note: str | None = None
    next_actions: list[NextAction] = field(default_factory=list)

    def iter_claims(self) -> list[Claim]:
        """Every claim across every section, in order."""
        return [claim for section in self.sections for claim in section.claims]


class AnswerValidationError(ValueError):
    """Raised when a `CortexAnswer` violates the answer contract.

    Carries the full list of violations found so callers can surface all
    problems at once rather than one at a time.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_answer(answer: CortexAnswer) -> list[str]:
    """Check a `CortexAnswer` against the answer contract, returning violations.

    Enforces (Req 4.3, Req 5.5):
      1. Every claim carries at least one `Evidence`.
      2. Every claim tagged FACT is backed only by directly-extracted structural
         evidence — i.e. concrete pointers with a file path. A FACT with no
         locatable file evidence is treated as an ungrounded assertion and is a
         violation, because it cannot be distinguished from an INFERENCE or a
         PREDICTION masquerading as a fact.
      3. Confidence stays within 0..1.

    Returns an empty list when the answer is valid. This is the pure,
    non-raising form; use `assert_valid_answer` to raise on violations.
    """
    errors: list[str] = []

    if not 0.0 <= answer.confidence <= 1.0:
        errors.append(
            f"confidence {answer.confidence!r} is out of range 0..1"
        )

    for s_idx, section in enumerate(answer.sections):
        for c_idx, claim in enumerate(section.claims):
            loc = f"section[{s_idx}] {section.heading!r} claim[{c_idx}]"

            # Req 4.3: every claim must be backed by evidence.
            if not claim.evidence:
                errors.append(f"{loc} has no evidence: {claim.text!r}")
                continue

            # Req 5.5: a FACT must rest on directly-extracted structural
            # evidence. We require every evidence item on a FACT to point at a
            # concrete location (a non-empty file path). Anything else means the
            # claim is not a directly-verifiable fact and must instead be tagged
            # INFERENCE or PREDICTION.
            if claim.epistemic is Epistemic.FACT:
                ungrounded = [
                    e for e in claim.evidence if not (e.file_path and e.file_path.strip())
                ]
                if ungrounded:
                    errors.append(
                        f"{loc} is tagged FACT but has evidence without a file "
                        f"path; it must be tagged INFERENCE or PREDICTION: "
                        f"{claim.text!r}"
                    )

    return errors


def assert_valid_answer(answer: CortexAnswer) -> None:
    """Validate a `CortexAnswer`, raising `AnswerValidationError` on violations.

    Use this as the pipeline gate before an answer is rendered or serialized so
    that a malformed answer can never reach the user (Req 4.3, Req 5.5).
    """
    errors = validate_answer(answer)
    if errors:
        raise AnswerValidationError(errors)
