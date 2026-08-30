"""Tests for the LanguageParser abstraction and ParserRegistry (Req 1.1, 1.3, 1.5)."""

from cortex.pipeline.infrastructure.ast_parser import (
    ASTParser,
    Language,
    ParsedFile,
    ParserRegistry,
    PythonASTParser,
    default_parser_registry,
)
from cortex.pipeline.infrastructure.tree_sitter_parser import TreeSitterParser


def test_python_parser_supports_py_extension() -> None:
    parser = PythonASTParser()
    assert parser.supports("app/module.py")
    assert not parser.supports("app/module.java")


def test_typescript_and_javascript_parsers_support_their_extensions() -> None:
    registry = default_parser_registry()
    for path in ("a.ts", "a.tsx"):
        parser = registry.parser_for(path)
        assert isinstance(parser, TreeSitterParser) and parser.language == Language.TYPESCRIPT, path
    for path in ("a.js", "a.jsx", "a.mjs", "a.cjs"):
        parser = registry.parser_for(path)
        assert isinstance(parser, TreeSitterParser) and parser.language == Language.JAVASCRIPT, path
    assert not isinstance(registry.parser_for("a.py"), TreeSitterParser)


def test_java_parser_supports_java_extension() -> None:
    registry = default_parser_registry()
    parser = registry.parser_for("Main.java")
    assert isinstance(parser, TreeSitterParser) and parser.language == Language.JAVA
    assert registry.parser_for("main.py") is not parser


def test_python_parser_supports_shebang_when_no_extension() -> None:
    parser = PythonASTParser()
    assert parser.supports("scripts/deploy", content="#!/usr/bin/env python3\nprint(1)\n")
    # A non-python shebang must not match the python parser.
    assert not parser.supports("scripts/deploy", content="#!/bin/bash\necho hi\n")


def test_registry_selects_parser_by_extension() -> None:
    registry = default_parser_registry()

    assert isinstance(registry.parser_for("m.py"), PythonASTParser)
    java = registry.parser_for("M.java")
    assert isinstance(java, TreeSitterParser) and java.language == Language.JAVA
    ts = registry.parser_for("a.ts")
    assert isinstance(ts, TreeSitterParser) and ts.language == Language.TYPESCRIPT
    js = registry.parser_for("a.jsx")
    assert isinstance(js, TreeSitterParser) and js.language == Language.JAVASCRIPT


def test_registry_returns_none_for_unknown_extension() -> None:
    registry = default_parser_registry()
    assert registry.parser_for("data.bin") is None
    assert registry.parser_for("README.md") is None


def test_registry_selects_by_shebang_for_extensionless_file() -> None:
    registry = default_parser_registry()
    parser = registry.parser_for("scripts/run", content="#!/usr/bin/env python\nx = 1\n")
    assert isinstance(parser, PythonASTParser)


def test_registry_registration_order_is_priority() -> None:
    registry = ParserRegistry()
    registry.register(PythonASTParser())
    assert isinstance(registry.parser_for("m.py"), PythonASTParser)
    # Empty registry resolves nothing.
    assert ParserRegistry().parser_for("m.py") is None


def test_astparser_routes_python_through_registry() -> None:
    parser = ASTParser()
    result = parser.parse("def foo():\n    return 1\n", "m.py")
    assert result.language == Language.PYTHON
    assert any(f.name == "foo" for f in result.functions)


def test_astparser_detect_language_matches_registry() -> None:
    parser = ASTParser()
    assert parser.detect_language("m.py") == Language.PYTHON
    assert parser.detect_language("M.java") == Language.JAVA
    assert parser.detect_language("a.ts") == Language.TYPESCRIPT
    assert parser.detect_language("a.js") == Language.JAVASCRIPT
    assert parser.detect_language("data.bin") == Language.UNKNOWN


def test_astparser_unknown_language_records_parse_error() -> None:
    parser = ASTParser()
    result = parser.parse("<<binary>>", "data.bin")
    assert result.language == Language.UNKNOWN
    assert result.has_errors()


def test_astparser_accepts_custom_registry() -> None:
    registry = ParserRegistry([PythonASTParser()])
    parser = ASTParser(registry=registry)
    # Python still routes; Java no longer resolves because it is not registered.
    assert parser.parse("def a():\n    pass\n", "m.py").language == Language.PYTHON
    java = parser.parse("public class X {}", "X.java")
    assert java.language == Language.UNKNOWN
    assert java.has_errors()


def test_parse_returns_parsed_file_type() -> None:
    parser = ASTParser()
    assert isinstance(parser.parse("x = 1\n", "m.py"), ParsedFile)
