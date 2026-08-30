"""Tree-sitter based parser for non-Python languages (Req 1.1, 1.2, 1.6).

A single :class:`TreeSitterParser` handles JavaScript, TypeScript, Java, Go,
Rust, C#, and Ruby by driving a per-language :class:`LanguageSpec` field-mapping
table (grammar node type -> ``ParsedFile`` field). Adding a language means adding
a grammar + a ``LanguageSpec`` entry -- nothing downstream changes (Req 1.5).

Every parser returns the shared ``ParsedFile`` dataclass, so the graph builder is
unchanged. Line/column spans come straight from tree-sitter's byte-accurate node
points (Req 1.6). Parsing is deterministic and offline; no ML.

If the ``tree-sitter-language-pack`` dependency is unavailable at runtime the
module degrades gracefully: ``tree_sitter_available()`` returns False and the
registry simply does not register this parser, leaving the languages unhandled
rather than crashing the pipeline.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from cortex.pipeline.domain.entities import LanguageCapabilityProfile
from cortex.pipeline.infrastructure.ast_parser import (
    Language,
    LanguageParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    _file_extension,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from tree_sitter import Node

logger = structlog.get_logger()


# ── Optional dependency handling ──────────────────────────────────────────────
try:  # pragma: no cover - import guard
    from tree_sitter_language_pack import get_parser as _get_ts_parser

    _TREE_SITTER_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - exercised only without the dep
    _get_ts_parser = None  # type: ignore[assignment]
    _TREE_SITTER_IMPORT_ERROR = exc


def tree_sitter_available() -> bool:
    """Return True if the tree-sitter grammars can be loaded in this env."""
    return _get_ts_parser is not None

# ── Per-language field-mapping table ──────────────────────────────────────────
@dataclass(frozen=True)
class LanguageSpec:
    """Maps a grammar's node types to ``ParsedFile`` fields for one language."""

    language: Language
    class_nodes: frozenset[str]
    interface_nodes: frozenset[str]
    enum_nodes: frozenset[str]
    function_nodes: frozenset[str]
    method_nodes: frozenset[str]
    import_nodes: frozenset[str]
    call_nodes: frozenset[str]
    # Node types opening a nested scope that holds methods (class/interface body).
    body_nodes: frozenset[str]
    # Branch node types for cyclomatic complexity (McCabe: 1 + decision points).
    branch_nodes: frozenset[str]
    # Field name on a call node that holds the callee identifier.
    call_target_field: str = "function"
    # Async is expressed by an "async" child token on the function node.
    async_token: str = "async"
    # Namespace containers (Ruby module, C# namespace) that hold nested defs and
    # should be recursed into rather than treated as leaf classes.
    namespace_nodes: frozenset[str] = frozenset()
    # Builds this language's capability profile (Req 2.1).
    profile_factory: Callable[[], LanguageCapabilityProfile] | None = None


# ── Capability profiles per language ──────────────────────────────────────────
def _js_profile() -> LanguageCapabilityProfile:
    return LanguageCapabilityProfile(
        language=Language.JAVASCRIPT.value,
        has_interfaces=False,
        has_decorators=True,
        has_generics=False,
        has_packages=False,
        has_traits=False,
        has_classes=True,
        has_enums=False,
        has_async=True,
        answer_sections=(
            "overview", "modules", "components", "classes",
            "functions", "endpoints", "dependencies",
        ),
    )


def _ts_profile() -> LanguageCapabilityProfile:
    return LanguageCapabilityProfile(
        language=Language.TYPESCRIPT.value,
        has_interfaces=True,
        has_decorators=True,
        has_generics=True,
        has_packages=False,
        has_traits=False,
        has_classes=True,
        has_enums=True,
        has_async=True,
        answer_sections=(
            "overview", "modules", "components", "classes",
            "interfaces", "functions", "endpoints", "dependencies",
        ),
    )


