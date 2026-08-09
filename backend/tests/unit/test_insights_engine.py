"""Unit tests for the InsightsEngine.

Covers:
  - file classification (source vs test vs vendor vs generated)
  - language rules (Python vs Java naming)
  - complexity detection (god functions, large classes, params)
  - coupling detection (fan-out, fan-in, deduplication)
  - documentation detection (uses has_docstring property)
  - architecture detection (circular deps, abstraction, modularisation)
  - size detection (large files)
  - naming (language-aware, no false positives on idiomatic names)
  - scoring model (normalisation, not raw count)
  - edge cases (empty repo, single file, test-only repo)
"""

from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from cortex.graph.domain.entities import GraphNode, GraphEdge, NodeType, RelationshipType
from cortex.insights.application.engine import InsightsEngine
from cortex.insights.application.file_classifier import FileClassifier, FileCategory
from cortex.insights.application.language_rules import get_rules, PythonRules, JavaRules
from cortex.insights.domain.entities import IssueSeverity, IssueCategory

# ── Helpers ───────────────────────────────────────────────────────────────────

_NOW = datetime.now(timezone.utc)
_JOB = "test-job-001"


def _node(id: str, label: str, ntype: NodeType, props: dict) -> GraphNode:
    return GraphNode(id=id, label=label, node_type=ntype, job_id=_JOB,
                     properties=props, created_at=_NOW)

def _edge(sid: str, tid: str, rel: RelationshipType) -> GraphEdge:
    return GraphEdge(id=f"{sid}-{tid}", source_id=sid, target_id=tid,
                     relationship=rel, job_id=_JOB, created_at=_NOW)

def _file(id: str, label: str, path: str, lines: int = 50, lang: str = "python",
          classes: int = 0, functions: int = 0) -> GraphNode:
    return _node(id, label, NodeType.FILE, {
        "path": path, "lines": lines, "language": lang,
        "classes": classes, "functions": functions,
    })

def _fn(id: str, label: str, file_path: str, lines: int = 10,
        params: int = 0, is_method: bool = False, has_doc: bool = False,
        is_async: bool = False) -> GraphNode:
    return _node(id, label, NodeType.FUNCTION, {
        "file": file_path, "line": 1, "lines": lines,
        "param_count": params, "is_method": is_method,
        "has_docstring": has_doc, "is_async": is_async,
    })

def _cls(id: str, label: str, file_path: str, methods: int = 2,
         lines: int = 40, has_doc: bool = False, is_abstract: bool = False,
         bases: str = "") -> GraphNode:
    return _node(id, label, NodeType.CLASS, {
        "file": file_path, "line": 1, "lines": lines,
        "methods": methods, "has_docstring": has_doc,
        "is_abstract": is_abstract, "base_classes": bases,
    })

engine = InsightsEngine()


# ══════════════════════════════════════════════════════════════════════════════
# FILE CLASSIFIER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFileClassifier:
    fc = FileClassifier()

    def test_source_python(self):
        assert self.fc.classify("src/cortex/engine.py").category == FileCategory.SOURCE

    def test_source_typescript(self):
        assert self.fc.classify("frontend/src/components/Button.tsx").category == FileCategory.SOURCE

    def test_test_directory(self):
        assert self.fc.classify("tests/unit/test_engine.py").category == FileCategory.TEST

    def test_test_filename_prefix(self):
        assert self.fc.classify("src/test_something.py").category == FileCategory.TEST

    def test_test_spec_suffix(self):
        assert self.fc.classify("src/Button.spec.ts").category == FileCategory.TEST

    def test_vendor_node_modules(self):
        assert self.fc.classify("node_modules/lodash/index.js").category == FileCategory.VENDOR

    def test_vendor_venv(self):
        assert self.fc.classify(".venv/lib/python3.12/requests/__init__.py").category == FileCategory.VENDOR

    def test_build_pycache(self):
        assert self.fc.classify("src/__pycache__/engine.cpython-312.pyc").category == FileCategory.BUILD

    def test_build_dist(self):
        assert self.fc.classify("dist/index.js").category == FileCategory.BUILD

    def test_config_pyproject(self):
        assert self.fc.classify("pyproject.toml").category == FileCategory.CONFIG

    def test_config_package_json(self):
        assert self.fc.classify("package.json").category == FileCategory.CONFIG

    def test_docs_readme(self):
        assert self.fc.classify("README.md").category == FileCategory.DOCS

    def test_migration_alembic(self):
        assert self.fc.classify("alembic/versions/20230101_add_users.py").category == FileCategory.MIGRATION

    def test_generated_pb2(self):
        assert self.fc.classify("src/proto/schema_pb2.py").category == FileCategory.GENERATED

    def test_asset_png(self):
        assert self.fc.classify("public/logo.png").category == FileCategory.ASSET

    def test_conftest_is_test(self):
        assert self.fc.classify("tests/conftest.py").category == FileCategory.TEST


