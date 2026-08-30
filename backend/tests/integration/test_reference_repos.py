"""Reference-repository regression suite (Task 19).

Assembles one small reference repository per supported language, then runs the
real engine pipeline over each one:

    ParserRegistry (Tasks 1-2) → GraphBuilder (Task 4) → CortexReasoner
    → Answer Producers (Tasks 7-8)

and asserts a **deterministic snapshot** of the stable, meaningful facts plus
that the key producers emit valid ``CortexAnswer`` objects. These snapshots are
the regression baseline: when engine logic changes, this suite catches the drift
(Req 11.2, 11.3). The reference set covers every supported language — Python,
JavaScript, TypeScript, Java, Go, Rust, C#, Ruby (Req 11.4).

Design notes (see design.md "Testing Strategy"):
- Fixtures are kept SMALL but exercise each language's key constructs (a
  class/struct, a function, an import, and where applicable an interface).
- Assertions are ROBUST, not brittle: we snapshot detected languages, counts of
  files/classes/functions/modules, presence of key symbol names, and that every
  producer emits a valid answer whose claims all carry evidence with sane
  epistemic tags. We deliberately avoid snapshotting volatile things like the
  generated UUID node ids; key nodes are addressed by type + label instead
  (mirroring the determinism approach).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from cortex.graph.domain.entities import GraphNode, NodeType
from cortex.pipeline.infrastructure.ast_parser import ASTParser, Language
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
from cortex.pipeline.infrastructure.tree_sitter_parser import tree_sitter_available
from cortex.reasoning.application.producers import (
    ApiSpecProducer,
    ArchitectureOverviewProducer,
    InterviewPrepProducer,
    LearningPathProducer,
    ModuleBreakdownProducer,
)
from cortex.reasoning.domain.answer import (
    CortexAnswer,
    Epistemic,
    assert_valid_answer,
    validate_answer,
)

# The non-Python reference repos require tree-sitter grammars. Python has its
# own stdlib-``ast`` parser and always runs; the parametrized cases below skip
# individually when tree-sitter is unavailable so Python coverage is never lost.
_TS_AVAILABLE = tree_sitter_available()


# ═══════════════════════════════════════════════════════════════════════════════
# Reference repositories — small, inline string fixtures, one per language.
#
# Each repo has a couple of files under a package/subdirectory so the reasoner
# detects at least one module, and each exercises the language's key constructs:
# an import, a class/struct/interface, and a function/method.
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ReferenceRepo:
    """A named, deterministic reference repository plus its expected snapshot."""

    name: str
    repo_url: str
    files: tuple[tuple[str, str], ...]  # (path, content)
    expected_language: str
    # Robust structural expectations (not brittle exact-UUID matches).
    min_files: int
    min_classes: int
    min_functions: int
    min_modules: int
    expected_class_labels: frozenset[str]
    expected_function_labels: frozenset[str]
    expects_interface: bool


# ── Python ────────────────────────────────────────────────────────────────────
_PY_MODELS = """from dataclasses import dataclass


@dataclass
class User:
    \"\"\"A user domain model.\"\"\"

    id: str
    name: str
"""

_PY_SERVICE = """from app.models import User


class UserService:
    \"\"\"Business logic for users.\"\"\"

    def get_user(self, user_id):
        return self._load(user_id)

    def _load(self, user_id):
        if user_id:
            return User(id=user_id, name="x")
        return None


def build_service():
    return UserService()
"""

PYTHON_REPO = ReferenceRepo(
    name="py-app",
    repo_url="https://github.com/example/py-app",
    files=(
        ("app/models.py", _PY_MODELS),
        ("app/service.py", _PY_SERVICE),
    ),
    expected_language="python",
    min_files=2,
    min_classes=2,
    min_functions=1,
    min_modules=1,
    expected_class_labels=frozenset({"User", "UserService"}),
    expected_function_labels=frozenset({"build_service"}),
    expects_interface=False,
)


# ── JavaScript ──────────────────────────────────────────────────────────────
_JS_HELPER = """export function double(x) {
  return x * 2;
}
"""

_JS_SERVICE = """import { double } from './helper';

