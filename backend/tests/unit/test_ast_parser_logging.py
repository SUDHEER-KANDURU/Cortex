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
    assert result.functions[0].name == "run"