# ══════════════════════════════════════════════════════════════════════════════
# LANGUAGE RULES TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestLanguageRules:

    # ── Python ────────────────────────────────────────────────────────────────
    def test_python_snake_case_ok(self):
        assert get_rules("python").naming_ok("get_user", "function") is True

    def test_python_camel_bad(self):
        assert get_rules("python").naming_ok("getUser", "function") is False

    def test_python_pascal_class_ok(self):
        assert get_rules("python").naming_ok("UserService", "class") is True

    def test_python_snake_class_bad(self):
        assert get_rules("python").naming_ok("user_service", "class") is False

    def test_python_dunder_ok(self):
        assert get_rules("python").naming_ok("__init__", "method") is True

    def test_python_private_ok(self):
        assert get_rules("python").naming_ok("_internal", "function") is True

    def test_python_idiomatic_i_ok(self):
        assert get_rules("python").is_idiomatic_short("i") is True

    def test_python_short_fn_not_idiomatic(self):
        assert get_rules("python").is_idiomatic_short("ab") is False

    # ── Java ──────────────────────────────────────────────────────────────────
    def test_java_camel_ok(self):
        assert get_rules("java").naming_ok("getUserById", "method") is True

    def test_java_snake_bad(self):
        assert get_rules("java").naming_ok("get_user_by_id", "method") is False

    def test_java_pascal_class_ok(self):
        assert get_rules("java").naming_ok("UserRepository", "class") is True

    def test_java_no_python_rules_applied(self):
        # camelCase should be VALID in Java — not flagged
        rules = get_rules("java")
        assert rules.naming_ok("processData", "method") is True
        # snake_case should be INVALID in Java
        assert rules.naming_ok("process_data", "method") is False

    # ── TypeScript ────────────────────────────────────────────────────────────
    def test_typescript_camel_ok(self):
        assert get_rules("typescript").naming_ok("handleClick", "function") is True

    def test_typescript_pascal_component_ok(self):
        assert get_rules("typescript").naming_ok("UserCard", "class") is True

    # ── Unknown ───────────────────────────────────────────────────────────────
    def test_unknown_no_violations(self):
        rules = get_rules("cobol")
        assert rules.naming_ok("SOME-WEIRD-NAME", "function") is True
        assert rules.is_supported() is False


# ══════════════════════════════════════════════════════════════════════════════
# FULL ENGINE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def _minimal_repo():
    """Build a minimal clean Python repo with no issues."""
    f1 = _file("f1", "service.py", "src/service.py", lines=80, lang="python", functions=3)
    fn1 = _fn("fn1", "create_user", "src/service.py", lines=15, params=2, has_doc=True)
    fn2 = _fn("fn2", "delete_user", "src/service.py", lines=12, params=1, has_doc=True)
    fn3 = _fn("fn3", "get_user",    "src/service.py", lines=10, params=1, has_doc=True)
    cls1 = _cls("cls1", "UserService", "src/service.py", methods=3, lines=80, has_doc=True)

    repo = _node("repo1", "myrepo", NodeType.REPOSITORY, {"url": "https://github.com/x/myrepo"})
    mod  = _node("mod1", "src/", NodeType.MODULE, {"path": "src"})

    edges = [
        _edge("repo1", "mod1",  RelationshipType.CONTAINS),
        _edge("mod1",  "f1",    RelationshipType.CONTAINS),
        _edge("f1",    "cls1",  RelationshipType.CONTAINS),
        _edge("cls1",  "fn1",   RelationshipType.CONTAINS),
        _edge("cls1",  "fn2",   RelationshipType.CONTAINS),
        _edge("cls1",  "fn3",   RelationshipType.CONTAINS),
    ]
    nodes = [repo, mod, f1, fn1, fn2, fn3, cls1]
    return nodes, edges


