"""Coverage computation — aggregates parse and resolution completeness.

Turns the raw analysis artifacts (the parsed files and the built graph) into a
single :class:`Coverage` object per analysis (Req 6.1):

* **File coverage** — analyzed files vs. total files. Files that failed to
  parse are recorded as :class:`CoverageGap` entries so nothing is ever
  silently dropped (Req 1.4).
* **Reference coverage** — resolved vs. unresolved references, aggregated from
  the per-node ``resolved_calls``/``unresolved_calls`` and per-file
  ``resolved_imports``/``unresolved_imports`` graph properties that the graph
  builder already records.

The computation is pure and deterministic: identical inputs always produce an
identical ``Coverage``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cortex.pipeline.domain.entities import Coverage, CoverageGap

if TYPE_CHECKING:
    from cortex.pipeline.infrastructure.ast_parser import ParsedFile
    from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult

# Graph-node/file property keys that hold resolution evidence. Kept as
# constants so this stays in lockstep with GraphBuilder's property names.
_RESOLVED_KEYS = ("resolved_calls", "resolved_imports")
_UNRESOLVED_KEYS = ("unresolved_calls", "unresolved_imports")


def collect_coverage_gaps(parsed_files: list[ParsedFile]) -> list[CoverageGap]:
    """Return a :class:`CoverageGap` for every file that failed to parse.

    A file "failed to parse" when it carries any ``parse_errors``. The reason
    is the joined error text; a file with an empty error list produces the
    generic ``"Unknown parse error"`` so a gap is never reasonless. Ordering
    follows the input order for determinism.
    """
    gaps: list[CoverageGap] = []
    for pf in parsed_files:
        if pf.has_errors():
            reason = "; ".join(e for e in pf.parse_errors if e) or "Unknown parse error"
            gaps.append(CoverageGap(file_path=pf.path, reason=reason))
    return gaps


def _sum_resolution_counts(properties: dict) -> tuple[int, int]:
    """Return (resolved, unresolved) reference counts from a properties dict."""
    resolved = 0
    unresolved = 0
    for key in _RESOLVED_KEYS:
        value = properties.get(key)
        if isinstance(value, int):
            resolved += value
    for key in _UNRESOLVED_KEYS:
        value = properties.get(key)
        if isinstance(value, int):
            unresolved += value
    return resolved, unresolved


#: Reason recorded for files skipped because the repo exceeded the file cap.
_OVER_LIMIT_REASON = "File skipped: repository exceeded the analysis file limit"


def compute_coverage(
    parsed_files: list[ParsedFile],
    graph_result: GraphBuildResult | None = None,
    skipped_files: list[str] | None = None,
) -> Coverage:
    """Compute :class:`Coverage` for one analysis (Req 1.4, Req 6.1, Req 10.3).

    ``total_files`` counts every file Cortex attempted to parse PLUS every file
    that was skipped because the repository exceeded the analysis file limit.
    ``analyzed_files`` counts those that parsed without errors. Every file that
    failed to parse OR was skipped over the limit is recorded as a
    :class:`CoverageGap` — never silently dropped. This lets analysis complete
    with partial Coverage on oversized repos instead of failing (Req 10.3).

    Resolved/unresolved reference counts are aggregated from the graph nodes'
    ``resolved_calls``/``unresolved_calls`` and the file nodes'
    ``resolved_imports``/``unresolved_imports`` properties. When no graph is
    available (e.g. graph building did not run), reference counts are zero.
    """
    gaps = collect_coverage_gaps(parsed_files)
    # Files dropped for exceeding the cap become coverage gaps too, so Coverage
    # honestly reflects partial analysis. Sorted for deterministic output.
    over_limit = sorted(skipped_files or [])
    gaps = gaps + [CoverageGap(file_path=p, reason=_OVER_LIMIT_REASON) for p in over_limit]

    total_files = len(parsed_files) + len(over_limit)
    analyzed_files = len(parsed_files) - len(collect_coverage_gaps(parsed_files))

    resolved = 0
    unresolved = 0
    if graph_result is not None:
        for node in graph_result.nodes:
            node_resolved, node_unresolved = _sum_resolution_counts(node.properties)
            resolved += node_resolved
            unresolved += node_unresolved

    return Coverage(
        total_files=total_files,
        analyzed_files=analyzed_files,
        resolved_references=resolved,
        unresolved_references=unresolved,
        gaps=tuple(gaps),
    )
