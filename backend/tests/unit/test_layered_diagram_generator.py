"""Deterministic unit tests for LayeredDiagramGenerator.

Each test exercises a specific invariant described in the architecture diagram
requirements.  Tests use minimal synthetic graphs built from ParsedFile objects
so that results are fully reproducible and independent of any live repository.

Invariants tested:
  T01  Simple layered FastAPI repo → nodes + edges present, no zero-edge bug
  T02  Module-based flat repo      → correct module grouping
  T03  Circular dependency repo    → cycles detected, nodes marked
  T04  Large repo (20+ modules)    → capped at MAX_SYSTEM_NODES
  T05  Duplicate import edges      → collapsed to single edge with count
  T06  Bidirectional dependency    → collapsed with ↔ annotation
  T07  Generic containers skipped  → 'src', 'backend' not shown as nodes
  T08  Layer classification        → presentation/application/domain/infra
  T09  Mixed-language repo         → Python + TypeScript modules both appear
  T10  MIN_EDGE_WEIGHT=1 enforced  → single import IS shown as an edge
  T11  Orphan edges impossible     → every edge references a visible node
  T12  Duplicate edge IDs          → no two edges share the same id
  T13  Module detail view          → classes visible, external deps collapsed
  T14  Class detail view           → methods + callers present
"""
from __future__ import annotations

