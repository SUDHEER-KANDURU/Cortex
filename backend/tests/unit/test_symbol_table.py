"""Unit tests for the symbol table and deterministic resolver (Task 4, Req 3)."""

from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.pipeline.infrastructure.ast_parser import (
    Language,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
)
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
from cortex.pipeline.infrastructure.symbol_table import SymbolTable

# ── Helpers ──────────────────────────────────────────────────────────────────


def _fn(name, file_path, line=1, calls=None, parent_class=None):
    return ParsedFunction(
        name=name,
        file_path=file_path,
        line_start=line,
        line_end=line,
        is_method=parent_class is not None,
        parent_class=parent_class,
        calls=calls or [],
    )


def _cls(name, file_path, line=1, methods=None):
    return ParsedClass(
        name=name,
        file_path=file_path,
        line_start=line,
        line_end=line + 10,
        methods=methods or [],
    )


def _file(path, functions=None, classes=None, imports=None):
    return ParsedFile(
        path=path,
        language=Language.PYTHON,
        functions=functions or [],
        classes=classes or [],
        imports=imports or [],
        line_count=20,
    )


# ── SymbolTable construction (Req 3.1) ─────────────────────────────────────────


def test_table_indexes_qualified_names_and_module_paths() -> None:
    files = [
        _file(
            "pkg/service.py",
            functions=[_fn("handle", "pkg/service.py")],
            classes=[
                _cls(
                    "Service",
                    "pkg/service.py",
                    methods=[_fn("run", "pkg/service.py", parent_class="Service")],
                )
            ],
        )
    ]
    table = SymbolTable.from_parsed_files(files)

    # Qualified method name resolves to the method's file.
    target = table.resolve("Service.run", from_file="other.py")
    assert target is not None
    assert target.file == "pkg/service.py"
    assert target.qualified_name == "Service.run"

    # Module path is indexed for import resolution.
    imp = table.resolve_import("pkg.service", from_file="other.py")
    assert imp is not None
    assert imp.file == "pkg/service.py"


# ── Call resolution scopes (Req 3.2) ───────────────────────────────────────────


def test_resolve_prefers_same_class_self_method() -> None:
    method = _fn("save", "a.py", parent_class="Repo")
    # A same-named free function elsewhere must NOT win over self.save.
    other = _fn("save", "b.py")
    files = [
        _file("a.py", classes=[_cls("Repo", "a.py", methods=[method])]),
        _file("b.py", functions=[other]),
    ]
    table = SymbolTable.from_parsed_files(files)

    target = table.resolve("self.save", from_file="a.py", parent_class="Repo")
    assert target is not None
    assert target.file == "a.py"
    assert target.qualified_name == "Repo.save"


def test_resolve_same_file_definition_wins() -> None:
    files = [
        _file("a.py", functions=[_fn("helper", "a.py"), _fn("caller", "a.py")]),
        _file("b.py", functions=[_fn("helper", "b.py")]),
    ]
    table = SymbolTable.from_parsed_files(files)

    target = table.resolve("helper", from_file="a.py")
    assert target is not None
    assert target.file == "a.py"


def test_ambiguous_bare_name_is_not_resolved() -> None:
    # Two unrelated definitions of `process` — resolving a bare `process` from a
    # third file must return None rather than guessing (Req 3.2).
    files = [
        _file("a.py", functions=[_fn("process", "a.py")]),
        _file("b.py", functions=[_fn("process", "b.py")]),
        _file("c.py", functions=[_fn("caller", "c.py")]),
    ]
    table = SymbolTable.from_parsed_files(files)

    assert table.resolve("process", from_file="c.py") is None


def test_repo_unique_definition_resolves() -> None:
    files = [
        _file("a.py", functions=[_fn("only_one", "a.py")]),
        _file("c.py", functions=[_fn("caller", "c.py")]),
    ]
    table = SymbolTable.from_parsed_files(files)

    target = table.resolve("only_one", from_file="c.py")
    assert target is not None
    assert target.file == "a.py"


# ── Import resolution: relative, alias, re-export (Req 3.3) ─────────────────────


def test_relative_import_resolves_within_package() -> None:
    files = [
        _file("pkg/service.py", functions=[_fn("run", "pkg/service.py")]),
        _file(
            "pkg/handler.py",
            imports=[ParsedImport(module=".service", names=["run"], is_relative=True)],
        ),
    ]
    table = SymbolTable.from_parsed_files(files)

    target = table.resolve_import(
        ".service", from_file="pkg/handler.py", imported_names=["run"], is_relative=True
    )
    assert target is not None
    assert target.file == "pkg/service.py"


def test_parent_relative_import_resolves() -> None:
    files = [
        _file("pkg/util.py", functions=[_fn("helper", "pkg/util.py")]),
        _file("pkg/sub/handler.py"),
    ]
    table = SymbolTable.from_parsed_files(files)

    target = table.resolve_import(
        "..util", from_file="pkg/sub/handler.py", imported_names=["helper"], is_relative=True
    )
    assert target is not None
    assert target.file == "pkg/util.py"


def test_path_alias_resolution() -> None:
    files = [_file("src/auth/service.ts", functions=[_fn("login", "src/auth/service.ts")])]
    table = SymbolTable.from_parsed_files(files, path_aliases={"@": "src"})

    target = table.resolve_import("@/auth/service", from_file="src/app/page.ts")
    assert target is not None
    assert target.file == "src/auth/service.ts"


