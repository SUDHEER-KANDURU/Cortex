"""SQLite repository memory repository using SQLAlchemy async engine.

Works with both SQLite (dev) and PostgreSQL (production) via
DATABASE_URL — same pattern as jobs/artifacts/chat repositories.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import select
from cortex.memory.domain.entities import RepositorySummary, RepositoryFact
from cortex.memory.domain.interfaces import AbstractMemoryRepository
from cortex.schema.models import RepositorySummaryModel, RepositoryFactModel
from shared.exceptions import InfrastructureError
import structlog

logger = structlog.get_logger()


def _summary_model_to_entity(model: RepositorySummaryModel) -> RepositorySummary:
    return RepositorySummary(
        id=model.id,
        repo_url=model.repo_url,
        repo_name=model.repo_name,
        last_job_id=model.last_job_id,
        analysis_count=model.analysis_count,
        overall_score=model.overall_score,
        overall_grade=model.overall_grade,
        dominant_language=model.dominant_language,
        total_files=model.total_files,
        total_classes=model.total_classes,
        total_functions=model.total_functions,
        headline=model.headline,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _fact_model_to_entity(model: RepositoryFactModel) -> RepositoryFact:
    return RepositoryFact(
        id=model.id,
        repo_url=model.repo_url,
        job_id=model.job_id,
        category=model.category,
        text=model.text,
        source_symbol=model.source_symbol,
        source_file=model.source_file,
        created_at=model.created_at,
    )


class SQLiteMemoryRepository(AbstractMemoryRepository):
    """Works with both SQLite (dev) and PostgreSQL (production).
    Set DATABASE_URL in .env to switch backends."""

    def __init__(self, database_url: str) -> None:
        connect_args: dict = {}
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}

        self._engine = create_async_engine(
            database_url,
            echo=False,
            connect_args=connect_args,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def get_summary_by_repo_url(self, repo_url: str) -> RepositorySummary | None:
        async with self._session_factory() as db:
            result = await db.execute(
                select(RepositorySummaryModel).where(
                    RepositorySummaryModel.repo_url == repo_url
                )
            )
            model = result.scalar_one_or_none()
            return _summary_model_to_entity(model) if model else None

    async def save_summary(self, summary: RepositorySummary) -> RepositorySummary:
        async with self._session_factory() as db:
            try:
                existing = await db.execute(
                    select(RepositorySummaryModel).where(
                        RepositorySummaryModel.repo_url == summary.repo_url
                    )
                )
                model = existing.scalar_one_or_none()

                if model is None:
                    model = RepositorySummaryModel(
                        id=summary.id,
                        repo_url=summary.repo_url,
                        repo_name=summary.repo_name,
                        last_job_id=summary.last_job_id,
                        analysis_count=summary.analysis_count,
                        overall_score=summary.overall_score,
                        overall_grade=summary.overall_grade,
                        dominant_language=summary.dominant_language,
                        total_files=summary.total_files,
                        total_classes=summary.total_classes,
                        total_functions=summary.total_functions,
                        headline=summary.headline,
                        created_at=summary.created_at,
                        updated_at=summary.updated_at,
                    )
                    db.add(model)
                else:
                    model.last_job_id = summary.last_job_id
                    model.analysis_count = summary.analysis_count
                    model.overall_score = summary.overall_score
                    model.overall_grade = summary.overall_grade
                    model.dominant_language = summary.dominant_language
                    model.total_files = summary.total_files
                    model.total_classes = summary.total_classes
                    model.total_functions = summary.total_functions
                    model.headline = summary.headline
                    model.updated_at = summary.updated_at

                await db.commit()
                logger.info(
                    "repository_summary_saved",
                    repo_url=summary.repo_url,
                    analysis_count=summary.analysis_count,
                )
                return summary
            except Exception as e:
                await db.rollback()
                raise InfrastructureError(
                    f"Failed to save repository summary for {summary.repo_url}: {e}"
                ) from e

    async def list_summaries(self, limit: int = 50) -> list[RepositorySummary]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(RepositorySummaryModel)
                .order_by(RepositorySummaryModel.updated_at.desc())
                .limit(limit)
            )
            return [_summary_model_to_entity(m) for m in result.scalars().all()]

    async def add_facts(self, facts: list[RepositoryFact]) -> None:
        if not facts:
            return
        async with self._session_factory() as db:
            try:
                for fact in facts:
                    db.add(
                        RepositoryFactModel(
                            id=fact.id,
                            repo_url=fact.repo_url,
                            job_id=fact.job_id,
                            category=fact.category,
                            text=fact.text,
                            source_symbol=fact.source_symbol,
                            source_file=fact.source_file,
                            created_at=fact.created_at,
                        )
                    )
                await db.commit()
                logger.info(
                    "repository_facts_added",
                    repo_url=facts[0].repo_url,
                    count=len(facts),
                )
            except Exception as e:
                await db.rollback()
                raise InfrastructureError(
                    f"Failed to save {len(facts)} repository facts: {e}"
                ) from e

    async def get_facts_for_repo(self, repo_url: str) -> list[RepositoryFact]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(RepositoryFactModel)
                .where(RepositoryFactModel.repo_url == repo_url)
                .order_by(RepositoryFactModel.created_at.desc())
            )
            return [_fact_model_to_entity(m) for m in result.scalars().all()]

    async def search_facts(
        self, query_keywords: list[str], repo_url: str | None = None, limit: int = 10
    ) -> list[RepositoryFact]:
        """Keyword search over stored facts. Scores by number of matched
        keywords found in the fact text, symbol, or file path — same
        approach as ContextRetriever's graph-node scoring, applied here
        to persisted facts instead of live graph nodes."""
        async with self._session_factory() as db:
            query = select(RepositoryFactModel)
            if repo_url:
                query = query.where(RepositoryFactModel.repo_url == repo_url)
            result = await db.execute(query)
            all_facts = result.scalars().all()

            scored: list[tuple[int, RepositoryFactModel]] = []
            for model in all_facts:
                text_lower = model.text.lower()
                symbol_lower = (model.source_symbol or "").lower()
                file_lower = (model.source_file or "").lower()
                score = 0
                for kw in query_keywords:
                    if kw in symbol_lower:
                        score += 3
                    if kw in text_lower:
                        score += 2
                    if kw in file_lower:
                        score += 1
                if score > 0:
                    scored.append((score, model))

            scored.sort(key=lambda pair: pair[0], reverse=True)
            return [_fact_model_to_entity(m) for _, m in scored[:limit]]