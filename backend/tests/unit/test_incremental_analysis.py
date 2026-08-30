"""Tests for Task 18 — incremental, hash-based analysis.

Covers:
  * Re-analysis re-parses ONLY changed/added files and reuses unchanged
    cached results (Req 10.1, Req 10.2).
  * A full parse and an incremental parse of an identical repository state
    produce byte-identical output (determinism, Req 10.4).
  * A repository that exceeds the analysis file limit degrades to partial
    Coverage (over-limit files recorded as gaps) rather than failing (Req 10.3).
"""

from __future__ import annotations

import uuid

import pytest

from cortex.pipeline.infrastructure.ast_parser import ASTParser, Language, ParsedFile
from cortex.pipeline.infrastructure.coverage import compute_coverage
from cortex.pipeline.infrastructure.github_client import (
    MAX_ANALYSIS_FILES,
    GitHubClient,
    GitHubTreeNode,
)
from cortex.pipeline.infrastructure.incremental_analyzer import (
    IncrementalAnalyzer,
    content_hash_of,
    deserialize_parsed_file,
    serialize_parsed_file,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def analyzer(tmp_path) -> IncrementalAnalyzer:
    """An IncrementalAnalyzer backed by an isolated temp SQLite file.

    A unique DB URL per test means get_engine's LRU cache never leaks state
    between tests, so each test starts with an empty cache.
    """
    db_file = tmp_path / f"inc_{uuid.uuid4().hex}.db"
    url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    return IncrementalAnalyzer(database_url=url)


def _parser_parse_many(files):
    return ASTParser().parse_many(files)


# ── Serialization round-trip ────────────────────────────────────────────────


def test_serialize_deserialize_round_trip() -> None:
    parser = ASTParser()
    src = (
        "class Greeter:\n"
        "    def hello(self, name):\n"
        "        return greet(name)\n"
        "\n"
        "def greet(name):\n"
        "    return 'hi ' + name\n"
    )
    parsed = parser.parse(src, "greeter.py")

    blob = serialize_parsed_file(parsed)
    restored = deserialize_parsed_file(blob)

    # Re-serializing the restored object yields the identical blob.
    assert serialize_parsed_file(restored) == blob
    assert restored.path == parsed.path
    assert restored.language == parsed.language
    assert [c.name for c in restored.classes] == [c.name for c in parsed.classes]
    assert [f.name for f in restored.all_functions()] == [
        f.name for f in parsed.all_functions()
    ]


# ── Reuse: only changed/added files are re-parsed (Req 10.1, 10.2) ───────────


async def test_reanalysis_reparses_only_changed_files(analyzer: IncrementalAnalyzer) -> None:
    await analyzer.ensure_table()
    repo = "https://github.com/example/incremental"

    files_v1 = {
        "a.py": "def a():\n    return 1\n",
        "b.py": "def b():\n    return 2\n",
        "c.py": "def c():\n    return 3\n",
    }

    # First analysis — nothing cached, everything is parsed.
    parsed_calls_1: list[str] = []

    def spy_parse_1(files):
        parsed_calls_1.extend(p for _, p in files)
        return _parser_parse_many(files)

    result_1 = await analyzer.incremental_parse(repo, files_v1, spy_parse_1)

    assert sorted(parsed_calls_1) == ["a.py", "b.py", "c.py"]
    assert result_1.reparsed_paths == ["a.py", "b.py", "c.py"]
    assert result_1.reused_paths == []

    # Second analysis — only b.py changed; a.py and c.py unchanged.
    files_v2 = dict(files_v1)
    files_v2["b.py"] = "def b():\n    return 22  # changed\n"
    files_v2["d.py"] = "def d():\n    return 4\n"  # added file

    parsed_calls_2: list[str] = []

    def spy_parse_2(files):
        parsed_calls_2.extend(p for _, p in files)
        return _parser_parse_many(files)

    result_2 = await analyzer.incremental_parse(repo, files_v2, spy_parse_2)

    # Only the changed (b.py) and added (d.py) files hit the parser.
    assert sorted(parsed_calls_2) == ["b.py", "d.py"]
    assert result_2.reparsed_paths == ["b.py", "d.py"]
    assert result_2.reused_paths == ["a.py", "c.py"]

    # The final set still contains every current file, in deterministic order.
    assert [p.path for p in result_2.parsed_files] == ["a.py", "b.py", "c.py", "d.py"]


async def test_incremental_parse_accepts_async_parse_callable(
    analyzer: IncrementalAnalyzer,
) -> None:
    """The pipeline passes an asyncio.to_thread offload — an awaitable result."""
    import asyncio

    await analyzer.ensure_table()
    repo = "https://github.com/example/async-callable"
    files = {"a.py": "def a():\n    return 1\n", "b.py": "def b():\n    return 2\n"}

    def async_parse(fs):
        return asyncio.to_thread(_parser_parse_many, fs)

    result = await analyzer.incremental_parse(repo, files, async_parse)

    assert [p.path for p in result.parsed_files] == ["a.py", "b.py"]
    assert result.reparsed_paths == ["a.py", "b.py"]


async def test_reused_file_result_matches_original(analyzer: IncrementalAnalyzer) -> None:
    await analyzer.ensure_table()
    repo = "https://github.com/example/reuse"

    files = {"keep.py": "def keep():\n    return 1\n", "edit.py": "def edit():\n    return 0\n"}
    first = await analyzer.incremental_parse(repo, files, _parser_parse_many)
    first_keep = next(p for p in first.parsed_files if p.path == "keep.py")

    # Change only edit.py; keep.py must be reused verbatim.
    files2 = dict(files)
    files2["edit.py"] = "def edit():\n    return 999\n"
    second = await analyzer.incremental_parse(repo, files2, _parser_parse_many)
    second_keep = next(p for p in second.parsed_files if p.path == "keep.py")

    assert "keep.py" in second.reused_paths
    assert serialize_parsed_file(second_keep) == serialize_parsed_file(first_keep)


# ── Determinism: full vs incremental identical output (Req 10.4) ─────────────


async def test_full_and_incremental_yield_identical_output(analyzer: IncrementalAnalyzer) -> None:
    await analyzer.ensure_table()
    repo = "https://github.com/example/determinism"

    files = {
        "z.py": "def z():\n    return call_x()\n",
        "x.py": "def call_x():\n    return 1\n",
        "m.py": "class M:\n    def run(self):\n        return z()\n",
    }

    # A "full" parse: parse every file directly, in the same deterministic
    # (sorted) order the incremental path uses.
    full_parsed = _parser_parse_many(
        [(files[p], p) for p in sorted(files)]
    )
    full_blob = [serialize_parsed_file(p) for p in full_parsed]

    # First incremental run (cold cache) then a second incremental run
    # (warm cache, everything reused) — both must match the full parse exactly.
    inc_1 = await analyzer.incremental_parse(repo, files, _parser_parse_many)
    inc_2 = await analyzer.incremental_parse(repo, files, _parser_parse_many)

    inc_1_blob = [serialize_parsed_file(p) for p in inc_1.parsed_files]
    inc_2_blob = [serialize_parsed_file(p) for p in inc_2.parsed_files]

    assert inc_1_blob == full_blob
    assert inc_2_blob == full_blob
    # Second run reused everything (identical repo state).
    assert inc_2.reused_paths == sorted(files.keys())
    assert inc_2.reparsed_paths == []


async def test_output_order_independent_of_dict_insertion_order(
    analyzer: IncrementalAnalyzer,
) -> None:
    await analyzer.ensure_table()
    repo = "https://github.com/example/order"

    forward = {"a.py": "x = 1\n", "b.py": "y = 2\n", "c.py": "z = 3\n"}
    reversed_ = {"c.py": "z = 3\n", "b.py": "y = 2\n", "a.py": "x = 1\n"}

    r1 = await analyzer.incremental_parse(repo, forward, _parser_parse_many)
    # Fresh analyzer/repo to avoid cache interference for the reversed insertion.
    r2 = await analyzer.incremental_parse(repo + "-2", reversed_, _parser_parse_many)

    assert [p.path for p in r1.parsed_files] == [p.path for p in r2.parsed_files]


# ── Partial Coverage degradation over the file limit (Req 10.3) ──────────────


def test_over_limit_files_become_coverage_gaps() -> None:
    parsed_files = [
        ParsedFile(path="kept1.py", language=Language.PYTHON, line_count=1),
        ParsedFile(path="kept2.py", language=Language.PYTHON, line_count=1),
    ]
    skipped = ["big/skipped_a.py", "big/skipped_b.py", "big/skipped_c.py"]

    # Analysis COMPLETES — compute_coverage returns rather than raising.
    coverage = compute_coverage(parsed_files, skipped_files=skipped)

    # Total counts analyzed + skipped; skipped files surface as gaps.
    assert coverage.total_files == 5
    assert coverage.analyzed_files == 2
    gap_paths = {g.file_path for g in coverage.gaps}
    assert gap_paths == set(skipped)
    # Coverage is partial (< 1.0) but the pipeline did not fail.
    assert coverage.file_coverage_ratio() == 2 / 5
    assert coverage.gap_count() == 3


def test_over_limit_gaps_are_deterministic() -> None:
    parsed_files = [ParsedFile(path="a.py", language=Language.PYTHON, line_count=1)]
    skipped = ["z.py", "a_extra.py", "m.py"]

    first = compute_coverage(parsed_files, skipped_files=skipped)
    second = compute_coverage(parsed_files, skipped_files=list(reversed(skipped)))

    assert first == second  # gap ordering is sorted, order-independent


async def test_get_code_files_records_over_limit_files_as_skipped(monkeypatch) -> None:
    """get_code_files fetches up to the cap and remembers the rest as skipped."""
    client = GitHubClient()
    try:
        # Build a synthetic tree of code files larger than a small cap.
        tree = [
            GitHubTreeNode(path=f"src/f{i}.py", type="blob", sha=f"s{i}", size=100 - i)
            for i in range(5)
        ]

        async def fake_tree(owner, repo):
            return tree

        async def fake_content(owner, repo, path):
            from cortex.pipeline.infrastructure.github_client import GitHubFile

            return GitHubFile(
                path=path,
                name=path.split("/")[-1],
                content="x = 1\n",
                size=1,
                sha="h",
            )

        monkeypatch.setattr(client, "get_file_tree", fake_tree)
        monkeypatch.setattr(client, "get_file_content", fake_content)

        fetched = await client.get_code_files("owner", "repo", max_files=2)

        # Exactly the cap is fetched; the remainder is recorded, not dropped.
        assert len(fetched) == 2
        assert len(client.last_skipped_files) == 3
        # Largest-first: f0 (size 100) and f1 (size 99) are kept.
        assert {f.path for f in fetched} == {"src/f0.py", "src/f1.py"}
        assert set(client.last_skipped_files) == {"src/f2.py", "src/f3.py", "src/f4.py"}
    finally:
        await client.close()


def test_default_cap_is_raised() -> None:
    # The fixed cap is gone — the default is far larger than the old 50/60/150.
    assert MAX_ANALYSIS_FILES >= 1000
    assert content_hash_of("abc") == content_hash_of("abc")
    assert content_hash_of("abc") != content_hash_of("abd")