def _java_profile() -> LanguageCapabilityProfile:
    return LanguageCapabilityProfile(
        language=Language.JAVA.value,
        has_interfaces=True,
        has_decorators=True,
        has_generics=True,
        has_packages=True,
        has_traits=False,
        has_classes=True,
        has_enums=True,
        has_async=False,
        answer_sections=(
            "overview", "modules", "packages", "classes",
            "interfaces", "annotations", "endpoints", "dependencies",
        ),
    )


def _go_profile() -> LanguageCapabilityProfile:
    return LanguageCapabilityProfile(
        language=Language.GO.value,
        has_interfaces=True,
        has_decorators=False,
        has_generics=True,
        has_packages=True,
        has_traits=False,
        has_classes=True,   # structs stand in for classes
        has_enums=False,
        has_async=False,    # goroutines, not async/await
        answer_sections=(
            "overview", "modules", "packages", "classes",
            "interfaces", "functions", "endpoints", "dependencies",
        ),
    )


def _rust_profile() -> LanguageCapabilityProfile:
    return LanguageCapabilityProfile(
        language=Language.RUST.value,
        has_interfaces=True,   # traits act as interfaces
        has_decorators=False,
        has_generics=True,
        has_packages=True,     # crates / modules
        has_traits=True,
        has_classes=True,      # structs / impl blocks
        has_enums=True,
        has_async=True,
        answer_sections=(
            "overview", "modules", "packages", "classes",
            "traits", "functions", "dependencies",
        ),
    )


def _csharp_profile() -> LanguageCapabilityProfile:
    return LanguageCapabilityProfile(
        language=Language.CSHARP.value,
        has_interfaces=True,
        has_decorators=True,   # attributes
        has_generics=True,
        has_packages=True,     # namespaces
        has_traits=False,
        has_classes=True,
        has_enums=True,
        has_async=True,
        answer_sections=(
            "overview", "modules", "packages", "classes",
            "interfaces", "annotations", "endpoints", "dependencies",
        ),
    )


def _ruby_profile() -> LanguageCapabilityProfile:
    return LanguageCapabilityProfile(
        language=Language.RUBY.value,
        has_interfaces=False,
        has_decorators=False,
        has_generics=False,
        has_packages=True,     # modules act as namespaces
        has_traits=True,       # mixins / modules
        has_classes=True,
        has_enums=False,
        has_async=False,
        answer_sections=(
            "overview", "modules", "classes",
            "functions", "endpoints", "dependencies",
        ),
    )


# ── The field-mapping table: one LanguageSpec per grammar ─────────────────────
_JS_SPEC = LanguageSpec(
    language=Language.JAVASCRIPT,
    class_nodes=frozenset({"class_declaration"}),
    interface_nodes=frozenset(),
    enum_nodes=frozenset(),
    function_nodes=frozenset({"function_declaration"}),
    method_nodes=frozenset({"method_definition"}),
    import_nodes=frozenset({"import_statement"}),
    call_nodes=frozenset({"call_expression"}),
    body_nodes=frozenset({"class_body"}),
    branch_nodes=frozenset({
        "if_statement", "for_statement", "for_in_statement", "while_statement",
        "do_statement", "switch_case", "catch_clause", "ternary_expression",
    }),
    call_target_field="function",
    profile_factory=_js_profile,
)

_TS_SPEC = LanguageSpec(
    language=Language.TYPESCRIPT,
    class_nodes=frozenset({"class_declaration", "abstract_class_declaration"}),
    interface_nodes=frozenset({"interface_declaration"}),
    enum_nodes=frozenset({"enum_declaration"}),
    function_nodes=frozenset({"function_declaration"}),
    method_nodes=frozenset({"method_definition", "method_signature"}),
    import_nodes=frozenset({"import_statement"}),
    call_nodes=frozenset({"call_expression"}),
    body_nodes=frozenset({"class_body", "interface_body"}),
    branch_nodes=frozenset({
        "if_statement", "for_statement", "for_in_statement", "while_statement",
        "do_statement", "switch_case", "catch_clause", "ternary_expression",
    }),
    call_target_field="function",
    profile_factory=_ts_profile,
)