class TestEngineCleanRepo:
    def test_no_issues_on_clean_repo(self):
        nodes, edges = _minimal_repo()
        report = engine.compute(_JOB, "https://github.com/x/myrepo", nodes, edges)
        critical_and_high = [i for i in report.issues
                             if i.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH)]
        assert len(critical_and_high) == 0, f"Unexpected issues: {[(i.title, i.severity) for i in critical_and_high]}"

    def test_clean_repo_scores_above_70(self):
        nodes, edges = _minimal_repo()
        report = engine.compute(_JOB, "https://github.com/x/myrepo", nodes, edges)
        assert report.overall_score >= 70, f"Score {report.overall_score} too low for clean repo"

    def test_report_has_all_dimensions(self):
        nodes, edges = _minimal_repo()
        report = engine.compute(_JOB, "https://github.com/x/myrepo", nodes, edges)
        names = [d.name for d in report.dimensions]
        assert "Complexity" in names
        assert "Coupling"   in names
        assert "Size"       in names
        assert "Architecture" in names
        assert "Documentation" in names
        assert "Naming"     in names

    def test_test_files_excluded_from_source_count(self):
        nodes, edges = _minimal_repo()
        # Add a test file
        tf = _file("tf1", "test_service.py", "tests/test_service.py", lines=200)
        tfn = _fn("tfn1", "test_create_user", "tests/test_service.py", lines=20)
        nodes.extend([tf, tfn])
        edges.append(_edge("tf1", "tfn1", RelationshipType.CONTAINS))
        report = engine.compute(_JOB, "https://github.com/x/myrepo", nodes, edges)
        assert report.stats["test_files"] >= 1
        assert report.coverage.test_files >= 1
        # Test function must not appear in source functions
        assert report.stats["functions"] == 3  # only source functions

    def test_deterministic(self):
        nodes, edges = _minimal_repo()
        r1 = engine.compute(_JOB, "https://github.com/x/myrepo", nodes, edges)
        r2 = engine.compute(_JOB, "https://github.com/x/myrepo", nodes, edges)
        assert r1.overall_score == r2.overall_score
        assert len(r1.issues) == len(r2.issues)


class TestEngineGodFunction:
    def test_god_function_detected(self):
        f1 = _file("f1", "big.py", "src/big.py", lines=300, functions=1)
        fn_god = _fn("fn1", "process_everything", "src/big.py",
                     lines=120, params=9, has_doc=False)
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [
            _edge("repo1", "f1",  RelationshipType.CONTAINS),
            _edge("f1",    "fn1", RelationshipType.CONTAINS),
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo, f1, fn_god], edges)
        god_issues = [i for i in report.issues
                     if i.category == IssueCategory.COMPLEXITY
                     and i.severity in (IssueSeverity.HIGH, IssueSeverity.CRITICAL)]
        assert len(god_issues) >= 1
        # Must have evidence
        assert any(i.evidence for i in god_issues)

    def test_normal_function_not_flagged(self):
        f1 = _file("f1", "svc.py", "src/svc.py", lines=60, functions=1)
        fn_normal = _fn("fn1", "create_user", "src/svc.py", lines=20, params=2, has_doc=True)
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [_edge("repo1","f1",RelationshipType.CONTAINS), _edge("f1","fn1",RelationshipType.CONTAINS)]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo, f1, fn_normal], edges)
        complexity_issues = [i for i in report.issues if i.category == IssueCategory.COMPLEXITY]
        assert len(complexity_issues) == 0, f"False positive: {[(i.title, i.evidence) for i in complexity_issues]}"

    def test_large_param_count_flagged(self):
        f1 = _file("f1", "svc.py", "src/svc.py", lines=50)
        fn = _fn("fn1", "configure", "src/svc.py", lines=25, params=9)
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [_edge("repo1","f1",RelationshipType.CONTAINS), _edge("f1","fn1",RelationshipType.CONTAINS)]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo, f1, fn], edges)
        param_issues = [i for i in report.issues
                       if i.category == IssueCategory.COMPLEXITY and "param" in i.title.lower()]
        assert len(param_issues) >= 1

    def test_acceptable_param_count_not_flagged(self):
        f1 = _file("f1", "svc.py", "src/svc.py", lines=50)
        fn = _fn("fn1", "create", "src/svc.py", lines=15, params=3)
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [_edge("repo1","f1",RelationshipType.CONTAINS), _edge("f1","fn1",RelationshipType.CONTAINS)]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo, f1, fn], edges)
        param_issues = [i for i in report.issues
                       if i.category == IssueCategory.COMPLEXITY and "param" in i.title.lower()]
        assert len(param_issues) == 0


