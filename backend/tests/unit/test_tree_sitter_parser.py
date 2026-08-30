"""Parser fixtures for the tree-sitter parser (Req 1.1, 1.2, 1.6, 11.2).

Each test parses a small source file with known symbols and asserts the
extracted ``ParsedFile`` matches expectations, including line/column-accurate
spans. One fixture per supported non-Python language.
"""

import pytest

from cortex.pipeline.infrastructure.ast_parser import Language, ParsedFile
from cortex.pipeline.infrastructure.tree_sitter_parser import (
    TreeSitterParser,
    tree_sitter_available,
    tree_sitter_parsers,
)

pytestmark = pytest.mark.skipif(
    not tree_sitter_available(),
    reason="tree-sitter grammars are not installed in this environment",
)


def _parser_for(language: Language) -> TreeSitterParser:
    for p in tree_sitter_parsers():
        if p.language == language:
            return p
    raise AssertionError(f"no tree-sitter parser for {language}")


def _find_class(result: ParsedFile, name: str):
    return next(c for c in result.classes if c.name == name)


def _find_fn(result: ParsedFile, name: str, parent_class: str | None = "__any__"):
    for f in result.all_functions():
        if f.name != name:
            continue
        if parent_class == "__any__" or f.parent_class == parent_class:
            return f
    raise StopIteration(f"function {name} (parent={parent_class}) not found")


# ── JavaScript ────────────────────────────────────────────────────────────────
JS_SRC = """import { readFile } from 'fs';
import helper from './helper';

class Service extends Base {
  async fetch(id, opts) {
    if (id) {
      return get(id);
    }
    return null;
  }
}

function topLevel(a) {
  return a + 1;
}
"""


def test_javascript_fixture() -> None:
    result = _parser_for(Language.JAVASCRIPT).parse(JS_SRC, "service.js")
    assert result.language == Language.JAVASCRIPT
    assert not result.has_errors()

    svc = _find_class(result, "Service")
    assert svc.base_classes == ["Base"]
    assert svc.line_start == 4  # 1-indexed, accurate span (Req 1.6)

    fetch = _find_fn(result, "fetch")
    assert fetch.is_method is True
    assert fetch.parent_class == "Service"
    assert fetch.parameters == ["id", "opts"]
    assert fetch.is_async is True
    assert "get" in fetch.calls
    assert fetch.cyclomatic_complexity == 2  # one `if`

    top = _find_fn(result, "topLevel")
    assert top.parameters == ["a"]
    assert top.is_method is False

    modules = {i.module for i in result.imports}
    assert "fs" in modules
    assert any(i.is_relative for i in result.imports)


# ── TypeScript ────────────────────────────────────────────────────────────────
TS_SRC = """import type { Shape } from './shape';

interface Drawable {
  draw(): void;
}

class Circle implements Drawable {
  @observable
  draw(scale: number): void {
    if (scale > 0) {
      render(scale);
    }
  }
}

function identity<T>(x: T): T {
  return x;
}
"""


def test_typescript_fixture() -> None:
    result = _parser_for(Language.TYPESCRIPT).parse(TS_SRC, "circle.ts")
    assert result.language == Language.TYPESCRIPT
    assert not result.has_errors()

    drawable = _find_class(result, "Drawable")
    assert drawable.is_interface is True

    circle = _find_class(result, "Circle")
    assert circle.base_classes == ["Drawable"]

    draw = _find_fn(result, "draw", parent_class="Circle")
    assert draw.parent_class == "Circle"
    assert draw.parameters == ["scale"]
    assert "observable" in draw.decorators
    assert draw.return_type is not None

    ident = _find_fn(result, "identity")
    assert ident.parameters == ["x"]


# ── Java ──────────────────────────────────────────────────────────────────────
JAVA_SRC = """package com.example.app;

import java.util.List;

public interface Shape {
    double area();
}

@Entity
public class Circle implements Shape {
    @Override
    public double area(int factor) {
        if (factor > 0) {
            return compute(factor);
        }
        return 0.0;
    }
}

enum Color { RED, GREEN, BLUE }
"""


def test_java_fixture() -> None:
    result = _parser_for(Language.JAVA).parse(JAVA_SRC, "Circle.java")
    assert result.language == Language.JAVA
    assert not result.has_errors()

    shape = _find_class(result, "Shape")
    assert shape.is_interface is True

    circle = _find_class(result, "Circle")
    assert circle.base_classes == ["Shape"]
    assert "Entity" in circle.decorators

    area = _find_fn(result, "area", parent_class="Circle")
    assert area.parent_class == "Circle"
    assert area.parameters == ["factor"]
    assert "Override" in area.decorators
    assert "compute" in area.calls
    assert area.cyclomatic_complexity == 2

    color = _find_class(result, "Color")
    assert color.is_enum is True

    imp = next(i for i in result.imports if "List" in i.names)
    assert imp.module == "java.util"


