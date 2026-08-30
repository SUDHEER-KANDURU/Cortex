"""AST parser — extracts code structure from source files.
Supports Python, Java, TypeScript, and JavaScript. Returns structured
data that the graph builder uses to create knowledge graph nodes and edges.

Extraction capabilities:
  - Functions/methods with parameters, return types, decorators, docstrings
  - Classes with base classes, attributes, interface/enum detection
  - Imports (module-level dependencies)
  - Cyclomatic complexity, nesting depth, branch count per function
  - API endpoint detection (route decorators)
  - Test function/file detection
  - Function call targets (for CALLS relationship edges)
"""

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

import structlog

from cortex.pipeline.domain.entities import LanguageCapabilityProfile

logger = structlog.get_logger()


class Language(str, Enum):
    PYTHON = "python"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUST = "rust"
    CSHARP = "csharp"
    RUBY = "ruby"
    UNKNOWN = "unknown"


@dataclass
class ParsedFunction:
    """A function or method extracted from source code."""
    name: str
    file_path: str
    line_start: int
    line_end: int
    is_method: bool = False
    parent_class: str | None = None
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    docstring: str | None = None
    # Complexity metrics (computed during parsing)
    cyclomatic_complexity: int = 1
    branch_count: int = 0
    nesting_depth: int = 0
    call_count: int = 0
    # Calls made by this function (list of qualified names or identifiers)
    calls: list[str] = field(default_factory=list)
    # Whether this looks like a test function
    is_test: bool = False
    # Whether this is an API endpoint (has route decorator)
    is_endpoint: bool = False
    # Route info (e.g. "GET /api/v1/users")
    route_info: str | None = None

    def qualified_name(self) -> str:
        """Returns class.method or just function name."""
        if self.parent_class:
            return f"{self.parent_class}.{self.name}"
        return self.name

    def line_count(self) -> int:
        return self.line_end - self.line_start + 1

    def has_docstring(self) -> bool:
        return self.docstring is not None and len(self.docstring.strip()) > 0

    def is_complex(self, threshold: int = 10) -> bool:
        """Returns True if cyclomatic complexity exceeds threshold."""
        return self.cyclomatic_complexity >= threshold

    def is_long(self, threshold: int = 50) -> bool:
        """Returns True if function exceeds line count threshold."""
        return self.line_count() >= threshold

    def parameter_count(self) -> int:
        return len(self.parameters)


@dataclass
class ParsedClass:
    """A class extracted from source code."""
    name: str
    file_path: str
    line_start: int
    line_end: int
    base_classes: list[str] = field(default_factory=list)
    methods: list[ParsedFunction] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: str | None = None
    # Whether this is an interface (ABC in Python, interface in TS/Java)
    is_interface: bool = False
    # Whether this is an enum
    is_enum: bool = False
    # Class-level attributes/fields detected
    attributes: list[str] = field(default_factory=list)

    def method_count(self) -> int:
        return len(self.methods)

    def is_abstract(self) -> bool:
        return (
            "ABC" in self.base_classes
            or "ABCMeta" in self.base_classes
            or "Abstract" in self.name
            or self.is_interface
        )

    def line_count(self) -> int:
        return self.line_end - self.line_start + 1

    def has_docstring(self) -> bool:
        return self.docstring is not None and len(self.docstring.strip()) > 0

    def total_complexity(self) -> int:
        """Sum of cyclomatic complexity across all methods."""
        return sum(m.cyclomatic_complexity for m in self.methods)

    def avg_method_complexity(self) -> float:
        """Average cyclomatic complexity per method."""
        if not self.methods:
            return 0.0
        return self.total_complexity() / len(self.methods)

    def is_god_class(self, method_threshold: int = 15, line_threshold: int = 300) -> bool:
        """Heuristic: too many methods OR too many lines."""
        return self.method_count() >= method_threshold or self.line_count() >= line_threshold


@dataclass
class ParsedImport:
    """An import statement extracted from source code."""
    module: str
    names: list[str] = field(default_factory=list)
    alias: str | None = None
    is_relative: bool = False
    line: int = 0

    def full_name(self) -> str:
        if self.names:
            return f"{self.module}.{', '.join(self.names)}"
        return self.module