class TestEngineCoupling:
    def test_high_fanout_detected(self):
        src_files = [_file(f"f{i}", f"mod{i}.py", f"src/mod{i}.py") for i in range(15)]
        hub = _file("hub", "hub.py", "src/hub.py")
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        nodes = [repo, hub] + src_files
        edges = [_edge("repo1", "hub", RelationshipType.CONTAINS)]
        # hub imports all 15 source files internally
        for f in src_files:
            edges.append(_edge("hub", f.id, RelationshipType.IMPORTS))
        report = engine.compute(_JOB, "https://github.com/x/r", nodes, edges)
        coupling_issues = [i for i in report.issues if i.category == IssueCategory.COUPLING]
        assert len(coupling_issues) >= 1

    def test_deduplication_imports_depends_on(self):
        """IMPORTS and DEPENDS_ON edges to same target must not double-count."""
        f1 = _file("f1", "a.py", "src/a.py")
        f2 = _file("f2", "b.py", "src/b.py")
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [
            _edge("repo1", "f1", RelationshipType.CONTAINS),
            _edge("repo1", "f2", RelationshipType.CONTAINS),
            _edge("f1", "f2", RelationshipType.IMPORTS),
            _edge("f1", "f2", RelationshipType.DEPENDS_ON),  # duplicate
        ]
        # Should count as 1 dependency, not 2
        report = engine.compute(_JOB, "https://github.com/x/r", [repo,f1,f2], edges)
        # f1 has 1 unique dependency — must NOT trigger high-fanout
        fanout_issues = [i for i in report.issues
                        if i.category == IssueCategory.COUPLING and "fan-out" in i.title.lower()]
        assert len(fanout_issues) == 0


class TestEngineCircularDeps:
    def test_circular_dep_detected(self):
        f1 = _file("f1", "a.py", "src/a.py")
        f2 = _file("f2", "b.py", "src/b.py")
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [
            _edge("repo1","f1",RelationshipType.CONTAINS),
            _edge("repo1","f2",RelationshipType.CONTAINS),
            _edge("f1","f2",RelationshipType.IMPORTS),
            _edge("f2","f1",RelationshipType.IMPORTS),  # cycle
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo,f1,f2], edges)
        cycle_issues = [i for i in report.issues
                       if i.category == IssueCategory.ARCHITECTURE and "circular" in i.title.lower()]
        assert len(cycle_issues) >= 1
        # Must have evidence with cycle path
        assert any("cycle_path" in i.evidence for i in cycle_issues)

    def test_no_circular_dep_when_none(self):
        f1 = _file("f1", "a.py", "src/a.py")
        f2 = _file("f2", "b.py", "src/b.py")
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [
            _edge("repo1","f1",RelationshipType.CONTAINS),
            _edge("repo1","f2",RelationshipType.CONTAINS),
            _edge("f1","f2",RelationshipType.IMPORTS),  # one-way, no cycle
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo,f1,f2], edges)
        cycle_issues = [i for i in report.issues
                       if i.category == IssueCategory.ARCHITECTURE and "circular" in i.title.lower()]
        assert len(cycle_issues) == 0


class TestEngineDocumentation:
    def test_undocumented_class_flagged(self):
        f1  = _file("f1", "svc.py", "src/svc.py", classes=1)
        cls1 = _cls("cls1", "UserService", "src/svc.py", methods=3, lines=50, has_doc=False)
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [_edge("repo1","f1",RelationshipType.CONTAINS), _edge("f1","cls1",RelationshipType.CONTAINS)]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo,f1,cls1], edges)
        doc_issues = [i for i in report.issues if i.category == IssueCategory.DOCUMENTATION]
        assert len(doc_issues) >= 1

    def test_documented_code_not_flagged(self):
        f1   = _file("f1", "svc.py", "src/svc.py", classes=1, functions=2)
        cls1 = _cls("cls1", "UserService", "src/svc.py", methods=2, lines=40, has_doc=True)
        fn1  = _fn("fn1", "create_user", "src/svc.py", lines=10, has_doc=True)
        fn2  = _fn("fn2", "delete_user", "src/svc.py", lines=8,  has_doc=True)
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [
            _edge("repo1","f1",RelationshipType.CONTAINS),
            _edge("f1","cls1",RelationshipType.CONTAINS),
            _edge("f1","fn1",RelationshipType.CONTAINS),
            _edge("f1","fn2",RelationshipType.CONTAINS),
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo,f1,cls1,fn1,fn2], edges)
        critical_doc = [i for i in report.issues
                       if i.category == IssueCategory.DOCUMENTATION
                       and i.severity in (IssueSeverity.HIGH, IssueSeverity.CRITICAL)]
        assert len(critical_doc) == 0


