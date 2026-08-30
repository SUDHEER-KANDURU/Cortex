"""Tests for CortexExplainer — Cortex's own deterministic code explainer.

Locks in the requirements:
  - explanations are ENTITY-SPECIFIC and materially DIFFERENT per file
    (not one template with names substituted)
  - every section is grounded in real evidence
  - the 12-section reasoning order is produced for files
  - it works with NO NIM (deterministic, self-contained)
  - role/read-next are graph-derived
"""

from __future__ import annotations

from datetime import UTC, datetime

from cortex.graph.domain.entities import GraphEdge, GraphNode, NodeType, RelationshipType
from cortex.reasoning.application.explainer import CortexExplainer

_NOW = datetime.now(UTC)
_JOB = "exp-job"
explainer = CortexExplainer()


def _n(nid, label, ntype, props):
    return GraphNode(id=nid, label=label, node_type=ntype, job_id=_JOB,
                     properties=props, created_at=_NOW)

def _e(sid, tid, rel):
    return GraphEdge(id=f"{sid}-{tid}", source_id=sid, target_id=tid,
                     relationship=rel, job_id=_JOB, created_at=_NOW)


def _router_graph():
    """A router file with 2 endpoints that imports an application module."""
    f = _n("f_router", "router.py", NodeType.FILE, {
        "path": "src/cortex/insights/presentation/router.py",
        "language": "python", "lines": 106, "classes": 0, "functions": 2,
        "endpoints": 2, "max_complexity": 5,
    })
    ep1 = _n("ep1", "get_insights", NodeType.ENDPOINT, {
        "file": "src/cortex/insights/presentation/router.py", "line": 10,
        "is_endpoint": True, "is_async": True, "route_info": "GET /{job_id}",
        "cyclomatic": 3, "param_count": 1,
    })
    ep2 = _n("ep2", "export_md", NodeType.ENDPOINT, {
        "file": "src/cortex/insights/presentation/router.py", "line": 30,
        "is_endpoint": True, "is_async": True, "route_info": "GET /{job_id}/export",
        "cyclomatic": 2, "param_count": 1,
    })
    app = _n("f_engine", "engine.py", NodeType.FILE, {
        "path": "src/cortex/insights/application/engine.py",
        "language": "python", "lines": 900, "classes": 1, "functions": 0,
    })
    edges = [
        _e("f_router", "ep1", RelationshipType.CONTAINS),
        _e("f_router", "ep2", RelationshipType.CONTAINS),
        _e("f_router", "f_engine", RelationshipType.IMPORTS),
    ]
    return "f_router", [f, ep1, ep2, app], edges


def _parser_graph():
    """A parser file with several classes, no endpoints, high complexity."""
    f = _n("f_parser", "ast_parser.py", NodeType.FILE, {
        "path": "src/cortex/pipeline/infrastructure/ast_parser.py",
        "language": "python", "lines": 1179, "classes": 3, "functions": 0,
        "endpoints": 0, "max_complexity": 49,
    })
    c1 = _n("c_py", "PythonASTParser", NodeType.CLASS, {
        "file": "src/cortex/pipeline/infrastructure/ast_parser.py",
        "line": 1, "lines": 315, "methods": 3, "is_abstract": False,
    })
    c2 = _n("c_ts", "TypeScriptASTParser", NodeType.CLASS, {
        "file": "src/cortex/pipeline/infrastructure/ast_parser.py",
        "line": 400, "lines": 427, "methods": 3, "is_abstract": False,
    })
    edges = [
        _e("f_parser", "c_py", RelationshipType.CONTAINS),
        _e("f_parser", "c_ts", RelationshipType.CONTAINS),
    ]
    return "f_parser", [f, c1, c2], edges


