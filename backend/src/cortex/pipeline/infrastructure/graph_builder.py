"""Graph builder — converts parsed code structure into knowledge graph.
Takes ParsedFile objects from the AST parser and creates
GraphNode and GraphEdge domain entities for persistent storage."""

import hashlib
import uuid
from dataclasses import dataclass, field

import structlog
from cortex.graph.domain.entities import (
    GraphEdge,
    GraphNode,
    NodeType,
    RelationshipType,
)
from cortex.pipeline.infrastructure.ast_parser import (
    ParsedClass,
    ParsedFile,
    ParsedFunction,
)
from cortex.pipeline.infrastructure.symbol_table import SymbolTable

logger = structlog.get_logger()


@dataclass
class GraphBuildResult:
    """Result of building a knowledge graph from parsed files."""
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    job_id: str = ""
    repo_url: str = ""
    stats: dict = field(default_factory=dict)
    # O(1) node lookup by id — populated by GraphBuilder.build()
    node_by_id: dict = field(default_factory=dict)

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)

    def nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        return [n for n in self.nodes if n.node_type == node_type]

    def summary(self) -> dict:
        return {
            "total_nodes": self.node_count(),
            "total_edges": self.edge_count(),
            "repositories": len(self.nodes_by_type(NodeType.REPOSITORY)),
            "modules": len(self.nodes_by_type(NodeType.MODULE)),
            "files": len(self.nodes_by_type(NodeType.FILE)),
            "classes": len(self.nodes_by_type(NodeType.CLASS)),
            "interfaces": len(self.nodes_by_type(NodeType.INTERFACE)),
            "enums": len(self.nodes_by_type(NodeType.ENUM)),
            "functions": len(self.nodes_by_type(NodeType.FUNCTION)),
            "methods": len(self.nodes_by_type(NodeType.METHOD)),
            "endpoints": len(self.nodes_by_type(NodeType.ENDPOINT)),
            "tests": len(self.nodes_by_type(NodeType.TEST)),
        }