class TestEngineNaming:
    def test_python_camel_case_flagged(self):
        f1 = _file("f1", "svc.py", "src/svc.py", lang="python")
        fn = _fn("fn1", "getUser", "src/svc.py", lines=10)  # camelCase in Python
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [_edge("repo1","f1",RelationshipType.CONTAINS), _edge("f1","fn1",RelationshipType.CONTAINS)]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo,f1,fn], edges)
        naming_issues = [i for i in report.issues if i.category == IssueCategory.NAMING]
        assert len(naming_issues) >= 1

    def test_java_camel_not_flagged(self):
        f1 = _file("f1", "Service.java", "src/Service.java", lang="java")
        fn = _fn("fn1", "getUserById", "src/Service.java", lines=10)
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [_edge("repo1","f1",RelationshipType.CONTAINS), _edge("f1","fn1",RelationshipType.CONTAINS)]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo,f1,fn], edges)
        naming_issues = [i for i in report.issues if i.category == IssueCategory.NAMING]
        assert len(naming_issues) == 0, f"False positive on Java camelCase: {naming_issues}"

    def test_idiomatic_loop_var_not_flagged(self):
        f1 = _file("f1", "math.py", "src/math.py", lang="python")
        fn = _fn("fn1", "i", "src/math.py", lines=3)  # loop variable
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        edges = [_edge("repo1","f1",RelationshipType.CONTAINS), _edge("f1","fn1",RelationshipType.CONTAINS)]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo,f1,fn], edges)
        naming_issues = [i for i in report.issues if i.category == IssueCategory.NAMING]
        assert len(naming_issues) == 0


class TestEngineEdgeCases:
    def test_empty_repository(self):
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        report = engine.compute(_JOB, "https://github.com/x/r", [repo], [])
        assert report.overall_score >= 0
        assert report.overall_score <= 100

    def test_no_impossible_score(self):
        nodes, edges = _minimal_repo()
        report = engine.compute(_JOB, "https://github.com/x/r", nodes, edges)
        assert 0 <= report.overall_score <= 100
        for d in report.dimensions:
            assert 0 <= d.score <= 100

    def test_score_not_raw_issue_count(self):
        """A repo with 100 files and 3 issues should not score lower than one with 5 files and 3 issues."""
        # Large repo: 100 files, 3 bad functions
        large_nodes = [_node("repo1","repo",NodeType.REPOSITORY,{})]
        large_edges = []
        for i in range(100):
            f = _file(f"f{i}", f"mod{i}.py", f"src/mod{i}.py", lines=50, functions=1)
            fn = _fn(f"fn{i}", f"func_{i}", f"src/mod{i}.py", lines=15, has_doc=True)
            large_nodes.extend([f, fn])
            large_edges.extend([
                _edge("repo1", f"f{i}", RelationshipType.CONTAINS),
                _edge(f"f{i}", f"fn{i}", RelationshipType.CONTAINS),
            ])
        # Add 3 god functions
        for j in range(3):
            f = _file(f"bad{j}", f"bad{j}.py", f"src/bad{j}.py", lines=300)
            fn = _fn(f"bfn{j}", f"process_{j}", f"src/bad{j}.py", lines=120, params=9)
            large_nodes.extend([f, fn])
            large_edges.extend([
                _edge("repo1", f"bad{j}", RelationshipType.CONTAINS),
                _edge(f"bad{j}", f"bfn{j}", RelationshipType.CONTAINS),
            ])
        large_report = engine.compute(_JOB, "https://github.com/x/big", large_nodes, large_edges)

        # Small repo: 5 files, 3 bad functions
        small_nodes = [_node("repo2","repo",NodeType.REPOSITORY,{})]
        small_edges = []
        for j in range(3):
            f = _file(f"sf{j}", f"bad{j}.py", f"src/bad{j}.py", lines=300)
            fn = _fn(f"sfn{j}", f"process_{j}", f"src/bad{j}.py", lines=120, params=9)
            small_nodes.extend([f, fn])
            small_edges.extend([
                _edge("repo2", f"sf{j}", RelationshipType.CONTAINS),
                _edge(f"sf{j}", f"sfn{j}", RelationshipType.CONTAINS),
            ])
        small_report = engine.compute(_JOB, "https://github.com/x/small", small_nodes, small_edges)

        # Large repo should score BETTER (same issues, more good code)
        assert large_report.overall_score >= small_report.overall_score, (
            f"Large repo ({large_report.overall_score}) scored lower than "
            f"small repo ({small_report.overall_score}) — scoring is not normalised"
        )

    def test_confidence_present_on_all_dimensions(self):
        nodes, edges = _minimal_repo()
        report = engine.compute(_JOB, "https://github.com/x/r", nodes, edges)
        for d in report.dimensions:
            assert 0.0 <= d.confidence <= 1.0, f"Dimension {d.name} has invalid confidence {d.confidence}"

    def test_every_issue_has_evidence(self):
        f1 = _file("f1", "svc.py", "src/svc.py", lines=600, functions=1)
        fn = _fn("fn1", "doEverything", "src/svc.py", lines=150, params=10)
        repo = _node("repo1","repo",NodeType.REPOSITORY,{})
        edges = [_edge("repo1","f1",RelationshipType.CONTAINS), _edge("f1","fn1",RelationshipType.CONTAINS)]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo,f1,fn], edges)
        high_issues = [i for i in report.issues
                      if i.severity in (IssueSeverity.HIGH, IssueSeverity.CRITICAL)]
        for issue in high_issues:
            assert issue.evidence, f"Issue '{issue.title}' has no evidence"

    def test_coverage_object_populated(self):
        nodes, edges = _minimal_repo()
        report = engine.compute(_JOB, "https://github.com/x/r", nodes, edges)
        assert report.coverage is not None
        assert report.coverage.analyzed_files >= 0
        assert 0.0 <= report.coverage.coverage_pct <= 1.0