@dataclass
class ParsedFile:
    """Complete parsed structure of a single source file."""
    path: str
    language: Language
    functions: list[ParsedFunction] = field(default_factory=list)
    classes: list[ParsedClass] = field(default_factory=list)
    imports: list[ParsedImport] = field(default_factory=list)
    line_count: int = 0
    parse_errors: list[str] = field(default_factory=list)
    # Whether this file is a test file
    is_test_file: bool = False
    # Whether this file is a configuration file
    is_config_file: bool = False
    # Module-level docstring (author intent for the whole file), if present
    docstring: str | None = None

    def has_errors(self) -> bool:
        return len(self.parse_errors) > 0

    def file_contents_available(self) -> bool:
        """Always returns False — raw file content is not stored in ParsedFile."""
        return False

    def all_functions(self) -> list[ParsedFunction]:
        """Returns top-level functions AND all class methods."""
        all_fns = list(self.functions)
        for cls in self.classes:
            all_fns.extend(cls.methods)
        return all_fns

    def all_endpoints(self) -> list[ParsedFunction]:
        """Returns all functions that are detected API endpoints."""
        return [f for f in self.all_functions() if f.is_endpoint]

    def total_complexity(self) -> int:
        """Total cyclomatic complexity across all functions in this file."""
        return sum(f.cyclomatic_complexity for f in self.all_functions())

    def max_complexity(self) -> int:
        """Maximum cyclomatic complexity of any single function."""
        fns = self.all_functions()
        return max((f.cyclomatic_complexity for f in fns), default=1)

    def complex_functions(self, threshold: int = 10) -> list[ParsedFunction]:
        """Functions exceeding the complexity threshold."""
        return [f for f in self.all_functions() if f.is_complex(threshold)]

    def long_functions(self, threshold: int = 50) -> list[ParsedFunction]:
        """Functions exceeding the line count threshold."""
        return [f for f in self.all_functions() if f.is_long(threshold)]

    def documentation_ratio(self) -> float:
        """Fraction of functions/classes that have docstrings."""
        all_symbols = self.all_functions() + self.classes  # type: ignore[operator]
        if not all_symbols:
            return 1.0
        documented = sum(1 for s in all_symbols if s.has_docstring())
        return documented / len(all_symbols)

    def summary(self) -> dict:
        return {
            "path": self.path,
            "language": self.language.value,
            "classes": len(self.classes),
            "functions": len(self.functions),
            "methods": sum(c.method_count() for c in self.classes),
            "imports": len(self.imports),
            "lines": self.line_count,
            "errors": len(self.parse_errors),
            "endpoints": len(self.all_endpoints()),
            "is_test": self.is_test_file,
            "max_complexity": self.max_complexity(),
        }


class LanguageParser(ABC):
    """Interface every language parser implements.

    A parser turns source text into the shared ``ParsedFile`` shape so that
    the graph builder and reasoner never need to know which language a file
    was written in (Req 1.5). Adding a new language means adding a parser that
    satisfies this interface and registering it with the ``ParserRegistry`` —
    no downstream change is required.
    """

    #: File extensions (without the leading dot, lowercased) this parser handles.
    extensions: tuple[str, ...] = ()

    #: Interpreter names matched against a ``#!`` shebang line (e.g. "python").
    shebangs: tuple[str, ...] = ()

    @property
    @abstractmethod
    def language(self) -> "Language":
        """The language this parser produces ``ParsedFile`` results for."""
        ...

    def supports(self, file_path: str, content: str | None = None) -> bool:
        """Return True if this parser can parse ``file_path``.

        Selection is by file extension first; when a file has no recognized
        extension, the first line is inspected for a ``#!`` shebang so that
        extensionless scripts (e.g. ``#!/usr/bin/env python``) still route to
        the right parser.
        """
        ext = _file_extension(file_path)
        if ext and ext in self.extensions:
            return True
        if not ext and content is not None and self.shebangs:
            interpreter = _shebang_interpreter(content)
            if interpreter and any(s in interpreter for s in self.shebangs):
                return True
        return False

    @abstractmethod
    def parse(self, content: str, file_path: str) -> ParsedFile:
        """Parse ``content`` and return a ``ParsedFile``. Never raises."""
        ...

    @abstractmethod
    def profile(self) -> LanguageCapabilityProfile:
        """Return the ``LanguageCapabilityProfile`` for this parser's language.

        The profile declares which structural concepts the language reliably
        supports and which answer sections apply, so downstream answer
        producers can adapt section composition and terminology per stack
        (Req 2.1, Req 2.2, Req 2.3).
        """
        ...


def _file_extension(file_path: str) -> str:
    """Return the lowercased extension without the dot, or "" if none."""
    return file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""


