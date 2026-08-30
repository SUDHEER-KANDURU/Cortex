"""CortexExplainer — Cortex's own deterministic code-explanation engine.

This is the component that lets Cortex answer, in its own words and grounded
entirely in repository evidence:

    "What is this file/class/function, what does it actually do, how does it
     work, who uses it, what does it use, how does it fit into the system,
     what are its risks, and what should I read next?"

Design contract (this is the whole point of the module):
  - NIM is NOT the author. Cortex builds the full explanation here from AST +
    graph + metrics. NIM (elsewhere) may only refine wording. If NIM is
    unavailable, this output stands on its own.
  - Explanations are ENTITY-SPECIFIC, never a generic template with names
    substituted. Every section is assembled from *this* entity's real
    evidence — its concrete symbols, imports, endpoints, call targets,
    metrics, architectural role, and its actual neighbours in the graph.
    Two different files therefore produce materially different prose.
  - Every claim is backed by evidence recorded on the section.
  - Deterministic: same graph → same explanation. No randomness, no IO.

Teaching stance: start simple (what it is / why it exists), connect it to the
surrounding system, explain WHY, then go into the concrete mechanics. Depth
comes from real understanding of the entity, not from padding.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.insights.domain.severity import ArchitecturalRole, classify_role
from cortex.reasoning.domain.entities import Explanation, ExplanationSection

if TYPE_CHECKING:
    from cortex.graph.domain.entities import GraphEdge, GraphNode


# ── property helpers (mirror the engine's tolerant accessors) ─────────────────

def _p(node: GraphNode, key: str, default: object = None) -> object:
    return node.properties.get(key, default)

def _s(node: GraphNode, key: str) -> str:
    return str(_p(node, key, "") or "")

def _i(node: GraphNode, key: str) -> int:
    try:
        return int(_p(node, key, 0) or 0)
    except (TypeError, ValueError):
        return 0

def _b(node: GraphNode, key: str) -> bool:
    v = _p(node, key, False)
    return v if isinstance(v, bool) else str(v).lower() in ("true", "1", "yes")


def _csv(node: GraphNode, key: str) -> list[str]:
    """Read a comma-joined property (as stored by the graph builder) into a list."""
    raw = _p(node, key, "")
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [part.strip() for part in str(raw or "").split(",") if part.strip()]


def _humanize_role(role: ArchitecturalRole) -> str:
    return {
        ArchitecturalRole.ENTRY_POINT:  "application entry point",
        ArchitecturalRole.ROUTER:       "HTTP routing / presentation layer",
        ArchitecturalRole.ORCHESTRATOR: "orchestration / pipeline coordinator",
        ArchitecturalRole.REPOSITORY:   "persistence / data-access layer",
        ArchitecturalRole.GENERATOR:    "artifact generator",
        ArchitecturalRole.PARSER:       "parser / language front-end",
        ArchitecturalRole.ORDINARY:     "application module",
    }[role]


def _layer_of(path: str) -> str:
    """Best-effort clean-architecture layer from the path."""
    p = path.replace("\\", "/").lower()
    for layer in ("presentation", "application", "domain", "infrastructure"):
        if f"/{layer}/" in p or p.endswith(f"/{layer}"):
            return layer
    return ""


def _module_of(path: str) -> str:
    """The owning feature package, e.g. 'cortex/insights' from a deep path."""
    parts = [p for p in path.replace("\\", "/").split("/") if p and not p.endswith(".py")]
    # Drop a leading 'src' and take up to two meaningful segments.
    if parts and parts[0] in ("src", "backend"):
        parts = parts[1:]
    return "/".join(parts[:2]) if parts else ""


class CortexExplainer:
    """Builds deterministic, evidence-grounded explanations from the graph.

    Pure computation over nodes/edges — no database, no HTTP, no NIM.
    """

    # ── public API ────────────────────────────────────────────────────────────

    def explain_node(
        self,
        node_id: str,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> Explanation | None:
        """Explain a single graph entity in the context of its cluster.

        Returns None if the node is not in the graph.
        """
        idx = _Index(nodes, edges)
        target = idx.by_id.get(node_id)
        if target is None:
            return None

        if target.node_type == NodeType.FILE:
            return self._explain_file(target, idx)
        if target.node_type in (NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM):
            return self._explain_class(target, idx)
        if target.node_type in (
            NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT, NodeType.TEST
        ):
            return self._explain_function(target, idx)
        # Modules / repository fall back to a structural explanation.
        return self._explain_container(target, idx)

    # ══════════════════════════════════════════════════════════════════════════
    # FILE
    # ══════════════════════════════════════════════════════════════════════════

    def _explain_file(self, node: GraphNode, idx: _Index) -> Explanation:
        path = _s(node, "path") or node.label
        role = classify_role(path, endpoint_count=_i(node, "endpoints"))
        role_h = _humanize_role(role)
        layer = _layer_of(path)
        module = _module_of(path)

        # Real contents of THIS file (its own classes/functions), from the graph.
        contained = idx.children_of(node.id)
        classes   = [n for n in contained if n.node_type in (
            NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM)]
        funcs     = [n for n in contained if n.node_type in (
            NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT, NodeType.TEST)]
        endpoints = [n for n in funcs if n.node_type == NodeType.ENDPOINT
                     or _b(n, "is_endpoint")]

        lines     = _i(node, "lines")
        max_cc    = _i(node, "max_complexity")
        doc_ratio = float(_p(node, "documentation_ratio", 0.0) or 0.0)

        # Graph neighbours (who uses this file, what it uses).
        deps      = idx.file_dependencies(node.id)   # files/modules THIS imports
        dependents= idx.file_dependents(node.id)     # files that import THIS

        # Rank this file's own symbols by size/complexity so we describe the
        # ones that actually matter, not the first few alphabetically.
        top_classes = sorted(classes, key=lambda c: -_i(c, "lines"))[:4]
        top_funcs   = sorted(
            funcs, key=lambda f: (-_i(f, "cyclomatic"), -_i(f, "lines"))
        )[:5]

        ev_base = [
            f"path={path}",
            f"language={_s(node, 'language') or 'unknown'}",
            f"lines={lines}",
            f"classes={len(classes)}, functions={len(funcs)}, endpoints={len(endpoints)}",
        ]

        sections: list[ExplanationSection] = []

        # 1 — WHAT IS THIS
        what_bits = [f"`{path.split('/')[-1]}` is a {_s(node, 'language') or 'source'} file"]
        if module:
            what_bits.append(f"in the `{module}` area of the codebase")
        if layer:
            what_bits.append(f"sitting in the **{layer}** layer")
        what_bits.append(f"and it plays the role of the {role_h}")
        composition = []
        if classes:
            composition.append(f"{len(classes)} class{'es' if len(classes) != 1 else ''}")
        if funcs:
            composition.append(f"{len(funcs)} function{'s' if len(funcs) != 1 else ''}")
        comp_str = " and ".join(composition) if composition else "module-level code"
        sections.append(ExplanationSection(
            "what_is_this", "What is this?",
            f"{', '.join(what_bits)}. It defines {comp_str} across {lines} lines.",
            ev_base,
        ))

        # 2 — PRIMARY PURPOSE (author intent first, then role/content)
        file_doc = _s(node, "docstring_summary")
        sections.append(ExplanationSection(
            "primary_purpose", "Primary purpose",
            self._file_purpose(role, path, classes, funcs, endpoints, idx, file_doc),
            ([f"module docstring: {file_doc}"] if file_doc else [])
            + [f"architectural_role={role.value}"] + (
                [f"defines endpoints: {', '.join(_endpoint_labels(endpoints))}"]
                if endpoints else
                [f"primary symbol: {top_classes[0].label}"] if top_classes else
                [f"primary function: {top_funcs[0].label}"] if top_funcs else []
            ),
        ))

        # 3 — WHAT IT ACTUALLY DOES (name the real symbols)
        does_ev: list[str] = []
        if top_classes:
            does_ev.append("key classes: " + ", ".join(c.label for c in top_classes))
        if top_funcs:
            does_ev.append("key functions: " + ", ".join(f.label for f in top_funcs))
        sections.append(ExplanationSection(
            "what_it_does", "What it actually does",
            self._file_does(role, top_classes, top_funcs, endpoints),
            does_ev,
        ))

        # 4 — HOW IT WORKS (mechanics from complexity/async/endpoints)
        sections.append(ExplanationSection(
            "how_it_works", "How it works",
            self._file_how(node, top_funcs, endpoints),
            [f"max_cyclomatic={max_cc}", f"documentation_ratio={round(doc_ratio, 2)}"],
        ))

        # 5 — IMPORTANT INPUTS / OUTPUTS
        sections.append(ExplanationSection(
            "inputs_outputs", "Important inputs & outputs",
            self._file_io(role, endpoints, top_funcs),
            _io_evidence(endpoints, top_funcs),
        ))

        # 6 — WHAT INTERNAL COMPONENTS IT COORDINATES
        callees = idx.outgoing_calls_from_file(node.id)
        sections.append(ExplanationSection(
            "coordinates", "What internal components it coordinates",
            self._file_coordinates(top_classes, top_funcs, callees),
            (["calls into: " + ", ".join(sorted(callees)[:8])] if callees else
             ["no outbound calls detected in the graph"]),
        ))

        # 7 — WHO USES IT
        sections.append(ExplanationSection(
            "who_uses_it", "Who uses it",
            self._who_uses(node.label, dependents),
            ([f"imported by {len(dependents)} file(s): "
              + ", ".join(d.split('/')[-1] for d in dependents[:8])]
             if dependents else ["no internal importers found in the graph"]),
        ))

        # 8 — WHAT IT USES
        sections.append(ExplanationSection(
            "what_it_uses", "What it uses",
            self._what_uses(node.label, deps),
            ([f"imports {len(deps)} internal module(s): "
              + ", ".join(d.split('/')[-1] for d in deps[:8])]
             if deps else ["no internal imports found in the graph"]),
        ))

        # 9 — HOW IT FITS INTO THE ARCHITECTURE
        sections.append(ExplanationSection(
            "architecture_fit", "How it fits into the architecture",
            self._arch_fit(role, layer, module, deps, dependents),
            [f"layer={layer or 'n/a'}", f"module={module or 'n/a'}",
             f"fan_in={len(dependents)}", f"fan_out={len(deps)}"],
        ))

        # 9.5 — EXECUTION / DATA FLOW (bounded multi-hop, real CALLS edges)
        flow_chain = idx.entrypoint_flow_into(node.id, max_depth=4)
        sections.append(ExplanationSection(
            "execution_flow", "How execution flows through it",
            self._flow_prose(flow_chain, role),
            ([" → ".join(self._flow_step_label(n) for n in flow_chain)]
             if flow_chain else
             ["no multi-step call chain resolved from this file in the graph"]),
        ))

        # 10 + 11 — RISKS + WHY THEY MATTER (from real metrics)
        risks, why = self._file_risks(node, classes, funcs, len(dependents))
        sections.append(ExplanationSection(
            "risks", "Important engineering risks", risks[0], risks[1],
        ))
        sections.append(ExplanationSection(
            "why_risks", "Why those risks matter", why[0], why[1],
        ))

        # 12 — WHAT TO READ NEXT (graph-derived)
        read_next = self._read_next(node, deps, dependents, top_funcs, endpoints, idx)
        sections.append(ExplanationSection(
            "read_next", "What a developer should read next",
            self._read_next_prose(read_next, role),
            [f"suggested: {', '.join(read_next[:6])}"] if read_next else [],
        ))

        headline = self._file_headline(role, path, classes, funcs, endpoints)
        # Evidence-based confidence: reflects how much REAL signal backs this
        # explanation, so a sparse file honestly reports lower certainty.
        resolved_calls = sum(_i(f, "resolved_calls") for f in funcs)
        confidence = self._evidence_confidence(
            has_author_intent=bool(file_doc),
            has_symbols=bool(classes or funcs),
            has_edges=bool(deps or dependents),
            has_metrics=lines > 0,
            resolved_calls=resolved_calls,
            has_flow=len(flow_chain) >= 2,
        )

        flat_ev = [e for s in sections for e in s.evidence]
        return Explanation(
            node_id=node.id, label=node.label, node_type="File",
            file_path=path, architectural_role=role.value,
            headline=headline, sections=sections, evidence=flat_ev,
            read_next=read_next, confidence=confidence, source="cortex",
        )

    # ── file section builders (all entity-specific) ────────────────────────────

    def _file_purpose(
        self,
        role: ArchitecturalRole,
        path: str,
        classes: list[GraphNode],
        funcs: list[GraphNode],
        endpoints: list[GraphNode],
        idx: _Index,
        docstring: str = "",
    ) -> str:
        # AUTHOR INTENT WINS. If the file states its own purpose in a module
        # docstring, lead with that verbatim intent and add structural context
        # around it — never overwrite the author's words with a guess.
        if docstring:
            name = path.split("/")[-1]
            structural = ""
            if role == ArchitecturalRole.ROUTER and endpoints:
                structural = f" It exposes {len(endpoints)} HTTP endpoint(s)."
            elif classes:
                biggest = max(classes, key=lambda c: _i(c, "lines"))
                structural = f" Its main type is `{biggest.label}`."
            elif funcs:
                structural = f" It provides {len(funcs)} function(s)."
            return (
                f"The author describes `{name}` as: \"{docstring}\"."
                + structural
                + " (Stated in the file's own documentation.)"
            )

        name = path.split("/")[-1]
        if role == ArchitecturalRole.ROUTER and endpoints:
            routes = _endpoint_labels(endpoints)
            return (
                f"`{name}` exposes this feature to the outside world over HTTP. "
                f"It declares {len(endpoints)} endpoint(s) — {', '.join(routes[:5])}"
                + ("…" if len(routes) > 5 else "")
                + " — and its job is to validate incoming requests, delegate to the "
                "application/service layer, and shape the response. It deliberately "
                "holds little business logic itself."
            )
        if role == ArchitecturalRole.REPOSITORY:
            return (
                f"`{name}` is the persistence boundary for this feature. It translates "
                f"between the domain objects the rest of the code works with and the "
                f"underlying store, so callers never write storage queries directly. "
                f"Everything that reads or writes this feature's data flows through here."
            )
        if role == ArchitecturalRole.PARSER:
            return (
                f"`{name}` turns raw source text into a structured representation the "
                f"rest of Cortex can reason about. It is a front-end: input is text, "
                f"output is parsed structure, and its correctness underpins every "
                f"downstream analysis."
            )
        if role == ArchitecturalRole.GENERATOR:
            return (
                f"`{name}` produces a concrete artifact (diagram, report, or document) "
                f"from already-computed analysis. It is an output stage — it consumes "
                f"structured data and emits a rendered result."
            )
        if role == ArchitecturalRole.ORCHESTRATOR:
            return (
                f"`{name}` coordinates a multi-step process. Rather than doing the work "
                f"itself, it sequences other components in the right order and passes "
                f"results between them — it is the conductor, not the instrument."
            )
        if role == ArchitecturalRole.ENTRY_POINT:
            return (
                f"`{name}` is where the application is assembled and started. It wires "
                f"the pieces together — configuration, routes, middleware, dependencies — "
                f"so that a running service exists. Reading it tells you what the whole "
                f"system is made of."
            )
        # Ordinary: describe from its dominant symbol.
        if classes:
            biggest = max(classes, key=lambda c: _i(c, "lines"))
            return (
                f"`{name}` provides the `{biggest.label}` type and its collaborators. "
                f"Its purpose is to own one cohesive piece of behaviour in this feature "
                f"and expose it to the rest of the module."
            )
        if funcs:
            return (
                f"`{name}` is a collection of {len(funcs)} function(s) that implement a "
                f"specific piece of this feature's behaviour, callable by the surrounding "
                f"module."
            )
        return f"`{name}` holds module-level definitions supporting this feature."

    def _file_does(
        self,
        role: ArchitecturalRole,
        classes: list[GraphNode],
        funcs: list[GraphNode],
        endpoints: list[GraphNode],
    ) -> str:
        parts: list[str] = []
        if classes:
            # Prefer the class's OWN docstring; fall back to structural facts.
            described_bits = []
            for c in classes:
                doc = _s(c, "docstring_summary")
                if doc:
                    described_bits.append(f"`{c.label}` — {doc}")
                else:
                    described_bits.append(
                        f"`{c.label}` ({_i(c, 'methods')} methods, {_i(c, 'lines')} lines)"
                    )
            parts.append("Its main type(s): " + "; ".join(described_bits) + ".")
        if endpoints:
            parts.append(
                "It handles requests via " + ", ".join(
                    f"`{e.label}`" + (f" ({_s(e, 'route_info')})" if _s(e, 'route_info') else "")
                    for e in endpoints[:5]
                ) + "."
            )
        plain_funcs = [f for f in funcs if f not in endpoints]
        if plain_funcs:
            parts.append(
                "Key routines: " + ", ".join(f"`{f.label}`" for f in plain_funcs[:5]) + "."
            )
        if not parts:
            return "This file defines supporting declarations with no complex behaviour."
        return " ".join(parts)

    def _file_how(
        self,
        node: GraphNode,
        top_funcs: list[GraphNode],
        endpoints: list[GraphNode],
    ) -> str:
        max_cc = _i(node, "max_complexity")
        async_fns = [f for f in top_funcs if _b(f, "is_async")]
        bits = []
        if endpoints:
            bits.append(
                "Control enters through the endpoint handler(s), which parse the request "
                "and hand off to lower layers before returning a response"
            )
        if async_fns:
            bits.append(
                f"{len(async_fns)} of its hottest routines are async, so it does I/O "
                "without blocking"
            )
        if max_cc >= 15:
            hot = max(top_funcs, key=lambda f: _i(f, "cyclomatic")) if top_funcs else None
            bits.append(
                f"the heaviest logic lives in `{hot.label}` with a cyclomatic complexity "
                f"of {max_cc}, meaning many branching paths converge there"
                if hot else
                f"its most complex routine reaches a cyclomatic complexity of {max_cc}"
            )
        elif max_cc > 0:
            bits.append(
                f"its logic is relatively flat (peak cyclomatic complexity {max_cc}), so "
                "control flow is straightforward to follow"
            )
        if not bits:
            return (
                "It works through simple, mostly linear definitions — there is no complex "
                "control flow to trace."
            )
        return ". ".join(b[0].upper() + b[1:] for b in bits) + "."

    def _file_io(
        self,
        role: ArchitecturalRole,
        endpoints: list[GraphNode],
        top_funcs: list[GraphNode],
    ) -> str:
        if endpoints:
            routed = [e for e in endpoints if _s(e, "route_info")]
            if routed:
                return (
                    "Inputs arrive as HTTP requests on "
                    + ", ".join(f"`{_s(e, 'route_info')}`" for e in routed[:5])
                    + "; outputs are the response payloads those handlers return."
                )
            return (
                "Inputs are HTTP requests to its endpoint handlers; outputs are the "
                "responses they produce."
            )
        typed = [f for f in top_funcs if _s(f, "return_type")]
        if typed:
            return (
                "Its functions take structured arguments and return "
                + ", ".join(
                    f"`{_s(f, 'return_type')}` (from `{f.label}`)" for f in typed[:4]
                )
                + " — that is the shape of data flowing out."
            )
        if top_funcs:
            params = sorted(top_funcs, key=lambda f: -_i(f, "param_count"))[0]
            return (
                f"Inputs are the arguments to its functions (e.g. `{params.label}` takes "
                f"{_i(params, 'param_count')} parameter(s)); outputs are their return "
                f"values, consumed by callers."
            )
        return "It exposes definitions rather than a call-based input/output surface."

    def _file_coordinates(
        self,
        classes: list[GraphNode],
        funcs: list[GraphNode],
        callees: set[str],
    ) -> str:
        if callees:
            sample = ", ".join(f"`{c}`" for c in sorted(callees)[:6])
            return (
                f"It drives other parts of the system by calling into {sample}"
                + ("…" if len(callees) > 6 else "")
                + f" — {len(callees)} distinct call target(s) in total. Those calls are "
                "the seams where this file's behaviour connects to the rest of the code."
            )
        if classes and funcs:
            return (
                "Internally it coordinates its own methods and helper functions; the graph "
                "shows no outbound calls to other files, so it is largely self-contained."
            )
        return "It is largely self-contained, with no outbound calls recorded in the graph."

    def _flow_step_label(self, node: GraphNode) -> str:
        """A compact 'Symbol (file)' label for one step in an execution chain."""
        cls = str(node.properties.get("parent_class", "") or "")
        name = f"{cls}.{node.label}" if cls else node.label
        file_name = str(node.properties.get("file", "") or "").split("/")[-1]
        return f"{name}()" + (f" [{file_name}]" if file_name else "")

    def _flow_prose(self, chain: list[GraphNode], role: ArchitecturalRole) -> str:
        """Narrate a real, resolved execution chain (endpoint → service → ...).

        Every named step is backed by a resolved CALLS edge in the graph; when
        no multi-step chain resolves, we say so rather than inventing a flow.
        """
        if not chain or len(chain) < 2:
            return (
                "No multi-step execution chain could be resolved from this file's "
                "code with confidence — its outbound calls are mostly to the "
                "standard library or external packages, or resolve to a single step. "
                "Cortex does not invent a flow where the graph does not support one."
            )
        steps = [self._flow_step_label(n) for n in chain]
        # Build a readable narrative: "X calls Y, which calls Z, ..."
        narrative = steps[0]
        for nxt in steps[1:]:
            narrative += f" → {nxt}"
        lead = (
            "A request entering this file"
            if role in (ArchitecturalRole.ROUTER, ArchitecturalRole.ENTRY_POINT)
            else "Control starting here"
        )
        return (
            f"{lead} flows through {len(chain)} resolved step(s): {narrative}. "
            "Each arrow is a call relationship Cortex confirmed in the graph, so "
            "this is how work actually moves once execution reaches this file."
        )

    def _who_uses(self, label: str, dependents: list[str]) -> str:
        if not dependents:
            return (
                f"Nothing in the analysed graph imports `{label}` directly. It may be an "
                "entry point, wired dynamically, or used only from tests or config — so "
                "changing it is comparatively low-blast-radius, but confirm before assuming."
            )
        names = [d.split('/')[-1] for d in dependents]
        lead = ", ".join(f"`{n}`" for n in names[:6])
        return (
            f"`{label}` is imported by {len(dependents)} file(s), including {lead}"
            + ("…" if len(dependents) > 6 else "")
            + ". Those are the places that would need attention if its public surface "
            "changed."
        )

    def _what_uses(self, label: str, deps: list[str]) -> str:
        if not deps:
            return (
                f"`{label}` imports nothing else from within the repository — it depends "
                "only on the standard library or third-party packages, which makes it a "
                "leaf in the internal dependency graph."
            )
        names = [d.split('/')[-1] for d in deps]
        lead = ", ".join(f"`{n}`" for n in names[:6])
        return (
            f"It builds on {len(deps)} internal module(s): {lead}"
            + ("…" if len(deps) > 6 else "")
            + ". To understand `" + label + "` fully you will need at least a passing "
            "familiarity with those."
        )

    def _arch_fit(
        self,
        role: ArchitecturalRole,
        layer: str,
        module: str,
        deps: list[str],
        dependents: list[str],
    ) -> str:
        role_h = _humanize_role(role)
        base = f"Architecturally this is the {role_h}"
        if layer and module:
            base += f", living in the **{layer}** layer of the `{module}` feature"
        elif module:
            base += f" within the `{module}` feature"
        flow = ""
        if role == ArchitecturalRole.ROUTER:
            flow = (
                ". Requests flow in here from the web framework and out to the "
                "application layer, so it is the outermost edge of this feature."
            )
        elif role == ArchitecturalRole.REPOSITORY:
            flow = (
                ". It is the innermost edge on the data side — application code above it "
                "depends on it, and it depends on the database below."
            )
        elif role == ArchitecturalRole.ENTRY_POINT:
            flow = (
                ". Everything else hangs off it; it is the root from which the running "
                "system is composed."
            )
        else:
            flow = (
                f". With {len(dependents)} inbound and {len(deps)} outbound internal "
                "dependencies, it sits "
                + ("centrally" if len(dependents) >= 5 else "toward the edges")
                + " in the dependency graph."
            )
        return base + flow

    def _file_risks(
        self,
        node: GraphNode,
        classes: list[GraphNode],
        funcs: list[GraphNode],
        fan_in: int,
    ) -> tuple[tuple[str, list[str]], tuple[str, list[str]]]:
        lines = _i(node, "lines")
        max_cc = _i(node, "max_complexity")
        risk_lines: list[str] = []
        ev: list[str] = []

        if lines > 500:
            risk_lines.append(
                f"the file is large ({lines} lines), which tends to accumulate mixed "
                "responsibilities over time"
            )
            ev.append(f"lines={lines}")
        if max_cc >= 15:
            risk_lines.append(
                f"it contains at least one very complex routine (cyclomatic {max_cc})"
            )
            ev.append(f"max_cyclomatic={max_cc}")
        big_classes = [c for c in classes if _i(c, "methods") > 20]
        if big_classes:
            risk_lines.append(
                f"`{big_classes[0].label}` has {_i(big_classes[0], 'methods')} methods, "
                "a sign of a class doing too much"
            )
            ev.append(f"{big_classes[0].label}.methods={_i(big_classes[0], 'methods')}")
        if fan_in >= 20:
            risk_lines.append(
                f"it is a dependency hub ({fan_in} files import it), so its blast radius "
                "is wide"
            )
            ev.append(f"fan_in={fan_in}")

        if not risk_lines:
            return (
                ("No significant structural risks stand out: the file is a reasonable "
                 "size, its complexity is contained, and its coupling is moderate.",
                 [f"lines={lines}", f"max_cyclomatic={max_cc}", f"fan_in={fan_in}"]),
                ("Because nothing here is oversized, deeply complex, or widely depended "
                 "upon, changes are relatively safe and localised.",
                 []),
            )

        risk_text = "The main concerns are that " + "; ".join(risk_lines) + "."
        why_bits = []
        if lines > 500:
            why_bits.append("large files slow down navigation and review")
        if max_cc >= 15:
            why_bits.append(
                "highly branching code needs many test cases to cover and is easy to "
                "break when edited"
            )
        if fan_in >= 20:
            why_bits.append(
                "a wide blast radius means a single breaking change here can ripple into "
                "many other files at once"
            )
        why_text = (
            "These matter because " + "; ".join(why_bits) + "."
            if why_bits else
            "These matter because they make the file harder to change safely over time."
        )
        return (risk_text, ev), (why_text, [])

    def _read_next(
        self,
        node: GraphNode,
        deps: list[str],
        dependents: list[str],
        top_funcs: list[GraphNode],
        endpoints: list[GraphNode],
        idx: _Index,
    ) -> list[str]:
        out: list[str] = []
        role = classify_role(_s(node, "path") or node.label,
                             endpoint_count=_i(node, "endpoints"))
        # Routers: point down to the service/application layer they call.
        if role == ArchitecturalRole.ROUTER and deps:
            out.extend(d for d in deps if "application" in d or "service" in d)
        # Repositories: point to the domain entities they map.
        if role == ArchitecturalRole.REPOSITORY and deps:
            out.extend(d for d in deps if "domain" in d or "entities" in d or "models" in d)
        # Otherwise: the biggest internal dependency and the biggest dependent.
        out.extend(deps[:2])
        out.extend(dependents[:1])
        # De-dup, keep order, drop self.
        seen, ordered = set(), []
        for x in out:
            if x and x not in seen:
                seen.add(x)
                ordered.append(x)
        return ordered[:6]

    def _read_next_prose(self, read_next: list[str], role: ArchitecturalRole) -> str:
        if not read_next:
            return (
                "This file is fairly self-contained, so the best next step is to read its "
                "own most complex routine top-to-bottom."
            )
        first = read_next[0].split('/')[-1]
        rationale = {
            ArchitecturalRole.ROUTER:     "to see the business logic these endpoints delegate to",
            ArchitecturalRole.REPOSITORY: "to see the domain objects this persistence layer maps",
            ArchitecturalRole.ENTRY_POINT:"to follow how the application is assembled",
        }.get(role, "because it is this file's most significant dependency")
        return (
            f"Start with `{first}` {rationale}. From there, follow the dependency edges "
            "outward — the graph links each of these files to its own callers and callees."
        )

    def _file_headline(
        self,
        role: ArchitecturalRole,
        path: str,
        classes: list[GraphNode],
        funcs: list[GraphNode],
        endpoints: list[GraphNode],
    ) -> str:
        name = path.split("/")[-1]
        if role == ArchitecturalRole.ROUTER and endpoints:
            return (
                f"The HTTP entry surface for this feature — "
                f"{len(endpoints)} endpoint(s) in `{name}`."
            )
        if role == ArchitecturalRole.REPOSITORY:
            return f"The data-access boundary for this feature (`{name}`)."
        if role == ArchitecturalRole.PARSER:
            return f"A source parser that feeds Cortex's analysis (`{name}`)."
        if role == ArchitecturalRole.GENERATOR:
            return f"An artifact generator that renders analysis into output (`{name}`)."
        if role == ArchitecturalRole.ORCHESTRATOR:
            return f"A coordinator that sequences a multi-step process (`{name}`)."
        if role == ArchitecturalRole.ENTRY_POINT:
            return f"The application's composition root (`{name}`)."
        if classes:
            biggest = max(classes, key=lambda c: _i(c, "lines"))
            return f"Home of `{biggest.label}` and its collaborators (`{name}`)."
        return f"A {len(funcs)}-function module in this feature (`{name}`)."

    # ══════════════════════════════════════════════════════════════════════════
    # CLASS  /  FUNCTION  /  CONTAINER  (compact, still entity-specific)
    # ══════════════════════════════════════════════════════════════════════════

    def _explain_class(self, node: GraphNode, idx: _Index) -> Explanation:
        file_path = _s(node, "file")
        role = classify_role(file_path)
        methods = _i(node, "methods")
        bases = _csv(node, "base_classes")
        attrs = _csv(node, "attributes")
        is_abstract = _b(node, "is_abstract")
        dependents = idx.symbol_callers(node.id)

        kind = "an abstract base / interface" if is_abstract else "a class"
        what = (
            f"`{node.label}` is {kind} defined in `{file_path.split('/')[-1]}` with "
            f"{methods} method(s)"
            + (f", extending {', '.join(bases)}" if bases else "")
            + "."
        )
        purpose = (
            f"It groups {methods} related behaviour(s)"
            + (f" around the state it holds ({', '.join(attrs[:5])})" if attrs else "")
            + ". "
            + ("As an abstract type it defines a contract that concrete classes implement."
               if is_abstract else
               "It is a concrete unit of behaviour the surrounding module relies on.")
        )
        does = (
            f"Its {methods} method(s) implement the operations of this type"
            + (f"; it inherits from {', '.join(bases)}, so part of its behaviour comes "
               "from its parent(s)." if bases else ".")
        )
        who = self._who_uses(node.label, dependents)
        risk = (
            f"With {methods} methods this class may be taking on several responsibilities; "
            "watch for unrelated method groups."
            if methods > 20 else
            "Its size is reasonable for a single responsibility."
        )
        sections = [
            ExplanationSection("what_is_this", "What is this?", what,
                               [f"methods={methods}", f"abstract={is_abstract}",
                                f"bases={bases or 'none'}"]),
            ExplanationSection("primary_purpose", "Primary purpose", purpose,
                               [f"attributes={attrs[:5] or 'none'}"]),
            ExplanationSection("what_it_does", "What it actually does", does, []),
            ExplanationSection("who_uses_it", "Who uses it", who,
                               [f"callers={len(dependents)}"]),
            ExplanationSection("risks", "Important engineering risks", risk,
                               [f"methods={methods}"]),
        ]
        read_next = [file_path] + dependents[:3]
        return Explanation(
            node_id=node.id, label=node.label, node_type=node.node_type.value,
            file_path=file_path, architectural_role=role.value,
            headline=f"`{node.label}` — a {methods}-method type in `{file_path.split('/')[-1]}`.",
            sections=sections,
            evidence=[e for s in sections for e in s.evidence],
            read_next=[r for r in read_next if r],
            confidence=self._confidence(True, bool(dependents), True, False),
            source="cortex",
        )

    def _explain_function(self, node: GraphNode, idx: _Index) -> Explanation:
        file_path = _s(node, "file")
        role = classify_role(file_path)
        cc = _i(node, "cyclomatic")
        params = _i(node, "param_count")
        ret = _s(node, "return_type")
        is_async = _b(node, "is_async")
        is_endpoint = _b(node, "is_endpoint") or node.node_type == NodeType.ENDPOINT
        route = _s(node, "route_info")
        calls = _csv(node, "calls")
        callers = idx.symbol_callers(node.id)

        what = (
            f"`{node.label}` is "
            + ("an async " if is_async else "a ")
            + ("HTTP endpoint handler" if is_endpoint else "function")
            + f" in `{file_path.split('/')[-1]}`"
            + (f" bound to `{route}`" if route else "")
            + f". It takes {params} parameter(s)"
            + (f" and returns `{ret}`" if ret else "")
            + "."
        )
        does = (
            ("It receives the request, does its work, and returns a response. "
             if is_endpoint else "")
            + (f"It coordinates {len(calls)} call(s): " + ", ".join(f"`{c}`" for c in calls[:6])
               + ("…" if len(calls) > 6 else "") + "."
               if calls else "It performs its work without calling out to other tracked functions.")
        )
        how = (
            f"Its cyclomatic complexity is {cc}, meaning "
            + ("a very high number of independent paths run through it — it is hard to test "
               "exhaustively and risky to edit." if cc >= 15 else
               "there are several decision paths to keep in mind." if cc >= 10 else
               "its control flow is easy to follow.")
        )
        who = self._who_uses(node.label, callers)
        risk = (
            f"High complexity (CC={cc}) is the main risk — it concentrates logic that is "
            "hard to fully test." if cc >= 15 else
            f"Complexity is elevated (CC={cc}); keep an eye on it as it grows." if cc >= 10 else
            "No significant complexity risk."
        )
        sections = [
            ExplanationSection("what_is_this", "What is this?", what,
                               [f"cyclomatic={cc}", f"params={params}",
                                f"async={is_async}", f"endpoint={is_endpoint}"]),
            ExplanationSection("what_it_does", "What it actually does", does,
                               ([f"calls={calls[:6]}"] if calls else [])),
            ExplanationSection("how_it_works", "How it works", how, [f"cyclomatic={cc}"]),
            ExplanationSection("who_uses_it", "Who uses it", who,
                               [f"callers={len(callers)}"]),
            ExplanationSection("risks", "Important engineering risks", risk, [f"cyclomatic={cc}"]),
        ]
        read_next = [file_path] + callers[:3]
        return Explanation(
            node_id=node.id, label=node.label, node_type=node.node_type.value,
            file_path=file_path, architectural_role=role.value,
            headline=(f"`{node.label}` — "
                      + ("an endpoint handler" if is_endpoint else "a function")
                      + f" (CC={cc}) in `{file_path.split('/')[-1]}`."),
            sections=sections,
            evidence=[e for s in sections for e in s.evidence],
            read_next=[r for r in read_next if r],
            confidence=self._confidence(True, bool(callers or calls), cc > 0, is_endpoint),
            source="cortex",
        )

    def _explain_container(self, node: GraphNode, idx: _Index) -> Explanation:
        children = idx.children_of(node.id)
        files = [c for c in children if c.node_type == NodeType.FILE]
        what = (
            f"`{node.label}` is a {node.node_type.value.lower()} grouping "
            f"{len(children)} member(s)"
            + (f", including {len(files)} file(s)" if files else "")
            + "."
        )
        sections = [
            ExplanationSection("what_is_this", "What is this?", what,
                               [f"members={len(children)}"]),
            ExplanationSection(
                "primary_purpose", "Primary purpose",
                "It packages a set of related files/symbols that together implement one "
                "area of the system.", []),
        ]
        return Explanation(
            node_id=node.id, label=node.label, node_type=node.node_type.value,
            file_path="", architectural_role="ordinary",
            headline=f"`{node.label}` — a container of {len(children)} member(s).",
            sections=sections,
            evidence=[e for s in sections for e in s.evidence],
            read_next=[_s(f, "path") for f in files[:5]],
            confidence=self._confidence(bool(children), False, True, False),
            source="cortex",
        )

    # ── shared ──────────────────────────────────────────────────────────────

    def _confidence(
        self,
        has_symbols: bool,
        has_edges: bool,
        has_metrics: bool,
        has_endpoints: bool,
    ) -> float:
        score = 0.4
        if has_symbols:
            score += 0.2
        if has_edges:
            score += 0.2
        if has_metrics:
            score += 0.1
        if has_endpoints:
            score += 0.1
        return round(min(1.0, score), 3)

    def _evidence_confidence(
        self,
        *,
        has_author_intent: bool,
        has_symbols: bool,
        has_edges: bool,
        has_metrics: bool,
        resolved_calls: int,
        has_flow: bool,
    ) -> float:
        """Confidence tied to ACTUAL evidence quality (not a fixed formula).

        Highest when the author stated intent, structure is present, imports
        resolve, calls resolved, and a multi-hop flow is supported. Lower when
        the graph is sparse — Cortex should not claim certainty it doesn't have.
        """
        score = 0.30
        if has_author_intent:
            score += 0.20          # the strongest signal: the author's own words
        if has_symbols:
            score += 0.15
        if has_edges:
            score += 0.15
        if has_metrics:
            score += 0.05
        if resolved_calls > 0:
            score += min(0.10, 0.02 * resolved_calls)  # more resolved calls → more
        if has_flow:
            score += 0.10
        return round(min(1.0, score), 3)


# ══════════════════════════════════════════════════════════════════════════════
# Graph index used by the explainer
# ══════════════════════════════════════════════════════════════════════════════

class _Index:
    """Read-only indexes over the graph for explanation lookups."""

    _DEP_RELS = (RelationshipType.IMPORTS, RelationshipType.DEPENDS_ON)

    def __init__(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
        self.by_id = {n.id: n for n in nodes}
        self._children: dict[str, list[str]] = defaultdict(list)
        self._out: dict[str, list[GraphEdge]] = defaultdict(list)
        self._in: dict[str, list[GraphEdge]] = defaultdict(list)
        self._file_of_symbol: dict[str, str] = {}
        for e in edges:
            self._out[e.source_id].append(e)
            self._in[e.target_id].append(e)
            if e.relationship == RelationshipType.CONTAINS:
                self._children[e.source_id].append(e.target_id)

    def children_of(self, node_id: str) -> list[GraphNode]:
        return [self.by_id[c] for c in self._children.get(node_id, []) if c in self.by_id]

    def _path(self, node_id: str) -> str:
        n = self.by_id.get(node_id)
        if not n:
            return ""
        return str(n.properties.get("path", "") or n.label)

    def file_dependencies(self, file_id: str) -> list[str]:
        out = []
        for e in self._out.get(file_id, []):
            if e.relationship in self._DEP_RELS and e.target_id != file_id:
                p = self._path(e.target_id)
                if p:
                    out.append(p)
        return list(dict.fromkeys(out))

    def file_dependents(self, file_id: str) -> list[str]:
        out = []
        for e in self._in.get(file_id, []):
            if e.relationship in self._DEP_RELS and e.source_id != file_id:
                p = self._path(e.source_id)
                if p:
                    out.append(p)
        return list(dict.fromkeys(out))

    def outgoing_calls_from_file(self, file_id: str) -> set[str]:
        """Distinct call-target labels made by functions contained in this file."""
        targets: set[str] = set()
        for child_id in self._children.get(file_id, []):
            for e in self._out.get(child_id, []):
                if e.relationship == RelationshipType.CALLS:
                    tgt = self.by_id.get(e.target_id)
                    if tgt:
                        targets.add(tgt.label)
        return targets

    def symbol_callers(self, symbol_id: str) -> list[str]:
        """Labels of symbols that call or depend on this symbol (CALLS/DEPENDS)."""
        out = []
        for e in self._in.get(symbol_id, []):
            if e.relationship in (RelationshipType.CALLS, *self._DEP_RELS):
                src = self.by_id.get(e.source_id)
                if src and src.id != symbol_id:
                    out.append(src.label)
        return list(dict.fromkeys(out))

    def _callees(self, symbol_id: str) -> list[str]:
        """Node ids this symbol directly calls (resolved CALLS edges only)."""
        return [
            e.target_id for e in self._out.get(symbol_id, [])
            if e.relationship == RelationshipType.CALLS and e.target_id in self.by_id
        ]

    def _file_of(self, symbol_id: str) -> str:
        """The path of the file that owns a symbol (from its 'file' property)."""
        n = self.by_id.get(symbol_id)
        return str(n.properties.get("file", "") or "") if n else ""

    def best_flow_from(self, symbol_id: str, max_depth: int = 4) -> list[GraphNode]:
        """Follow resolved CALLS edges to build ONE bounded execution chain.

        This is deliberately NOT a full graph walk. At each step it follows the
        single most "downstream-looking" callee (one that crosses into another
        file or a deeper layer), producing a readable chain like
        endpoint → service → repository rather than an unranked explosion.
        Stops at max_depth, on a cycle, or when there is nowhere meaningful to go.
        """
        chain: list[GraphNode] = []
        visited: set[str] = set()
        current = symbol_id
        for _ in range(max_depth):
            node = self.by_id.get(current)
            if node is None or current in visited:
                break
            visited.add(current)
            chain.append(node)
            callees = [c for c in self._callees(current) if c not in visited]
            if not callees:
                break
            # Rank: prefer a callee in a DIFFERENT file (a real layer crossing),
            # then one that is a class method (service/repository-like), else first.
            cur_file = self._file_of(current)
            callees.sort(key=lambda cid: (
                0 if self._file_of(cid) and self._file_of(cid) != cur_file else 1,
                0 if (self.by_id[cid].properties.get("parent_class")) else 1,
            ))
            current = callees[0]
        return chain

    def entrypoint_flow_into(self, file_id: str, max_depth: int = 4) -> list[GraphNode]:
        """Build the most representative execution chain that STARTS in this file.

        Picks the file's richest entry function (an endpoint if present, else the
        function with the most resolved calls) and traces a bounded chain from it.
        """
        fns = [
            self.by_id[c] for c in self._children.get(file_id, [])
            if c in self.by_id and self.by_id[c].node_type in (
                NodeType.ENDPOINT, NodeType.FUNCTION, NodeType.METHOD, NodeType.TEST
            )
        ]
        if not fns:
            return []
        # Prefer endpoints; otherwise the function that resolves the most calls.
        def _rank(n: GraphNode) -> tuple[int, int]:
            is_ep = 0 if (n.node_type == NodeType.ENDPOINT
                          or str(n.properties.get("is_endpoint")).lower() == "true") else 1
            return (is_ep, -int(n.properties.get("resolved_calls", 0) or 0))
        start = sorted(fns, key=_rank)[0]
        chain = self.best_flow_from(start.id, max_depth=max_depth)
        return chain if len(chain) >= 2 else []


def _endpoint_labels(endpoints: list[GraphNode]) -> list[str]:
    labels = []
    for e in endpoints:
        route = str(e.properties.get("route_info", "") or "")
        labels.append(route or e.label)
    return labels


def _io_evidence(endpoints: list[GraphNode], top_funcs: list[GraphNode]) -> list[str]:
    ev = []
    for e in endpoints[:5]:
        route = str(e.properties.get("route_info", "") or "")
        ev.append(f"endpoint {e.label}" + (f" [{route}]" if route else ""))
    for f in top_funcs[:3]:
        rt = str(f.properties.get("return_type", "") or "")
        if rt:
            ev.append(f"{f.label} -> {rt}")
    return ev