class Service extends Base {
  async fetch(id, opts) {
    if (id) {
      return double(id);
    }
    return null;
  }
}

function topLevel(a) {
  return a + 1;
}
"""

JAVASCRIPT_REPO = ReferenceRepo(
    name="js-app",
    repo_url="https://github.com/example/js-app",
    files=(
        ("src/helper.js", _JS_HELPER),
        ("src/service.js", _JS_SERVICE),
    ),
    expected_language="javascript",
    min_files=2,
    min_classes=1,
    min_functions=1,
    min_modules=1,
    expected_class_labels=frozenset({"Service"}),
    expected_function_labels=frozenset({"topLevel", "double"}),
    expects_interface=False,
)


# ── TypeScript ────────────────────────────────────────────────────────────────
_TS_SHAPE = """export interface Shape {
  area(): number;
}
"""

_TS_CIRCLE = """import { Shape } from './shape';

class Circle implements Shape {
  area(scale: number): number {
    if (scale > 0) {
      return 3.14 * scale;
    }
    return 0;
  }
}

function identity<T>(x: T): T {
  return x;
}
"""

TYPESCRIPT_REPO = ReferenceRepo(
    name="ts-app",
    repo_url="https://github.com/example/ts-app",
    files=(
        ("src/shape.ts", _TS_SHAPE),
        ("src/circle.ts", _TS_CIRCLE),
    ),
    expected_language="typescript",
    min_files=2,
    min_classes=1,
    min_functions=1,
    min_modules=1,
    expected_class_labels=frozenset({"Circle"}),
    expected_function_labels=frozenset({"identity"}),
    expects_interface=True,
)


# ── Java ──────────────────────────────────────────────────────────────────────
_JAVA_SHAPE = """package com.example.app;

public interface Shape {
    double area();
}
"""

_JAVA_CIRCLE = """package com.example.app;

import java.util.List;

public class Circle implements Shape {
    public double area(int factor) {
        if (factor > 0) {
            return compute(factor);
        }
        return 0.0;
    }

    private double compute(int factor) {
        return 3.14 * factor;
    }
}
"""

JAVA_REPO = ReferenceRepo(
    name="java-app",
    repo_url="https://github.com/example/java-app",
    files=(
        ("src/com/example/app/Shape.java", _JAVA_SHAPE),
        ("src/com/example/app/Circle.java", _JAVA_CIRCLE),
    ),
    expected_language="java",
    min_files=2,
    min_classes=1,
    min_functions=1,
    min_modules=1,
    expected_class_labels=frozenset({"Circle"}),
    expected_function_labels=frozenset({"area"}),
    expects_interface=True,
)


# ── Go ────────────────────────────────────────────────────────────────────────
_GO_SHAPE = """package geometry

type Shape interface {
    Area() float64
}
"""

_GO_CIRCLE = """package geometry

import "fmt"

type Circle struct {
    r float64
}

func (c Circle) Area() float64 {
    return 3.14 * c.r
}

func Describe(c Circle) {
    fmt.Println(c.Area())
}
"""

GO_REPO = ReferenceRepo(
    name="go-svc",
    repo_url="https://github.com/example/go-svc",
    files=(
        ("geometry/shape.go", _GO_SHAPE),
        ("geometry/circle.go", _GO_CIRCLE),
    ),
    expected_language="go",
    min_files=2,
    min_classes=1,
    min_functions=1,
    min_modules=1,
    expected_class_labels=frozenset({"Circle"}),
    expected_function_labels=frozenset({"Describe"}),
    expects_interface=True,
)


# ── Rust ──────────────────────────────────────────────────────────────────────
_RUST_SHAPE = """pub trait Shape {
    fn area(&self) -> f64;
}
"""

_RUST_CIRCLE = """use std::f64::consts::PI;

pub struct Circle {
    r: f64,
}

impl Shape for Circle {
    fn area(&self) -> f64 {
        PI * self.r
    }
}