# ── Go ────────────────────────────────────────────────────────────────────────
GO_SRC = """package main

import "fmt"

type Shape interface {
    Area() float64
}

type Circle struct {
    r float64
}

func (c Circle) Area() float64 {
    return 3.14 * c.r
}

func main() {
    fmt.Println("hello")
}
"""


def test_go_fixture() -> None:
    result = _parser_for(Language.GO).parse(GO_SRC, "main.go")
    assert result.language == Language.GO
    assert not result.has_errors()

    shape = _find_class(result, "Shape")
    assert shape.is_interface is True

    circle = _find_class(result, "Circle")
    assert circle.is_interface is False

    main = _find_fn(result, "main")
    assert "Println" in main.calls

    assert any(i.module == "fmt" for i in result.imports)


# ── Rust ──────────────────────────────────────────────────────────────────────
RUST_SRC = """use std::collections::HashMap;

trait Shape {
    fn area(&self) -> f64;
}

struct Circle {
    r: f64,
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        3.14
    }
}

fn main() {
    let _ = compute();
}
"""


def test_rust_fixture() -> None:
    result = _parser_for(Language.RUST).parse(RUST_SRC, "lib.rs")
    assert result.language == Language.RUST
    assert not result.has_errors()

    shape = _find_class(result, "Shape")
    assert shape.is_interface is True  # traits map to interfaces

    main = _find_fn(result, "main")
    assert "compute" in main.calls
    assert any(i.module == "std" for i in result.imports)


# ── C# ────────────────────────────────────────────────────────────────────────
CSHARP_SRC = """using System;

namespace App
{
    interface IShape
    {
        double Area();
    }

    [Serializable]
    public class Circle : IShape
    {
        public double Area(int factor)
        {
            if (factor > 0)
            {
                return 3.14;
            }
            return 0.0;
        }
    }

    enum Color { Red, Green }
}
"""


def test_csharp_fixture() -> None:
    result = _parser_for(Language.CSHARP).parse(CSHARP_SRC, "Circle.cs")
    assert result.language == Language.CSHARP
    assert not result.has_errors()

    ishape = _find_class(result, "IShape")
    assert ishape.is_interface is True

    circle = _find_class(result, "Circle")
    assert circle.base_classes == ["IShape"]
    assert "Serializable" in circle.decorators

    area = _find_fn(result, "Area", parent_class="Circle")
    assert area.parent_class == "Circle"
    assert area.parameters == ["factor"]
    assert area.cyclomatic_complexity == 2

    color = _find_class(result, "Color")
    assert color.is_enum is True


# ── Ruby ──────────────────────────────────────────────────────────────────────
RUBY_SRC = """module Billing
  class Invoice < Record
    def total(items, tax)
      subtotal = sum(items)
      subtotal + tax if subtotal
    end
  end
end

def standalone(x)
  x
end
"""


def test_ruby_fixture() -> None:
    result = _parser_for(Language.RUBY).parse(RUBY_SRC, "invoice.rb")
    assert result.language == Language.RUBY
    assert not result.has_errors()

    invoice = _find_class(result, "Invoice")
    assert invoice.base_classes == ["Record"]

    total = _find_fn(result, "total")
    assert total.parent_class == "Invoice"
    assert total.parameters == ["items", "tax"]
    assert total.cyclomatic_complexity == 2  # trailing `if`

    standalone = _find_fn(result, "standalone")
    assert standalone.is_method is False


# ── Cross-cutting guarantees ──────────────────────────────────────────────────
def test_line_spans_are_one_indexed_and_within_file() -> None:
    """Every extracted symbol has a 1-indexed span within the file (Req 1.6)."""
    result = _parser_for(Language.JAVA).parse(JAVA_SRC, "Circle.java")
    total_lines = len(JAVA_SRC.splitlines())
    for cls in result.classes:
        assert 1 <= cls.line_start <= cls.line_end <= total_lines
    for fn in result.all_functions():
        assert 1 <= fn.line_start <= fn.line_end <= total_lines


def test_parser_never_raises_on_broken_source() -> None:
    """Malformed input yields a ParsedFile, never an exception (contract)."""
    result = _parser_for(Language.JAVA).parse("public class {{{ broken", "Broken.java")
    assert isinstance(result, ParsedFile)
    assert result.language == Language.JAVA


def test_output_is_deterministic() -> None:
    """Identical input yields identical structure across runs (Req 11.1)."""
    p = _parser_for(Language.GO)
    a = p.parse(GO_SRC, "main.go")
    b = p.parse(GO_SRC, "main.go")
    assert [c.name for c in a.classes] == [c.name for c in b.classes]
    assert [f.name for f in a.all_functions()] == [f.name for f in b.all_functions()]
