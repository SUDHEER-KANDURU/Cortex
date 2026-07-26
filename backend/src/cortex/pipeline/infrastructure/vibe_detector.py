"""Vibe code detector — identifies AI-generated code patterns.
Analyzes parsed files and returns specific flags with explanations
and fix suggestions for each detected pattern."""

from dataclasses import dataclass, field
from enum import Enum
from cortex.pipeline.infrastructure.ast_parser import (
    ParsedFile,
    ParsedFunction,
    ParsedClass,
)
import re
import structlog

logger = structlog.get_logger()


class VibePattern(str, Enum):
    NO_ERROR_HANDLING = "no_error_handling"
    DUPLICATE_LOGIC = "duplicate_logic"
    GOD_FUNCTION = "god_function"
    INCONSISTENT_NAMING = "inconsistent_naming"
    UNUSED_IMPORTS = "unused_imports"
    MISSING_DOCSTRINGS = "missing_docstrings"
    HARDCODED_VALUES = "hardcoded_values"
    DEEP_NESTING = "deep_nesting"
    LONG_PARAMETER_LIST = "long_parameter_list"
    COPY_PASTE_BLOCKS = "copy_paste_blocks"


@dataclass
class VibeFlag:
    """A single detected vibe code pattern."""
    pattern: VibePattern
    severity: str          # "high", "medium", "low"
    file_path: str
    line: int
    message: str
    fix: str
    code_snippet: str = ""

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern.value,
            "severity": self.severity,
            "file": self.file_path,
            "line": self.line,
            "message": self.message,
            "fix": self.fix,
            "snippet": self.code_snippet,
        }


@dataclass
class VibeReport:
    """Complete vibe code detection report for a repository."""
    repo_url: str
    flags: list[VibeFlag] = field(default_factory=list)
    files_analyzed: int = 0
    health_score: int = 100

    def high_severity(self) -> list[VibeFlag]:
        return [f for f in self.flags if f.severity == "high"]

    def medium_severity(self) -> list[VibeFlag]:
        return [f for f in self.flags if f.severity == "medium"]

    def low_severity(self) -> list[VibeFlag]:
        return [f for f in self.flags if f.severity == "low"]

    def by_pattern(self, pattern: VibePattern) -> list[VibeFlag]:
        return [f for f in self.flags if f.pattern == pattern]

    def calculate_health_score(self) -> int:
        """Score from 0-100. Deduct points per severity."""
        score = 100
        score -= len(self.high_severity()) * 8
        score -= len(self.medium_severity()) * 4
        score -= len(self.low_severity()) * 1
        return max(0, min(100, score))

    def to_markdown(self) -> str:
        """Generate a markdown report."""
        repo_name = self.repo_url.rstrip("/").split("/")[-1]
        score = self.calculate_health_score()
        lines = [
            f"# Vibe Code Detection Report — {repo_name}",
            "",
            "## Health Score",
            "",
            f"**{score}/100**",
            "",
            self._score_description(score),
            "",
            "## Summary",
            "",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| 🔴 High | {len(self.high_severity())} |",
            f"| 🟡 Medium | {len(self.medium_severity())} |",
            f"| 🟢 Low | {len(self.low_severity())} |",
            f"| Total flags | {len(self.flags)} |",
            f"| Files analyzed | {self.files_analyzed} |",
            "",
        ]

        if not self.flags:
            lines += [
                "## Result",
                "",
                "✅ No vibe code patterns detected. "
                "This codebase looks clean.",
                "",
            ]
            return "\n".join(lines)

        lines.append("## Detected Patterns")
        lines.append("")

        # Group by pattern
        by_pattern: dict[str, list[VibeFlag]] = {}
        for flag in self.flags:
            key = flag.pattern.value
            if key not in by_pattern:
                by_pattern[key] = []
            by_pattern[key].append(flag)

        severity_order = {"high": 0, "medium": 1, "low": 2}
        sorted_flags = sorted(
            self.flags,
            key=lambda f: severity_order.get(f.severity, 3),
        )

        for flag in sorted_flags[:20]:  # Cap at 20
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                flag.severity, "⚪"
            )
            lines += [
                f"### {icon} {flag.pattern.value.replace('_', ' ').title()}",
                "",
                f"**File:** `{flag.file_path}` — line {flag.line}",
                "",
                f"**Issue:** {flag.message}",
                "",
                f"**Fix:** {flag.fix}",
                "",
            ]
            if flag.code_snippet:
                lines += [
                    "```",
                    flag.code_snippet,
                    "```",
                    "",
                ]

        return "\n".join(lines)

    def _score_description(self, score: int) -> str:
        if score >= 90:
            return "✅ Excellent — this codebase is clean and well-structured."
        elif score >= 75:
            return "🟡 Good — a few patterns worth addressing."
        elif score >= 50:
            return (
                "🟠 Needs attention — several AI-generated patterns detected."
            )
        else:
            return (
                "🔴 High risk — significant vibe code detected. "
                "Review before shipping."
            )