def _shebang_interpreter(content: str) -> str | None:
    """Return the interpreter name from a leading ``#!`` line, if present.

    ``#!/usr/bin/env python3`` -> ``python3`` ; ``#!/bin/bash`` -> ``bash``.
    """
    first_line = content.lstrip().split("\n", 1)[0] if content else ""
    if not first_line.startswith("#!"):
        return None
    tokens = first_line[2:].split()
    if not tokens:
        return None
    # `#!/usr/bin/env python` → interpreter is the arg after env
    last = tokens[-1]
    return last.rsplit("/", 1)[-1].strip()


class PythonASTParser(LanguageParser):
    """Parses Python source files using the built-in ast module."""

    extensions = ("py", "pyi")
    shebangs = ("python",)

    @property
    def language(self) -> "Language":
        return Language.PYTHON

    def profile(self) -> LanguageCapabilityProfile:
        # Python: no first-class interfaces (Protocol/ABC approximate them) or
        # traits; decorators, packages, enums, and native async are all present.
        return LanguageCapabilityProfile(
            language=Language.PYTHON.value,
            has_interfaces=True,   # Protocol / ABC stand in for interfaces
            has_decorators=True,
            has_generics=True,     # typing generics (List[T], Generic[T])
            has_packages=True,     # packages / modules
            has_traits=False,
            has_classes=True,
            has_enums=True,
            has_async=True,
            answer_sections=(
                "overview",
                "modules",
                "classes",
                "functions",
                "decorators",
                "endpoints",
                "dependencies",
            ),
        )

    def parse(self, content: str, file_path: str) -> ParsedFile:
        """Parse a Python file and extract all code structure."""
        result = ParsedFile(
            path=file_path,
            language=Language.PYTHON,
            line_count=len(content.splitlines()),
        )

        # Detect test files by path pattern
        import os
        basename = os.path.basename(file_path)
        result.is_test_file = (
            basename.startswith("test_")
            or basename.endswith("_test.py")
            or "/tests/" in file_path.replace("\\", "/")
            or "/test/" in file_path.replace("\\", "/")
            or basename == "conftest.py"
        )

        # Detect config files
        result.is_config_file = basename in (
            "config.py", "settings.py", "conf.py", "setup.py",
            "pyproject.toml", "setup.cfg",
        ) or "config" in basename.lower()

        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            result.parse_errors.append(
                f"SyntaxError at line {e.lineno}: {e.msg}"
            )
            logger.warning(
                "python_parse_error",
                path=file_path,
                error=str(e),
            )
            return result

        # Module-level docstring — the author's own statement of file intent.
        result.docstring = ast.get_docstring(tree)

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(ParsedImport(
                        module=alias.name,
                        alias=alias.asname,
                        line=node.lineno,
                    ))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    result.imports.append(ParsedImport(
                        module=node.module,
                        names=[a.name for a in node.names],
                        is_relative=node.level > 0,
                        line=node.lineno,
                    ))

        # Extract top-level classes and functions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                parsed_class = self._parse_class(node, file_path)
                result.classes.append(parsed_class)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parsed_fn = self._parse_function(node, file_path)
                result.functions.append(parsed_fn)

        # Log once per file after the loop, not once per top-level function.
        logger.info(
            "python_file_parsed",
            file=file_path,
            **result.summary(),
        )
        logger.debug(
            "python_file_structure",
            path=file_path,
            classes=[c.name for c in result.classes],
            functions=[f.name for f in result.functions],
        )

        return result

    def _parse_class(
        self,
        node: ast.ClassDef,
        file_path: str,
    ) -> ParsedClass:
        """Extract class structure including all methods."""
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_classes.append(f"{base.attr}")

        docstring = ast.get_docstring(node)
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(dec.attr)

        # Detect if this is an interface (ABC-based)
        is_interface = any(
            b in ("ABC", "ABCMeta", "Protocol") for b in base_classes
        ) or "abstractmethod" in " ".join(decorators)

        # Detect if this is an enum
        is_enum = any(
            b in ("Enum", "IntEnum", "StrEnum", "Flag", "IntFlag")
            for b in base_classes
        )

        # Extract class-level attributes (annotated assignments)
        attributes = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                attributes.append(child.target.id)
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)

        parsed_class = ParsedClass(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            base_classes=base_classes,
            decorators=decorators,
            docstring=docstring,
            is_interface=is_interface,
            is_enum=is_enum,
            attributes=attributes[:30],  # cap to avoid memory bloat
        )

        # Extract methods
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                method = self._parse_function(
                    child, file_path,
                    is_method=True,
                    parent_class=node.name,
                )
                parsed_class.methods.append(method)

        return parsed_class

    def _parse_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: str,
        is_method: bool = False,
        parent_class: str | None = None,
    ) -> ParsedFunction:
        """Extract function/method structure with real complexity metrics.

        Cyclomatic complexity = 1 + number of decision points.
        Decision points: if/elif, for, while, except, with, assert,
                         boolean operators (and/or), comprehensions.
        This matches the standard McCabe complexity definition.
        """
        params = []
        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls":
                params.append(arg.arg)

        # Extract return type annotation
        return_type = None
        if node.returns:
            try:
                return_type = ast.unparse(node.returns)
            except Exception:
                pass

        decorators = []
        decorator_strs = []  # full decorator text for endpoint detection
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
                decorator_strs.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(dec.attr)
                try:
                    decorator_strs.append(ast.unparse(dec))
                except Exception:
                    decorator_strs.append(dec.attr)
            elif isinstance(dec, ast.Call):
                try:
                    full_dec = ast.unparse(dec)
                    decorator_strs.append(full_dec)
                    # Get the base name
                    if isinstance(dec.func, ast.Attribute):
                        decorators.append(dec.func.attr)
                    elif isinstance(dec.func, ast.Name):
                        decorators.append(dec.func.id)
                except Exception:
                    pass

        # ── Detect if this is an API endpoint ─────────────────────────────────
        is_endpoint = False
        route_info = None
        _http_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
        for dec_str in decorator_strs:
            dec_lower = dec_str.lower()
            for method in _http_methods:
                if f".{method}(" in dec_lower or f"@{method}(" in dec_lower:
                    # Extract the route path from the decorator
                    import re as _re
                    path_match = _re.search(r'["\']([^"\']+)["\']', dec_str)
                    path = path_match.group(1) if path_match else "/"
                    route_info = f"{method.upper()} {path}"
                    is_endpoint = True
                    break
            if f"route(" in dec_lower or f"api_view" in dec_lower:
                is_endpoint = True
            if is_endpoint:
                break

        # ── Detect if this is a test function ─────────────────────────────────
        is_test = (
            node.name.startswith("test_")
            or node.name.startswith("test")
            and node.name != "test"
            or "pytest" in " ".join(decorators).lower()
            or "parametrize" in " ".join(decorators).lower()
        )

        # ── Cyclomatic complexity (McCabe) ────────────────────────────────────
        branch_count  = 0
        nesting_depth = 0
        call_count    = 0
        max_depth     = 0
        calls_made: list[str] = []

        def _walk_complexity(subtree: ast.AST, depth: int) -> None:
            nonlocal branch_count, nesting_depth, call_count, max_depth
            max_depth = max(max_depth, depth)

            for child in ast.iter_child_nodes(subtree):
                if isinstance(child, (ast.If, ast.IfExp)):
                    branch_count += 1
                    _walk_complexity(child, depth + 1)
                elif isinstance(child, (ast.For, ast.AsyncFor,
                                         ast.While, ast.ListComp,
                                         ast.SetComp, ast.DictComp,
                                         ast.GeneratorExp)):
                    branch_count += 1
                    _walk_complexity(child, depth + 1)
                elif isinstance(child, ast.ExceptHandler):
                    branch_count += 1
                    _walk_complexity(child, depth + 1)
                elif isinstance(child, ast.With):
                    _walk_complexity(child, depth + 1)
                elif isinstance(child, ast.BoolOp):
                    branch_count += len(child.values) - 1
                    _walk_complexity(child, depth)
                elif isinstance(child, ast.Assert):
                    branch_count += 1
                    _walk_complexity(child, depth)
                elif isinstance(child, ast.Call):
                    call_count += 1
                    # Extract the call target name
                    try:
                        call_name = ast.unparse(child.func)
                        # Simplify: keep last segment for attribute access
                        if "." in call_name:
                            # e.g. self._repo.save -> save
                            parts = call_name.split(".")
                            # Keep class.method or just method
                            if len(parts) >= 2 and parts[0] == "self":
                                calls_made.append(".".join(parts[1:]))
                            else:
                                calls_made.append(parts[-1])
                        else:
                            calls_made.append(call_name)
                    except Exception:
                        pass
                    _walk_complexity(child, depth)
                else:
                    _walk_complexity(child, depth)

        _walk_complexity(node, 0)
        cyclomatic = 1 + branch_count

        # Deduplicate calls (keep unique call targets)
        unique_calls = list(dict.fromkeys(calls_made))[:20]  # cap at 20

        fn = ParsedFunction(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            is_method=is_method,
            parent_class=parent_class,
            parameters=params,
            return_type=return_type,
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=ast.get_docstring(node),
            cyclomatic_complexity=cyclomatic,
            branch_count=branch_count,
            nesting_depth=max_depth,
            call_count=call_count,
            calls=unique_calls,
            is_test=is_test,
            is_endpoint=is_endpoint,
            route_info=route_info,
        )
        return fn