# ══════════════════════════════════════════════════════════════════════════════
# TARJAN SCC CYCLE DETECTION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestTarjanSCC:
    """Req 2 — proper SCC cycle detection, not just A↔B pair check."""

    def _repo_and_files(self, file_ids: list[str]):
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        files = [_file(fid, f"{fid}.py", f"src/{fid}.py") for fid in file_ids]
        edges = [_edge("repo1", fid, RelationshipType.CONTAINS) for fid in file_ids]
        return repo, files, edges

    def test_2node_cycle_detected(self):
        """A -> B -> A must be found."""
        repo, files, base_edges = self._repo_and_files(["a", "b"])
        edges = base_edges + [
            _edge("a", "b", RelationshipType.IMPORTS),
            _edge("b", "a", RelationshipType.IMPORTS),
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo]+files, edges)
        cycles = [i for i in report.issues
                  if i.category == IssueCategory.ARCHITECTURE and "circular" in i.title.lower()]
        assert len(cycles) >= 1, "Expected 2-node cycle to be detected"
        c = cycles[0]
        assert c.evidence.get("cycle_length") == 2
        assert c.confidence == 1.0

    def test_3node_cycle_detected(self):
        """A -> B -> C -> A must be found (was missed by old A↔B check)."""
        repo, files, base_edges = self._repo_and_files(["a", "b", "c"])
        edges = base_edges + [
            _edge("a", "b", RelationshipType.IMPORTS),
            _edge("b", "c", RelationshipType.IMPORTS),
            _edge("c", "a", RelationshipType.IMPORTS),   # closes the 3-cycle
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo]+files, edges)
        cycles = [i for i in report.issues
                  if i.category == IssueCategory.ARCHITECTURE and "circular" in i.title.lower()]
        assert len(cycles) >= 1, "Expected 3-node cycle to be detected"
        c = cycles[0]
        assert c.evidence.get("cycle_length") == 3, f"Expected cycle_length=3, got {c.evidence}"
        # Path must include all three files
        path = c.evidence.get("cycle_path", [])
        assert len(path) >= 3, f"Path should have >= 3 entries: {path}"

    def test_4node_cycle_detected(self):
        """A -> B -> C -> D -> A must be found."""
        repo, files, base_edges = self._repo_and_files(["a", "b", "c", "d"])
        edges = base_edges + [
            _edge("a", "b", RelationshipType.IMPORTS),
            _edge("b", "c", RelationshipType.IMPORTS),
            _edge("c", "d", RelationshipType.IMPORTS),
            _edge("d", "a", RelationshipType.IMPORTS),
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo]+files, edges)
        cycles = [i for i in report.issues
                  if i.category == IssueCategory.ARCHITECTURE and "circular" in i.title.lower()]
        assert len(cycles) >= 1, "Expected 4-node cycle"
        assert cycles[0].evidence.get("cycle_length") == 4

    def test_no_cycle_when_none(self):
        """A -> B -> C (no back edge) must NOT produce a cycle issue."""
        repo, files, base_edges = self._repo_and_files(["a", "b", "c"])
        edges = base_edges + [
            _edge("a", "b", RelationshipType.IMPORTS),
            _edge("b", "c", RelationshipType.IMPORTS),
            # NO back edge from c → no cycle
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo]+files, edges)
        cycles = [i for i in report.issues
                  if i.category == IssueCategory.ARCHITECTURE and "circular" in i.title.lower()]
        assert len(cycles) == 0, f"False positive cycle: {[(i.title, i.evidence) for i in cycles]}"

    def test_two_independent_cycles(self):
        """Two separate 2-node cycles in the same repo both reported."""
        repo, files, base_edges = self._repo_and_files(["a", "b", "c", "d"])
        edges = base_edges + [
            _edge("a", "b", RelationshipType.IMPORTS),
            _edge("b", "a", RelationshipType.IMPORTS),  # cycle 1
            _edge("c", "d", RelationshipType.IMPORTS),
            _edge("d", "c", RelationshipType.IMPORTS),  # cycle 2
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo]+files, edges)
        cycles = [i for i in report.issues
                  if i.category == IssueCategory.ARCHITECTURE and "circular" in i.title.lower()]
        assert len(cycles) >= 2, f"Expected 2 separate cycles, got {len(cycles)}"

    def test_cycle_evidence_has_full_path(self):
        """Every cycle issue must have cycle_path and files_in_cycle in evidence."""
        repo, files, base_edges = self._repo_and_files(["x", "y"])
        edges = base_edges + [
            _edge("x", "y", RelationshipType.IMPORTS),
            _edge("y", "x", RelationshipType.IMPORTS),
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo]+files, edges)
        cycles = [i for i in report.issues
                  if i.category == IssueCategory.ARCHITECTURE and "circular" in i.title.lower()]
        assert len(cycles) >= 1
        ev = cycles[0].evidence
        assert "cycle_path" in ev,      "Missing cycle_path in evidence"
        assert "cycle_length" in ev,    "Missing cycle_length in evidence"
        assert "files_in_cycle" in ev,  "Missing files_in_cycle in evidence"
        assert isinstance(ev["cycle_path"], list)
        assert len(ev["cycle_path"]) >= 2