class VibeDetector:
    """Detects AI-generated code patterns in parsed source files.

    Each detection method checks for one specific pattern.
    Returns VibeFlag objects with file location, severity,
    explanation, and a concrete fix suggestion.
    """

    def analyze(
        self,
        parsed_files: list[ParsedFile],
        repo_url: str,
    ) -> VibeReport:
        """Run all detectors on all parsed files."""
        report = VibeReport(
            repo_url=repo_url,
            files_analyzed=len(parsed_files),
        )

        for parsed_file in parsed_files:
            if parsed_file.has_errors():
                continue

            self._detect_god_functions(parsed_file, report)
            self._detect_long_parameter_lists(parsed_file, report)
            self._detect_missing_docstrings(parsed_file, report)
            self._detect_hardcoded_values(parsed_file, report)
            self._detect_inconsistent_naming(parsed_file, report)
            self._detect_no_error_handling(parsed_file, report)

        self._detect_duplicate_logic(parsed_files, report)

        report.health_score = report.calculate_health_score()

        logger.info(
            "vibe_detection_complete",
            repo_url=repo_url,
            files=len(parsed_files),
            flags=len(report.flags),
            health_score=report.health_score,
        )

        return report

    def _detect_god_functions(
        self,
        parsed_file: ParsedFile,
        report: VibeReport,
    ) -> None:
        """Flag functions over 50 lines — AI tends to generate
        monolithic functions that do too many things."""
        for fn in parsed_file.all_functions():
            if fn.line_count() > 50:
                report.flags.append(VibeFlag(
                    pattern=VibePattern.GOD_FUNCTION,
                    severity="high",
                    file_path=parsed_file.path,
                    line=fn.line_start,
                    message=(
                        f"`{fn.qualified_name()}` is {fn.line_count()} "
                        f"lines long. Functions this large typically "
                        f"violate the Single Responsibility Principle "
                        f"and are hard to test."
                    ),
                    fix=(
                        f"Split `{fn.name}` into smaller functions, "
                        f"each doing one thing. Aim for under 30 lines."
                    ),
                ))
            elif fn.line_count() > 30:
                report.flags.append(VibeFlag(
                    pattern=VibePattern.GOD_FUNCTION,
                    severity="medium",
                    file_path=parsed_file.path,
                    line=fn.line_start,
                    message=(
                        f"`{fn.qualified_name()}` is {fn.line_count()} "
                        f"lines. Consider splitting it."
                    ),
                    fix="Extract helper functions for each logical step.",
                ))

    def _detect_long_parameter_lists(
        self,
        parsed_file: ParsedFile,
        report: VibeReport,
    ) -> None:
        """Flag functions with more than 5 parameters.
        AI often generates functions with excessive parameters
        instead of using objects or dataclasses."""
        for fn in parsed_file.all_functions():
            param_count = len(fn.parameters)
            if param_count > 7:
                report.flags.append(VibeFlag(
                    pattern=VibePattern.LONG_PARAMETER_LIST,
                    severity="high",
                    file_path=parsed_file.path,
                    line=fn.line_start,
                    message=(
                        f"`{fn.qualified_name()}` takes {param_count} "
                        f"parameters. This is a sign the function is "
                        f"doing too much or needs a request object."
                    ),
                    fix=(
                        f"Group related parameters into a dataclass "
                        f"or typed dict. Pass that object instead."
                    ),
                ))
            elif param_count > 5:
                report.flags.append(VibeFlag(
                    pattern=VibePattern.LONG_PARAMETER_LIST,
                    severity="medium",
                    file_path=parsed_file.path,
                    line=fn.line_start,
                    message=(
                        f"`{fn.qualified_name()}` takes {param_count} "
                        f"parameters."
                    ),
                    fix="Consider grouping related parameters.",
                ))

    def _detect_missing_docstrings(
        self,
        parsed_file: ParsedFile,
        report: VibeReport,
    ) -> None:
        """Flag public functions and classes with no docstring.
        AI often skips documentation for non-obvious functions."""
        for cls in parsed_file.classes:
            if not cls.docstring and not cls.name.startswith("_"):
                report.flags.append(VibeFlag(
                    pattern=VibePattern.MISSING_DOCSTRINGS,
                    severity="low",
                    file_path=parsed_file.path,
                    line=cls.line_start,
                    message=(
                        f"Class `{cls.name}` has no docstring. "
                        f"Future developers (and interviewers) "
                        f"need to understand what it does."
                    ),
                    fix=(
                        f'Add a one-line docstring: '
                        f'"""Brief description of {cls.name}."""'
                    ),
                ))

        for fn in parsed_file.functions:
            if (
                not fn.docstring
                and not fn.name.startswith("_")
                and fn.line_count() > 10
            ):
                report.flags.append(VibeFlag(
                    pattern=VibePattern.MISSING_DOCSTRINGS,
                    severity="low",
                    file_path=parsed_file.path,
                    line=fn.line_start,
                    message=(
                        f"Function `{fn.name}` ({fn.line_count()} lines) "
                        f"has no docstring."
                    ),
                    fix="Add a docstring explaining what this function does.",
                ))

    def _detect_hardcoded_values(
        self,
        parsed_file: ParsedFile,
        report: VibeReport,
    ) -> None:
        """Detect hardcoded strings that look like secrets or config.
        AI frequently hardcodes passwords, URLs, and API keys."""
        suspicious_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "hardcoded password"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "hardcoded secret"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "hardcoded API key"),
            (r'token\s*=\s*["\'][^"\']+["\']', "hardcoded token"),
            (r'http://localhost:\d+', "hardcoded localhost URL"),
            (r'127\.0\.0\.1', "hardcoded IP address"),
        ]

        if not parsed_file.file_contents_available():
            return

        for pattern, description in suspicious_patterns:
            # We check via function names as a proxy
            # (full content analysis requires content storage)
            for fn in parsed_file.all_functions():
                if any(
                    kw in fn.name.lower()
                    for kw in ["password", "secret", "token", "key"]
                ):
                    report.flags.append(VibeFlag(
                        pattern=VibePattern.HARDCODED_VALUES,
                        severity="high",
                        file_path=parsed_file.path,
                        line=fn.line_start,
                        message=(
                            f"Function `{fn.name}` may handle sensitive "
                            f"data. Check for hardcoded secrets."
                        ),
                        fix=(
                            "Use environment variables via os.getenv() "
                            "or a config class. Never hardcode secrets."
                        ),
                    ))
                    break

    def _detect_inconsistent_naming(
        self,
        parsed_file: ParsedFile,
        report: VibeReport,
    ) -> None:
        """Detect mixed naming conventions — camelCase vs snake_case.
        AI often mixes conventions when combining code from
        different sources."""
        camel_count = 0
        snake_count = 0

        for fn in parsed_file.all_functions():
            if re.search(r'[a-z][A-Z]', fn.name):
                camel_count += 1
            elif "_" in fn.name:
                snake_count += 1

        if camel_count > 0 and snake_count > 0:
            report.flags.append(VibeFlag(
                pattern=VibePattern.INCONSISTENT_NAMING,
                severity="medium",
                file_path=parsed_file.path,
                line=1,
                message=(
                    f"Mixed naming conventions detected: "
                    f"{camel_count} camelCase and {snake_count} "
                    f"snake_case functions in the same file."
                ),
                fix=(
                    "Pick one convention and apply it consistently. "
                    "Python standard is snake_case. "
                    "Java standard is camelCase."
                ),
            ))

    def _detect_no_error_handling(
        self,
        parsed_file: ParsedFile,
        report: VibeReport,
    ) -> None:
        """Flag files with many functions but no exception classes.
        AI often skips error handling entirely."""
        if len(parsed_file.all_functions()) < 3:
            return

        has_error_class = any(
            "Error" in cls.name
            or "Exception" in cls.name
            or any(
                "Error" in base or "Exception" in base
                for base in cls.base_classes
            )
            for cls in parsed_file.classes
        )

        has_try_import = any(
            "exception" in imp.module.lower()
            or "error" in imp.module.lower()
            for imp in parsed_file.imports
        )

        if (
            not has_error_class
            and not has_try_import
            and len(parsed_file.all_functions()) > 5
        ):
            report.flags.append(VibeFlag(
                pattern=VibePattern.NO_ERROR_HANDLING,
                severity="medium",
                file_path=parsed_file.path,
                line=1,
                message=(
                    f"File has {len(parsed_file.all_functions())} "
                    f"functions but no error handling imports or "
                    f"exception classes detected."
                ),
                fix=(
                    "Add try/except blocks for external calls. "
                    "Define custom exceptions for domain errors."
                ),
            ))

    def _detect_duplicate_logic(
        self,
        parsed_files: list[ParsedFile],
        report: VibeReport,
    ) -> None:
        """Detect functions with identical names across multiple files.
        AI frequently copy-pastes logic instead of extracting utilities."""
        function_names: dict[str, list[str]] = {}

        for parsed_file in parsed_files:
            for fn in parsed_file.functions:
                if fn.name not in function_names:
                    function_names[fn.name] = []
                function_names[fn.name].append(parsed_file.path)

        for fn_name, file_paths in function_names.items():
            if len(file_paths) >= 3 and not fn_name.startswith("_"):
                report.flags.append(VibeFlag(
                    pattern=VibePattern.DUPLICATE_LOGIC,
                    severity="medium",
                    file_path=file_paths[0],
                    line=1,
                    message=(
                        f"Function `{fn_name}` appears in "
                        f"{len(file_paths)} different files: "
                        f"{', '.join(f.split('/')[-1] for f in file_paths[:3])}"
                        f"{'...' if len(file_paths) > 3 else ''}. "
                        f"This suggests copy-pasted logic."
                    ),
                    fix=(
                        f"Extract `{fn_name}` into a shared utility "
                        f"module and import it where needed."
                    ),
                ))