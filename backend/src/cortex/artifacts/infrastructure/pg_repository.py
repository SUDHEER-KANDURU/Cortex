"""PostgreSQL artifact repository — replaces InMemoryArtifactRepository.
Uses SQLAlchemy async engine. Ready to swap in when Docker is running."""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete
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
    """PostgreSQL implementation of AbstractArtifactRepository.

    To switch from in-memory to PostgreSQL:
    1. Start Docker: docker compose -f docker/docker-compose.yml up
    2. Run migrations: alembic upgrade head
    3. In artifacts/presentation/router.py change:
       _repository = InMemoryArtifactRepository()
       to:
       _repository = PostgresArtifactRepository(database_url)
    """

    def __init__(self, database_url: str) -> None:
        connect_args = {}
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}

        self._engine = create_async_engine(
            database_url,
            echo=False,
            connect_args=connect_args,
        )
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def save(self, artifact: Artifact) -> Artifact:
        async with self._session_factory() as session:
            try:
                model = _entity_to_model(artifact)
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(
                    "artifact_saved_to_postgres",
                    artifact_id=artifact.id,
                    job_id=artifact.job_id,
                )
                return _model_to_entity(model)
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to save artifact {artifact.id}: {e}"
                )

    async def get_by_id(
        self, artifact_id: str
    ) -> Artifact | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ArtifactModel).where(
                    ArtifactModel.id == artifact_id
                )
            )
            model = result.scalar_one_or_none()
            return _model_to_entity(model) if model else None

    async def get_by_job_id(
        self, job_id: str
    ) -> list[Artifact]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ArtifactModel)
                .where(ArtifactModel.job_id == job_id)
                .order_by(ArtifactModel.created_at.asc())
            )
            return [
                _model_to_entity(m)
                for m in result.scalars().all()
            ]

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
            return [
                _model_to_entity(m)
                for m in result.scalars().all()
            ]

    async def delete_by_job_id(self, job_id: str) -> int:
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    select(ArtifactModel).where(
                        ArtifactModel.job_id == job_id
                    )
                )
                models = result.scalars().all()
                count = len(models)
                await session.execute(
                    delete(ArtifactModel).where(
                        ArtifactModel.job_id == job_id
                    )
                )
                await session.commit()
                logger.info(
                    "artifacts_deleted_from_postgres",
                    job_id=job_id,
                    count=count,
                )
                return count
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to delete artifacts for job {job_id}: {e}"
                )

    async def delete(self, artifact_id: str) -> None:
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
                )

    async def count_by_job_id(self, job_id: str) -> int:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ArtifactModel).where(
                    ArtifactModel.job_id == job_id
                )
            )
            return len(result.scalars().all())