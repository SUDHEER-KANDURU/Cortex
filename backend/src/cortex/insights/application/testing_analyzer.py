"""Testing Analyzer — Cortex's deterministic testing coverage intelligence.

Detects testing gaps and quality signals WITHOUT running tests.
This is Cortex's own testing intelligence — purely structural analysis.

Detections:
  - Untested modules (source modules with no corresponding test file)
  - Test-to-source ratio (overall and per-module)
  - High-risk untested code (complex functions without tests)
  - Test quality signals (test naming, assertion patterns)
  - Missing test infrastructure (no conftest, no fixtures)

Each finding: evidence, severity, fix_template.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict

from cortex.graph.domain.entities import GraphNode, NodeType, RelationshipType
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult


@dataclass
class TestingFinding:
    """A single testing issue with evidence and fix."""
    title: str
    severity: str  # high, medium, low
    category: str  # coverage, quality, infrastructure, risk
    description: str
    file_path: str = ""
    symbol: str = ""
    evidence: str = ""
    fix_template: str = ""
    confidence: float = 0.8


@dataclass
class TestingReport:
    """Complete testing assessment."""
    total_source_files: int = 0
    total_test_files: int = 0
    total_test_functions: int = 0
    test_ratio: float = 0.0
    tested_modules: list[str] = field(default_factory=list)
    untested_modules: list[str] = field(default_factory=list)
    findings: list[TestingFinding] = field(default_factory=list)


class TestingAnalyzer:
    """Deterministic testing analysis from graph structure.

    Uses file path patterns, TEST node types, and TESTS edges to
    assess the testing posture without running any tests.
    """

    def analyze(self, graph: GraphBuildResult) -> TestingReport:
        """Run full testing analysis."""
        report = TestingReport()

        files = graph.nodes_by_type(NodeType.FILE)
        modules = graph.nodes_by_type(NodeType.MODULE)
        tests = graph.nodes_by_type(NodeType.TEST)

        test_files = [f for f in files if f.properties.get("is_test_file")]
        source_files = [f for f in files if not f.properties.get("is_test_file")]

        report.total_source_files = len(source_files)
        report.total_test_files = len(test_files)
        report.total_test_functions = len(tests)
        report.test_ratio = round(
            len(test_files) / max(len(source_files), 1), 2
        )

        # Analyze module-level test coverage
        self._analyze_module_coverage(graph, modules, test_files, report)

        # Detection 1: Overall test ratio
        report.findings.extend(self._check_overall_coverage(report))

        # Detection 2: Untested high-complexity modules
        report.findings.extend(self._check_untested_complex_code(graph, modules, report))

        # Detection 3: Test quality signals
        report.findings.extend(self._check_test_quality(tests, test_files))

        # Detection 4: Missing test infrastructure
        report.findings.extend(self._check_test_infrastructure(files))

        return report

    def _analyze_module_coverage(
        self,
        graph: GraphBuildResult,
        modules: list[GraphNode],
        test_files: list[GraphNode],
        report: TestingReport,
    ) -> None:
        """Determine which modules have tests and which don't."""
        # Build module names set
        module_names: dict[str, GraphNode] = {}
        for m in modules:
            path = str(m.properties.get("path", m.label))
            name = path.rstrip("/").split("/")[-1].lower()
            if name not in ("test", "tests", "__pycache__", "node_modules"):
                module_names[name] = m

        # Check which modules are tested (by TESTS edges or test file naming)
        tested: set[str] = set()

        # Via TESTS edges
        for edge in graph.edges:
            if edge.relationship == RelationshipType.TESTS:
                target = graph.node_by_id.get(edge.target_id)
                if target:
                    target_name = str(target.properties.get("path", target.label)).rstrip("/").split("/")[-1].lower()
                    tested.add(target_name)

        # Via test file naming convention (test_jobs.py → tests "jobs" module)
        for tf in test_files:
            path = str(tf.properties.get("path", tf.label)).lower()
            filename = path.split("/")[-1]
            # Extract tested module name from filename
            stem = filename.replace(".py", "").replace(".ts", "").replace(".js", "")
            tested_name = (
                stem.replace("test_", "").replace("_test", "")
                .replace(".test", "").replace(".spec", "")
                .replace("spec_", "")
            )
            if tested_name:
                tested.add(tested_name)

        report.tested_modules = sorted(tested & set(module_names.keys()))
        report.untested_modules = sorted(set(module_names.keys()) - tested)

    def _check_overall_coverage(self, report: TestingReport) -> list[TestingFinding]:
        """Check overall test coverage ratio."""
        findings: list[TestingFinding] = []

        if report.total_source_files == 0:
            return []

        if report.total_test_files == 0:
            findings.append(TestingFinding(
                title="No test files detected",
                severity="high",
                category="coverage",
                description=f"{report.total_source_files} source files with zero test coverage.",
                evidence=f"source_files={report.total_source_files}, test_files=0",
                fix_template=(
                    "Start testing from the inside out: (1) Domain entities and value objects "
                    "(pure, no dependencies). (2) Application services with mocked repos. "
                    "(3) API endpoints with TestClient. Use pytest + pytest-asyncio for async."
                ),
                confidence=1.0,
            ))
        elif report.test_ratio < 0.2:
            findings.append(TestingFinding(
                title=f"Low test coverage (ratio: {report.test_ratio})",
                severity="medium",
                category="coverage",
                description=(
                    f"{report.total_test_files} test files for {report.total_source_files} "
                    f"source files. Target ratio: 0.5+"
                ),
                evidence=f"test_ratio={report.test_ratio}, test_files={report.total_test_files}",
                fix_template=(
                    "Prioritize: (1) Test the highest-complexity modules first, "
                    "(2) Add integration tests for API endpoints, "
                    "(3) Cover edge cases in domain logic."
                ),
                confidence=0.9,
            ))

        return findings

    def _check_untested_complex_code(
        self, graph: GraphBuildResult, modules: list[GraphNode], report: TestingReport
    ) -> list[TestingFinding]:
        """Identify high-complexity modules without tests."""
        findings: list[TestingFinding] = []

        if not report.untested_modules:
            return []

        # Find complexity of untested modules
        contains_children: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.relationship == RelationshipType.CONTAINS:
                contains_children[edge.source_id].append(edge.target_id)

        untested_complex: list[tuple[str, int]] = []
        for m in modules:
            path = str(m.properties.get("path", m.label))
            name = path.rstrip("/").split("/")[-1].lower()
            if name not in report.untested_modules:
                continue

            # Sum complexity for this module
            total_cc = 0
            queue = list(contains_children.get(m.id, []))
            visited: set[str] = set()
            while queue:
                child_id = queue.pop()
                if child_id in visited:
                    continue
                visited.add(child_id)
                child = graph.node_by_id.get(child_id)
                if child:
                    total_cc += int(child.properties.get("cyclomatic", 0) or 0)
                    queue.extend(contains_children.get(child_id, []))

            if total_cc > 10:
                untested_complex.append((name, total_cc))

        untested_complex.sort(key=lambda x: x[1], reverse=True)

        if untested_complex:
            top = untested_complex[:4]
            findings.append(TestingFinding(
                title=f"{len(untested_complex)} complex modules without tests",
                severity="high",
                category="risk",
                description=(
                    "These modules have high complexity but no detected tests: "
                    + ", ".join(f"`{name}` (CC={cc})" for name, cc in top)
                ),
                evidence=f"untested_complex_modules={len(untested_complex)}",
                fix_template=(
                    "High-complexity untested code is the highest bug risk. "
                    "Add unit tests for: " + ", ".join(name for name, _ in top[:3]) +
                    ". Focus on boundary conditions and error paths."
                ),
                confidence=0.85,
            ))

        return findings

    def _check_test_quality(
        self, tests: list[GraphNode], test_files: list[GraphNode]
    ) -> list[TestingFinding]:
        """Check test quality signals."""
        findings: list[TestingFinding] = []

        if not tests:
            return []

        # Check for very short test functions (likely incomplete)
        short_tests = [
            t for t in tests
            if int(t.properties.get("lines", 0) or 0) <= 2
        ]

        if len(short_tests) > len(tests) * 0.3:
            findings.append(TestingFinding(
                title=f"{len(short_tests)} test functions are very short (≤2 lines)",
                severity="low",
                category="quality",
                description="Short tests may lack meaningful assertions.",
                evidence=f"short_tests={len(short_tests)}, total_tests={len(tests)}",
                fix_template=(
                    "Ensure each test has at least one meaningful assertion. "
                    "Tests should verify behavior, not just that code doesn't crash."
                ),
                confidence=0.5,
            ))

        return findings

    def _check_test_infrastructure(self, files: list[GraphNode]) -> list[TestingFinding]:
        """Check for test infrastructure files (conftest, fixtures)."""
        findings: list[TestingFinding] = []

        file_names = [str(f.properties.get("path", f.label)).split("/")[-1].lower() for f in files]

        has_conftest = any("conftest" in name for name in file_names)
        has_test_files = any("test" in name for name in file_names)

        if has_test_files and not has_conftest:
            findings.append(TestingFinding(
                title="No conftest.py / test setup file detected",
                severity="low",
                category="infrastructure",
                description="Tests exist but no shared fixtures or configuration file found.",
                evidence="conftest.py not found",
                fix_template=(
                    "Add conftest.py with shared fixtures: database sessions, "
                    "test client, sample data factories. This reduces boilerplate "
                    "across test files."
                ),
                confidence=0.6,
            ))

        return findings