_JAVA_SPEC = LanguageSpec(
    language=Language.JAVA,
    class_nodes=frozenset({"class_declaration", "record_declaration"}),
    interface_nodes=frozenset({"interface_declaration"}),
    enum_nodes=frozenset({"enum_declaration"}),
    function_nodes=frozenset(),
    method_nodes=frozenset({"method_declaration", "constructor_declaration"}),
    import_nodes=frozenset({"import_declaration"}),
    call_nodes=frozenset({"method_invocation"}),
    body_nodes=frozenset({"class_body", "interface_body", "enum_body"}),
    branch_nodes=frozenset({
        "if_statement", "for_statement", "enhanced_for_statement",
        "while_statement", "do_statement", "switch_label", "catch_clause",
        "ternary_expression",
    }),
    call_target_field="name",
    profile_factory=_java_profile,
)

_GO_SPEC = LanguageSpec(
    language=Language.GO,
    class_nodes=frozenset({"type_declaration"}),
    interface_nodes=frozenset(),   # detected via interface_type child of type_spec
    enum_nodes=frozenset(),
    function_nodes=frozenset({"function_declaration"}),
    method_nodes=frozenset({"method_declaration"}),
    import_nodes=frozenset({"import_declaration"}),
    call_nodes=frozenset({"call_expression"}),
    body_nodes=frozenset(),
    branch_nodes=frozenset({
        "if_statement", "for_statement", "expression_switch_statement",
        "type_switch_statement", "select_statement", "communication_case",
    }),
    call_target_field="function",
    profile_factory=_go_profile,
)

_RUST_SPEC = LanguageSpec(
    language=Language.RUST,
    class_nodes=frozenset({"struct_item", "impl_item"}),
    interface_nodes=frozenset({"trait_item"}),
    enum_nodes=frozenset({"enum_item"}),
    function_nodes=frozenset({"function_item"}),
    method_nodes=frozenset({"function_item", "function_signature_item"}),
    import_nodes=frozenset({"use_declaration"}),
    call_nodes=frozenset({"call_expression", "macro_invocation"}),
    body_nodes=frozenset({"declaration_list"}),
    branch_nodes=frozenset({
        "if_expression", "for_expression", "while_expression",
        "loop_expression", "match_arm",
    }),
    call_target_field="function",
    profile_factory=_rust_profile,
)

_CSHARP_SPEC = LanguageSpec(
    language=Language.CSHARP,
    class_nodes=frozenset({"class_declaration", "struct_declaration", "record_declaration"}),
    interface_nodes=frozenset({"interface_declaration"}),
    enum_nodes=frozenset({"enum_declaration"}),
    function_nodes=frozenset(),
    method_nodes=frozenset({"method_declaration", "constructor_declaration"}),
    import_nodes=frozenset({"using_directive"}),
    call_nodes=frozenset({"invocation_expression"}),
    body_nodes=frozenset({"declaration_list"}),
    branch_nodes=frozenset({
        "if_statement", "for_statement", "for_each_statement", "while_statement",
        "do_statement", "switch_section", "catch_clause", "conditional_expression",
    }),
    call_target_field="function",
    profile_factory=_csharp_profile,
)

_RUBY_SPEC = LanguageSpec(
    language=Language.RUBY,
    class_nodes=frozenset({"class"}),
    interface_nodes=frozenset(),
    enum_nodes=frozenset(),
    function_nodes=frozenset({"method"}),
    method_nodes=frozenset({"method", "singleton_method"}),
    import_nodes=frozenset(),   # require is a plain call; handled specially
    call_nodes=frozenset({"call", "method_call"}),
    body_nodes=frozenset({"body_statement"}),
    branch_nodes=frozenset({
        "if", "elsif", "unless", "for", "while", "until", "when", "rescue",
    }),
    call_target_field="method",
    namespace_nodes=frozenset({"module"}),
    profile_factory=_ruby_profile,
)