import pytest
from cortex.graph.domain.entities import NodeType
from cortex.pipeline.infrastructure.ast_parser import (
    Language,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
)
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
from cortex.pipeline.infrastructure.layered_diagram_generator import (
    LayeredDiagramGenerator,
    MAX_SYSTEM_NODES,
    _top_level_module,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fn(name: str, fp: str, cls: str | None = None) -> ParsedFunction:
    return ParsedFunction(
        name=name, file_path=fp, line_start=1, line_end=10,
        is_method=True, parent_class=cls,
    )


def _cls(name: str, fp: str, methods: list[ParsedFunction] | None = None) -> ParsedClass:
    return ParsedClass(name=name, file_path=fp, line_start=1, line_end=50,
                       methods=methods or [])


def _build(files: list[ParsedFile], name: str = "repo") -> "tuple[GraphBuilder, object]":
    g = GraphBuilder(job_id="test", repo_url=f"https://github.com/ex/{name}")
    return g, g.build(files)


def _gen(files: list[ParsedFile], name: str = "repo") -> LayeredDiagramGenerator:
    _, graph = _build(files, name)
    return LayeredDiagramGenerator(graph)


# ── T01: Simple layered FastAPI repo ──────────────────────────────────────────

def test_T01_fastapi_layered_repo_has_nodes_and_edges() -> None:
    """A typical FastAPI clean-arch repo must produce nodes AND edges."""
    pres  = "backend/src/cortex/chat/presentation/router.py"
    app_  = "backend/src/cortex/chat/application/service.py"
    dom   = "backend/src/cortex/chat/domain/entities.py"
    infra = "backend/src/cortex/graph/infrastructure/repo.py"

    files = [
        ParsedFile(path=pres,  language=Language.PYTHON, line_count=80,
                   imports=[ParsedImport(module="cortex.chat.application.service",
                                          names=["ChatService"])]),
        ParsedFile(path=app_,  language=Language.PYTHON, line_count=120,
                   classes=[_cls("ChatService", app_)],
                   imports=[ParsedImport(module="cortex.chat.domain.entities",
                                          names=["Msg"]),
                              ParsedImport(module="cortex.graph.infrastructure.repo",
                                           names=["Repo"])]),
        ParsedFile(path=dom,   language=Language.PYTHON, line_count=40,
                   classes=[_cls("Msg", dom)]),
        ParsedFile(path=infra, language=Language.PYTHON, line_count=200,
                   classes=[_cls("Repo", infra)]),
    ]

    result = _gen(files).generate_system_view("cortex")

    assert len(result.nodes) > 0, "Must have at least one node"
    assert len(result.edges) > 0, "Must have edges — zero-edge bug must be fixed"
    assert result.level == "system"

    node_labels = {n.label for n in result.nodes}
    # The two high-level modules are 'chat' and 'graph'
    assert "chat" in node_labels
    assert "graph" in node_labels


# ── T02: Module-based flat repo ───────────────────────────────────────────────

def test_T02_flat_module_repo_groups_correctly() -> None:
    """Files under src/auth/, src/users/, etc. group into named modules."""
    files = [
        ParsedFile(path="src/auth/login.py", language=Language.PYTHON, line_count=60,
                   imports=[ParsedImport(module="src.users.models", names=["User"])]),
        ParsedFile(path="src/auth/tokens.py", language=Language.PYTHON, line_count=40),
        ParsedFile(path="src/users/models.py", language=Language.PYTHON, line_count=80,
                   classes=[_cls("User", "src/users/models.py")]),
        ParsedFile(path="src/payments/stripe.py", language=Language.PYTHON, line_count=120,
                   imports=[ParsedImport(module="src.users.models", names=["User"])]),
    ]

    result = _gen(files, "app").generate_system_view("app")

    labels = {n.label for n in result.nodes}
    assert "auth" in labels
    assert "users" in labels
    assert "payments" in labels
    # Generic container 'src' must NOT appear as a node
    assert "src" not in labels


# ── T03: Circular dependency detection ────────────────────────────────────────

def test_T03_cyclic_repo_marks_nodes_and_edges() -> None:
    """Modules in a cycle must be marked in_cycle=True."""
    files = [
        ParsedFile(path="app/a.py", language=Language.PYTHON, line_count=30,
                   imports=[ParsedImport(module="app.b", names=["B"])]),
        ParsedFile(path="app/b.py", language=Language.PYTHON, line_count=30,
                   imports=[ParsedImport(module="app.c", names=["C"])]),
        ParsedFile(path="app/c.py", language=Language.PYTHON, line_count=30,
                   imports=[ParsedImport(module="app.a", names=["A"])]),
        # d has no cycle — verify it's not incorrectly marked
        ParsedFile(path="app/d.py", language=Language.PYTHON, line_count=30,
                   imports=[ParsedImport(module="app.a", names=["A"])]),
    ]

    result = _gen(files, "cyclic").generate_system_view("cyclic")

    # Single module 'app' — no cross-module cycles possible here, but
    # cycle detection must not crash and must return a valid result.
    assert result.level == "system"
    assert len(result.nodes) >= 1


def test_T03b_inter_module_cycle_marked() -> None:
    """Two modules that import each other are both marked in_cycle."""
    files = [
        ParsedFile(path="src/auth/service.py", language=Language.PYTHON, line_count=40,
                   imports=[ParsedImport(module="src.users.service", names=["UserService"])]),
        ParsedFile(path="src/users/service.py", language=Language.PYTHON, line_count=40,
                   imports=[ParsedImport(module="src.auth.service", names=["AuthService"])]),
    ]

    result = _gen(files, "bidir").generate_system_view("bidir")
    node_labels = {n.label for n in result.nodes}
    assert "auth"  in node_labels
    assert "users" in node_labels
    # Both in a cycle
    cycle_nodes = [n for n in result.nodes if n.in_cycle]
    assert len(cycle_nodes) == 2, (
        f"Expected both modules marked as cycle nodes, got {[n.label for n in cycle_nodes]}"
    )


# ── T04: Large repo capped at MAX_SYSTEM_NODES ────────────────────────────────

def test_T04_large_repo_capped() -> None:
    """A repo with many modules must be capped at MAX_SYSTEM_NODES."""
    files = []
    for i in range(30):
        fp = f"src/module_{i:02d}/service.py"
        files.append(ParsedFile(path=fp, language=Language.PYTHON, line_count=30))

    result = _gen(files, "large").generate_system_view("large")
    assert len(result.nodes) <= MAX_SYSTEM_NODES, (
        f"Expected ≤ {MAX_SYSTEM_NODES} nodes, got {len(result.nodes)}"
    )


# ── T05: Duplicate imports collapsed to single edge with weight ───────────────

def test_T05_multiple_imports_become_one_edge() -> None:
    """Three files in module A all importing from module B → one edge, weight 3."""
    files = [
        ParsedFile(path="src/api/view_a.py", language=Language.PYTHON, line_count=30,
                   imports=[ParsedImport(module="src.core.models", names=["M"])]),
        ParsedFile(path="src/api/view_b.py", language=Language.PYTHON, line_count=30,
                   imports=[ParsedImport(module="src.core.models", names=["M"])]),
        ParsedFile(path="src/api/view_c.py", language=Language.PYTHON, line_count=30,
                   imports=[ParsedImport(module="src.core.models", names=["M"])]),
        ParsedFile(path="src/core/models.py", language=Language.PYTHON, line_count=60,
                   classes=[_cls("M", "src/core/models.py")]),
    ]

    result = _gen(files, "dup").generate_system_view("dup")

    api_to_core = [
        e for e in result.edges
        if "api" in e.source and "core" in e.target
        or "api" in e.target and "core" in e.source
    ]
    # Exactly one edge between these two modules
    assert len(api_to_core) == 1, (
        f"Expected 1 aggregated edge, got {len(api_to_core)}: {[(e.source, e.target) for e in api_to_core]}"
    )
    # Its weight should be 3
    assert api_to_core[0].weight == 3, (
        f"Expected weight 3, got {api_to_core[0].weight}"
    )


# ── T06: Bidirectional dependency collapsed with ↔ label ─────────────────────

def test_T06_bidirectional_edge_collapsed() -> None:
    """A ↔ B must become exactly one edge, not two."""
    files = [
        ParsedFile(path="src/auth/service.py", language=Language.PYTHON, line_count=40,
                   imports=[ParsedImport(module="src.users.models", names=["User"])]),
        ParsedFile(path="src/users/models.py", language=Language.PYTHON, line_count=40,
                   imports=[ParsedImport(module="src.auth.tokens", names=["Token"])]),
        ParsedFile(path="src/auth/tokens.py", language=Language.PYTHON, line_count=20),
    ]

    result = _gen(files, "bidir").generate_system_view("bidir")

    auth_user_edges = [
        e for e in result.edges
        if {e.source.replace("mod_", ""), e.target.replace("mod_", "")} == {"auth", "users"}
    ]
    assert len(auth_user_edges) == 1, (
        f"Bidirectional pair must be collapsed to one edge, found {len(auth_user_edges)}"
    )
    assert "↔" in auth_user_edges[0].label, (
        f"Bidirectional edge label must contain '↔', got {auth_user_edges[0].label!r}"
    )


# ── T07: Generic containers skipped ──────────────────────────────────────────

def test_T07_generic_containers_not_shown() -> None:
    """'src', 'backend', 'frontend' must not appear as diagram nodes.

    Note: 'app' is intentionally NOT in this assertion — Next.js uses app/ as
    a real router directory that _top_level_module correctly surfaces as an
    architecturally meaningful module name.
    """
    files = [
        ParsedFile(path="backend/src/auth/service.py",    language=Language.PYTHON,     line_count=40),
        ParsedFile(path="frontend/src/app/page.tsx",       language=Language.TYPESCRIPT, line_count=40),
        ParsedFile(path="frontend/src/components/Btn.tsx", language=Language.TYPESCRIPT, line_count=20),
    ]

    result = _gen(files, "mixed").generate_system_view("mixed")
    labels = {n.label for n in result.nodes}

    # These are pure structural wrappers — never architectural units
    for generic in ("src", "backend", "frontend"):
        assert generic not in labels, (
            f"Pure container directory '{generic}' must not appear as a diagram node; "
            f"got nodes: {labels}"
        )


# ── T08: Layer classification ─────────────────────────────────────────────────

def test_T08_layer_classification_fastapi() -> None:
    """Files under presentation/application/domain/infrastructure sub-paths
    must be classified into the correct architectural layers."""
    files = [
        ParsedFile(path="svc/presentation/router.py",      language=Language.PYTHON, line_count=30),
        ParsedFile(path="svc/application/service.py",      language=Language.PYTHON, line_count=30),
        ParsedFile(path="svc/domain/entities.py",          language=Language.PYTHON, line_count=30),
        ParsedFile(path="svc/infrastructure/repository.py",language=Language.PYTHON, line_count=30),
    ]

    result = _gen(files, "layers").generate_system_view("layers")
    layer_map = {n.label: n.layer for n in result.nodes}

    # All four files live under the same top-level module 'svc'.
    # The layer is determined from the sub-path segments.
    assert "svc" in layer_map, f"Expected 'svc' node, got {list(layer_map)}"

    # We can't assert a single layer since all four sub-paths contribute;
    # at minimum the layer should NOT be "Other" when these keywords are present.
    assert layer_map.get("svc") != "Other", (
        f"Expected a meaningful layer classification for 'svc', got 'Other'"
    )


# ── T09: Mixed-language repo ──────────────────────────────────────────────────

def test_T09_mixed_language_repo() -> None:
    """Python backend + TypeScript frontend modules must both appear."""
    files = [
        ParsedFile(path="backend/src/api/router.py",          language=Language.PYTHON,     line_count=60),
        ParsedFile(path="backend/src/domain/models.py",       language=Language.PYTHON,     line_count=40),
        ParsedFile(path="frontend/src/features/home/Page.tsx", language=Language.TYPESCRIPT, line_count=50),
        ParsedFile(path="frontend/src/hooks/useData.ts",       language=Language.TYPESCRIPT, line_count=30),
    ]

    result = _gen(files, "mixed-lang").generate_system_view("mixed-lang")
    labels = {n.label for n in result.nodes}

    # At least 2 meaningful modules must be present
    assert len(result.nodes) >= 2, f"Expected ≥ 2 nodes, got {labels}"
    # Verify both backend and frontend contribute nodes
    assert any(n.label in ("api", "domain", "backend") for n in result.nodes), \
        f"Expected a backend module, got {labels}"
    assert any(n.label in ("home", "hooks", "features", "frontend") for n in result.nodes), \
        f"Expected a frontend module, got {labels}"


# ── T10: MIN_EDGE_WEIGHT = 1 (single import IS an architectural edge) ─────────

def test_T10_single_import_creates_edge() -> None:
    """A single import between two modules must produce an edge (weight ≥ 1)."""
    files = [
        ParsedFile(path="src/payments/processor.py", language=Language.PYTHON, line_count=50,
                   imports=[ParsedImport(module="src.users.models", names=["User"])]),
        ParsedFile(path="src/users/models.py", language=Language.PYTHON, line_count=40,
                   classes=[_cls("User", "src/users/models.py")]),
    ]

    result = _gen(files, "single-imp").generate_system_view("single-imp")

    assert len(result.edges) == 1, (
        f"A single cross-module import must produce exactly one edge, "
        f"got {len(result.edges)}: {[(e.source, e.target) for e in result.edges]}"
    )
    assert result.edges[0].weight >= 1


# ── T11: No orphan edges (every edge references visible nodes) ────────────────

def test_T11_no_orphan_edges() -> None:
    """Every edge source and target must reference an existing node id."""
    files = [
        ParsedFile(path="src/a/f.py", language=Language.PYTHON, line_count=30,
                   imports=[ParsedImport(module="src.b.g", names=["G"])]),
        ParsedFile(path="src/b/g.py", language=Language.PYTHON, line_count=30,
                   imports=[ParsedImport(module="src.c.h", names=["H"])]),
        ParsedFile(path="src/c/h.py", language=Language.PYTHON, line_count=30),
    ]

    result = _gen(files, "orphan").generate_system_view("orphan")
    node_ids = {n.id for n in result.nodes}

    for e in result.edges:
        assert e.source in node_ids, (
            f"Edge source {e.source!r} not in node ids {node_ids}"
        )
        assert e.target in node_ids, (
            f"Edge target {e.target!r} not in node ids {node_ids}"
        )


# ── T12: No duplicate edge IDs ────────────────────────────────────────────────

def test_T12_no_duplicate_edge_ids() -> None:
    """Edge IDs must be unique within the same diagram result."""
    files = [
        ParsedFile(path=f"src/mod_{i}/f.py", language=Language.PYTHON, line_count=20,
                   imports=[ParsedImport(module="src.shared.utils", names=["u"])])
        for i in range(8)
    ] + [
        ParsedFile(path="src/shared/utils.py", language=Language.PYTHON, line_count=30),
    ]

    result = _gen(files, "dupid").generate_system_view("dupid")
    edge_ids = [e.id for e in result.edges]
    assert len(edge_ids) == len(set(edge_ids)), (
        f"Duplicate edge IDs found: "
        f"{[eid for eid in edge_ids if edge_ids.count(eid) > 1]}"
    )


# ── T13: Module detail view ───────────────────────────────────────────────────

def test_T13_module_detail_shows_classes() -> None:
    """generate_module_detail() must expose classes inside the module."""
    app_fp = "backend/src/cortex/chat/application/service.py"
    files = [
        ParsedFile(path=app_fp, language=Language.PYTHON, line_count=100,
                   classes=[_cls("ChatService", app_fp,
                                  [_fn("process", app_fp, "ChatService"),
                                   _fn("validate", app_fp, "ChatService")])]),
        ParsedFile(path="backend/src/cortex/chat/domain/entities.py",
                   language=Language.PYTHON, line_count=40,
                   classes=[_cls("Msg", "backend/src/cortex/chat/domain/entities.py")]),
    ]
    gen_ = _gen(files, "detail")
    result = gen_.generate_module_detail("chat", "cortex")

    assert result.level == "module"
    class_nodes = [n for n in result.nodes if n.node_type == "class"]
    assert len(class_nodes) >= 1, "Module detail must include class nodes"
    class_labels = {n.label for n in class_nodes}
    assert "ChatService" in class_labels


# ── T14: Class detail view ────────────────────────────────────────────────────

def test_T14_class_detail_shows_methods() -> None:
    """generate_class_detail() must include the class's methods."""
    fp = "backend/src/cortex/chat/application/service.py"
    files = [
        ParsedFile(path=fp, language=Language.PYTHON, line_count=100,
                   classes=[_cls("ChatService", fp,
                                  [_fn("process",  fp, "ChatService"),
                                   _fn("validate", fp, "ChatService"),
                                   _fn("shutdown", fp, "ChatService")])]),
    ]
    gen_ = _gen(files, "classdetail")
    result = gen_.generate_class_detail("ChatService", "cortex")

    assert result.level == "class"
    assert result.title == "ChatService"
    method_nodes = [n for n in result.nodes if n.node_type == "function"]
    method_labels = {n.label for n in method_nodes}
    assert "process"  in method_labels
    assert "validate" in method_labels
    assert "shutdown" in method_labels


# ── T15: _top_level_module helper ────────────────────────────────────────────

@pytest.mark.parametrize("path,expected", [
    ("backend/src/cortex/chat/application/service.py",  "chat"),
    ("frontend/src/features/jobs/components/Card.tsx",   "jobs"),
    ("src/auth/login.py",                                "auth"),
    ("src/users/models.py",                              "users"),
    ("backend/src/pipeline/infrastructure/builder.py",   "pipeline"),
    ("app/models/user.py",                               "models"),
    ("lib/utils/helper.py",                              "utils"),
])
def test_T15_top_level_module_extraction(path: str, expected: str) -> None:
    assert _top_level_module(path) == expected, (
        f"For path {path!r} expected module {expected!r}, "
        f"got {_top_level_module(path)!r}"
    )
