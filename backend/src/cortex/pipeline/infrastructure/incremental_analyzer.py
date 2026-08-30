"""Incremental Analysis Engine — Cortex's own intelligence for detecting change.

When re-analyzing the same repository, this module determines WHICH files
changed since the last analysis, enabling the pipeline to skip unchanged files.

This is Cortex's CHANGE DETECTION BRAIN — deterministic, no AI:
  1. Store SHA hashes of file contents per job
  2. On re-analysis, compare current tree against stored hashes
  3. Return only the changed file paths
  4. Delete stale graph nodes for changed files
  5. Pipeline re-parses only changed files

Performance impact:
  Full analysis of 10,000 files: ~60 seconds
  Incremental (5 files changed): ~2 seconds

Storage: ~40 bytes per file (path + sha256 prefix) = ~400KB for 10K files
"""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cortex.db import get_engine
from cortex.config import get_settings
import structlog

if TYPE_CHECKING:
    from cortex.pipeline.infrastructure.ast_parser import ParsedFile

logger = structlog.get_logger()


def content_hash_of(content: str) -> str:
    """Return the canonical content hash used across incremental analysis.

    A single definition keeps hashing consistent everywhere (store_hashes,
    compute_diff, and the parsed-result cache all use this), so identical file
    content always maps to the same key (Req 10.4).
    """
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def serialize_parsed_file(parsed: "ParsedFile") -> str:
    """Serialize a ``ParsedFile`` to a deterministic JSON string.

    ``dataclasses.asdict`` recurses through the nested functions/classes/imports
    dataclasses. The ``Language`` enum is stored as its string value. Keys are
    sorted so identical inputs always produce byte-identical output (Req 10.4).
    """
    data = asdict(parsed)
    data["language"] = parsed.language.value
    return json.dumps(data, sort_keys=True)


def deserialize_parsed_file(blob: str) -> "ParsedFile":
    """Reconstruct a ``ParsedFile`` from :func:`serialize_parsed_file` output."""
    from cortex.pipeline.infrastructure.ast_parser import (
        Language,
        ParsedClass,
        ParsedFile,
        ParsedFunction,
        ParsedImport,
    )

    data = json.loads(blob)

    def _fn(d: dict) -> ParsedFunction:
        return ParsedFunction(**d)

    def _cls(d: dict) -> ParsedClass:
        methods = [_fn(m) for m in d.get("methods", [])]
        return ParsedClass(**{**d, "methods": methods})

    def _imp(d: dict) -> ParsedImport:
        return ParsedImport(**d)

    return ParsedFile(
        path=data["path"],
        language=Language(data["language"]),
        functions=[_fn(f) for f in data.get("functions", [])],
        classes=[_cls(c) for c in data.get("classes", [])],
        imports=[_imp(i) for i in data.get("imports", [])],
        line_count=data.get("line_count", 0),
        parse_errors=list(data.get("parse_errors", [])),
        is_test_file=data.get("is_test_file", False),
        is_config_file=data.get("is_config_file", False),
        docstring=data.get("docstring"),
    )


@dataclass
class FileHash:
    """Stored hash for a single file from a previous analysis."""
    path: str
    content_hash: str  # SHA-256 hex prefix (first 16 chars)
    line_count: int = 0


#: Callable that turns [(content, path)] into a list of ParsedFile. The pipeline
#: passes ``ASTParser.parse_many`` (optionally thread-offloaded) as this callable.
ParseFilesCallable = Any


@dataclass
class IncrementalParseResult:
    """Result of :meth:`IncrementalAnalyzer.incremental_parse`."""
    #: All parsed files (reused + re-parsed) in deterministic path order.
    parsed_files: list["ParsedFile"] = field(default_factory=list)
    #: Paths whose cached ParsedFile was reused (content unchanged).
    reused_paths: list[str] = field(default_factory=list)
    #: Paths that were (re-)parsed this run (changed, added, or uncached).
    reparsed_paths: list[str] = field(default_factory=list)


