"""FTS5 Full-Text Search Engine — Cortex's own search intelligence.

SQLite FTS5 provides BM25-ranked full-text search with zero external
dependencies. This is Cortex's SEARCH BRAIN — not NIM, not a vector DB.

Capabilities:
  - Porter stemming (searching "authenticating" finds "authentication")
  - BM25 relevance ranking (most relevant results first)
  - Phrase search ("god class" as a phrase)
  - Prefix search (auth* matches authentication, authorize, etc.)
  - Column-weighted scoring (symbol matches rank higher than text matches)

The FTS5 index is populated from:
  - repository_facts (durable facts from memory system)
  - graph_nodes (labels and properties from knowledge graph)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from cortex.db import get_engine
from cortex.config import get_settings

logger = structlog.get_logger()


@dataclass
class SearchResult:
    """A single search result with relevance score."""
    source: str  # "fact" or "node"
    text: str
    category: str = ""
    source_symbol: str = ""
    source_file: str = ""
    repo_url: str = ""
    job_id: str = ""
    relevance: float = 0.0
    node_id: str = ""


class FTSEngine:
    """SQLite FTS5 search engine for Cortex's knowledge base.

    Manages:
      - FTS5 virtual table creation
      - Index population from repository_facts and graph_nodes
      - BM25-ranked search queries
      - Index refresh after new analyses
    """

    def __init__(self, database_url: str | None = None) -> None:
        url = database_url or get_settings().database_url
        self._engine: AsyncEngine = get_engine(url)

    async def ensure_fts_tables(self) -> None:
        """Create FTS5 virtual tables if they don't exist.

        Called once at startup (in app lifespan) and is idempotent.
        """
        async with self._engine.begin() as conn:
            # FTS5 table for repository facts
            await conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
                    fact_id UNINDEXED,
                    repo_url UNINDEXED,
                    job_id UNINDEXED,
                    category,
                    source_symbol,
                    source_file,
                    text,
                    tokenize='porter unicode61'
                )
            """))

            # FTS5 table for graph node labels and properties
            await conn.execute(text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                    node_id UNINDEXED,
                    job_id UNINDEXED,
                    node_type,
                    label,
                    file_path,
                    properties_text,
                    tokenize='porter unicode61'
                )
            """))

        logger.info("fts5_tables_ensured")

    async def index_facts(self, repo_url: str, job_id: str) -> int:
        """Populate FTS5 index from repository_facts for a given repo.

        Clears previous entries for this repo_url before re-indexing
        to avoid duplicates across re-analyses.
        """
        async with self._engine.begin() as conn:
            # Clear old entries for this repo
            await conn.execute(text(
                "DELETE FROM facts_fts WHERE repo_url = :repo_url"
            ), {"repo_url": repo_url})

            # Insert current facts
            result = await conn.execute(text("""
                INSERT INTO facts_fts (fact_id, repo_url, job_id, category, source_symbol, source_file, text)
                SELECT id, repo_url, job_id, category,
                       COALESCE(source_symbol, ''),
                       COALESCE(source_file, ''),
                       text
                FROM repository_facts
                WHERE repo_url = :repo_url
            """), {"repo_url": repo_url})

            count = result.rowcount or 0
            logger.info("fts5_facts_indexed", repo_url=repo_url, count=count)
            return count

    async def index_nodes(self, job_id: str) -> int:
        """Populate FTS5 index from graph_nodes for a given job.

        Indexes node labels and key properties to make graph nodes
        searchable by natural language queries.
        """
        async with self._engine.begin() as conn:
            # Clear old entries for this job
            await conn.execute(text(
                "DELETE FROM nodes_fts WHERE job_id = :job_id"
            ), {"job_id": job_id})

            # Insert node data with searchable text from properties
            result = await conn.execute(text("""
                INSERT INTO nodes_fts (node_id, job_id, node_type, label, file_path, properties_text)
                SELECT id, job_id, node_type, label,
                       COALESCE(json_extract(properties, '$.file'), json_extract(properties, '$.path'), ''),
                       COALESCE(label, '') || ' ' ||
                       COALESCE(json_extract(properties, '$.qualified_name'), '') || ' ' ||
                       COALESCE(json_extract(properties, '$.route_info'), '') || ' ' ||
                       COALESCE(json_extract(properties, '$.decorators'), '')
                FROM graph_nodes
                WHERE job_id = :job_id
            """), {"job_id": job_id})

            count = result.rowcount or 0
            logger.info("fts5_nodes_indexed", job_id=job_id, count=count)
            return count

    async def search(
        self,
        query: str,
        job_id: str | None = None,
        repo_url: str | None = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """Search across facts and nodes using FTS5 BM25 ranking.

        The query is automatically enhanced:
          - Multi-word queries are treated as OR by default
          - Exact phrases can be quoted: "god class"
          - Prefix matching: auth* matches authentication, authorize

        Results from both facts and nodes are merged and sorted by relevance.
        """
        if not query or not query.strip():
            return []

        # Sanitize query for FTS5 (escape special chars, add OR between words)
        fts_query = self._build_fts_query(query)
        results: list[SearchResult] = []

        async with self._engine.begin() as conn:
            # Search facts
            fact_params: dict = {"query": fts_query, "limit": limit}
            fact_sql = """
                SELECT fact_id, repo_url, job_id, category, source_symbol,
                       source_file, text, rank
                FROM facts_fts
                WHERE facts_fts MATCH :query
            """
            if repo_url:
                fact_sql += " AND repo_url = :repo_url"
                fact_params["repo_url"] = repo_url
            fact_sql += " ORDER BY rank LIMIT :limit"

            try:
                fact_results = await conn.execute(text(fact_sql), fact_params)
                for row in fact_results:
                    results.append(SearchResult(
                        source="fact",
                        text=row[6],  # text column
                        category=row[3] or "",
                        source_symbol=row[4] or "",
                        source_file=row[5] or "",
                        repo_url=row[1] or "",
                        job_id=row[2] or "",
                        relevance=abs(row[7]) if row[7] else 0.0,  # rank is negative in FTS5
                    ))
            except Exception as e:
                logger.warning("fts5_fact_search_failed", error=str(e), query=query)

            # Search nodes
            node_params: dict = {"query": fts_query, "limit": limit}
            node_sql = """
                SELECT node_id, job_id, node_type, label, file_path,
                       properties_text, rank
                FROM nodes_fts
                WHERE nodes_fts MATCH :query
            """
            if job_id:
                node_sql += " AND job_id = :job_id"
                node_params["job_id"] = job_id
            node_sql += " ORDER BY rank LIMIT :limit"

            try:
                node_results = await conn.execute(text(node_sql), node_params)
                for row in node_results:
                    results.append(SearchResult(
                        source="node",
                        text=row[3],  # label
                        category=row[2] or "",  # node_type
                        source_file=row[4] or "",
                        job_id=row[1] or "",
                        relevance=abs(row[6]) if row[6] else 0.0,
                        node_id=row[0] or "",
                    ))
            except Exception as e:
                logger.warning("fts5_node_search_failed", error=str(e), query=query)

        # Sort by relevance (higher = better match)
        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:limit]

    def _build_fts_query(self, raw_query: str) -> str:
        """Convert a natural language query to FTS5 query syntax.

        Strategy:
          - If quoted, keep as phrase: "god class" → "god class"
          - Split words and join with OR for broad matching
          - Add prefix matching for partial words
        """
        query = raw_query.strip()

        # If already a phrase query (quoted), pass through
        if query.startswith('"') and query.endswith('"'):
            return query

        # Split into words, filter short ones
        words = [w.strip() for w in query.split() if len(w.strip()) >= 2]
        if not words:
            return query

        # Build OR query with prefix matching for each word
        parts = []
        for word in words:
            # Escape FTS5 special characters
            clean = word.replace('"', '').replace("'", "").replace("*", "")
            if clean:
                parts.append(f"{clean}*")  # Prefix match

        if not parts:
            return query

        # Join with OR — matches documents containing ANY of the terms
        return " OR ".join(parts)