def default_parser_registry() -> "ParserRegistry":
    """Build the registry with all built-in language parsers registered.

    Python is registered first (via the stdlib ``ast`` module) so it wins for
    shebang scripts and keeps its docstring fidelity. Every non-Python language
    (JavaScript, TypeScript, Java, Go, Rust, C#, Ruby) is parsed with
    tree-sitter (Req 1.2), which replaces the retired regex Java/TS/JS parsers.

    If the tree-sitter grammars are unavailable in this environment, the
    tree-sitter parsers are simply not registered (``tree_sitter_parsers()``
    returns an empty list) and those languages fall through to the registry's
    "no parser" path rather than crashing — a graceful degradation.
    """
    # Imported lazily to avoid a hard dependency on tree-sitter at import time.
    from cortex.pipeline.infrastructure.tree_sitter_parser import tree_sitter_parsers

    parsers: list[LanguageParser] = [PythonASTParser()]
    parsers.extend(tree_sitter_parsers())
    return ParserRegistry(parsers)


class ParserRegistry:
    """Selects a ``LanguageParser`` for a file by extension or shebang.

    The registry is the single decision point for which parser handles a
    file. Registration order is priority order: the first registered parser
    whose ``supports()`` returns True wins. Adding a language means
    registering another ``LanguageParser`` — nothing downstream changes
    (Req 1.5).
    """

    def __init__(self, parsers: list[LanguageParser] | None = None) -> None:
        self._parsers: list[LanguageParser] = list(parsers) if parsers else []

    def register(self, parser: LanguageParser) -> None:
        """Add a parser. Earlier-registered parsers take priority on ties."""
        self._parsers.append(parser)

    def parsers(self) -> list[LanguageParser]:
        """Return the registered parsers in priority order."""
        return list(self._parsers)

    def parser_for(
        self, file_path: str, content: str | None = None
    ) -> LanguageParser | None:
        """Return the parser that supports ``file_path``, or None."""
        for parser in self._parsers:
            if parser.supports(file_path, content):
                return parser
        return None


