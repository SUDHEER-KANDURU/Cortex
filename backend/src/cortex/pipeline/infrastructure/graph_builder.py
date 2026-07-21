"""Graph builder — converts parsed code structure into knowledge graph.
Takes ParsedFile objects from the AST parser and creates
GraphNode and GraphEdge domain entities ready for Neo4j storage."""

import uuid
from dataclasses import dataclass, field
import structlog

from cortex.graph.domain.entities import (
    GraphNode,
    GraphEdge,
    NodeType,
    RelationshipType,
)
from cortex.pipeline.infrastructure.ast_parser import (
    ParsedFile,
    ParsedClass,
    ParsedFunction,
    Language,
)

logger = structlog.get_logger()


@dataclass
class GraphBuildResult:
    """Result of building a knowledge graph from parsed files."""
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    job_id: str = ""
    repo_url: str = ""
    stats: dict = field(default_factory=dict)

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
            "functions": len(self.nodes_by_type(NodeType.FUNCTION)),
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
                      └── CONTAINS → Class
                            └── CONTAINS → Function (method)
                      └── CONTAINS → Function (top-level)
        File → IMPORTS → Module (external dependency)
        Class → INHERITS → Class (base class)
        Function → CALLS → Function (detected call)
    """

    def __init__(self, job_id: str, repo_url: str) -> None:
        self._job_id = job_id
        self._repo_url = repo_url
        self._node_index: dict[str, GraphNode] = {}

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

        module_name_index: dict[str, list[GraphNode]] = {}
        for parsed_file in parsed_files:
            file_node = file_nodes.get(parsed_file.path)
            if not file_node:
                continue
            for module_name in self._candidate_module_names(parsed_file.path):
                module_name_index.setdefault(module_name, []).append(file_node)

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

            # Step 7 — Create import edges
            for imp in parsed_file.imports:
                if not imp.module:
                    continue
                target_nodes = self._resolve_import_targets(
                    imp.module,
                    module_name_index,
                    file_node,
                )
                for target_node in target_nodes:
                    if target_node.id == file_node.id:
                        continue
                    result.edges.append(self._create_edge(
                        source=file_node,
                        target=target_node,
                        relationship=RelationshipType.IMPORTS,
                    ))
                    result.edges.append(self._create_edge(
                        source=file_node,
                        target=target_node,
                        relationship=RelationshipType.DEPENDS_ON,
                    ))

        # Step 8 — Add inheritance edges between classes
        class_name_index: dict[str, GraphNode] = {
            n.label: n
            for n in result.nodes
            if n.node_type == NodeType.CLASS
        }

        for parsed_file in parsed_files:
            for parsed_class in parsed_file.classes:
                class_node = class_name_index.get(parsed_class.name)
                if not class_node:
                    continue
                for base in parsed_class.base_classes:
                    base_node = class_name_index.get(base)
                    if base_node:
                        result.edges.append(self._create_edge(
                            source=class_node,
                            target=base_node,
                            relationship=RelationshipType.INHERITS,
                        ))

        result.stats = result.summary()
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
            },
        )

    def _create_class_node(
        self,
        parsed_class: ParsedClass,
        file_path: str,
    ) -> GraphNode:
        """Create a class node."""
        return GraphNode(
            id=self._make_id("class", f"{file_path}.{parsed_class.name}"),
            label=parsed_class.name,
            node_type=NodeType.CLASS,
            job_id=self._job_id,
            properties={
                "file": file_path,
                "line": parsed_class.line_start,
                "methods": parsed_class.method_count(),
                "base_classes": ", ".join(parsed_class.base_classes),
                "is_abstract": parsed_class.is_abstract(),
            },
        )

    def _create_function_node(
        self,
        fn: ParsedFunction,
        file_path: str,
    ) -> GraphNode:
        """Create a function or method node."""
        return GraphNode(
            id=self._make_id(
                "fn", f"{file_path}.{fn.qualified_name()}"
            ),
            label=fn.name,
            node_type=NodeType.FUNCTION,
            job_id=self._job_id,
            properties={
                "file": file_path,
                "line": fn.line_start,
                "is_async": fn.is_async,
                "is_method": fn.is_method,
                "parameters": ", ".join(fn.parameters),
                "lines": fn.line_count(),
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
        """Detect the full directory hierarchy for each parsed file."""
        modules: set[str] = set()
        for parsed_file in parsed_files:
            normalized_path = self._normalize_path(parsed_file.path)
            parts = [part for part in normalized_path.split("/") if part]
            if not parts:
                continue

            parent_dirs = parts[:-1]
            for depth in range(1, len(parent_dirs) + 1):
                modules.add("/".join(parent_dirs[:depth]))

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

    def _candidate_module_names(self, file_path: str) -> list[str]:
        """Return import-style module names that could match a file path."""
        normalized = self._normalize_path(file_path)
        parts = [part for part in normalized.split("/") if part]
        if not parts:
            return []

        names: list[str] = []
        for index in range(len(parts)):
            if parts[index].endswith(".py"):
                stem = parts[index][:-3]
                module_parts = parts[index + 1:] if index < len(parts) - 1 else []
                candidates = [
                    ".".join(parts[index + 1:]),
                    ".".join(parts[index + 1:-1]) if len(parts[index + 1:]) > 1 else None,
                    stem,
                ]
                names.extend(
                    candidate
                    for candidate in candidates
                    if candidate
                )
                break

        if not names:
            return []

        # Also include suffix-based names for nested packages.
        suffix_names = []
        for index in range(1, len(parts)):
            suffix_names.append(".".join(parts[index:]))
        return list(dict.fromkeys(names + suffix_names))

    def _resolve_import_targets(
        self,
        import_module: str,
        module_name_index: dict[str, list[GraphNode]],
        source_node: GraphNode,
    ) -> list[GraphNode]:
        """Resolve a Python import to file nodes using module-name matching."""
        candidates: list[GraphNode] = []
        seen: set[str] = set()
        normalized_import = import_module.strip(".")

        for module_name in {normalized_import, normalized_import.split(".")[-1]}:
            if not module_name:
                continue
            for target_node in module_name_index.get(module_name, []):
                if target_node.id not in seen:
                    seen.add(target_node.id)
                    candidates.append(target_node)

        if not candidates:
            for module_name, targets in module_name_index.items():
                if module_name.endswith(normalized_import) or normalized_import.endswith(module_name):
                    for target_node in targets:
                        if target_node.id != source_node.id and target_node.id not in seen:
                            seen.add(target_node.id)
                            candidates.append(target_node)

        return candidates

    def _emit_debug_summary(
        self,
        parsed_files: list[ParsedFile],
        result: GraphBuildResult,
        modules: list[str],
    ) -> None:
        """Temporary debug logging for graph construction."""
        print("[graph_debug] total_repository_files", len(parsed_files))
        print("[graph_debug] total_asts_parsed", len(parsed_files))
        print("[graph_debug] total_graph_nodes", len(result.nodes))
        print("[graph_debug] total_graph_edges", len(result.edges))
        print("[graph_debug] detected_modules", modules[:50])
        print(
            "[graph_debug] first_20_nodes",
            [
                {
                    "type": node.node_type.value,
                    "label": node.label,
                    "path": node.properties.get("path"),
                }
                for node in result.nodes[:20]
            ],
        )
        print(
            "[graph_debug] first_20_edges",
            [
                {
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relationship": edge.relationship.value,
                }
                for edge in result.edges[:20]
            ],
        )

    def _make_id(self, prefix: str, value: str) -> str:
        """Create a deterministic node ID from a prefix and value.
        Same input always produces same ID — no duplicates."""
        clean = value.replace("/", "_").replace(".", "_").lower()
        return f"{self._job_id[:8]}_{prefix}_{clean}"