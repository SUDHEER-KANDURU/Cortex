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
import re
from dataclasses import dataclass, field
from enum import Enum
import structlog

logger = structlog.get_logger()


class Language(str, Enum):
    PYTHON = "python"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
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


class PythonASTParser:
    """Parses Python source files using the built-in ast module."""

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


class JavaASTParser:
    """Parses Java source files using regex patterns.
    Not as precise as a real Java parser but covers the common cases."""

    METHOD_PATTERN = re.compile(
        r'(?:public|private|protected)\s+'
        r'(?:static\s+)?(?:final\s+)?(?:async\s+)?'
        r'(?:[\w<>\[\]]+)\s+'
        r'(\w+)\s*\(([^)]*)\)\s*'
        r'(?:throws\s+[\w,\s]+)?\s*\{',
        re.MULTILINE,
    )

    IMPORT_PATTERN = re.compile(
        r'^import\s+(?:static\s+)?([\w.]+)(?:\.\*)?;',
        re.MULTILINE,
    )

    ANNOTATION_PATTERN = re.compile(
        r'@(\w+)(?:\([^)]*\))?',
        re.MULTILINE,
    )

    def parse(self, content: str, file_path: str) -> ParsedFile:
        """Parse a Java file using regex patterns."""
        lines = content.splitlines()
        result = ParsedFile(
            path=file_path,
            language=Language.JAVA,
            line_count=len(lines),
        )

        # Extract imports
        for match in self.IMPORT_PATTERN.finditer(content):
            module_parts = match.group(1).rsplit(".", 1)
            if len(module_parts) == 2:
                result.imports.append(ParsedImport(
                    module=module_parts[0],
                    names=[module_parts[1]],
                    line=content[:match.start()].count("\n") + 1,
                ))

        # Extract classes — improved pattern
        class_pattern = re.compile(
            r'(?:^|\s)(?:public\s+)?(?:abstract\s+|final\s+)?'
            r'(?:class|interface|enum)\s+(\w+)',
            re.MULTILINE,
        )
        for match in class_pattern.finditer(content):
            class_name = match.group(1)
            # Skip keywords that are not class names
            if class_name in {
                "if", "while", "for", "switch", "try",
                "catch", "new", "return", "extends", "implements",
            }:
                continue
            line_num = content[:match.start()].count("\n") + 1

            # Find base classes
            base_classes = []
            extends_match = re.search(
                rf'{class_name}\s+extends\s+(\w+)', content
            )
            if extends_match:
                base_classes.append(extends_match.group(1))

            parsed_class = ParsedClass(
                name=class_name,
                file_path=file_path,
                line_start=line_num,
                line_end=line_num,   # will be estimated below
                base_classes=base_classes,
            )
            result.classes.append(parsed_class)

        # Estimate class end lines by finding the next class start (or EOF)
        for i, cls in enumerate(result.classes):
            next_start = result.classes[i + 1].line_start if i + 1 < len(result.classes) else len(lines)
            cls.line_end = max(cls.line_start, next_start - 1)

        # Extract methods
        for match in self.METHOD_PATTERN.finditer(content):
            method_name = match.group(1)
            if method_name in {"if", "while", "for", "switch", "new"}:
                continue
            params_str = match.group(2)
            line_num = content[:match.start()].count("\n") + 1
            params = []
            if params_str.strip():
                for param in params_str.split(","):
                    parts = param.strip().split()
                    if len(parts) >= 2:
                        params.append(parts[-1])

            # Estimate method end by scanning for matching closing brace
            body_start = content.find("{", match.end() - 1)
            if body_start != -1:
                depth, pos = 1, body_start + 1
                while pos < len(content) and depth > 0:
                    if content[pos] == "{": depth += 1
                    elif content[pos] == "}": depth -= 1
                    pos += 1
                line_end = content[:pos].count("\n") + 1
                fn_body  = content[body_start:pos]
            else:
                line_end = line_num + 10
                fn_body  = ""

            # ── Complexity metrics (regex-based, same approach as TS) ────────
            fn_body_clean = re.sub(r'/\*.*?\*/', ' ', fn_body, flags=re.DOTALL)
            fn_body_clean = re.sub(r'//[^\n]*', ' ', fn_body_clean)
            fn_body_clean = re.sub(r'"(?:[^"\\]|\\.)*"', '""', fn_body_clean)
            _java_branch_re = re.compile(
                r'\bif\b|\belse\s+if\b|\bfor\b|\bwhile\b|\bswitch\b|\bcatch\b'
                r'|\?\s*(?![\?\.:])|&&|\|\|'
            )
            branch_c = len(_java_branch_re.findall(fn_body_clean))
            cyclo    = 1 + branch_c
            max_d, cur_d = 0, 0
            for ch in fn_body_clean:
                if ch == '{':
                    cur_d += 1
                    max_d = max(max_d, cur_d)
                elif ch == '}':
                    cur_d -= 1
            nest_d   = max(0, max_d - 1)
            _call_re = re.compile(r'\b\w+\s*\(')
            _java_kw = {'if','for','while','switch','catch','new','return',
                        'throw','instanceof','typeof'}
            call_c   = sum(
                1 for cm in _call_re.finditer(fn_body_clean)
                if cm.group(0).split('(')[0].strip() not in _java_kw
            )

            fn = ParsedFunction(
                name=method_name,
                file_path=file_path,
                line_start=line_num,
                line_end=line_end,
                is_method=True,
                parameters=params,
                cyclomatic_complexity=cyclo,
                branch_count=branch_c,
                nesting_depth=nest_d,
                call_count=call_c,
            )
            result.functions.append(fn)

        logger.info("java_file_parsed", file=file_path, **result.summary())
        return result


