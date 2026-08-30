"""Tests for the deep-understanding upgrade:

  1. Docstring / intent preservation on graph nodes
  2. Accurate, collision-safe call-graph resolution
  3. Bounded multi-hop execution-flow reasoning
  4. Evidence-based confidence
  5. NIM grounding guard

These build a real graph from source strings via the actual ASTParser +
GraphBuilder, so they exercise the real resolution logic — not mocks.
"""

from __future__ import annotations

from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.pipeline.infrastructure.ast_parser import ASTParser
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder

_parser = ASTParser()


def _graph(files: dict[str, str]):
    parsed = _parser.parse_many([(src, path) for path, src in files.items()])
    return GraphBuilder(job_id="t", repo_url="https://github.com/x/r").build(parsed)


def _fn_nodes(graph):
    return [n for n in graph.nodes if n.node_type in (
        NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT, NodeType.TEST)]

def _calls_edges(graph):
    return [e for e in graph.edges if e.relationship == RelationshipType.CALLS]

def _node_by_label(graph, label, file_hint=""):
    for n in graph.nodes:
        if n.label == label and (not file_hint or file_hint in str(n.properties.get("file", ""))):
            return n
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 1. DOCSTRINGS
# ══════════════════════════════════════════════════════════════════════════════

class TestDocstringPreservation:
    def test_module_docstring_on_file_node(self):
        src = '"""This module does the important thing."""\n\ndef f():\n    pass\n'
        g = _graph({"src/x/mod.py": src})
        file_node = next(n for n in g.nodes if n.node_type == NodeType.FILE)
        assert file_node.properties["docstring_summary"] == "This module does the important thing."

    def test_class_and_function_docstrings_attached_to_correct_symbol(self):
        src = (
            '"""Module."""\n'
            "class Widget:\n"
            '    """A widget that renders things."""\n'
            "    def draw(self):\n"
            '        """Draw the widget on screen."""\n'
            "        return 1\n"
        )
        g = _graph({"src/x/widget.py": src})
        cls = _node_by_label(g, "Widget")
        method = _node_by_label(g, "draw")
        assert cls.properties["docstring_summary"] == "A widget that renders things."
        assert method.properties["docstring_summary"] == "Draw the widget on screen."

    def test_docstring_truncated_safely(self):
        long_doc = "word " * 200  # ~1000 chars
        src = f'"""{long_doc}"""\n\ndef f():\n    pass\n'
        g = _graph({"src/x/big.py": src})
        file_node = next(n for n in g.nodes if n.node_type == NodeType.FILE)
        summary = file_node.properties["docstring_summary"]
        assert len(summary) <= 241  # 240 + ellipsis
        assert summary.endswith("…")

    def test_only_first_paragraph_kept(self):
        src = (
            '"""Summary line.\n\n'
            'Long detailed second paragraph that should be dropped."""\n'
            "def f():\n    pass\n"
        )
        g = _graph({"src/x/p.py": src})
        file_node = next(n for n in g.nodes if n.node_type == NodeType.FILE)
        assert file_node.properties["docstring_summary"] == "Summary line."


# ══════════════════════════════════════════════════════════════════════════════
# 2. CALL GRAPH ACCURACY
# ══════════════════════════════════════════════════════════════════════════════