#: tree-sitter grammar name per language (the key ``get_parser`` expects).
_GRAMMAR_NAME: dict[Language, str] = {
    Language.JAVASCRIPT: "javascript",
    Language.TYPESCRIPT: "typescript",
    Language.JAVA: "java",
    Language.GO: "go",
    Language.RUST: "rust",
    Language.CSHARP: "csharp",
    Language.RUBY: "ruby",
}

#: File extension (no dot, lowercased) -> LanguageSpec.
_EXTENSION_SPEC: dict[str, LanguageSpec] = {
    "js": _JS_SPEC, "jsx": _JS_SPEC, "mjs": _JS_SPEC, "cjs": _JS_SPEC,
    "ts": _TS_SPEC, "tsx": _TS_SPEC,
    "java": _JAVA_SPEC,
    "go": _GO_SPEC,
    "rs": _RUST_SPEC,
    "cs": _CSHARP_SPEC,
    "rb": _RUBY_SPEC,
}


def _grammar_for_extension(ext: str, spec: LanguageSpec) -> str:
    """Return the tree-sitter grammar name for a file extension.

    TypeScript ships two grammars: ``typescript`` (no JSX) and ``tsx`` (JSX).
    ``.tsx`` files must use the ``tsx`` grammar or JSX tags fail to parse.
    """
    if ext == "tsx":
        return "tsx"
    return _GRAMMAR_NAME[spec.language]