# ══════════════════════════════════════════════════════════════════════════════
# CYCLOMATIC COMPLEXITY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCyclomaticComplexity:
    """Req 3 — real McCabe CC from Python AST, not just line count."""

    from cortex.pipeline.infrastructure.ast_parser import PythonASTParser
    _py_parser = PythonASTParser()

    def _parse(self, code: str):
        result = self._py_parser.parse(code, "test.py")
        assert not result.parse_errors, f"Parse error: {result.parse_errors}"
        return result

    def test_simple_function_cc1(self):
        """No branches → CC = 1."""
        code = "def add(a, b):\n    return a + b\n"
        result = self._parse(code)
        fn = result.functions[0]
        assert fn._cyclomatic == 1, f"Expected CC=1, got {fn._cyclomatic}"

    def test_one_if_cc2(self):
        """One if → CC = 2."""
        code = "def check(x):\n    if x > 0:\n        return True\n    return False\n"
        result = self._parse(code)
        fn = result.functions[0]
        assert fn._cyclomatic == 2, f"Expected CC=2, got {fn._cyclomatic}"

    def test_if_elif_else_cc3(self):
        """if + elif → 2 branches → CC = 3."""
        code = (
            "def classify(x):\n"
            "    if x > 0:\n"
            "        return 'pos'\n"
            "    elif x < 0:\n"
            "        return 'neg'\n"
            "    return 'zero'\n"
        )
        result = self._parse(code)
        fn = result.functions[0]
        assert fn._cyclomatic == 3, f"Expected CC=3, got {fn._cyclomatic}"

    def test_for_loop_adds_branch(self):
        """for loop adds 1 branch → CC >= 2."""
        code = "def total(items):\n    s = 0\n    for x in items:\n        s += x\n    return s\n"
        result = self._parse(code)
        fn = result.functions[0]
        assert fn._cyclomatic >= 2, f"Expected CC>=2 for loop, got {fn._cyclomatic}"

    def test_try_except_adds_branch(self):
        """except handler adds 1 branch."""
        code = (
            "def safe_div(a, b):\n"
            "    try:\n"
            "        return a / b\n"
            "    except ZeroDivisionError:\n"
            "        return 0\n"
        )
        result = self._parse(code)
        fn = result.functions[0]
        assert fn._cyclomatic >= 2, f"Expected CC>=2 for try/except, got {fn._cyclomatic}"

    def test_boolean_and_adds_branch(self):
        """a and b adds 1 branch (short-circuit path)."""
        code = "def both(a, b):\n    return a and b\n"
        result = self._parse(code)
        fn = result.functions[0]
        assert fn._cyclomatic >= 2, f"Expected CC>=2 for 'and', got {fn._cyclomatic}"

    def test_complex_function_high_cc(self):
        """A function with many branches should have CC >= 5."""
        code = (
            "def process(x, y, z):\n"
            "    if x > 0:\n"
            "        for i in range(y):\n"
            "            if i % 2 == 0:\n"
            "                try:\n"
            "                    r = x / i\n"
            "                except ZeroDivisionError:\n"
            "                    r = 0\n"
            "            elif z > 10:\n"
            "                r = z\n"
            "    return 0\n"
        )
        result = self._parse(code)
        fn = result.functions[0]
        assert fn._cyclomatic >= 5, f"Expected CC>=5 for complex fn, got {fn._cyclomatic}"
        assert fn._nesting_depth >= 3, f"Expected nesting>=3, got {fn._nesting_depth}"

    def test_nesting_depth_measured(self):
        """Deeply nested function should report nesting_depth > 2."""
        code = (
            "def deep(x):\n"
            "    if x:\n"
            "        for i in range(x):\n"
            "            if i > 0:\n"
            "                while i > 1:\n"
            "                    i -= 1\n"
        )
        result = self._parse(code)
        fn = result.functions[0]
        assert fn._nesting_depth >= 3, f"Expected depth>=3, got {fn._nesting_depth}"

    def test_call_count_measured(self):
        """Function with multiple calls should have call_count > 0."""
        code = (
            "def orchestrate():\n"
            "    a = foo()\n"
            "    b = bar(a)\n"
            "    return baz(a, b)\n"
        )
        result = self._parse(code)
        fn = result.functions[0]
        assert fn._call_count >= 3, f"Expected >= 3 calls, got {fn._call_count}"

    def test_cc_stored_in_graph_node(self):
        """cyclomatic property must be stored on FUNCTION graph nodes."""
        from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
        code = (
            "def multi_branch(x, y):\n"
            "    if x > 0:\n"
            "        if y > 0:\n"
            "            return x + y\n"
            "    return 0\n"
        )
        import sys; sys.path.insert(0, 'src')
        from cortex.pipeline.infrastructure.ast_parser import ASTParser
        parser = ASTParser()
        parsed = parser.parse(code, "src/utils.py")
        builder = GraphBuilder(job_id="test-j", repo_url="https://github.com/x/r")
        result = builder.build([parsed])
        fn_nodes = [n for n in result.nodes if n.node_type.value == "Function"]
        assert len(fn_nodes) >= 1
        fn = fn_nodes[0]
        cc = fn.properties.get("cyclomatic", 0)
        assert cc >= 3, f"Expected CC>=3 in graph node, got {cc} (properties={fn.properties})"

    def test_cyclomatic_issue_reported_in_engine(self):
        """Engine must report a complexity issue for high-CC Python functions."""
        f1 = _file("f1", "svc.py", "src/svc.py", lang="python", lines=50)
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        # Build a function node with high cyclomatic stored
        fn = _node("fn1", "complex_fn", NodeType.FUNCTION, {
            "file": "src/svc.py", "line": 1, "lines": 40,
            "param_count": 2, "is_method": False,
            "has_docstring": False, "is_async": False,
            "cyclomatic": 12,   # above CYCLOMATIC_HIGH (10)
            "branch_count": 11,
            "nesting_depth": 4,
            "call_count": 8,
        })
        edges = [
            _edge("repo1", "f1", RelationshipType.CONTAINS),
            _edge("f1", "fn1", RelationshipType.CONTAINS),
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo, f1, fn], edges)
        cc_issues = [i for i in report.issues
                     if i.category == IssueCategory.COMPLEXITY
                     and "cyclomatic" in i.title.lower()]
        assert len(cc_issues) >= 1, "Expected cyclomatic complexity issue to be raised"
        assert cc_issues[0].evidence.get("cyclomatic") == 12
        assert cc_issues[0].confidence == 1.0

    def test_no_cyclomatic_issue_for_simple_function(self):
        """Simple Python function with CC=2 must not produce a cyclomatic issue."""
        f1 = _file("f1", "svc.py", "src/svc.py", lang="python")
        repo = _node("repo1", "repo", NodeType.REPOSITORY, {})
        fn = _node("fn1", "simple", NodeType.FUNCTION, {
            "file": "src/svc.py", "line": 1, "lines": 8,
            "param_count": 1, "is_method": False,
            "has_docstring": True, "is_async": False,
            "cyclomatic": 2, "branch_count": 1, "nesting_depth": 1, "call_count": 1,
        })
        edges = [
            _edge("repo1", "f1", RelationshipType.CONTAINS),
            _edge("f1", "fn1", RelationshipType.CONTAINS),
        ]
        report = engine.compute(_JOB, "https://github.com/x/r", [repo, f1, fn], edges)
        cc_issues = [i for i in report.issues
                     if i.category == IssueCategory.COMPLEXITY
                     and "cyclomatic" in i.title.lower()]
        assert len(cc_issues) == 0, f"False positive cyclomatic issue: {cc_issues}"