fn describe() {
    let _ = compute();
}
"""

RUST_REPO = ReferenceRepo(
    name="rust-crate",
    repo_url="https://github.com/example/rust-crate",
    files=(
        ("src/shape.rs", _RUST_SHAPE),
        ("src/circle.rs", _RUST_CIRCLE),
    ),
    expected_language="rust",
    min_files=2,
    min_classes=1,
    min_functions=1,
    min_modules=1,
    expected_class_labels=frozenset({"Circle"}),
    expected_function_labels=frozenset({"describe"}),
    expects_interface=True,  # traits map to interfaces
)


# ── C# ────────────────────────────────────────────────────────────────────────
_CS_SHAPE = """namespace App
{
    interface IShape
    {
        double Area();
    }
}
"""

_CS_CIRCLE = """using System;

namespace App
{
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
}
"""

CSHARP_REPO = ReferenceRepo(
    name="csharp-app",
    repo_url="https://github.com/example/csharp-app",
    files=(
        ("src/Shape.cs", _CS_SHAPE),
        ("src/Circle.cs", _CS_CIRCLE),
    ),
    expected_language="csharp",
    min_files=2,
    min_classes=1,
    min_functions=1,
    min_modules=1,
    expected_class_labels=frozenset({"Circle"}),
    expected_function_labels=frozenset({"Area"}),
    expects_interface=True,
)


# ── Ruby ──────────────────────────────────────────────────────────────────────
_RUBY_RECORD = """module Billing
  class Record
    def persisted?
      true
    end
  end
end
"""

_RUBY_INVOICE = """require_relative 'record'

module Billing
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

RUBY_REPO = ReferenceRepo(
    name="ruby-app",
    repo_url="https://github.com/example/ruby-app",
    files=(
        ("lib/record.rb", _RUBY_RECORD),
        ("lib/invoice.rb", _RUBY_INVOICE),
    ),
    expected_language="ruby",
    min_files=2,
    min_classes=2,
    min_functions=1,
    min_modules=1,
    expected_class_labels=frozenset({"Invoice", "Record"}),
    expected_function_labels=frozenset({"standalone"}),
    expects_interface=False,
)


# One repo per supported language (Req 11.4).
REFERENCE_REPOS: dict[str, ReferenceRepo] = {
    "python": PYTHON_REPO,
    "javascript": JAVASCRIPT_REPO,
    "typescript": TYPESCRIPT_REPO,
    "java": JAVA_REPO,
    "go": GO_REPO,
    "rust": RUST_REPO,
    "csharp": CSHARP_REPO,
    "ruby": RUBY_REPO,
}

# Languages parsed via tree-sitter (everything except Python).
_TS_LANGUAGES = frozenset(REFERENCE_REPOS) - {"python"}


# ═══════════════════════════════════════════════════════════════════════════════
# Engine driver — the real pipeline, no mocks.
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AnalyzedRepo:
    """The materialized understanding + graph for a reference repo."""

    repo: ReferenceRepo
    nodes: list[GraphNode]
    edges: list
    understanding: object


def _analyze(repo: ReferenceRepo) -> AnalyzedRepo:
    """Run the real pipeline: parse → graph → understand."""
    from cortex.reasoning.application.reasoner import CortexReasoner

    parser = ASTParser()
    parsed = [parser.parse(content, path) for path, content in repo.files]

    # No file should have failed to parse — a parse failure here is a real bug
    # in the language grammar/mapping, not something to mask (Req 1.4).
    for pf in parsed:
        assert not pf.has_errors(), (
            f"{repo.name}: parse error(s) in {pf.path}: {pf.parse_errors}"
        )

    builder = GraphBuilder(job_id=f"ref-{repo.name}", repo_url=repo.repo_url)
    graph = builder.build(parsed)

    reasoner = CortexReasoner()
    understanding = reasoner.understand(
        job_id=f"ref-{repo.name}",
        repo_url=repo.repo_url,
        nodes=graph.nodes,
        edges=graph.edges,
    )
    return AnalyzedRepo(
        repo=repo,
        nodes=graph.nodes,
        edges=graph.edges,
        understanding=understanding,
    )


