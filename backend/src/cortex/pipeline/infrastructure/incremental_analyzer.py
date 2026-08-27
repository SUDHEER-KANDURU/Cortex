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
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cortex.db import get_engine
from cortex.config import get_settings
import structlog

logger = structlog.get_logger()


@dataclass
class FileHash:
    """Stored hash for a single file from a previous analysis."""
    path: str
    content_hash: str  # SHA-256 hex prefix (first 16 chars)
    line_count: int = 0


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
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
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
            current_hash = hashlib.sha256(current_files[path].encode()).hexdigest()[:16]
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