class GraphBuilder:
    """Builds a knowledge graph from parsed source code.

    Takes a list of ParsedFile objects (from ASTParser) and
    produces GraphNode and GraphEdge objects representing the
    full structure of the codebase.

    Graph structure:
        Repository
          └── CONTAINS → Module (directory/package)
                └── CONTAINS → File
                      └── CONTAINS → Class | Interface | Enum
                            └── CONTAINS → Method
                      └── CONTAINS → Function | Endpoint | Test
        File → IMPORTS → File (via module resolution)
        Class → INHERITS → Class (base class)
        Class → IMPLEMENTS → Interface (ABC/Protocol)
        Function → CALLS → Function (detected call targets)
        TestFile → TESTS → Module (heuristic from filename)
    """

    def __init__(
        self,
        job_id: str,
        repo_url: str,
        path_aliases: dict[str, str] | None = None,
    ) -> None:
        self._job_id = job_id
        self._repo_url = repo_url
        self._node_index: dict[str, GraphNode] = {}
        # Configured path aliases (e.g. tsconfig ``paths``) used by the symbol
        # resolver to resolve aliased imports (Req 3.3). Empty by default.
        self._path_aliases: dict[str, str] = dict(path_aliases or {})

    def build(self, parsed_files: list[ParsedFile]) -> GraphBuildResult:
        """Build the complete knowledge graph from parsed files.

        Returns a GraphBuildResult with all nodes and edges.
        Safe to call with empty list — returns empty graph.
        """
        result = GraphBuildResult(
            job_id=self._job_id,
            repo_url=self._repo_url,
        )

        if not parsed_files:
            logger.warning(
                "graph_builder_no_files",
                job_id=self._job_id,
            )
            return result

        # Step 0 — Build the deterministic symbol table pre-pass (Req 3.1).
        # Populated from ALL parsed files so call/import resolution has full
        # repo context before any edge is created.
        symbol_table = SymbolTable.from_parsed_files(
            parsed_files, path_aliases=self._path_aliases
        )

        # Step 1 — Create repository root node
        repo_node = self._create_repo_node()
        result.nodes.append(repo_node)
        self._node_index[repo_node.id] = repo_node

        # Step 2 — Detect modules from file paths
        modules = self._detect_modules(parsed_files)
        module_nodes: dict[str, GraphNode] = {}

        for module_path in modules:
            module_node = self._create_module_node(module_path)
            result.nodes.append(module_node)
            module_nodes[module_path] = module_node
            self._node_index[module_node.id] = module_node

        # Module hierarchy (repo -> top-level module -> nested module)
        for module_path in modules:
            parent_module_path = self._get_parent_module_path(module_path)
            parent_node = (
                module_nodes[parent_module_path]
                if parent_module_path and parent_module_path in module_nodes
                else repo_node
            )
            result.edges.append(self._create_edge(
                source=parent_node,
                target=module_nodes[module_path],
                relationship=RelationshipType.CONTAINS,
            ))

        # Step 3 — Create file nodes
        file_nodes: dict[str, GraphNode] = {}

        for parsed_file in parsed_files:
            if parsed_file.has_errors() and not parsed_file.classes:
                continue

            file_node = self._create_file_node(parsed_file)
            result.nodes.append(file_node)
            file_nodes[parsed_file.path] = file_node
            self._node_index[file_node.id] = file_node

            # Find parent module and connect
            parent_module = self._find_parent_module(
                parsed_file.path, module_nodes
            )
            parent_node = (
                module_nodes[parent_module]
                if parent_module
                else repo_node
            )
            result.edges.append(self._create_edge(
                source=parent_node,
                target=file_node,
                relationship=RelationshipType.CONTAINS,
            ))

        # Step 4 — Create class and function nodes and import edges
        for parsed_file in parsed_files:
            file_node = file_nodes.get(parsed_file.path)
            if not file_node:
                continue

            for parsed_class in parsed_file.classes:
                class_node = self._create_class_node(
                    parsed_class, parsed_file.path
                )
                result.nodes.append(class_node)
                self._node_index[class_node.id] = class_node

                # File CONTAINS Class
                result.edges.append(self._create_edge(
                    source=file_node,
                    target=class_node,
                    relationship=RelationshipType.CONTAINS,
                ))

                # Step 5 — Create method nodes
                for method in parsed_class.methods:
                    method_node = self._create_function_node(
                        method, parsed_file.path
                    )
                    result.nodes.append(method_node)
                    self._node_index[method_node.id] = method_node

                    # Class CONTAINS Method
                    result.edges.append(self._create_edge(
                        source=class_node,
                        target=method_node,
                        relationship=RelationshipType.CONTAINS,
                    ))

            # Step 6 — Create top-level function nodes
            for function in parsed_file.functions:
                fn_node = self._create_function_node(
                    function, parsed_file.path
                )
                result.nodes.append(fn_node)
                self._node_index[fn_node.id] = fn_node

                # File CONTAINS Function
                result.edges.append(self._create_edge(
                    source=file_node,
                    target=fn_node,
                    relationship=RelationshipType.CONTAINS,
                ))

            # Step 7 — Create import edges via the deterministic resolver.
            # The resolver understands relative imports, package re-exports,
            # and configured path aliases (Req 3.3). An IMPORTS edge is created
            # ONLY when a module resolves to a single file; otherwise the
            # reference is counted as unresolved, never fabricated (Req 3.2).
            resolved_imports = 0
            unresolved_imports = 0
            seen_import_targets: set[str] = set()
            for imp in parsed_file.imports:
                if not imp.module:
                    continue
                resolved = symbol_table.resolve_import(
                    imp.module,
                    from_file=parsed_file.path,
                    imported_names=imp.names,
                    is_relative=imp.is_relative,
                )
                target_node = None
                if resolved is not None:
                    target_node = file_nodes.get(resolved.file)
                    if target_node is None:
                        target_node = self._node_index.get(
                            self._make_id("file", resolved.file)
                        )
                if target_node is None or target_node.id == file_node.id:
                    unresolved_imports += 1
                    continue
                if target_node.id in seen_import_targets:
                    continue
                seen_import_targets.add(target_node.id)
                resolved_imports += 1
                result.edges.append(self._create_edge(
                    source=file_node,
                    target=target_node,
                    relationship=RelationshipType.IMPORTS,
                ))

            # Honest per-file evidence of import-graph completeness (Req 3.4).
            file_node.properties["resolved_imports"] = resolved_imports
            file_node.properties["unresolved_imports"] = unresolved_imports

        # Step 8 — Add inheritance and implements edges between classes
        class_name_index: dict[str, GraphNode] = {
            n.label: n
            for n in result.nodes
            if n.node_type in (NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM)
        }

        for parsed_file in parsed_files:
            for parsed_class in parsed_file.classes:
                class_node = class_name_index.get(parsed_class.name)
                if not class_node:
                    continue
                for base in parsed_class.base_classes:
                    base_node = class_name_index.get(base)
                    if base_node:
                        # If base is an interface/protocol, use IMPLEMENTS
                        if base_node.node_type == NodeType.INTERFACE:
                            result.edges.append(self._create_edge(
                                source=class_node,
                                target=base_node,
                                relationship=RelationshipType.IMPLEMENTS,
                            ))
                        else:
                            result.edges.append(self._create_edge(
                                source=class_node,
                                target=base_node,
                                relationship=RelationshipType.INHERITS,
                            ))

        # Step 9 — Add CALLS edges from function call targets
        # ── Scoped, collision-safe call resolution ───────────────────────────
        # A bare name like `save` must NOT link to every `save` in the repo.
        # Resolve each call using the STRONGEST available context, in order:
        #   1. self.<method>  → a method of the SAME class
        #   2. <name>         → a symbol defined in the SAME file
        #   3. <name>         → a symbol imported by this file (unambiguous)
        #   4. Class.method / qualified → exact qualified-name match
        #   5. <name>         → a repo-wide UNIQUE definition (only if exactly one)
        # If a call cannot be resolved confidently, it is counted as UNRESOLVED
        # and NO edge is fabricated.
        # Which internal modules/symbols each file imports (for imported scope).
        imports_by_file = self._imports_by_file(parsed_files)

        # A generous but bounded per-function edge cap prevents pathological
        # fan-out while preserving complete meaningful relationships.
        max_call_edges_per_fn = 25

        for parsed_file in parsed_files:
            file_path = parsed_file.path
            for fn in parsed_file.all_functions():
                if not fn.calls:
                    continue
                source_node_id = self._make_id("fn", f"{file_path}.{fn.qualified_name()}")
                source_node = self._node_index.get(source_node_id)
                if not source_node:
                    continue

                parent_class = fn.parent_class or ""
                resolved_targets: set[str] = set()
                unresolved = 0

                for raw_call in fn.calls:
                    resolved = symbol_table.resolve(
                        raw_call,
                        from_file=file_path,
                        imports=imports_by_file.get(file_path, set()),
                        parent_class=parent_class,
                    )
                    target = None
                    if resolved is not None:
                        target = self._node_index.get(
                            self._make_id("fn", f"{resolved.file}.{resolved.qualified_name}")
                        )
                    if target is None or target.id == source_node.id:
                        if resolved is None or target is None:
                            unresolved += 1
                        continue
                    if target.id in resolved_targets:
                        continue
                    if len(resolved_targets) >= max_call_edges_per_fn:
                        break
                    resolved_targets.add(target.id)
                    result.edges.append(self._create_edge(
                        source=source_node,
                        target=target,
                        relationship=RelationshipType.CALLS,
                    ))

                # Record how many calls we could NOT resolve — honest evidence
                # of graph incompleteness that the explainer uses for confidence.
                source_node.properties["resolved_calls"] = len(resolved_targets)
                source_node.properties["unresolved_calls"] = unresolved

        # Step 10 — Add TESTS edges from test files to modules they test
        # Heuristic: test file "test_jobs.py" or "jobs_test.py" likely tests
        # the module "jobs". Connect test file node to the matching module.
        test_file_nodes = [
            (pf, file_nodes[pf.path])
            for pf in parsed_files
            if pf.is_test_file and pf.path in file_nodes
        ]
        for parsed_file, test_node in test_file_nodes:
            # Extract what this test might be testing from filename
            import os
            basename = os.path.basename(parsed_file.path)
            stem = basename.replace(".py", "").replace(".ts", "").replace(".js", "")
            # Remove test prefixes/suffixes
            tested_name = (
                stem.replace("test_", "")
                .replace("_test", "")
                .replace(".test", "")
                .replace(".spec", "")
                .replace("spec_", "")
            )
            if tested_name:
                # Look for a matching module or file
                for module_path, module_node in module_nodes.items():
                    if tested_name in module_path.split("/"):
                        result.edges.append(self._create_edge(
                            source=test_node,
                            target=module_node,
                            relationship=RelationshipType.TESTS,
                        ))
                        break

        result.stats = result.summary()
        # Build the O(1) lookup dict so artifact generators don't need
        # to do linear scans over result.nodes.
        result.node_by_id = {n.id: n for n in result.nodes}
        self._emit_debug_summary(parsed_files, result, modules)

        logger.info(
            "graph_built",
            job_id=self._job_id,
            **result.stats,
        )

        return result

    def _create_repo_node(self) -> GraphNode:
        """Create the root repository node."""
        repo_name = self._repo_url.rstrip("/").split("/")[-1]
        return GraphNode(
            id=self._make_id("repo", repo_name),
            label=repo_name,
            node_type=NodeType.REPOSITORY,
            job_id=self._job_id,
            properties={
                "url": self._repo_url,
                "name": repo_name,
            },
        )

    def _create_module_node(self, module_path: str) -> GraphNode:
        """Create a module (directory/package) node."""
        name = module_path.split("/")[-1]
        return GraphNode(
            id=self._make_id("module", module_path),
            label=f"{name}/",
            node_type=NodeType.MODULE,
            job_id=self._job_id,
            properties={"path": module_path},
        )

    def _create_file_node(self, parsed_file: ParsedFile) -> GraphNode:
        """Create a file node from a parsed file."""
        name = parsed_file.path.split("/")[-1]
        return GraphNode(
            id=self._make_id("file", parsed_file.path),
            label=name,
            node_type=NodeType.FILE,
            job_id=self._job_id,
            properties={
                "path": parsed_file.path,
                "language": parsed_file.language.value,
                "lines": parsed_file.line_count,
                "classes": len(parsed_file.classes),
                "functions": len(parsed_file.functions),
                "imports": len(parsed_file.imports),
                "is_test_file": parsed_file.is_test_file,
                "is_config_file": parsed_file.is_config_file,
                "total_complexity": parsed_file.total_complexity(),
                "max_complexity": parsed_file.max_complexity(),
                "endpoints": len(parsed_file.all_endpoints()),
                "documentation_ratio": round(parsed_file.documentation_ratio(), 2),
                # Author intent: the module-level docstring, bounded.
                "docstring_summary": self._docstring_summary(parsed_file.docstring),
            },
        )

    def _create_class_node(
        self,
        parsed_class: ParsedClass,
        file_path: str,
    ) -> GraphNode:
        """Create a class, interface, or enum node based on detection."""
        cls_lines = max(0, (parsed_class.line_end or parsed_class.line_start) - parsed_class.line_start + 1)

        # Determine node type based on AST detection
        if parsed_class.is_enum:
            node_type = NodeType.ENUM
        elif parsed_class.is_interface:
            node_type = NodeType.INTERFACE
        else:
            node_type = NodeType.CLASS

        return GraphNode(
            id=self._make_id("class", f"{file_path}.{parsed_class.name}"),
            label=parsed_class.name,
            node_type=node_type,
            job_id=self._job_id,
            properties={
                "file": file_path,
                "line": parsed_class.line_start,
                "lines": cls_lines,
                "methods": parsed_class.method_count(),
                "base_classes": ", ".join(parsed_class.base_classes),
                "is_abstract": parsed_class.is_abstract(),
                "is_interface": parsed_class.is_interface,
                "is_enum": parsed_class.is_enum,
                "has_docstring": parsed_class.has_docstring(),
                "docstring_summary": self._docstring_summary(parsed_class.docstring),
                "decorators": ", ".join(parsed_class.decorators),
                "attributes": ", ".join(parsed_class.attributes[:15]),
                "attribute_count": len(parsed_class.attributes),
                "total_complexity": parsed_class.total_complexity(),
                "avg_method_complexity": round(parsed_class.avg_method_complexity(), 2),
            },
        )

    def _create_function_node(
        self,
        fn: ParsedFunction,
        file_path: str,
    ) -> GraphNode:
        """Create a function, method, endpoint, or test node."""
        # Determine node type based on function characteristics
        if fn.is_endpoint:
            node_type = NodeType.ENDPOINT
        elif fn.is_test:
            node_type = NodeType.TEST
        elif fn.is_method:
            node_type = NodeType.METHOD
        else:
            node_type = NodeType.FUNCTION

        return GraphNode(
            id=self._make_id(
                "fn", f"{file_path}.{fn.qualified_name()}"
            ),
            label=fn.name,
            node_type=node_type,
            job_id=self._job_id,
            properties={
                "file":          file_path,
                "line":          fn.line_start,
                "is_async":      fn.is_async,
                "is_method":     fn.is_method,
                "parameters":    ", ".join(fn.parameters),
                "param_count":   len(fn.parameters),
                "lines":         fn.line_count(),
                "has_docstring": fn.has_docstring(),
                "docstring_summary": self._docstring_summary(fn.docstring),
                "decorators":    ", ".join(fn.decorators),
                "qualified_name": fn.qualified_name(),
                "parent_class":   fn.parent_class or "",
                # ── Complexity metrics ────────────────────────────────────────
                "cyclomatic":       fn.cyclomatic_complexity,
                "branch_count":     fn.branch_count,
                "nesting_depth":    fn.nesting_depth,
                "call_count":       fn.call_count,
                "return_type":      fn.return_type or "",
                "is_test":          fn.is_test,
                "is_endpoint":      fn.is_endpoint,
                "route_info":       fn.route_info or "",
                "calls":            ", ".join(fn.calls[:20]),
            },
        )

    def _create_edge(
        self,
        source: GraphNode,
        target: GraphNode,
        relationship: RelationshipType,
    ) -> GraphEdge:
        """Create an edge between two nodes."""
        return GraphEdge(
            id=str(uuid.uuid4()),
            source_id=source.id,
            target_id=target.id,
            relationship=relationship,
            job_id=self._job_id,
        )

    def _detect_modules(
        self,
        parsed_files: list[ParsedFile],
    ) -> list[str]:
        """Detect repository-relative module paths, including root folders.

        The production graph expects module boundaries to include the repo root
        and the top-level directory segments, not only the deepest package folder.
        This keeps the graph hierarchical and matches the module expectations in
        the tests.
        """
        modules: set[str] = set()
        for parsed_file in parsed_files:
            parts = [part for part in self._normalize_path(parsed_file.path).split("/") if part]
            if not parts:
                continue

            max_depth = min(len(parts) - 1, 4)
            for end in range(1, max_depth + 1):
                modules.add("/".join(parts[:end]))

        return sorted(modules)

    def _get_parent_module_path(self, module_path: str) -> str | None:
        """Return the parent directory module path for a module."""
        normalized_path = self._normalize_path(module_path)
        parts = [part for part in normalized_path.split("/") if part]
        if len(parts) <= 1:
            return None
        return "/".join(parts[:-1])

    def _find_parent_module(
        self,
        file_path: str,
        module_nodes: dict[str, GraphNode],
    ) -> str | None:
        """Find which module a file belongs to — longest path match wins."""
        normalized_file = self._normalize_path(file_path)
        best_match = None
        best_length = 0
        for module_path in module_nodes.keys():
            normalized_module = self._normalize_path(module_path)
            if normalized_module and (
                normalized_file == normalized_module
                or normalized_file.startswith(f"{normalized_module}/")
            ) and len(normalized_module) > best_length:
                best_match = module_path
                best_length = len(normalized_module)
        return best_match

    def _normalize_path(self, path: str) -> str:
        """Normalize a repository-relative path to forward-slash form."""
        return path.replace("\\", "/").strip("/")

    def _emit_debug_summary(
        self,
        parsed_files: list[ParsedFile],
        result: GraphBuildResult,
        modules: list[str],
    ) -> None:
        """Emit graph construction summary at DEBUG level.

        Previously used print() calls that fired unconditionally in
        production. Now uses structlog at debug level — only appears
        when LOG_LEVEL=DEBUG is set.
        """
        logger.debug(
            "graph_debug_summary",
            total_repository_files=len(parsed_files),
            total_graph_nodes=len(result.nodes),
            total_graph_edges=len(result.edges),
            detected_modules=modules[:50],
            first_20_nodes=[
                {
                    "type": node.node_type.value,
                    "label": node.label,
                    "path": node.properties.get("path"),
                }
                for node in result.nodes[:20]
            ],
            first_20_edges=[
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relationship": edge.relationship.value,
                }
                for edge in result.edges[:20]
            ],
        )

    def _imports_by_file(
        self,
        parsed_files: list[ParsedFile],
    ) -> dict[str, set[str]]:
        """Map each file path to the set of simple symbol names it imports.

        Used so a bare call can be resolved to an imported symbol only when the
        current file actually imports something of that name.
        """
        out: dict[str, set[str]] = {}
        for pf in parsed_files:
            names: set[str] = set()
            for imp in pf.imports:
                for n in imp.names:
                    names.add(n)
                # `import x.y.z` / `from a import b` — last module segment too.
                if imp.module:
                    names.add(imp.module.split(".")[-1])
            out[pf.path] = names
        return out

    @staticmethod
    def _docstring_summary(docstring: str | None, limit: int = 240) -> str:
        """Return a bounded, single-paragraph summary of a docstring.

        Preserves the author's intent (the first paragraph — the part that
        states *what* the symbol is for) while keeping the graph small. Never
        stores the full body. Returns "" when there is no docstring.
        """
        if not docstring:
            return ""
        text = docstring.strip()
        if not text:
            return ""
        # First paragraph = up to the first blank line (the summary line/para).
        para = text.split("\n\n", 1)[0].strip()
        # Collapse internal whitespace/newlines so it reads as one clean line.
        para = " ".join(para.split())
        if len(para) > limit:
            # Cut on a word boundary within the limit and mark truncation.
            para = para[:limit].rsplit(" ", 1)[0].rstrip() + "…"
        return para

    def _make_id(self, prefix: str, value: str) -> str:
        """Create a deterministic, collision-free node ID.

        Uses a short SHA-256 hash of the value so that paths that
        differ only in separators (e.g. 'a/b.c' vs 'a/b/c') never
        produce the same ID. The job prefix keeps IDs scoped per job.
        """
        digest = hashlib.sha256(value.encode()).hexdigest()[:12]
        return f"{self._job_id[:8]}_{prefix}_{digest}"