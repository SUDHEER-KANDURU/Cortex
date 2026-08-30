"""Render a `CortexAnswer` to markdown for streaming and NIM refinement.

This is the single place that turns the structured answer contract
(`CortexAnswer`) into human-readable markdown. Chat streams this markdown to the
client, and it is also the text handed to NIM as the authoritative DRAFT ANSWER
to reword (Req 9.2) — NIM never sees the raw dataclasses and cannot add or drop
claims, evidence, or epistemic tags because those live only in the original
`CortexAnswer`.

Zero framework dependencies — pure rendering over domain objects, consistent
with the producers and the `reasoning/domain` style.
"""

from __future__ import annotations

from cortex.reasoning.domain.answer import (
    Claim,
    CortexAnswer,
    Epistemic,
    Evidence,
)

# Human-facing labels for epistemic tags. Kept explicit so the rendered draft
# carries the FACT/INFERENCE/PREDICTION distinction into the text NIM refines
# (Req 5.6-adjacent) without NIM being able to change the underlying tag.
_EPISTEMIC_LABEL: dict[Epistemic, str] = {
    Epistemic.FACT: "Fact",
    Epistemic.INFERENCE: "Inference",
    Epistemic.PREDICTION: "Prediction",
}


def _format_evidence(evidence: list[Evidence]) -> str:
    """Render a claim's evidence pointers as a compact inline suffix."""
    parts: list[str] = []
    for ev in evidence:
        loc = ev.file_path or "repository"
        if ev.line_start is not None:
            if ev.line_end is not None and ev.line_end != ev.line_start:
                loc += f":{ev.line_start}-{ev.line_end}"
            else:
                loc += f":{ev.line_start}"
        parts.append(f"`{loc}`")
    if not parts:
        return ""
    return " (evidence: " + ", ".join(parts) + ")"


def _format_claim(claim: Claim) -> str:
    label = _EPISTEMIC_LABEL.get(claim.epistemic, claim.epistemic.value.title())
    return f"- [{label}] {claim.text}{_format_evidence(claim.evidence)}"


def render_answer_markdown(answer: CortexAnswer) -> str:
    """Render a `CortexAnswer` to markdown.

    Layout: title, summary, each section as a heading with its claims (every
    claim prefixed by its epistemic tag and suffixed with its evidence), a
    coverage note when present, and suggested next actions. This is the exact
    text streamed to the user offline and handed to NIM for wording refinement.
    """
    lines: list[str] = [f"## {answer.title}", ""]

    if answer.summary:
        lines.append(answer.summary)
        lines.append("")

    for section in answer.sections:
        lines.append(f"### {section.heading}")
        for claim in section.claims:
            lines.append(_format_claim(claim))
        lines.append("")

    if answer.coverage_note:
        lines.append(f"> Coverage: {answer.coverage_note}")
        lines.append("")

    if answer.next_actions:
        lines.append("**Suggested next:**")
        for action in answer.next_actions:
            lines.append(f"- {action.label}")
        lines.append("")

    # Trim a single trailing blank line for tidy output.
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)
