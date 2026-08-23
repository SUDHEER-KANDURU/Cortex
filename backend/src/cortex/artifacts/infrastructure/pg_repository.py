"""SQLite/PostgreSQL artifact repository.

Uses SQLAlchemy async engine — works with both SQLite (default dev setup)
and PostgreSQL (production). Named generically since `database_url` in
config.py defaults to SQLite, not Postgres.

To switch to PostgreSQL:
  1. Start Docker: docker compose -f docker/docker-compose.yml up
  2. Set DATABASE_URL=postgresql+asyncpg://... in backend/.env
  3. Run migrations: alembic upgrade head
  No code changes required — this class handles both backends.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import select, delete, func
from cortex.db import get_engine
from cortex.artifacts.domain.entities import Artifact, ArtifactContentType
from cortex.artifacts.domain.interfaces import AbstractArtifactRepository
from cortex.schema.models import ArtifactModel
from shared.exceptions import NotFoundError, InfrastructureError
import structlog

logger = structlog.get_logger()


def _model_to_entity(model: ArtifactModel) -> Artifact:
    """Convert SQLAlchemy model to domain entity."""
    return Artifact(
        id=model.id,
        job_id=model.job_id,
        artifact_type=model.artifact_type,
        content_type=ArtifactContentType(model.content_type),
        content_inline=model.content_inline,
        storage_path=model.storage_path,
        created_at=model.created_at,
    )


def _entity_to_model(artifact: Artifact) -> ArtifactModel:
    """Convert domain entity to SQLAlchemy model."""
    return ArtifactModel(
        id=artifact.id,
        job_id=artifact.job_id,
        artifact_type=artifact.artifact_type,
        content_type=artifact.content_type.value,
        content_inline=artifact.content_inline,
        storage_path=artifact.storage_path,
        created_at=artifact.created_at,
    )


class PostgresArtifactRepository(AbstractArtifactRepository):
    """Database implementation of AbstractArtifactRepository.

    Works with SQLite (dev) and PostgreSQL (production).
    Swap the DATABASE_URL environment variable to switch backends.
    """

    def __init__(self, database_url: str) -> None:
        self._engine = get_engine(database_url)
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def save(self, artifact: Artifact) -> Artifact:
        """Persist an artifact. Inserts or updates if ID already exists."""
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    select(ArtifactModel).where(
                        ArtifactModel.id == artifact.id
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Update mutable fields
                    existing.artifact_type = artifact.artifact_type
                    existing.content_type = artifact.content_type.value
                    existing.content_inline = artifact.content_inline
                    existing.storage_path = artifact.storage_path
                    saved_model = existing
                else:
                    saved_model = _entity_to_model(artifact)
                    session.add(saved_model)

                await session.commit()
                await session.refresh(saved_model)

                logger.info(
                    "artifact_saved",
                    artifact_id=artifact.id,
                    job_id=artifact.job_id,
                )
                return _model_to_entity(saved_model)

            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to save artifact {artifact.id}: {e}"
                ) from e

    async def get_by_id(self, artifact_id: str) -> Artifact | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ArtifactModel).where(
                    ArtifactModel.id == artifact_id
                )
            )
            model = result.scalar_one_or_none()
            return _model_to_entity(model) if model else None

    async def get_by_job_id(self, job_id: str) -> list[Artifact]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ArtifactModel)
                .where(ArtifactModel.job_id == job_id)
                .order_by(ArtifactModel.created_at.asc())
            )
            return [_model_to_entity(m) for m in result.scalars().all()]

    async def get_by_content_type(
        self,
        content_type: ArtifactContentType,
    ) -> list[Artifact]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ArtifactModel).where(
                    ArtifactModel.content_type == content_type.value
                )
            )
            return [_model_to_entity(m) for m in result.scalars().all()]

    async def delete_by_job_id(self, job_id: str) -> int:
        """Delete all artifacts for a job. Returns count deleted."""
        async with self._session_factory() as session:
            try:
                # Count first with a lightweight query
                count_result = await session.execute(
                    select(func.count())
                    .select_from(ArtifactModel)
                    .where(ArtifactModel.job_id == job_id)
                )
                count = count_result.scalar_one()

                await session.execute(
                    delete(ArtifactModel).where(
                        ArtifactModel.job_id == job_id
                    )
                )
                await session.commit()

                logger.info(
                    "artifacts_deleted_for_job",
                    job_id=job_id,
                    count=count,
                )
                return count

            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to delete artifacts for job {job_id}: {e}"
                ) from e

    async def delete(self, artifact_id: str) -> None:
        """Delete a single artifact by ID. Raises NotFoundError if missing."""
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    select(ArtifactModel).where(
                        ArtifactModel.id == artifact_id
                    )
                )
                model = result.scalar_one_or_none()
                if not model:
                    raise NotFoundError(
                        f"Artifact not found: {artifact_id}"
                    )
                await session.delete(model)
                await session.commit()

            except NotFoundError:
                raise
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to delete artifact {artifact_id}: {e}"
                ) from e

    async def count_by_job_id(self, job_id: str) -> int:
        """Return count of artifacts for a job using a scalar COUNT query."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(func.count())
                .select_from(ArtifactModel)
                .where(ArtifactModel.job_id == job_id)
            )
            return result.scalar_one()
