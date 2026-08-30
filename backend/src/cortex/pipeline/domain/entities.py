"""Pipeline domain entities — zero-dependency dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LanguageCapabilityProfile:
    """Declares which structural concepts a language reliably supports (Req 2.1).

    A profile is the switch that makes Cortex explain each repository in terms
    native to its stack: a Go service (packages, no decorators), a TypeScript
    app (interfaces, decorators, generics), and a Rust crate (traits, generics)
    each expose a different set of concepts, and only the answer sections that
    apply to those concepts are assembled (Req 2.2, Req 2.3).

    Every parser returns one of these from ``LanguageParser.profile()``.
    """

    #: Canonical language name (matches ``Language`` enum value, e.g. "python").
    language: str

    # ── Structural concepts the language supports ─────────────────────────────
    has_interfaces: bool = False   # Java/TS interfaces, Python Protocol/ABC, Go interfaces
    has_decorators: bool = False   # Python decorators, TS/Java annotations
    has_generics: bool = False     # Java/TS/Rust/C# generics
    has_packages: bool = False     # Java/Go packages, first-class namespaces
    has_traits: bool = False       # Rust traits, Ruby mixins/modules
    has_classes: bool = True       # OO classes (near-universal for these languages)
    has_enums: bool = False        # first-class enums
    has_async: bool = False        # native async/await

    #: Machine keys of the answer sections that apply to this language. Answer
    #: producers include a section only if its key appears here for at least
    #: one detected language (Req 2.2, Req 2.3).
    answer_sections: tuple[str, ...] = ()

    def supports(self, concept: str) -> bool:
        """Return True if this profile declares support for ``concept``.

        ``concept`` is the concept name without the ``has_`` prefix, e.g.
        ``profile.supports("interfaces")``. Unknown concepts return False.
        """
        return bool(getattr(self, f"has_{concept}", False))

    def applicable_sections(self) -> tuple[str, ...]:
        """Return the answer section keys that apply to this language."""
        return self.answer_sections


@dataclass
class ManifestDependency:
    """A single dependency declared in a manifest file."""

    name: str
    version: str = ""
    #: "runtime" | "dev" | "build" | "" (unknown)
    scope: str = ""


@dataclass
class ManifestInfo:
    """Deterministic result of parsing one manifest file (Req 2.4).

    Identifies the ecosystem language, the frameworks implied by declared
    dependencies, and the raw dependency list. Framework detection in the
    reasoner consumes ``languages`` and ``frameworks`` in addition to
    import/label signals, so identification no longer relies only on sniffing
    imports.
    """

    #: The manifest file that produced this info (e.g. "package.json").
    source: str
    #: Languages implied by this manifest (lowercased, e.g. ["typescript"]).
    languages: list[str] = field(default_factory=list)
    #: Frameworks implied by the declared dependencies (lowercased).
    frameworks: list[str] = field(default_factory=list)
    #: All declared dependencies.
    dependencies: list[ManifestDependency] = field(default_factory=list)

    def dependency_names(self) -> list[str]:
        """Return the declared dependency names (lowercased)."""
        return [d.name.lower() for d in self.dependencies]


@dataclass(frozen=True)
class CoverageGap:
    """A single file Cortex could not parse, recorded rather than dropped.

    When a source file cannot be parsed, Cortex records a ``CoverageGap`` with
    the file path and a human-readable reason instead of silently omitting the
    file (Req 1.4). The gaps are aggregated onto the analysis ``Coverage`` so
    the user can see exactly what was missed and why.
    """

    #: Repository-relative path of the file that could not be parsed.
    file_path: str
    #: Human-readable reason (e.g. a SyntaxError message or "No parser available").
    reason: str


@dataclass(frozen=True)
class Coverage:
    """How much of the repository Cortex was able to parse and resolve (Req 6.1).

    Coverage has two independent dimensions:

    * **File coverage** — analyzed files vs. total files. A file counts as
      *analyzed* when it parsed without errors; every file that failed to parse
      is recorded as a :class:`CoverageGap` and excluded from the analyzed count.
    * **Reference coverage** — resolved vs. unresolved references. This
      aggregates the per-node ``resolved_calls``/``unresolved_calls`` and
      per-file ``resolved_imports``/``unresolved_imports`` graph properties
      produced during graph building.

    The object is zero-dependency and deterministic: the same parsed input and
    graph always produce the same ``Coverage``.
    """

    total_files: int = 0
    analyzed_files: int = 0
    resolved_references: int = 0
    unresolved_references: int = 0
    gaps: tuple[CoverageGap, ...] = ()

    def file_coverage_ratio(self) -> float:
        """Fraction of files analyzed (0..1). Empty repo → 1.0 (nothing missed)."""
        if self.total_files <= 0:
            return 1.0
        return self.analyzed_files / self.total_files

    def reference_coverage_ratio(self) -> float:
        """Fraction of references resolved (0..1). No references → 1.0."""
        total = self.resolved_references + self.unresolved_references
        if total <= 0:
            return 1.0
        return self.resolved_references / total

    def gap_count(self) -> int:
        """Number of files recorded as coverage gaps."""
        return len(self.gaps)

    def summary(self) -> dict:
        """Return a JSON-serializable summary of this coverage."""
        return {
            "total_files": self.total_files,
            "analyzed_files": self.analyzed_files,
            "resolved_references": self.resolved_references,
            "unresolved_references": self.unresolved_references,
            "file_coverage_ratio": round(self.file_coverage_ratio(), 4),
            "reference_coverage_ratio": round(self.reference_coverage_ratio(), 4),
            "gap_count": self.gap_count(),
            "gaps": [
                {"file_path": g.file_path, "reason": g.reason}
                for g in self.gaps
            ],
        }
