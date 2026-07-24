"""PostgreSQL job repository — replaces InMemoryJobRepository.
Uses SQLAlchemy async engine. Swap in main.py when Docker is running."""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from cortex.jobs.domain.entities import Job, JobStatus, ArtifactType
from cortex.jobs.domain.interfaces import AbstractJobRepository
from cortex.schema.models import JobModel
from shared.exceptions import NotFoundError, InfrastructureError
import structlog

logger = structlog.get_logger()


def _model_to_entity(model: JobModel) -> Job:
    """Convert a SQLAlchemy model to a domain entity."""
    return Job(
        id=model.id,
        repo_url=model.repo_url,
        artifact_type=ArtifactType(model.artifact_type),
        status=JobStatus(model.status),
        error_message=model.error_message,
        options=model.options,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _entity_to_model(job: Job) -> JobModel:
    """Convert a domain entity to a SQLAlchemy model."""
    return JobModel(
        id=job.id,
        repo_url=job.repo_url,
        artifact_type=job.artifact_type.value,
        status=job.status.value,
        error_message=job.error_message,
        options=job.options,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


class PostgresJobRepository(AbstractJobRepository):
    """PostgreSQL implementation of AbstractJobRepository.

    Requires a running PostgreSQL instance.
    Configure DATABASE_URL in .env before using this.

    To switch from in-memory to PostgreSQL:
    1. Start Docker: docker compose -f docker/docker-compose.yml up
    2. Run migrations: alembic upgrade head
    3. In jobs/presentation/router.py change:
       _repository = InMemoryJobRepository()
       to:
       _repository = PostgresJobRepository(database_url)
    """

    def __init__(self, database_url: str) -> None:
        self._engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def save(self, job: Job) -> Job:
        async with self._session_factory() as session:
            try:
                model = _entity_to_model(job)
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info("job_saved_to_postgres", job_id=job.id)
                return _model_to_entity(model)
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to save job {job.id}: {e}"
                )

    async def get_by_id(self, job_id: str) -> Job | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobModel).where(JobModel.id == job_id)
            )
            model = result.scalar_one_or_none()
            return _model_to_entity(model) if model else None

    async def get_all(self) -> list[Job]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobModel).order_by(
                    JobModel.created_at.desc()
                )
            )
            return [
                _model_to_entity(m)
                for m in result.scalars().all()
            ]

    async def get_by_status(self, status: JobStatus) -> list[Job]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobModel).where(
                    JobModel.status == status.value
                ).order_by(JobModel.created_at.desc())
            )
            return [
                _model_to_entity(m)
                for m in result.scalars().all()
            ]

    async def get_by_repo_url(self, repo_url: str) -> list[Job]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobModel).where(
                    JobModel.repo_url == repo_url
                ).order_by(JobModel.created_at.desc())
            )
            return [
                _model_to_entity(m)
                for m in result.scalars().all()
            ]

    async def get_by_artifact_type(
        self, artifact_type: ArtifactType
    ) -> list[Job]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobModel).where(
                    JobModel.artifact_type == artifact_type.value
                )
            )
            return [
                _model_to_entity(m)
                for m in result.scalars().all()
            ]

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: str | None = None,
    ) -> Job:
        async with self._session_factory() as session:
            try:
                values: dict = {
                    "status": status.value,
                    "updated_at": datetime.utcnow(),
                }
                if error_message is not None:
                    values["error_message"] = error_message

                await session.execute(
                    update(JobModel)
                    .where(JobModel.id == job_id)
                    .values(**values)
                )
                await session.commit()

                result = await session.execute(
                    select(JobModel).where(JobModel.id == job_id)
                )
                model = result.scalar_one_or_none()
                if not model:
                    raise NotFoundError(f"Job not found: {job_id}")
                return _model_to_entity(model)

            except NotFoundError:
                raise
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to update job {job_id}: {e}"
                )

    async def delete(self, job_id: str) -> None:
        async with self._session_factory() as session:
            try:
                result = await session.execute(
                    select(JobModel).where(JobModel.id == job_id)
                )
                model = result.scalar_one_or_none()
                if not model:
                    raise NotFoundError(f"Job not found: {job_id}")
                await session.delete(model)
                await session.commit()
            except NotFoundError:
                raise
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(
                    f"Failed to delete job {job_id}: {e}"
                )

    async def count_by_status(self) -> dict[JobStatus, int]:
        async with self._session_factory() as session:
            result = await session.execute(select(JobModel))
            all_jobs = result.scalars().all()
            counts: dict[JobStatus, int] = {
                s: 0 for s in JobStatus
            }
            for job in all_jobs:
                counts[JobStatus(job.status)] += 1
            return counts