class TypeScriptASTParser:
    """Regex-based TypeScript/JavaScript parser.

    Extracts with high fidelity:
      - ES6/TS class declarations + extends/implements
      - Function declarations (function foo, async function foo)
      - Arrow functions assigned to const/let/var (const foo = () => ...)
      - Class methods (including async, static, private)
      - JSDoc/TSDoc comment blocks → docstring
      - import statements (ES6 import ... from '...')
      - Parameter lists (with type annotations stripped)
      - Accurate line counts via brace-matching for class/function bodies

    Not supported (would need tree-sitter):
      - Overloaded signatures
      - Decorator expressions beyond simple @decorator
      - Type-only imports
    """

    # ── Import detection ──────────────────────────────────────────────────────
    _IMPORT_RE = re.compile(
        r'''^import\s+
        (?:
            (?:type\s+)?                      # optional 'type'
            (?:\*\s+as\s+(\w+)|              # * as alias
               \{([^}]+)\}|                  # { a, b, c }
               (\w+)(?:\s*,\s*\{[^}]+\})?)  # default or default + named
        )\s+from\s+['"]([\w@/.\-]+)['"]
        |
        ^import\s+['"]([\w@/.\-]+)['"]       # side-effect import
        ''',
        re.VERBOSE | re.MULTILINE,
    )

    # ── Class declaration ─────────────────────────────────────────────────────
    _CLASS_RE = re.compile(
        r'''(?:^|\n)
        [ \t]*(?:export\s+)?(?:abstract\s+)?
        class\s+(\w+)                          # class Name
        (?:<[^>]+>)?                           # optional <T>
        (?:\s+extends\s+([\w.]+)(?:<[^>]+>)?)?  # extends Base
        (?:\s+implements\s+([\w,\s<>]+))?      # implements A, B
        \s*\{
        ''',
        re.VERBOSE | re.MULTILINE,
    )

    # ── Function declaration ──────────────────────────────────────────────────
    _FUNC_DECL_RE = re.compile(
        r'''(?:^|\n)[ \t]*
        (?:export\s+)?(?:default\s+)?
        (async\s+)?function\s*\*?\s*
        (\w+)\s*
        (?:<[^>]+>)?           # optional generics
        \(([^)]*)\)            # params
        ''',
        re.VERBOSE | re.MULTILINE,
    )

    # ── Arrow function assigned to identifier ─────────────────────────────────
    _ARROW_RE = re.compile(
        r'''(?:^|\n)[ \t]*
        (?:export\s+)?
        (?:const|let|var)\s+
        (\w+)\s*(?::[^=]+)?\s*=\s*   # identifier : Type =
        (?:React\.memo\(|forwardRef\()*  # optional wrappers
        (async\s+)?
        (?:
            \(([^)]*)\)      # (params)
            |
            (\w+)            # single param without parens
        )
        \s*(?::[^=>\n]+)?\s*   # optional return type
        =>
        ''',
        re.VERBOSE | re.MULTILINE,
    )

    # ── Class method ─────────────────────────────────────────────────────────
    _METHOD_RE = re.compile(
        r'''(?:^|\n)[ \t]*
        (?:(?:public|private|protected|static|abstract|override|readonly)\s+)*
        (?:readonly\s+)?
        (async\s+|get\s+|set\s+)?   # optional modifier
        (?!\bif\b|\bfor\b|\bwhile\b|\bswitch\b|\breturn\b|\bdelete\b)
        (\w+)\s*
        (?:<[^>]+>)?
        \(([^)]*)\)                   # params
        (?:\s*:\s*[^{;]+)?            # return type
        \s*\{
        ''',
        re.VERBOSE | re.MULTILINE,
    )

    # ── JSDoc block ───────────────────────────────────────────────────────────
    _JSDOC_RE = re.compile(r'/\*\*.*?\*/', re.DOTALL)
    _SINGLE_COMMENT_RE = re.compile(r'//[^\n]*')

    # ── Decorator ─────────────────────────────────────────────────────────────
    _DECORATOR_RE = re.compile(r'@(\w+)(?:\([^)]*\))?')

    # ── Complexity: branch-counting keywords & operators ─────────────────────
    # Matches: if / else if, for, while, switch, catch, ternary (?),
    # logical AND (&&) and OR (||) — each adds a branch point.
    # Word-boundary anchored to avoid matching inside identifiers.
    _BRANCH_KW_RE = re.compile(
        r'\bif\b|\belse\s+if\b|\bfor\b|\bwhile\b|\bswitch\b|\bcatch\b'
        r'|\?\s*(?![\?\.:])'   # ternary ? — exclude ??, ?., ?:
        r'|&&|\|\|',
    )
    # Function calls: identifier followed by (
    _CALL_RE = re.compile(r'\b\w+\s*\(')

    @staticmethod
    def _strip_strings_and_comments(src: str) -> str:
        """Remove string literals and comments so they don't pollute
        branch/call counting.  Not 100% perfect but good enough for
        token-level pattern matching."""
        # Strip block comments
        src = re.sub(r'/\*.*?\*/', ' ', src, flags=re.DOTALL)
        # Strip line comments
        src = re.sub(r'//[^\n]*', ' ', src)
        # Strip template literals (basic — no nested ${} support needed)
        src = re.sub(r'`[^`]*`', '""', src, flags=re.DOTALL)
        # Strip double-quoted strings
        src = re.sub(r'"(?:[^"\\]|\\.)*"', '""', src)
        # Strip single-quoted strings
        src = re.sub(r"'(?:[^'\\]|\\.)*'", "''", src)
        return src

    def _compute_ts_complexity(self, body: str) -> tuple[int, int, int, int]:
        """Compute (branch_count, cyclomatic, nesting_depth, call_count)
        for a TS/JS function body string (the text between the outer braces,
        including the braces themselves).

        Algorithm:
          branch_count  — count of if/else if/for/while/switch/catch/?/&&/||
                          tokens in the cleaned body (strings/comments stripped)
          cyclomatic    — 1 + branch_count   (McCabe formula)
          nesting_depth — maximum brace-nesting depth reached inside the body
                          (outer { } of the function itself counts as depth 1,
                          so the first nested block is depth 2, reported as 1
                          relative nesting level)
          call_count    — approximate count of function-call expressions
        """
        cleaned = self._strip_strings_and_comments(body)

        branch_count = len(self._BRANCH_KW_RE.findall(cleaned))
        cyclomatic   = 1 + branch_count

        # Nesting depth via brace scanning
        max_depth = 0
        depth     = 0
        for ch in cleaned:
            if ch == '{':
                depth += 1
                if depth > max_depth:
                    max_depth = depth
            elif ch == '}':
                depth -= 1
        # depth 1 = the function's own outer braces; relative nesting = max_depth - 1
        nesting_depth = max(0, max_depth - 1)

        # Call count: rough approximation — word( patterns, minus keywords
        _kw = {'if','for','while','switch','catch','function','return',
               'typeof','instanceof','new','delete','throw','await','yield'}
        call_count = sum(
            1 for m in self._CALL_RE.finditer(cleaned)
            if m.group(0).split('(')[0].strip() not in _kw
        )

        return branch_count, cyclomatic, nesting_depth, call_count

    def parse(self, content: str, file_path: str) -> ParsedFile:
        lines = content.splitlines()
        result = ParsedFile(
            path=file_path,
            language=Language.TYPESCRIPT if file_path.endswith((".ts", ".tsx")) else Language.JAVASCRIPT,
            line_count=len(lines),
        )

        # Pre-compute line start offsets for fast position→line conversion
        line_offsets: list[int] = []
        offset = 0
        for line in lines:
            line_offsets.append(offset)
            offset += len(line) + 1  # +1 for \n

        def pos_to_line(pos: int) -> int:
            lo, hi = 0, len(line_offsets) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if line_offsets[mid] <= pos:
                    lo = mid
                else:
                    hi = mid - 1
            return lo + 1  # 1-indexed

        def find_body_end(start_pos: int) -> int:
            """Find the closing } of a block starting at start_pos."""
            brace_pos = content.find("{", start_pos)
            if brace_pos == -1:
                return start_pos
            depth, pos = 1, brace_pos + 1
            while pos < len(content) and depth > 0:
                c = content[pos]
                if c == "{":   depth += 1
                elif c == "}": depth -= 1
                pos += 1
            return pos

        def get_jsdoc_before(pos: int) -> str | None:
            """Return JSDoc content if there's one immediately before pos."""
            snippet = content[max(0, pos - 400):pos]
            matches = list(self._JSDOC_RE.finditer(snippet))
            if not matches:
                return None
            last = matches[-1]
            # Must be close to the position (only whitespace between)
            between = snippet[last.end():]
            if between.strip() == "" or re.match(r'^[\s@]*$', between):
                return last.group(0)
            return None

        def strip_types_from_params(params_str: str) -> list[str]:
            """Extract parameter names from 'name: Type = default, ...'"""
            if not params_str.strip():
                return []
            params = []
            for part in params_str.split(","):
                part = part.strip()
                # remove default values
                part = re.sub(r'\s*=\s*.*', '', part)
                # remove type annotation
                part = re.sub(r'\s*:\s*.*', '', part)
                # remove rest operator
                part = part.lstrip(".")
                # remove destructuring
                if part.startswith("{") or part.startswith("["):
                    params.append("<destructured>")
                    continue
                # remove modifiers (private, readonly, etc.)
                part = re.sub(r'^(public|private|protected|readonly)\s+', '', part)
                name = part.strip()
                if name and re.match(r'^\w+$', name):
                    params.append(name)
            return params

        # ── Parse imports ─────────────────────────────────────────────────────
        for match in self._IMPORT_RE.finditer(content):
            line_no = pos_to_line(match.start())
            # Determine module (last non-None group)
            module = match.group(4) or match.group(5) or ""
            if module:
                names = []
                if match.group(2):  # named imports { a, b }
                    names = [n.strip().split(" as ")[0].strip()
                             for n in match.group(2).split(",") if n.strip()]
                result.imports.append(ParsedImport(
                    module=module,
                    names=names,
                    is_relative=module.startswith("."),
                    line=line_no,
                ))

        # ── Parse classes ─────────────────────────────────────────────────────
        class_positions: list[tuple[int, int, ParsedClass]] = []  # (start_pos, end_pos, cls)

        for match in self._CLASS_RE.finditer(content):
            class_name = match.group(1)
            base_raw   = match.group(2) or ""
            bases = [b.strip() for b in base_raw.split(",") if b.strip()] if base_raw else []

            line_start = pos_to_line(match.start())
            body_end   = find_body_end(match.end() - 1)
            line_end   = pos_to_line(body_end)

            jsdoc = get_jsdoc_before(match.start())

            decorators = []
            pre_snippet = content[max(0, match.start() - 200):match.start()]
            for dm in self._DECORATOR_RE.finditer(pre_snippet):
                decorators.append(dm.group(1))

            parsed_class = ParsedClass(
                name=class_name,
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                base_classes=bases,
                decorators=decorators,
                docstring=jsdoc,
            )
            class_positions.append((match.start(), body_end, parsed_class))
            result.classes.append(parsed_class)

        # ── Parse class methods (within class bodies) ─────────────────────────
        # Use class position ranges to assign methods to classes
        class_ranges: list[tuple[int, int, ParsedClass]] = class_positions

        # Keywords that cannot be method names
        _KW = {"if","for","while","switch","return","new","delete","typeof",
               "instanceof","void","throw","catch","finally","try","else",
               "case","break","continue","const","let","var","import","export"}

        for class_start, class_end, cls in class_ranges:
            class_body = content[class_start:class_end]
            body_offset = class_start

            for m in self._METHOD_RE.finditer(class_body):
                name = m.group(2)
                if name in _KW or name == cls.name:  # skip constructor and keywords
                    continue
                params_raw = m.group(3) or ""
                is_async   = bool(m.group(1) and "async" in m.group(1))
                params     = strip_types_from_params(params_raw)
                abs_start  = body_offset + m.start()
                line_start = pos_to_line(abs_start)
                body_end_abs = find_body_end(body_offset + m.end() - 1)
                line_end   = pos_to_line(body_end_abs)
                jsdoc      = get_jsdoc_before(abs_start)

                fn_body = content[abs_start:body_end_abs]
                branch_c, cyclo, nest_d, call_c = self._compute_ts_complexity(fn_body)

                method = ParsedFunction(
                    name=name,
                    file_path=file_path,
                    line_start=line_start,
                    line_end=line_end,
                    is_method=True,
                    parent_class=cls.name,
                    parameters=params,
                    is_async=is_async,
                    docstring=jsdoc,
                    cyclomatic_complexity=cyclo,
                    branch_count=branch_c,
                    nesting_depth=nest_d,
                    call_count=call_c,
                )
                cls.methods.append(method)

        # ── Parse top-level function declarations ─────────────────────────────
        inside_class_ranges = {(s, e) for s, e, _ in class_ranges}

        def in_class(pos: int) -> bool:
            return any(s <= pos <= e for s, e, _ in class_ranges)

        for m in self._FUNC_DECL_RE.finditer(content):
            if in_class(m.start()):
                continue
            name      = m.group(2)
            is_async  = bool(m.group(1))
            params    = strip_types_from_params(m.group(3) or "")
            line_start= pos_to_line(m.start())
            body_end  = find_body_end(m.end())
            line_end  = pos_to_line(body_end)
            jsdoc     = get_jsdoc_before(m.start())

            fn_body = content[m.start():body_end]
            branch_c, cyclo, nest_d, call_c = self._compute_ts_complexity(fn_body)

            fn = ParsedFunction(
                name=name,
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                is_method=False,
                parameters=params,
                is_async=is_async,
                docstring=jsdoc,
                cyclomatic_complexity=cyclo,
                branch_count=branch_c,
                nesting_depth=nest_d,
                call_count=call_c,
            )
            result.functions.append(fn)

        # ── Parse top-level arrow functions ───────────────────────────────────
        for m in self._ARROW_RE.finditer(content):
            if in_class(m.start()):
                continue
            name     = m.group(1)
            is_async = bool(m.group(2))
            params_raw = m.group(3) or m.group(4) or ""
            params   = strip_types_from_params(params_raw)
            line_start = pos_to_line(m.start())
            # Arrow body: either { block } or expression
            arrow_pos = content.find("=>", m.start())
            arrow_body_start = -1
            if arrow_pos == -1:
                line_end = line_start
                body_end = m.end()
            else:
                after_arrow = content[arrow_pos + 2:].lstrip()
                if after_arrow.startswith("{"):
                    arrow_body_start = arrow_pos + 2 + content[arrow_pos + 2:].index("{")
                    body_end = find_body_end(arrow_body_start)
                    line_end = pos_to_line(body_end)
                else:
                    # expression arrow — ends at next newline
                    nl = content.find("\n", arrow_pos)
                    line_end = pos_to_line(nl) if nl != -1 else line_start
                    body_end = nl if nl != -1 else arrow_pos + 2
            jsdoc = get_jsdoc_before(m.start())

            fn_body = content[m.start():body_end]
            branch_c, cyclo, nest_d, call_c = self._compute_ts_complexity(fn_body)

            arrow_fn = ParsedFunction(
                name=name,
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                is_method=False,
                parameters=params,
                is_async=is_async,
                docstring=jsdoc,
                cyclomatic_complexity=cyclo,
                branch_count=branch_c,
                nesting_depth=nest_d,
                call_count=call_c,
            )
            result.functions.append(arrow_fn)

        logger.info("ts_file_parsed", file=file_path, **result.summary())
        return result


class ASTParser:
    """Main parser — detects language and delegates to the right parser."""

    def __init__(self) -> None:
        self._python_parser = PythonASTParser()
        self._java_parser   = JavaASTParser()
        self._ts_parser     = TypeScriptASTParser()

    def detect_language(self, file_path: str) -> Language:
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        mapping = {
            "py":   Language.PYTHON,
            "java": Language.JAVA,
            "ts":   Language.TYPESCRIPT,
            "tsx":  Language.TYPESCRIPT,
            "js":   Language.JAVASCRIPT,
            "jsx":  Language.JAVASCRIPT,
        }
        return mapping.get(ext, Language.UNKNOWN)

    def parse(self, content: str, file_path: str) -> ParsedFile:
        language = self.detect_language(file_path)
        if language == Language.PYTHON:
            return self._python_parser.parse(content, file_path)
        elif language == Language.JAVA:
            return self._java_parser.parse(content, file_path)
        elif language in (Language.TYPESCRIPT, Language.JAVASCRIPT):
            return self._ts_parser.parse(content, file_path)
        else:
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