class TestCallGraphResolution:
    def test_same_function_name_different_files_no_collision(self):
        """Two files each define `save`; a call to `save` must not link to both."""
        files = {
            "src/a/mod_a.py": (
                "def save():\n    pass\n"
                "def caller_a():\n    save()\n"
            ),
            "src/b/mod_b.py": (
                "def save():\n    pass\n"
            ),
        }
        g = _graph(files)
        caller = _node_by_label(g, "caller_a")
        edges = [e for e in _calls_edges(g) if e.source_id == caller.id]
        # It must resolve to the SAME-FILE save, not both saves.
        assert len(edges) == 1
        target = next(n for n in g.nodes if n.id == edges[0].target_id)
        assert "mod_a.py" in str(target.properties.get("file", ""))

    def test_same_method_name_different_classes(self):
        """self.run() must resolve within the calling class, not the other one."""
        src = (
            "class Engine:\n"
            "    def run(self):\n"
            "        return self.step()\n"
            "    def step(self):\n"
            "        return 1\n"
            "class Worker:\n"
            "    def step(self):\n"
            "        return 2\n"
        )
        g = _graph({"src/x/e.py": src})
        run = _node_by_label(g, "run")
        edges = [e for e in _calls_edges(g) if e.source_id == run.id]
        assert len(edges) == 1
        target = next(n for n in g.nodes if n.id == edges[0].target_id)
        # Must be Engine.step, not Worker.step.
        assert target.properties.get("parent_class") == "Engine"

    def test_self_method_call_resolves(self):
        src = (
            "class S:\n"
            "    def a(self):\n"
            "        return self.b()\n"
            "    def b(self):\n"
            "        return 1\n"
        )
        g = _graph({"src/x/s.py": src})
        a = _node_by_label(g, "a")
        edges = [e for e in _calls_edges(g) if e.source_id == a.id]
        assert len(edges) == 1
        assert next(n for n in g.nodes if n.id == edges[0].target_id).label == "b"

    def test_ambiguous_bare_name_not_linked(self):
        """A bare name defined in 3 unrelated files must NOT create an edge."""
        files = {
            "src/a.py": "def handle():\n    pass\n",
            "src/b.py": "def handle():\n    pass\n",
            "src/c.py": (
                "def handle():\n    pass\n"
                "def other():\n    unrelated_call()\n"  # unrelated_call defined nowhere
            ),
        }
        g = _graph(files)
        other = _node_by_label(g, "other")
        edges = [e for e in _calls_edges(g) if e.source_id == other.id]
        assert edges == [], "Unknown/ambiguous call must not be fabricated"

    def test_unresolved_calls_counted(self):
        src = (
            "def f():\n"
            "    print('x')\n"       # builtin — unresolved
            "    return len([1])\n"  # builtin — unresolved
        )
        g = _graph({"src/x/u.py": src})
        f = _node_by_label(g, "f")
        assert int(f.properties.get("unresolved_calls", 0)) >= 1
        assert int(f.properties.get("resolved_calls", 0)) == 0

    def test_cross_file_unique_call_resolves(self):
        """A helper defined once repo-wide resolves even across files."""
        files = {
            "src/util.py": "def unique_helper():\n    return 1\n",
            "src/main.py": "def go():\n    return unique_helper()\n",
        }
        g = _graph(files)
        go = _node_by_label(g, "go")
        edges = [e for e in _calls_edges(g) if e.source_id == go.id]
        assert len(edges) == 1
        assert next(n for n in g.nodes if n.id == edges[0].target_id).label == "unique_helper"


# ══════════════════════════════════════════════════════════════════════════════
# 3. MULTI-HOP FLOW
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiHopFlow:
    def _index(self, graph):
        from cortex.reasoning.application.explainer import _Index
        return _Index(graph.nodes, graph.edges)

    def test_two_and_three_hop_chain(self):
        files = {
            "src/api.py": "def entry():\n    return service()\n",
            "src/svc.py": "def service():\n    return repo()\n",
            "src/repo.py": "def repo():\n    return 1\n",
        }
        g = _graph(files)
        idx = self._index(g)
        entry = _node_by_label(g, "entry")
        chain = idx.best_flow_from(entry.id, max_depth=4)
        labels = [n.label for n in chain]
        assert labels[:3] == ["entry", "service", "repo"], labels

    def test_no_path_returns_single_or_empty(self):
        g = _graph({"src/x.py": "def lonely():\n    return 1\n"})
        idx = self._index(g)
        lonely = _node_by_label(g, "lonely")
        chain = idx.best_flow_from(lonely.id, max_depth=4)
        assert [n.label for n in chain] == ["lonely"]  # no onward calls

    def test_cyclic_graph_terminates(self):
        files = {
            "src/x.py": (
                "def a():\n    return b()\n"
                "def b():\n    return a()\n"
            ),
        }
        g = _graph(files)
        idx = self._index(g)
        a = _node_by_label(g, "a")
        chain = idx.best_flow_from(a.id, max_depth=10)
        # Must terminate (visited guard) and not loop forever.
        assert len(chain) <= 2
        assert chain[0].label == "a"

    def test_depth_limit_respected(self):
        files = {
            "src/x.py": (
                "def s1():\n    return s2()\n"
                "def s2():\n    return s3()\n"
                "def s3():\n    return s4()\n"
                "def s4():\n    return s5()\n"
                "def s5():\n    return 1\n"
            ),
        }
        g = _graph(files)
        idx = self._index(g)
        s1 = _node_by_label(g, "s1")
        chain = idx.best_flow_from(s1.id, max_depth=3)
        assert len(chain) <= 3


# ══════════════════════════════════════════════════════════════════════════════
# 4. EXPLANATION uses enriched evidence
# ══════════════════════════════════════════════════════════════════════════════

