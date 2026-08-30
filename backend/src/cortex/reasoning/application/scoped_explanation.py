"""ScopedExplanationProducer — explain a file + line range as a `CortexAnswer`.

This backs the Code Navigator's inline chat (Req 7.3, Req 7.4): a user selects a
range of lines in a file and asks a question; Cortex resolves that selection to
the graph node(s) whose span overlaps those lines, then produces a single
`CortexAnswer` grounded entirely in repository evidence.

Design contract (mirrors the other producers in ``producers.py``):
  - The output is a `CortexAnswer` that always passes ``assert_valid_answer`` —
    every claim carries `Evidence` and no INFERENCE/PREDICTION is emitted as a
    FACT (Req 4.3, Req 5.5).
  - Epistemic tagging follows the fixed rule set: directly-extracted structure
    (the resolved symbol, its file/line span, its callers/callees read straight
    from the graph) → FACT; the inferred architectural role/purpose → INFERENCE.
  - Deterministic: same graph + same range → same answer. No IO, no NIM.

Line-range → node resolution:
  FUNCTION/METHOD/CLASS/ENDPOINT/TEST nodes carry a ``line`` property (the 1-based
  start line) and a ``lines`` property (line count), so a symbol occupies
  ``[line, line + lines - 1]``. A selection ``[line_start, line_end]`` resolves to
  every symbol node in the target file whose span intersects the selection; the
  most specific (smallest-span, innermost) match is chosen. When no inner symbol
  matches, the whole file node is used as a fallback scope so a question over
  imports/module-level code still gets an answer (Req 7.3).

Callers/callees/role reuse the same graph indexes the `CortexExplainer` uses
(``_Index``) rather than duplicating traversal logic (Req 7.4).
"""

from __future__ import annotations

from cortex.graph.domain.entities import GraphEdge, GraphNode, NodeType
from cortex.insights.domain.severity import classify_role
from cortex.reasoning.application.explainer import _humanize_role, _Index
from cortex.reasoning.application.producers import LOW_CONFIDENCE_THRESHOLD
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

# Node types that represent a locatable code symbol with a line span.
_SYMBOL_TYPES = (
    NodeType.FUNCTION,
    NodeType.METHOD,
    NodeType.ENDPOINT,
    NodeType.TEST,
    NodeType.CLASS,
    NodeType.INTERFACE,
    NodeType.ENUM,
)


def _prop(node: GraphNode, key: str, default: object = None) -> object:
    return node.properties.get(key, default)


def _int_prop(node: GraphNode, key: str, default: int = 0) -> int:
    try:
        return int(_prop(node, key, default) or default)
    except (TypeError, ValueError):
        return default


def _str_prop(node: GraphNode, key: str) -> str:
    return str(_prop(node, key, "") or "")


def _node_file(node: GraphNode) -> str:
    """The repository path a node lives in.

    FILE nodes store their path under ``path``; symbol nodes store the owning
    file under ``file``. Fall back across both so callers need not care.
    """
    return _str_prop(node, "file") or _str_prop(node, "path")


def _node_span(node: GraphNode) -> tuple[int, int] | None:
    """The 1-based inclusive ``(start, end)`` line span of a node, if known.

    Symbol nodes carry ``line`` (start) and ``lines`` (count); a FILE node
    spans ``[1, lines]``. Returns ``None`` when no span can be determined.
    """
    lines = _int_prop(node, "lines")
    if node.node_type == NodeType.FILE:
        return (1, lines) if lines > 0 else None

    start = _int_prop(node, "line")
    if start <= 0:
        return None
    # A node with a known count spans [start, start + count - 1]; a node with a
    # start but no count is treated as a single line.
    end = start + lines - 1 if lines > 0 else start
    return (start, max(start, end))


