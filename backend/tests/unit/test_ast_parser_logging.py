from cortex.pipeline.infrastructure.ast_parser import ASTParser


def test_java_ast_parser_logging_does_not_duplicate_path_kwarg() -> None:
    parser = ASTParser()
    content = """
public class Example {
    public void run() {}
}
"""

    result = parser.parse(content, "Example.java")

    assert result.path == "Example.java"
    assert result.language.value == "java"
    # tree-sitter attributes `run` to its enclosing class as a method; the point
    # of this test is that logging with **summary() does not raise on the `path`
    # kwarg, and that the symbol is extracted.
    assert any(f.name == "run" for f in result.all_functions())