def test_package_reexport_resolution() -> None:
    # pkg/__init__.py re-exports `Service`; importing the package resolves it.
    files = [
        _file(
            "pkg/__init__.py",
            classes=[_cls("Service", "pkg/__init__.py")],
        ),
        _file("app.py", imports=[ParsedImport(module="pkg", names=["Service"])]),
    ]
    table = SymbolTable.from_parsed_files(files)

    target = table.resolve_import("pkg", from_file="app.py", imported_names=["Service"])
    assert target is not None
    assert target.file == "pkg/__init__.py"


def test_unresolvable_import_returns_none() -> None:
    files = [_file("a.py", functions=[_fn("x", "a.py")])]
    table = SymbolTable.from_parsed_files(files)

    assert table.resolve_import("nonexistent.module", from_file="a.py") is None


# ── GraphBuilder wiring: counters, no fabricated edges (Req 3.2, 3.4) ───────────


def _calls_edges(result):
    return [e for e in result.edges if e.relationship == RelationshipType.CALLS]


def test_graph_builder_resolves_calls_and_counts_unresolved() -> None:
    # caller() calls resolvable `target` and unresolvable `mystery`.
    caller = _fn("caller", "pkg/a.py", calls=["target", "mystery"])
    target = _fn("target", "pkg/a.py", line=5)
    files = [_file("pkg/a.py", functions=[caller, target])]

    builder = GraphBuilder(job_id="job-1", repo_url="https://example.com/r")
    result = builder.build(files)

    calls = _calls_edges(result)
    assert len(calls) == 1

    caller_node = next(
        n for n in result.nodes
        if n.node_type == NodeType.FUNCTION and n.label == "caller"
    )
    assert caller_node.properties["resolved_calls"] == 1
    assert caller_node.properties["unresolved_calls"] == 1


def test_graph_builder_does_not_fabricate_edge_for_ambiguous_call() -> None:
    # Two `process` definitions; a bare `process` call must NOT create an edge.
    files = [
        _file("a.py", functions=[_fn("process", "a.py")]),
        _file("b.py", functions=[_fn("process", "b.py")]),
        _file("c.py", functions=[_fn("caller", "c.py", calls=["process"])]),
    ]
    builder = GraphBuilder(job_id="job-2", repo_url="https://example.com/r")
    result = builder.build(files)

    assert _calls_edges(result) == []
    caller_node = next(n for n in result.nodes if n.label == "caller")
    assert caller_node.properties["unresolved_calls"] == 1


def test_graph_builder_import_edges_use_resolver() -> None:
    files = [
        _file("pkg/service.py", functions=[_fn("run", "pkg/service.py")]),
        _file(
            "pkg/handler.py",
            imports=[ParsedImport(module="pkg.service", names=["run"])],
        ),
    ]
    builder = GraphBuilder(job_id="job-3", repo_url="https://example.com/r")
    result = builder.build(files)

    import_edges = [e for e in result.edges if e.relationship == RelationshipType.IMPORTS]
    assert len(import_edges) == 1

    handler_node = next(
        n for n in result.nodes
        if n.node_type == NodeType.FILE and n.properties.get("path") == "pkg/handler.py"
    )
    assert handler_node.properties["resolved_imports"] == 1
    assert handler_node.properties["unresolved_imports"] == 0


# ── Determinism (Req 3.5) ───────────────────────────────────────────────────────


def _sorted_edge_signatures(result):
    """Stable, id-independent signature of every edge for comparison."""
    id_to_key = {}
    for n in result.nodes:
        # Node ids embed the job prefix; key by type+label+file for stability.
        id_to_key[n.id] = (
            n.node_type.value,
            n.label,
            str(n.properties.get("path", "") or n.properties.get("file", "")),
        )
    return sorted(
        (
            id_to_key.get(e.source_id, ("?",)),
            id_to_key.get(e.target_id, ("?",)),
            e.relationship.value,
        )
        for e in result.edges
    )


def test_resolution_is_deterministic_across_runs() -> None:
    # A repository with calls, imports, and one ambiguous name.
    def make_files():
        return [
            _file(
                "pkg/service.py",
                functions=[
                    _fn("run", "pkg/service.py", calls=["persist", "helper"]),
                    _fn("persist", "pkg/service.py", line=5),
                ],
                classes=[
                    _cls(
                        "Service",
                        "pkg/service.py",
                        methods=[
                            _fn(
                                "act",
                                "pkg/service.py",
                                parent_class="Service",
                                calls=["self.run"],
                            )
                        ],
                    )
                ],
            ),
            _file("pkg/util.py", functions=[_fn("helper", "pkg/util.py")]),
            _file(
                "pkg/handler.py",
                functions=[_fn("dispatch", "pkg/handler.py", calls=["run"])],
                imports=[ParsedImport(module="pkg.service", names=["run"])],
            ),
        ]

    sig_runs = []
    for i in range(3):
        builder = GraphBuilder(job_id=f"job-{i}", repo_url="https://example.com/r")
        # Feed files in different orders to prove order-independence.
        files = make_files()
        if i == 1:
            files = list(reversed(files))
        result = builder.build(files)
        sig_runs.append(_sorted_edge_signatures(result))

    assert sig_runs[0] == sig_runs[1] == sig_runs[2]