def _spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def _same_file(node_path: str, target_path: str) -> bool:
    """Tolerant path comparison (normalises separators, ignores case on Windows)."""
    def norm(p: str) -> str:
        return p.replace("\\", "/").strip().lower()

    np, tp = norm(node_path), norm(target_path)
    if not np or not tp:
        return False
    # Exact, or one is a suffix of the other (handles repo-relative vs. absolute).
    return np == tp or np.endswith("/" + tp) or tp.endswith("/" + np)


def _low_confidence_note(confidence: float) -> str | None:
    """Surface a caveat when a scoped explanation rests on thin evidence (Req 6.3).

    A scoped explanation is grounded in a single resolved symbol; when few
    corroborating signals exist (no span, no callers, no callees) its confidence
    stays below :data:`LOW_CONFIDENCE_THRESHOLD` and the reader is told plainly
    that the explanation is provisional. Returns ``None`` for a well-grounded
    explanation so no spurious caveat appears.
    """
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        return (
            f"Confidence is low ({confidence:.0%}); this explanation rests on "
            "limited surrounding evidence (few resolved callers/callees) and "
            "should be treated as provisional."
        )
    return None


def resolve_scope_nodes(
    file_path: str,
    line_start: int,
    line_end: int,
    nodes: list[GraphNode],
) -> list[GraphNode]:
    """Resolve a file + line range to the graph node(s) at those lines (Req 7.3).

    Returns the most-specific symbol node(s) in ``file_path`` whose line span
    intersects ``[line_start, line_end]``. "Most specific" means the smallest
    span among the overlapping symbols — the innermost function/method the
    selection touches — with ties broken deterministically by ``(start, id)``.
    Several nodes may share the smallest span (e.g. overlapping selections), so a
    list is returned.

    When no inner symbol overlaps the selection, the enclosing FILE node is
    returned as a whole-file fallback scope so module-level code still resolves
    to something (Req 7.3). Returns an empty list only when the file itself is
    not in the graph.
    """
    lo, hi = (line_start, line_end) if line_start <= line_end else (line_end, line_start)
    selection = (lo, hi)

    symbols: list[tuple[int, tuple[int, int], GraphNode]] = []
    file_node: GraphNode | None = None

    for node in nodes:
        if not _same_file(_node_file(node), file_path):
            continue
        if node.node_type == NodeType.FILE:
            file_node = node
            continue
        if node.node_type not in _SYMBOL_TYPES:
            continue
        span = _node_span(node)
        if span is None or not _spans_overlap(span, selection):
            continue
        size = span[1] - span[0]
        symbols.append((size, span, node))

    if symbols:
        smallest = min(size for size, _, _ in symbols)
        matched = [
            node
            for size, _, node in symbols
            if size == smallest
        ]
        # Deterministic ordering by start line then id.
        matched.sort(key=lambda n: (_int_prop(n, "line"), n.id))
        return matched

    # Whole-file fallback (Req 7.3): the selection hit no inner symbol.
    return [file_node] if file_node is not None else []