class ASTParser:
    """Main parser — routes each file through the ``ParserRegistry``.

    Public API (``detect_language``, ``parse``, ``parse_many``) is unchanged
    so existing callers (``ASTParseStage``, ``GitHubAnalyzer``) keep working.
    Parser selection now flows through the registry instead of a hard-coded
    if/elif chain, so new languages are added by registration alone.
    """

    def __init__(self, registry: "ParserRegistry | None" = None) -> None:
        self._registry = registry if registry is not None else default_parser_registry()

    def detect_language(self, file_path: str, content: str | None = None) -> Language:
        parser = self._registry.parser_for(file_path, content)
        if parser is None:
            return Language.UNKNOWN
        # TS/JS share one parser; resolve the precise language by extension.
        if parser.language in (Language.TYPESCRIPT, Language.JAVASCRIPT):
            ext = _file_extension(file_path)
            if ext in ("js", "jsx", "mjs", "cjs"):
                return Language.JAVASCRIPT
            return Language.TYPESCRIPT
        return parser.language

    def parse(self, content: str, file_path: str) -> ParsedFile:
        parser = self._registry.parser_for(file_path, content)
        if parser is not None:
            return parser.parse(content, file_path)
        language = self.detect_language(file_path, content)
        return ParsedFile(
            path=file_path,
            language=language,
            line_count=len(content.splitlines()),
            parse_errors=[f"No parser available for {language.value}"],
        )

    def parse_many(
        self,
        files: list[tuple[str, str]],
    ) -> list[ParsedFile]:
        """Parse multiple files. Each tuple is (content, file_path).
        Skips files that fail — never crashes the whole pipeline."""
        results = []
        for content, path in files:
            try:
                parsed = self.parse(content, path)
                results.append(parsed)
            except Exception as e:
                logger.error(
                    "ast_parse_unexpected_error",
                    path=path,
                    error=str(e),
                )
                results.append(ParsedFile(
                    path=path,
                    language=self.detect_language(path),
                    parse_errors=[f"Unexpected error: {e}"],
                ))
        return results