@dataclass
class IncrementalDiff:
    """Result of comparing current files against stored hashes."""
    total_files: int = 0
    unchanged_count: int = 0
    changed_count: int = 0
    added_count: int = 0
    removed_count: int = 0
    # The actual paths
    changed_files: list[str] = field(default_factory=list)
    added_files: list[str] = field(default_factory=list)
    removed_files: list[str] = field(default_factory=list)
    # Whether incremental is possible (requires previous hashes)
    is_incremental: bool = False

    @property
    def affected_files(self) -> list[str]:
        """All files that need re-processing."""
        return self.changed_files + self.added_files


class IncrementalAnalyzer:
    """Manages file hash storage and change detection.

    Uses a dedicated SQLite table (file_hashes) to store content hashes
    keyed by (repo_url, file_path). On re-analysis, compares current
    file contents against stored hashes to produce a minimal diff.
    """

    def __init__(self, database_url: str | None = None) -> None:
        url = database_url or get_settings().database_url
        self._engine: AsyncEngine = get_engine(url)

    async def ensure_table(self) -> None:
        """Create the file_hashes table if it doesn't exist."""
        async with self._engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS file_hashes (
                    repo_url TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    line_count INTEGER DEFAULT 0,
                    job_id TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (repo_url, file_path)
                )
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_file_hashes_repo
                ON file_hashes(repo_url)
            """))
            # Cache of parsed results keyed by (repo_url, file_path, content_hash).
            # This is the source of truth for reusing UNCHANGED files on
            # re-analysis: if a file's content hash matches a cached row, its
            # ParsedFile is reconstructed from the stored blob instead of being
            # re-parsed (Req 10.2, Req 10.4).
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS parsed_results (
                    repo_url TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    parsed_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (repo_url, file_path, content_hash)
                )
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_parsed_results_repo
                ON parsed_results(repo_url)
            """))

    async def store_hashes(
        self,
        repo_url: str,
        job_id: str,
        file_contents: dict[str, str],
    ) -> int:
        """Store content hashes for all files in a job.

        Replaces any existing hashes for this repo_url (each re-analysis
        fully refreshes the hash table for that repo).
        """
        if not file_contents:
            return 0

        async with self._engine.begin() as conn:
            # Clear old hashes for this repo
            await conn.execute(
                text("DELETE FROM file_hashes WHERE repo_url = :repo_url"),
                {"repo_url": repo_url},
            )

            # Insert new hashes
            count = 0
            for path, content in file_contents.items():
                content_hash = content_hash_of(content)
                line_count = content.count("\n") + 1
                await conn.execute(
                    text("""
                        INSERT INTO file_hashes (repo_url, file_path, content_hash, line_count, job_id)
                        VALUES (:repo_url, :path, :hash, :lines, :job_id)
                    """),
                    {
                        "repo_url": repo_url,
                        "path": path,
                        "hash": content_hash,
                        "lines": line_count,
                        "job_id": job_id,
                    },
                )
                count += 1

        logger.info(
            "file_hashes_stored",
            repo_url=repo_url,
            job_id=job_id,
            file_count=count,
        )
        return count

    async def get_stored_hashes(self, repo_url: str) -> dict[str, FileHash]:
        """Get all stored file hashes for a repository.

        Returns: {file_path: FileHash} dict, empty if no previous analysis.
        """
        async with self._engine.begin() as conn:
            result = await conn.execute(
                text("SELECT file_path, content_hash, line_count FROM file_hashes WHERE repo_url = :repo_url"),
                {"repo_url": repo_url},
            )
            rows = result.fetchall()

        return {
            row[0]: FileHash(path=row[0], content_hash=row[1], line_count=row[2] or 0)
            for row in rows
        }

    async def store_parsed_results(
        self,
        repo_url: str,
        parsed_by_path: dict[str, "ParsedFile"],
        file_contents: dict[str, str],
    ) -> int:
        """Persist parsed results so unchanged files can be reused next run.

        Rows are keyed by (repo_url, file_path, content_hash). Only files whose
        content is available are stored. Existing rows for this repo are cleared
        first so the cache always reflects the latest analyzed state and never
        grows unbounded across re-analyses.
        """
        if not parsed_by_path:
            return 0

        async with self._engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM parsed_results WHERE repo_url = :repo_url"),
                {"repo_url": repo_url},
            )
            count = 0
            for path, parsed in parsed_by_path.items():
                content = file_contents.get(path)
                if content is None:
                    continue
                await conn.execute(
                    text("""
                        INSERT OR REPLACE INTO parsed_results
                            (repo_url, file_path, content_hash, parsed_json)
                        VALUES (:repo_url, :path, :hash, :blob)
                    """),
                    {
                        "repo_url": repo_url,
                        "path": path,
                        "hash": content_hash_of(content),
                        "blob": serialize_parsed_file(parsed),
                    },
                )
                count += 1

        logger.info(
            "parsed_results_stored",
            repo_url=repo_url,
            file_count=count,
        )
        return count

    async def get_cached_parsed_results(
        self,
        repo_url: str,
    ) -> dict[tuple[str, str], "ParsedFile"]:
        """Return cached parsed results keyed by (file_path, content_hash).

        The content hash is part of the key so a reused result is only returned
        when the file content is byte-for-byte identical to what was parsed
        before (Req 10.2). Returns an empty dict when nothing is cached.
        """
        async with self._engine.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT file_path, content_hash, parsed_json "
                    "FROM parsed_results WHERE repo_url = :repo_url"
                ),
                {"repo_url": repo_url},
            )
            rows = result.fetchall()

        cache: dict[tuple[str, str], "ParsedFile"] = {}
        for path, chash, blob in rows:
            try:
                cache[(path, chash)] = deserialize_parsed_file(blob)
            except Exception as err:  # pragma: no cover - defensive
                logger.warning(
                    "parsed_result_deserialize_failed",
                    repo_url=repo_url,
                    file_path=path,
                    error=str(err),
                )
        return cache

    async def compute_diff(
        self,
        repo_url: str,
        current_files: dict[str, str],
    ) -> IncrementalDiff:
        """Compare current file contents against stored hashes.

        Returns an IncrementalDiff showing what changed, was added, or removed.
        If no previous hashes exist, returns is_incremental=False (full analysis needed).
        """
        stored = await self.get_stored_hashes(repo_url)
        diff = IncrementalDiff(total_files=len(current_files))

        if not stored:
            # No previous analysis — must do full
            diff.is_incremental = False
            diff.added_files = list(current_files.keys())
            diff.added_count = len(current_files)
            return diff

        diff.is_incremental = True
        current_paths = set(current_files.keys())
        stored_paths = set(stored.keys())

        # Added files (in current but not in stored)
        diff.added_files = sorted(current_paths - stored_paths)
        diff.added_count = len(diff.added_files)

        # Removed files (in stored but not in current)
        diff.removed_files = sorted(stored_paths - current_paths)
        diff.removed_count = len(diff.removed_files)

        # Changed files (in both, but hash differs)
        common_paths = current_paths & stored_paths
        for path in sorted(common_paths):
            current_hash = content_hash_of(current_files[path])
            if current_hash != stored[path].content_hash:
                diff.changed_files.append(path)

        diff.changed_count = len(diff.changed_files)
        diff.unchanged_count = len(common_paths) - diff.changed_count

        logger.info(
            "incremental_diff_computed",
            repo_url=repo_url,
            total=diff.total_files,
            changed=diff.changed_count,
            added=diff.added_count,
            removed=diff.removed_count,
            unchanged=diff.unchanged_count,
        )

        return diff

    async def incremental_parse(
        self,
        repo_url: str,
        file_contents: dict[str, str],
        parse_files: "ParseFilesCallable",
    ) -> "IncrementalParseResult":
        """Parse ``file_contents`` reusing unchanged cached results (Req 10.1, 10.2).

        Determines which files changed via stored content hashes, re-parses ONLY
        the changed/added files, and reuses the cached ``ParsedFile`` for every
        unchanged file whose content hash matches. The parsed results and hashes
        for the whole current file set are then persisted so the next run can
        reuse them.

        ``parse_files`` is an injected callable that turns ``[(content, path)]``
        into ``[ParsedFile]`` (the pipeline passes ``ASTParser.parse_many`` via a
        thread offload). Output ordering follows ``sorted(file_contents)`` so the
        result is deterministic regardless of dict insertion order (Req 10.4).
        """
        cache = await self.get_cached_parsed_results(repo_url)

        ordered_paths = sorted(file_contents.keys())
        reused: dict[str, ParsedFile] = {}
        to_parse: list[tuple[str, str]] = []  # (content, path)

        for path in ordered_paths:
            content = file_contents[path]
            key = (path, content_hash_of(content))
            cached = cache.get(key)
            if cached is not None:
                reused[path] = cached
            else:
                to_parse.append((content, path))

        newly_parsed_list = parse_files(to_parse) if to_parse else []
        # Allow parse_files to be async (e.g. an asyncio.to_thread offload) so
        # callers can keep CPU-bound parsing off the event loop.
        if inspect.isawaitable(newly_parsed_list):
            newly_parsed_list = await newly_parsed_list
        newly_parsed = {pf.path: pf for pf in newly_parsed_list}

        # Assemble the final result in deterministic path order.
        parsed_by_path: dict[str, ParsedFile] = {}
        for path in ordered_paths:
            if path in newly_parsed:
                parsed_by_path[path] = newly_parsed[path]
            elif path in reused:
                parsed_by_path[path] = reused[path]

        # Persist the fresh state for the next run.
        await self.store_parsed_results(repo_url, parsed_by_path, file_contents)

        result = IncrementalParseResult(
            parsed_files=[parsed_by_path[p] for p in ordered_paths if p in parsed_by_path],
            reused_paths=sorted(reused.keys()),
            reparsed_paths=sorted(newly_parsed.keys()),
        )

        logger.info(
            "incremental_parse_completed",
            repo_url=repo_url,
            total=len(result.parsed_files),
            reused=len(result.reused_paths),
            reparsed=len(result.reparsed_paths),
        )
        return result

    async def delete_graph_nodes_for_files(
        self,
        job_id: str,
        file_paths: list[str],
    ) -> int:
        """Delete graph nodes and edges for specific files.

        Used before re-parsing changed files to avoid duplicate nodes.
        Deletes nodes where properties->>'file' matches any of the given paths,
        plus their associated edges.
        """
        if not file_paths:
            return 0

        async with self._engine.begin() as conn:
            # Find node IDs for these files
            # SQLite JSON extraction: json_extract(properties, '$.file')
            placeholders = ", ".join(f":p{i}" for i in range(len(file_paths)))
            params: dict[str, Any] = {f"p{i}": p for i, p in enumerate(file_paths)}
            params["job_id"] = job_id

            result = await conn.execute(text(f"""
                SELECT id FROM graph_nodes
                WHERE job_id = :job_id
                AND json_extract(properties, '$.file') IN ({placeholders})
            """), params)
            node_ids = [row[0] for row in result.fetchall()]

            if not node_ids:
                return 0

            # Delete edges referencing these nodes
            id_placeholders = ", ".join(f":nid{i}" for i in range(len(node_ids)))
            id_params = {f"nid{i}": nid for i, nid in enumerate(node_ids)}
            id_params["job_id"] = job_id

            await conn.execute(text(f"""
                DELETE FROM graph_edges
                WHERE job_id = :job_id
                AND (source_id IN ({id_placeholders}) OR target_id IN ({id_placeholders}))
            """), id_params)

            # Delete the nodes themselves
            await conn.execute(text(f"""
                DELETE FROM graph_nodes
                WHERE job_id = :job_id
                AND id IN ({id_placeholders})
            """), id_params)

            logger.info(
                "incremental_graph_cleanup",
                job_id=job_id,
                files_cleaned=len(file_paths),
                nodes_deleted=len(node_ids),
            )
            return len(node_ids)