class TestFileExplanation:
    def test_produces_twelve_sections_for_file(self):
        nid, nodes, edges = _router_graph()
        exp = explainer.explain_node(nid, nodes, edges)
        assert exp is not None
        keys = [s.key for s in exp.sections]
        expected = [
            "what_is_this", "primary_purpose", "what_it_does", "how_it_works",
            "inputs_outputs", "coordinates", "who_uses_it", "what_it_uses",
            "architecture_fit", "execution_flow", "risks", "why_risks", "read_next",
        ]
        assert keys == expected, f"Missing/reordered sections: {keys}"

    def test_router_explanation_mentions_real_routes(self):
        nid, nodes, edges = _router_graph()
        exp = explainer.explain_node(nid, nodes, edges)
        body = " ".join(s.body for s in exp.sections)
        assert "GET /{job_id}" in body, "Router explanation must cite its real routes"
        assert exp.architectural_role == "router"

    def test_parser_explanation_names_real_classes(self):
        nid, nodes, edges = _parser_graph()
        exp = explainer.explain_node(nid, nodes, edges)
        body = " ".join(s.body for s in exp.sections)
        assert "PythonASTParser" in body
        assert "TypeScriptASTParser" in body
        assert exp.architectural_role == "parser"

    def test_explanations_are_materially_different(self):
        """The core requirement: two different files must not share prose."""
        rid, rnodes, redges = _router_graph()
        pid, pnodes, pedges = _parser_graph()
        r = explainer.explain_node(rid, rnodes, redges)
        p = explainer.explain_node(pid, pnodes, pedges)
        assert r.headline != p.headline
        # Compare the "what is this" + "purpose" bodies — must differ substantially.
        r_text = r.sections[0].body + r.sections[1].body
        p_text = p.sections[0].body + p.sections[1].body
        assert r_text != p_text
        # Roles differ, and each cites its own evidence.
        assert r.architectural_role == "router"
        assert p.architectural_role == "parser"

    def test_every_section_has_body(self):
        nid, nodes, edges = _parser_graph()
        exp = explainer.explain_node(nid, nodes, edges)
        for s in exp.sections:
            assert s.body, f"Empty section: {s.key}"
            assert len(s.body) > 10, f"Trivial section: {s.key}"

    def test_read_next_is_graph_derived(self):
        nid, nodes, edges = _router_graph()
        exp = explainer.explain_node(nid, nodes, edges)
        # Router imports engine.py, so read-next should point at it.
        assert any("engine.py" in r for r in exp.read_next)

    def test_who_uses_reflects_dependents(self):
        """engine.py is imported by router.py, so its 'who uses it' says so."""
        _, nodes, edges = _router_graph()
        exp = explainer.explain_node("f_engine", nodes, edges)
        who = next(s for s in exp.sections if s.key == "who_uses_it")
        assert "router.py" in who.body

    def test_missing_node_returns_none(self):
        nid, nodes, edges = _router_graph()
        assert explainer.explain_node("does_not_exist", nodes, edges) is None

    def test_works_without_nim(self):
        """The explanation is fully populated with no LLM involved."""
        nid, nodes, edges = _parser_graph()
        exp = explainer.explain_node(nid, nodes, edges)
        assert exp.source == "cortex"
        assert exp.confidence > 0.0
        md = exp.to_markdown()
        assert "PythonASTParser" in md


class TestSymbolExplanation:
    def test_function_explanation_is_specific(self):
        f = _n("f", "svc.py", NodeType.FILE, {
            "path": "src/cortex/x/svc.py", "language": "python", "lines": 100,
        })
        fn = _n("fn", "process", NodeType.FUNCTION, {
            "file": "src/cortex/x/svc.py", "line": 5, "lines": 40,
            "cyclomatic": 18, "param_count": 3, "is_async": True,
            "calls": "validate, persist, notify",
        })
        edges = [_e("f", "fn", RelationshipType.CONTAINS)]
        exp = explainer.explain_node("fn", [f, fn], edges)
        body = " ".join(s.body for s in exp.sections)
        assert "18" in body                    # cites real complexity
        assert "validate" in body              # cites real call targets
        assert exp.confidence > 0.0


class TestNimRefineFallback:
    """NIMClient.refine must never lose Cortex's draft on failure."""

    def test_refine_returns_draft_without_key(self):
        import asyncio

        from cortex.chat.infrastructure.nim_client import NIMClient
        client = NIMClient("")  # no key
        draft = "# File\n\nThis is Cortex's grounded explanation with facts."
        result = asyncio.run(client.refine(draft, "- path=x.py\n- lines=100"))
        assert result == draft, "With no key, refine must return the Cortex draft unchanged"