def _labels_of(nodes: list[GraphNode], *types: NodeType) -> set[str]:
    wanted = set(types)
    return {n.label for n in nodes if n.node_type in wanted}


def _param(lang: str) -> pytest.param:
    """Wrap a language id, skipping tree-sitter langs when unavailable."""
    if lang != "python" and not _TS_AVAILABLE:
        return pytest.param(
            lang,
            marks=pytest.mark.skip(reason="tree-sitter grammars not installed"),
        )
    return pytest.param(lang)


_ALL_LANG_PARAMS = [_param(lang) for lang in REFERENCE_REPOS]


# ═══════════════════════════════════════════════════════════════════════════════
# Snapshot regression: understanding facts per language (Req 11.2, 11.3, 11.4).
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("lang", _ALL_LANG_PARAMS)
def test_reference_repo_understanding_snapshot(lang: str) -> None:
    """Snapshot the stable understanding facts for each reference repo."""
    repo = REFERENCE_REPOS[lang]
    analyzed = _analyze(repo)
    u = analyzed.understanding

    # Detected language(s): the repo's language is present and dominant.
    assert repo.expected_language in u.languages, (
        f"{repo.name}: expected {repo.expected_language} in {u.languages}"
    )

    # Structural counts meet the known-good floor (robust, not exact).
    assert u.total_files >= repo.min_files, (
        f"{repo.name}: files {u.total_files} < {repo.min_files}"
    )
    assert u.total_classes >= repo.min_classes, (
        f"{repo.name}: classes {u.total_classes} < {repo.min_classes}"
    )
    assert u.total_functions >= repo.min_functions, (
        f"{repo.name}: functions {u.total_functions} < {repo.min_functions}"
    )
    assert u.total_modules >= repo.min_modules, (
        f"{repo.name}: modules {u.total_modules} < {repo.min_modules}"
    )

    # Key symbol names are present in the graph (keyed by type+label, not UUID).
    class_labels = _labels_of(
        analyzed.nodes, NodeType.CLASS, NodeType.INTERFACE, NodeType.ENUM
    )
    assert repo.expected_class_labels <= class_labels, (
        f"{repo.name}: missing classes {repo.expected_class_labels - class_labels}"
    )

    fn_labels = _labels_of(
        analyzed.nodes, NodeType.FUNCTION, NodeType.METHOD, NodeType.ENDPOINT
    )
    assert repo.expected_function_labels <= fn_labels, (
        f"{repo.name}: missing functions {repo.expected_function_labels - fn_labels}"
    )


@pytest.mark.parametrize("lang", _ALL_LANG_PARAMS)
def test_reference_repo_detects_interface_where_applicable(lang: str) -> None:
    """Languages with interfaces/traits produce at least one INTERFACE node."""
    repo = REFERENCE_REPOS[lang]
    analyzed = _analyze(repo)
    interface_nodes = [
        n for n in analyzed.nodes if n.node_type == NodeType.INTERFACE
    ]
    if repo.expects_interface:
        assert interface_nodes, f"{repo.name}: expected an interface node"
    # For languages without an interface construct we make no positive claim —
    # absence is fine, presence would also be acceptable, so no assertion.


# ═══════════════════════════════════════════════════════════════════════════════
# Producer regression: key producers emit valid CortexAnswers (Req 11.2, 11.3).
# ═══════════════════════════════════════════════════════════════════════════════

_KEY_PRODUCERS = (
    ArchitectureOverviewProducer,
    ModuleBreakdownProducer,
    ApiSpecProducer,
    LearningPathProducer,
    InterviewPrepProducer,
)


def _produce_all(analyzed: AnalyzedRepo) -> list[CortexAnswer]:
    answers: list[CortexAnswer] = []
    for producer_cls in _KEY_PRODUCERS:
        producer = producer_cls(
            analyzed.understanding,
            nodes=analyzed.nodes,
            edges=analyzed.edges,
        )
        answers.append(producer.produce())
    return answers