class ScopedExplanationProducer:
    """Produce a scoped explanation for a file + line range as a `CortexAnswer`.

    Pure computation over graph nodes/edges — no database, no HTTP, no NIM,
    consistent with the other producers. Construct with the job's graph, then
    call :meth:`produce`.
    """

    intent = "scoped_explanation"

    def __init__(
        self,
        nodes: list[GraphNode] | None = None,
        edges: list[GraphEdge] | None = None,
    ) -> None:
        self.nodes = nodes or []
        self.edges = edges or []
        self._index = _Index(self.nodes, self.edges)

    def produce(
        self,
        file_path: str,
        line_start: int,
        line_end: int,
        question: str = "",
    ) -> CortexAnswer:
        """Resolve the selection and build a validated `CortexAnswer` (Req 7.3)."""
        answer = self._build(file_path, line_start, line_end, question)
        assert_valid_answer(answer)
        return answer

    # ── internals ─────────────────────────────────────────────────────────────

    def _build(
        self,
        file_path: str,
        line_start: int,
        line_end: int,
        question: str,
    ) -> CortexAnswer:
        matched = resolve_scope_nodes(file_path, line_start, line_end, self.nodes)

        if not matched:
            # The file is not in the analysed graph: state the gap (Req 4.6)
            # rather than fabricate an explanation.
            return self._gap_answer(file_path, line_start, line_end, question)

        primary = matched[0]
        sections: list[AnswerSection] = []

        # ── selection → resolved symbol(s) (directly extracted → FACT) ─────────
        sections.append(self._scope_section(matched, file_path, line_start, line_end))

        # ── inferred role (heuristic → INFERENCE) ─────────────────────────────
        sections.append(self._role_section(primary))

        # ── callers / callees (relationships read from the graph → FACT) ──────
        sections.append(self._callers_section(primary))
        sections.append(self._callees_section(primary))

        title, summary = self._title_summary(primary, file_path, line_start, line_end, question)

        confidence = self._confidence(primary)
        return CortexAnswer(
            intent=self.intent,
            title=title,
            summary=summary,
            sections=sections,
            confidence=confidence,
            coverage_note=_low_confidence_note(confidence),
            next_actions=self._next_actions(primary),
        )

    # ── evidence helpers ──────────────────────────────────────────────────────

    def _evidence_for(self, node: GraphNode) -> Evidence:
        span = _node_span(node)
        return Evidence(
            file_path=_node_file(node) or node.label,
            line_start=span[0] if span else None,
            line_end=span[1] if span else None,
            node_id=node.id,
        )

    # ── sections ───────────────────────────────────────────────────────────────

    def _scope_section(
        self,
        matched: list[GraphNode],
        file_path: str,
        line_start: int,
        line_end: int,
    ) -> AnswerSection:
        claims: list[Claim] = []
        for node in matched:
            span = _node_span(node)
            span_text = (
                f"lines {span[0]}–{span[1]}" if span else "an unknown line range"
            )
            if node.node_type == NodeType.FILE:
                text = (
                    f"The selection (lines {line_start}–{line_end}) does not fall inside "
                    f"a specific symbol, so it is explained at file scope: "
                    f"`{node.label}` ({span_text})."
                )
            else:
                kind = node.node_type.value.lower()
                text = (
                    f"The selection resolves to the {kind} `{node.label}` "
                    f"({span_text} of {_node_file(node)})."
                )
            claims.append(
                Claim(text=text, epistemic=Epistemic.FACT, evidence=[self._evidence_for(node)])
            )
        return AnswerSection(heading="Selected code", claims=claims)

    def _role_section(self, node: GraphNode) -> AnswerSection:
        role = classify_role(
            _node_file(node) or node.label,
            endpoint_count=_int_prop(node, "endpoints")
            or (1 if node.node_type == NodeType.ENDPOINT else 0),
        )
        role_h = _humanize_role(role)
        text = (
            f"`{node.label}` appears to play the role of the {role_h}, inferred from its "
            "location and shape in the codebase."
        )
        return AnswerSection(
            heading="Inferred role",
            claims=[
                Claim(
                    text=text,
                    epistemic=Epistemic.INFERENCE,
                    evidence=[self._evidence_for(node)],
                )
            ],
        )

    def _callers_section(self, node: GraphNode) -> AnswerSection:
        callers = self._index.symbol_callers(node.id)
        ev = self._evidence_for(node)
        if callers:
            shown = ", ".join(f"`{c}`" for c in callers[:8])
            text = (
                f"`{node.label}` is called or depended on by {len(callers)} symbol(s): "
                f"{shown}" + ("…" if len(callers) > 8 else "") + "."
            )
        else:
            text = (
                f"No callers of `{node.label}` were found in the analysed graph — nothing "
                "recorded calls or depends on it directly."
            )
        return AnswerSection(
            heading="Callers",
            claims=[Claim(text=text, epistemic=Epistemic.FACT, evidence=[ev])],
        )

    def _callees_section(self, node: GraphNode) -> AnswerSection:
        ev = self._evidence_for(node)
        callee_labels = self._callee_labels(node)
        if callee_labels:
            shown = ", ".join(f"`{c}`" for c in callee_labels[:8])
            text = (
                f"`{node.label}` calls {len(callee_labels)} symbol(s): {shown}"
                + ("…" if len(callee_labels) > 8 else "")
                + "."
            )
        else:
            text = (
                f"No outbound calls from `{node.label}` were resolved in the graph — it "
                "does not call other tracked symbols."
            )
        return AnswerSection(
            heading="Callees",
            claims=[Claim(text=text, epistemic=Epistemic.FACT, evidence=[ev])],
        )

    def _callee_labels(self, node: GraphNode) -> list[str]:
        """Labels of the symbols this node directly calls (resolved CALLS edges).

        For a FILE scope, aggregates the outbound calls made by the symbols it
        contains (reusing the explainer's file-level index). For a symbol node,
        resolves its own CALLS edges to labels.
        """
        if node.node_type == NodeType.FILE:
            return sorted(self._index.outgoing_calls_from_file(node.id))
        labels: list[str] = []
        for callee_id in self._index._callees(node.id):
            target = self._index.by_id.get(callee_id)
            if target is not None and target.id != node.id:
                labels.append(target.label)
        # De-dup, preserve order.
        return list(dict.fromkeys(labels))

    # ── framing ────────────────────────────────────────────────────────────────

    def _title_summary(
        self,
        node: GraphNode,
        file_path: str,
        line_start: int,
        line_end: int,
        question: str,
    ) -> tuple[str, str]:
        name = (file_path.replace("\\", "/").split("/")[-1]) or file_path
        title = f"Explanation — {node.label} ({name}:{line_start}–{line_end})"
        if node.node_type == NodeType.FILE:
            summary = (
                f"Whole-file explanation of `{name}` for the selected lines "
                f"{line_start}–{line_end}."
            )
        else:
            summary = (
                f"Scoped explanation of the {node.node_type.value.lower()} "
                f"`{node.label}` covering lines {line_start}–{line_end} of `{name}`."
            )
        if question.strip():
            summary = f"{summary} In response to: “{question.strip()}”."
        return title, summary

    def _next_actions(self, node: GraphNode) -> list[NextAction]:
        span = _node_span(node)
        actions = [
            NextAction(
                label=f"Open {node.label}",
                kind=NextActionKind.OPEN_FILE,
                target=_node_file(node) or node.label,
                line_start=span[0] if span else None,
                line_end=span[1] if span else None,
            ),
            NextAction(
                label=f"View {node.label} in the graph",
                kind=NextActionKind.VIEW_NODE,
                target=node.id,
            ),
        ]
        return actions

    def _confidence(self, node: GraphNode) -> float:
        """Confidence tied to how much evidence backs the scoped explanation."""
        score = 0.4
        if _node_span(node) is not None:
            score += 0.2
        if self._index.symbol_callers(node.id):
            score += 0.2
        if self._callee_labels(node):
            score += 0.15
        return round(min(0.95, score), 2)

    def _gap_answer(
        self,
        file_path: str,
        line_start: int,
        line_end: int,
        question: str,
    ) -> CortexAnswer:
        name = (file_path.replace("\\", "/").split("/")[-1]) or file_path
        gap = (
            f"`{file_path}` is not present in the analysed graph, so lines "
            f"{line_start}–{line_end} cannot be resolved to a code symbol."
        )
        return CortexAnswer(
            intent=self.intent,
            title=f"Explanation — {name}:{line_start}–{line_end}",
            summary="The selected file was not found in the analysed repository graph.",
            sections=[
                AnswerSection(
                    heading="No matching code",
                    claims=[
                        Claim(
                            text=gap,
                            epistemic=Epistemic.FACT,
                            evidence=[Evidence(file_path=file_path or "repository")],
                        )
                    ],
                )
            ],
            confidence=0.3,
            coverage_note="The file could not be located in the analysed graph.",
            next_actions=[],
        )