class TreeSitterParser(LanguageParser):
    """A tree-sitter-backed parser for one language, chosen by ``spec`` (Req 1.2).

    Instances are created per language from a :class:`LanguageSpec`. Selection by
    file path still flows through the :class:`ParserRegistry`; each instance
    advertises the extensions its grammar owns.
    """

    #: Human-facing test path markers reused across languages.
    _TEST_PATH_MARKERS = ("/test/", "/tests/", "/spec/", "/__tests__/")

    def __init__(self, spec: LanguageSpec, extensions: tuple[str, ...]) -> None:
        if not tree_sitter_available():  # pragma: no cover - guarded by registry
            raise RuntimeError(
                "tree-sitter grammars are unavailable: "
                f"{_TREE_SITTER_IMPORT_ERROR!r}"
            )
        self._spec = spec
        self.extensions = extensions
        self.shebangs = ()

    @property
    def language(self) -> Language:
        return self._spec.language

    def profile(self) -> LanguageCapabilityProfile:
        factory = self._spec.profile_factory
        if factory is None:  # every built-in spec sets one; defensive fallback
            return LanguageCapabilityProfile(language=self._spec.language.value)
        return factory()


    # ── Text / span helpers ──────────────────────────────────────────────────
    @staticmethod
    def _text(node: Node, source: bytes) -> str:
        return source[node.start_byte:node.end_byte].decode("utf-8", "replace")

    @staticmethod
    def _line_start(node: Node) -> int:
        # tree-sitter rows are 0-indexed; ParsedFile uses 1-indexed lines (Req 1.6).
        return node.start_point.row + 1

    @staticmethod
    def _line_end(node: Node) -> int:
        return node.end_point.row + 1

    def _field_text(self, node: Node, field_name: str, source: bytes) -> str | None:
        child = node.child_by_field_name(field_name)
        return self._text(child, source) if child is not None else None

    # ── Entry point ──────────────────────────────────────────────────────────
    def parse(self, content: str, file_path: str) -> ParsedFile:
        result = ParsedFile(
            path=file_path,
            language=self._spec.language,
            line_count=len(content.splitlines()),
        )
        self._mark_test_and_config(result, file_path)

        if not tree_sitter_available():  # pragma: no cover - guarded by registry
            result.parse_errors.append("tree-sitter unavailable")
            return result

        ext = _file_extension(file_path)
        try:
            parser = _get_ts_parser(_grammar_for_extension(ext, self._spec))
            source = content.encode("utf-8")
            tree = parser.parse(source)
        except Exception as exc:  # never raise (LanguageParser contract)
            result.parse_errors.append(f"tree-sitter parse error: {exc}")
            logger.warning("tree_sitter_parse_error", path=file_path, error=str(exc))
            return result

        root = tree.root_node
        if root.has_error:
            # A recoverable syntax error: tree-sitter still yields a partial tree,
            # so record the gap but keep extracting what parsed (Req 1.4).
            result.parse_errors.append("syntax errors present; extracted partial structure")

        try:
            self._extract(root, source, file_path, result)
        except Exception as exc:  # defensive: extraction must never crash pipeline
            result.parse_errors.append(f"extraction error: {exc}")
            logger.warning("tree_sitter_extract_error", path=file_path, error=str(exc))

        logger.info("tree_sitter_file_parsed", file=file_path, **result.summary())
        return result

    def _mark_test_and_config(self, result: ParsedFile, file_path: str) -> None:
        normalized = file_path.replace("\\", "/")
        basename = os.path.basename(normalized).lower()
        result.is_test_file = (
            any(m in normalized.lower() for m in self._TEST_PATH_MARKERS)
            or basename.startswith("test_")
            or ".test." in basename
            or ".spec." in basename
            or basename.endswith("_test.go")
            or basename.endswith("_spec.rb")
        )
        result.is_config_file = "config" in basename or "settings" in basename


    # ── Traversal ────────────────────────────────────────────────────────────
    def _extract(self, root: Node, source: bytes, file_path: str, result: ParsedFile) -> None:
        """Walk the tree top-down, dispatching on the spec's node-type sets.

        Container nodes (class/interface/enum/struct/impl) are handled as a unit
        (their methods are pulled from the body), so once a container is entered
        we do not also emit its methods as free functions.
        """
        spec = self._spec

        def visit(node: Node, enclosing_class: str | None) -> None:
            ntype = node.type

            if ntype in spec.namespace_nodes:
                # A namespace (Ruby module / C# namespace) holds nested defs;
                # recurse so nested classes and functions are still captured.
                for child in node.children:
                    visit(child, enclosing_class)
                return

            if ntype in spec.import_nodes:
                imp = self._parse_import(node, source)
                if imp is not None:
                    result.imports.append(imp)
                return

            if ntype in spec.interface_nodes:
                result.classes.append(
                    self._parse_container(node, source, file_path, is_interface=True)
                )
                return

            if ntype in spec.enum_nodes:
                result.classes.append(
                    self._parse_container(node, source, file_path, is_enum=True)
                )
                return

            if ntype in spec.class_nodes:
                container = self._parse_container(node, source, file_path)
                # Go/Rust: a type_declaration may actually wrap an interface.
                if container is None:
                    for child in node.children:
                        visit(child, enclosing_class)
                    return
                result.classes.append(container)
                return

            if ntype in spec.function_nodes and enclosing_class is None:
                result.functions.append(
                    self._parse_function(node, source, file_path)
                )
                return

            for child in node.children:
                visit(child, enclosing_class)

        visit(root, None)


    # ── Container (class / interface / enum / struct / impl) ─────────────────
    def _parse_container(
        self,
        node: Node,
        source: bytes,
        file_path: str,
        is_interface: bool = False,
        is_enum: bool = False,
    ) -> ParsedClass | None:
        spec = self._spec

        # Go wraps the real shape in type_declaration -> type_spec -> {struct,interface}.
        if node.type == "type_declaration":
            spec_node = node.child_by_field_name("type") or self._find_child(
                node, {"type_spec"}
            )
            if spec_node is not None and spec_node.type == "type_spec":
                name = self._field_text(spec_node, "name", source) or "<anonymous>"
                inner = spec_node.child_by_field_name("type")
                if inner is not None and inner.type == "interface_type":
                    return ParsedClass(
                        name=name, file_path=file_path,
                        line_start=self._line_start(node),
                        line_end=self._line_end(node),
                        is_interface=True,
                    )
                # struct_type or other → treat as a class-like container.
                return ParsedClass(
                    name=name, file_path=file_path,
                    line_start=self._line_start(node),
                    line_end=self._line_end(node),
                )
            return None

        name = self._container_name(node, source)
        base_classes = self._container_bases(node, source)
        decorators = self._decorators_before(node, source)

        parsed = ParsedClass(
            name=name,
            file_path=file_path,
            line_start=self._line_start(node),
            line_end=self._line_end(node),
            base_classes=base_classes,
            decorators=decorators,
            is_interface=is_interface,
            is_enum=is_enum,
        )

        body = self._container_body(node)
        if body is not None:
            for child in self._iter_all(body):
                if child.type in spec.method_nodes:
                    method = self._parse_function(
                        child, source, file_path,
                        is_method=True, parent_class=name,
                    )
                    parsed.methods.append(method)
        return parsed

    def _container_name(self, node: Node, source: bytes) -> str:
        name = self._field_text(node, "name", source)
        if name:
            return name
        # Rust impl blocks: name the implemented type.
        if node.type == "impl_item":
            t = node.child_by_field_name("type")
            return self._text(t, source) if t is not None else "<impl>"
        return "<anonymous>"


    def _container_bases(self, node: Node, source: bytes) -> list[str]:
        """Extract base classes / implemented interfaces / superclass."""
        bases: list[str] = []
        # Java: super_interfaces + superclass; TS/JS: class_heritage; C#: base_list;
        # Ruby: superclass; Rust impl: trait field.
        for child in node.children:
            ct = child.type
            if ct in {"super_interfaces", "superclass", "extends_clause",
                      "class_heritage", "base_list", "type_list"}:
                for ident in self._iter_all(child):
                    if ident.type in {"type_identifier", "identifier", "constant",
                                       "scoped_type_identifier", "generic_type"}:
                        bases.append(self._text(ident, source).split("<")[0].strip())
        if node.type == "impl_item":
            trait = node.child_by_field_name("trait")
            if trait is not None:
                bases.append(self._text(trait, source))
        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique = []
        for b in bases:
            if b and b not in seen:
                seen.add(b)
                unique.append(b)
        return unique

    def _container_body(self, node: Node) -> Node | None:
        body = node.child_by_field_name("body")
        if body is not None:
            return body
        for child in node.children:
            if child.type in self._spec.body_nodes:
                return child
        return None

    def _decorators_before(self, node: Node, source: bytes) -> list[str]:
        """Collect decorator/annotation names attached to or preceding a node."""
        names: list[str] = []
        # TS: decorator siblings precede the node. Java/C#: annotations are inside
        # a modifiers/attribute_list child.
        prev = node.prev_named_sibling
        while prev is not None and prev.type in {"decorator", "attribute_list"}:
            names.extend(self._annotation_names(prev, source))
            prev = prev.prev_named_sibling
        for child in node.children:
            if child.type in {"modifiers", "attribute_list", "decorator"}:
                names.extend(self._annotation_names(child, source))
        return list(dict.fromkeys(names))

    def _annotation_names(self, node: Node, source: bytes) -> list[str]:
        names: list[str] = []
        for n in self._iter_all(node):
            if n.type in {"marker_annotation", "annotation", "attribute", "decorator"}:
                ident = self._find_child(n, {"identifier", "type_identifier",
                                              "scoped_identifier"})
                if ident is not None:
                    names.append(self._text(ident, source).lstrip("@"))
        return names

    @staticmethod
    def _iter_all(node: Node) -> Iterator[Node]:
        """Yield node then all descendants (pre-order)."""
        stack = [node]
        while stack:
            cur = stack.pop()
            yield cur
            stack.extend(reversed(cur.children))

    @staticmethod
    def _find_child(node: Node, types: set[str]) -> Node | None:
        for n in TreeSitterParser._iter_all(node):
            if n is not node and n.type in types:
                return n
        return None


    # ── Function / method ────────────────────────────────────────────────────
    def _parse_function(
        self,
        node: Node,
        source: bytes,
        file_path: str,
        is_method: bool = False,
        parent_class: str | None = None,
    ) -> ParsedFunction:
        name = self._function_name(node, source)
        params = self._parameters(node, source)
        return_type = self._return_type(node, source)
        is_async = self._is_async(node, source)
        decorators = self._decorators_before(node, source)

        branch_count, calls = self._complexity_and_calls(node, source)
        cyclomatic = 1 + branch_count
        nesting = self._nesting_depth(node)

        is_test = name.lower().startswith("test") or "test" in name.lower()[:5]

        return ParsedFunction(
            name=name,
            file_path=file_path,
            line_start=self._line_start(node),
            line_end=self._line_end(node),
            is_method=is_method,
            parent_class=parent_class,
            parameters=params,
            return_type=return_type,
            decorators=decorators,
            is_async=is_async,
            cyclomatic_complexity=cyclomatic,
            branch_count=branch_count,
            nesting_depth=nesting,
            call_count=len(calls),
            calls=list(dict.fromkeys(calls))[:20],
            is_test=is_test,
        )

    def _function_name(self, node: Node, source: bytes) -> str:
        name = self._field_text(node, "name", source)
        if name:
            return name
        # Go methods use field_identifier; some grammars differ.
        for fld in ("name",):
            child = node.child_by_field_name(fld)
            if child is not None:
                return self._text(child, source)
        return "<anonymous>"

    def _parameters(self, node: Node, source: bytes) -> list[str]:
        params_node = node.child_by_field_name("parameters")
        if params_node is None:
            return []
        names: list[str] = []
        for child in params_node.named_children:
            if child.type in {"comment"}:
                continue
            pname = child.child_by_field_name("name") or child.child_by_field_name("pattern")
            if pname is not None:
                text = self._text(pname, source)
            elif child.type in {"identifier", "shorthand_property_identifier_pattern"}:
                text = self._text(child, source)
            else:
                # Fall back to the first identifier descendant.
                ident = self._find_child(child, {"identifier", "field_identifier"})
                text = self._text(ident, source) if ident is not None else ""
            text = text.strip()
            if text and text not in ("self", "cls", "this"):
                names.append(text)
        return names

    def _return_type(self, node: Node, source: bytes) -> str | None:
        for fld in ("return_type", "result", "type", "returns"):
            child = node.child_by_field_name(fld)
            if child is not None:
                return self._text(child, source).lstrip(":").strip() or None
        # TS/JS: type_annotation sibling of parameters.
        for child in node.children:
            if child.type == "type_annotation":
                return self._text(child, source).lstrip(":").strip() or None
        return None

    def _is_async(self, node: Node, source: bytes) -> bool:
        for child in node.children:
            if child.type == self._spec.async_token:
                return True
            if not child.is_named and self._text(child, source) == "async":
                return True
        return False


    # ── Complexity + call targets ────────────────────────────────────────────
    def _complexity_and_calls(self, node: Node, source: bytes) -> tuple[int, list[str]]:
        """Count decision points (McCabe) and collect call targets in one walk."""
        spec = self._spec
        branch_count = 0
        calls: list[str] = []
        for n in self._iter_all(node):
            if n is node:
                continue
            # Do not descend into nested function bodies' own decisions? We still
            # count them; nested functions are rare and counting is conservative.
            if n.type in spec.branch_nodes:
                branch_count += 1
            elif n.type in {"binary_expression", "boolean_operator"}:
                op = n.child_by_field_name("operator")
                if op is not None and self._text(op, source) in {"&&", "||", "and", "or"}:
                    branch_count += 1
            if n.type in spec.call_nodes:
                target = self._call_target(n, source)
                if target:
                    calls.append(target)
        return branch_count, calls

    def _call_target(self, node: Node, source: bytes) -> str | None:
        field_name = self._spec.call_target_field
        callee = node.child_by_field_name(field_name)
        if callee is None and node.type == "macro_invocation":
            callee = node.child_by_field_name("macro")
        if callee is None:
            # C# invocation_expression stores callee as first named child.
            callee = node.named_children[0] if node.named_children else None
        if callee is None:
            return None
        text = self._text(callee, source)
        # Reduce member access to the final segment (obj.method -> method).
        for sep in (".", "::", "->"):
            if sep in text:
                text = text.split(sep)[-1]
        text = text.strip()
        return text or None

    def _nesting_depth(self, node: Node) -> int:
        """Maximum block-nesting depth inside the function body."""
        body = node.child_by_field_name("body")
        if body is None:
            return 0
        block_types = self._spec.branch_nodes | {"block", "statement_block"}
        max_depth = 0

        def walk(n: Node, depth: int) -> None:
            nonlocal max_depth
            d = depth + 1 if n.type in block_types else depth
            if d > max_depth:
                max_depth = d
            for child in n.children:
                walk(child, d)

        for child in body.children:
            walk(child, 0)
        return max_depth


    # ── Imports ──────────────────────────────────────────────────────────────
    def _parse_import(self, node: Node, source: bytes) -> ParsedImport | None:
        line = self._line_start(node)
        lang = self._spec.language

        if lang in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            src_node = node.child_by_field_name("source")
            if src_node is None:
                return None
            module = self._string_value(src_node, source)
            names = [
                self._text(spec, source)
                for spec in self._iter_all(node)
                if spec.type == "import_specifier"
                for spec in [spec.child_by_field_name("name") or spec]
            ]
            return ParsedImport(
                module=module, names=[n for n in names if n],
                is_relative=module.startswith("."), line=line,
            )

        if lang == Language.JAVA:
            ident = self._find_child(node, {"scoped_identifier", "identifier"})
            full = self._text(ident, source) if ident is not None else ""
            parts = full.rsplit(".", 1)
            module = parts[0] if len(parts) == 2 else full
            names = [parts[1]] if len(parts) == 2 else []
            return ParsedImport(module=module, names=names, line=line)

        if lang == Language.GO:
            for spec in self._iter_all(node):
                if spec.type == "interpreted_string_literal":
                    module = self._string_value(spec, source)
                    return ParsedImport(module=module, line=line)
            return None

        if lang == Language.RUST:
            path = self._find_child(node, {"scoped_identifier", "identifier",
                                           "use_wildcard", "scoped_use_list",
                                           "use_list"})
            module = self._text(path, source) if path is not None else ""
            module = module.split("::")[0] if "::" in module else module
            return ParsedImport(module=module.strip(), line=line)

        if lang == Language.CSHARP:
            ident = self._find_child(node, {"qualified_name", "identifier"})
            module = self._text(ident, source) if ident is not None else ""
            return ParsedImport(module=module.strip(), line=line)

        return None

    def _string_value(self, node: Node, source: bytes) -> str:
        """Return the inner text of a string literal node (quotes stripped)."""
        for child in self._iter_all(node):
            if child.type in {"string_fragment", "interpreted_string_literal_content",
                              "string_content"}:
                return self._text(child, source)
        return self._text(node, source).strip("\"'`")


# ── Factory helpers ───────────────────────────────────────────────────────────
def _build_parsers() -> list[TreeSitterParser]:
    """Instantiate one TreeSitterParser per grammar with its extensions."""
    grouped: dict[Language, list[str]] = {}
    for ext, spec in _EXTENSION_SPEC.items():
        grouped.setdefault(spec.language, []).append(ext)
    specs = {spec.language: spec for spec in _EXTENSION_SPEC.values()}
    parsers: list[TreeSitterParser] = []
    for lang, exts in grouped.items():
        parsers.append(TreeSitterParser(specs[lang], tuple(sorted(exts))))
    return parsers


def tree_sitter_parsers() -> list[TreeSitterParser]:
    """Return TreeSitterParser instances for all supported languages.

    Returns an empty list when the tree-sitter dependency is unavailable, so
    the registry can degrade gracefully instead of failing to import.
    """
    if not tree_sitter_available():
        logger.warning(
            "tree_sitter_unavailable",
            error=repr(_TREE_SITTER_IMPORT_ERROR),
        )
        return []
    return _build_parsers()
