"""Abstract repository interface for repository memory.
Nothing in this file knows about databases, HTTP, or frameworks."""

from abc import ABC, abstractmethod
from cortex.memory.domain.entities import RepositorySummary, RepositoryFact


class AbstractMemoryRepository(ABC):
    """Defines every storage operation the memory domain needs.
    The infrastructure layer implements this against SQLite."""

    @abstractmethod
    async def get_summary_by_repo_url(self, repo_url: str) -> RepositorySummary | None:
        """Return the summary for a repo, or None if never analyzed before."""
        ...

    @abstractmethod
    async def save_summary(self, summary: RepositorySummary) -> RepositorySummary:
        """Insert a new summary or update an existing one (upsert by repo_url)."""
        ...

    @abstractmethod
    async def list_summaries(self, limit: int = 50) -> list[RepositorySummary]:
        """Return all known repository summaries, most recently updated first."""
        ...

    @abstractmethod
    async def add_facts(self, facts: list[RepositoryFact]) -> None:
        """Persist new facts extracted from a completed analysis."""
        ...

    @abstractmethod
    async def get_facts_for_repo(self, repo_url: str) -> list[RepositoryFact]:
        """Return every fact ever recorded for a repo, across all its jobs."""
        ...

    @abstractmethod
    async def search_facts(
        self, query_keywords: list[str], repo_url: str | None = None, limit: int = 10
    ) -> list[RepositoryFact]:
        """Keyword search over facts, optionally scoped to one repo."""
        ...