@pytest.mark.parametrize("lang", _ALL_LANG_PARAMS)
def test_reference_repo_producers_emit_valid_answers(lang: str) -> None:
    """Every key producer yields a valid CortexAnswer for every language."""
    repo = REFERENCE_REPOS[lang]
    analyzed = _analyze(repo)

    for answer in _produce_all(analyzed):
        # Contract validity: no violations, and validation raises nothing.
        assert validate_answer(answer) == [], (
            f"{repo.name}/{answer.intent}: {validate_answer(answer)}"
        )
        assert_valid_answer(answer)

        # Every claim carries at least one Evidence (Req 4.3).
        claims = answer.iter_claims()
        assert claims, f"{repo.name}/{answer.intent}: produced no claims"
        assert all(c.evidence for c in claims), (
            f"{repo.name}/{answer.intent}: a claim lacks evidence"
        )

        # Epistemic tags are sane: only the three known kinds appear.
        assert all(
            c.epistemic in (Epistemic.FACT, Epistemic.INFERENCE, Epistemic.PREDICTION)
            for c in claims
        )

        # Confidence stays within bounds.
        assert 0.0 <= answer.confidence <= 1.0


@pytest.mark.parametrize("lang", _ALL_LANG_PARAMS)
def test_reference_repo_architecture_answer_names_the_repo(lang: str) -> None:
    """The architecture overview references the actual repository by name."""
    repo = REFERENCE_REPOS[lang]
    analyzed = _analyze(repo)
    answer = ArchitectureOverviewProducer(
        analyzed.understanding, nodes=analyzed.nodes, edges=analyzed.edges
    ).produce()
    assert answer.intent == "architecture_overview"
    assert repo.name in answer.title


# ═══════════════════════════════════════════════════════════════════════════════
# Determinism: the reference baseline is stable across runs (Req 11.1, 11.3).
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("lang", _ALL_LANG_PARAMS)
def test_reference_repo_understanding_is_deterministic(lang: str) -> None:
    """Two independent analyses of the same repo agree on the stable facts."""
    repo = REFERENCE_REPOS[lang]
    a = _analyze(repo)
    b = _analyze(repo)

    ua, ub = a.understanding, b.understanding
    assert ua.languages == ub.languages
    assert ua.total_files == ub.total_files
    assert ua.total_classes == ub.total_classes
    assert ua.total_functions == ub.total_functions
    assert ua.total_modules == ub.total_modules

    # Node identity keyed by type+label (never volatile UUIDs) is stable.
    def keyed(nodes: list[GraphNode]) -> set[tuple[str, str]]:
        return {(n.node_type.value, n.label) for n in nodes}

    assert keyed(a.nodes) == keyed(b.nodes)


@pytest.mark.parametrize("lang", _ALL_LANG_PARAMS)
def test_reference_repo_producer_output_is_deterministic(lang: str) -> None:
    """Producer claim text is identical across repeated runs."""
    repo = REFERENCE_REPOS[lang]
    a = _analyze(repo)
    b = _analyze(repo)

    for producer_cls in _KEY_PRODUCERS:
        ans_a = producer_cls(a.understanding, nodes=a.nodes, edges=a.edges).produce()
        ans_b = producer_cls(b.understanding, nodes=b.nodes, edges=b.edges).produce()
        assert [c.text for c in ans_a.iter_claims()] == [
            c.text for c in ans_b.iter_claims()
        ], f"{repo.name}/{ans_a.intent}: non-deterministic claim text"


# ═══════════════════════════════════════════════════════════════════════════════
# Coverage guard: the suite genuinely spans every supported language (Req 11.4).
# ═══════════════════════════════════════════════════════════════════════════════


def test_reference_set_covers_every_supported_language() -> None:
    """The reference set includes at least one repo per supported language."""
    supported = {
        Language.PYTHON,
        Language.JAVASCRIPT,
        Language.TYPESCRIPT,
        Language.JAVA,
        Language.GO,
        Language.RUST,
        Language.CSHARP,
        Language.RUBY,
    }
    covered = {Language(repo.expected_language) for repo in REFERENCE_REPOS.values()}
    assert supported <= covered, f"missing reference repos for {supported - covered}"
