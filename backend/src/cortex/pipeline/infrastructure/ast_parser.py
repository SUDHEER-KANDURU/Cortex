"""AST parser — extracts code structure from source files.
Supports Python and Java. Returns structured data that the
graph builder uses to create Neo4j nodes and edges."""

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
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    docstring: str | None = None

    def qualified_name(self) -> str:
        """Returns class.method or just function name."""
        if self.parent_class:
            return f"{self.parent_class}.{self.name}"
        return self.name

    def line_count(self) -> int:
        return self.line_end - self.line_start + 1


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

    def method_count(self) -> int:
        return len(self.methods)

    def is_abstract(self) -> bool:
        return "ABC" in self.base_classes or "ABCMeta" in self.base_classes


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

    def has_errors(self) -> bool:
        return len(self.parse_errors) > 0

    def all_functions(self) -> list[ParsedFunction]:
        """Returns top-level functions AND all class methods."""
        all_fns = list(self.functions)
        for cls in self.classes:
            all_fns.extend(cls.methods)
        return all_fns

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

                logger.info(
                    "python_file_parsed",
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

        parsed_class = ParsedClass(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            base_classes=base_classes,
            decorators=decorators,
            docstring=docstring,
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
        """Extract function/method structure."""
        params = []
        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls":
                params.append(arg.arg)

        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                decorators.append(dec.attr)

        return ParsedFunction(
            name=node.name,
            file_path=file_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            is_method=is_method,
            parent_class=parent_class,
            parameters=params,
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=ast.get_docstring(node),
        )


class JavaASTParser:
    """Parses Java source files using regex patterns.
    Not as precise as a real Java parser but covers the common cases."""

    # Regex patterns for Java
    CLASS_PATTERN = re.compile(
        r'(?:public|private|protected)?\s*'
        r'(?:abstract|final)?\s*'
        r'class\s+(\w+)'
        r'(?:\s+extends\s+(\w+))?'
        r'(?:\s+implements\s+([\w,\s]+))?'
        r'\s*\{',
        re.MULTILINE,
    )

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
            else:
                result.imports.append(ParsedImport(
                    module=match.group(1),
                    line=content[:match.start()].count("\n") + 1,
                ))

        # Extract classes
        for match in self.CLASS_PATTERN.finditer(content):
            class_name = match.group(1)
            base_class = match.group(2)
            line_num = content[:match.start()].count("\n") + 1

            base_classes = []
            if base_class:
                base_classes.append(base_class)
            if match.group(3):
                base_classes.extend(
                    [i.strip() for i in match.group(3).split(",")]
                )

            parsed_class = ParsedClass(
                name=class_name,
                file_path=file_path,
                line_start=line_num,
                line_end=line_num + 10,  # Approximate
                base_classes=base_classes,
            )
            result.classes.append(parsed_class)

        # Extract methods
        for match in self.METHOD_PATTERN.finditer(content):
            method_name = match.group(1)
            params_str = match.group(2)
            line_num = content[:match.start()].count("\n") + 1

            # Skip constructors and common false positives
            if method_name in {"if", "while", "for", "switch"}:
                continue

            params = []
            if params_str.strip():
                for param in params_str.split(","):
                    parts = param.strip().split()
                    if len(parts) >= 2:
                        params.append(parts[-1])

            fn = ParsedFunction(
                name=method_name,
                file_path=file_path,
                line_start=line_num,
                line_end=line_num + 5,
                is_method=True,
                parameters=params,
            )
            result.functions.append(fn)

        logger.info(
            "java_file_parsed",
            **result.summary(),
        )

        return result


class ASTParser:
    """Main parser — detects language and delegates to the right parser."""

    def __init__(self) -> None:
        self._python_parser = PythonASTParser()
        self._java_parser = JavaASTParser()

    def detect_language(self, file_path: str) -> Language:
        """Detect the programming language from file extension."""
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
        mapping = {
            "py": Language.PYTHON,
            "java": Language.JAVA,
            "ts": Language.TYPESCRIPT,
            "tsx": Language.TYPESCRIPT,
            "js": Language.JAVASCRIPT,
            "jsx": Language.JAVASCRIPT,
        }
        return mapping.get(ext, Language.UNKNOWN)

    def parse(self, content: str, file_path: str) -> ParsedFile:
        """Parse a source file and return its structure."""
        language = self.detect_language(file_path)

        if language == Language.PYTHON:
            return self._python_parser.parse(content, file_path)
        elif language == Language.JAVA:
            return self._java_parser.parse(content, file_path)
        else:
            # For unsupported languages return a minimal result
            return ParsedFile(
                path=file_path,
                language=language,
                line_count=len(content.splitlines()),
                parse_errors=[
                    f"No parser available for {language.value}"
                ],
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