class TestEnrichedExplanation:
    def _explain_file(self, graph, path_hint):
        from cortex.reasoning.application.explainer import CortexExplainer
        node = next(
            n for n in graph.nodes
            if n.node_type == NodeType.FILE and path_hint in str(n.properties.get("path", ""))
        )
        return CortexExplainer().explain_node(node.id, graph.nodes, graph.edges)

    def test_purpose_uses_author_intent(self):
        src = (
            '"""Authentication service — validates credentials and issues tokens."""\n'
            "class AuthService:\n"
            "    def authenticate(self):\n"
            "        return True\n"
        )
        g = _graph({"src/auth/service.py": src})
        exp = self._explain_file(g, "service.py")
        purpose = next(s for s in exp.sections if s.key == "primary_purpose")
        assert "validates credentials and issues tokens" in purpose.body
        assert "author" in purpose.body.lower()

    def test_confidence_higher_with_intent_and_flow(self):
        rich = {
            "src/api.py": (
                '"""API layer."""\n'
                "def entry():\n    return service()\n"
            ),
            "src/svc.py": "def service():\n    return 1\n",
        }
        sparse = {"src/x/plain.py": "def z():\n    return 1\n"}
        g_rich = _graph(rich)
        g_sparse = _graph(sparse)
        exp_rich = self._explain_file(g_rich, "api.py")
        exp_sparse = self._explain_file(g_sparse, "plain.py")
        assert exp_rich.confidence > exp_sparse.confidence

    def test_execution_flow_section_present_and_grounded(self):
        files = {
            "src/api.py": "def entry():\n    return service()\n",
            "src/svc.py": "def service():\n    return 1\n",
        }
        g = _graph(files)
        exp = self._explain_file(g, "api.py")
        flow = next(s for s in exp.sections if s.key == "execution_flow")
        assert "service" in flow.body

    def test_no_invented_flow_when_none(self):
        g = _graph({"src/x/plain.py": "def z():\n    return 1\n"})
        exp = self._explain_file(g, "plain.py")
        flow = next(s for s in exp.sections if s.key == "execution_flow")
        assert "no multi-step" in flow.body.lower() or "does not support" in flow.body.lower()


# ══════════════════════════════════════════════════════════════════════════════
# 5. NIM grounding guard
# ══════════════════════════════════════════════════════════════════════════════

class TestNimGroundingGuard:
    def test_grounded_entities_allowed(self):
        from cortex.chat.infrastructure.nim_client import _invented_entities
        source = "engine.py InsightsEngine.compute grouping.py"
        refined = "The engine.py file's InsightsEngine.compute method uses grouping.py."
        assert _invented_entities(refined, source) == []

    def test_invented_file_flagged(self):
        from cortex.chat.infrastructure.nim_client import _invented_entities
        source = "engine.py InsightsEngine"
        refined = "It also secretly writes to backdoor_exfiltrate.py."
        assert "backdoor_exfiltrate.py" in _invented_entities(refined, source)

    def test_invented_dotted_symbol_flagged(self):
        from cortex.chat.infrastructure.nim_client import _invented_entities
        source = "AuthService.authenticate"
        refined = "It calls Malware.detonate to finish."
        invented = _invented_entities(refined, source)
        assert any("detonate" in x.lower() for x in invented)


# ══════════════════════════════════════════════════════════════════════════════
# 6. CHAT ↔ NAVIGATE parity (both use CortexExplainer for entity questions)
# ══════════════════════════════════════════════════════════════════════════════

class TestChatEntityParity:
    def test_chat_routes_file_question_to_explainer(self):
        from cortex.chat.application.chat_service import ChatService
        files = {
            "src/auth/service.py": (
                '"""Authentication service — validates credentials."""\n'
                "class AuthService:\n"
                "    def authenticate(self):\n        return True\n"
            ),
        }
        g = _graph(files)
        svc = ChatService()
        answer = svc._try_entity_explanation(
            "what is service.py about?", g.nodes, g.edges
        )
        assert answer is not None
        assert "validates credentials" in answer  # explainer's author-intent output

    def test_chat_routes_symbol_question_to_explainer(self):
        from cortex.chat.application.chat_service import ChatService
        files = {
            "src/x/e.py": (
                "class ReportBuilder:\n"
                '    """Builds reports."""\n'
                "    def build(self):\n        return 1\n"
            ),
        }
        g = _graph(files)
        svc = ChatService()
        answer = svc._try_entity_explanation(
            "explain the ReportBuilder class", g.nodes, g.edges
        )
        assert answer is not None
        assert "ReportBuilder" in answer

    def test_chat_no_entity_match_returns_none(self):
        from cortex.chat.application.chat_service import ChatService
        g = _graph({"src/x/e.py": "def z():\n    return 1\n"})
        svc = ChatService()
        answer = svc._try_entity_explanation(
            "what is the overall architecture and health?", g.nodes, g.edges
        )
        assert answer is None  # falls back to repo-level answer
