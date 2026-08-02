"""SQLite/PostgreSQL job repository using SQLAlchemy async engine."""

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import select, update, func
from cortex.jobs.domain.entities import Job, JobStatus, ArtifactType
from cortex.jobs.domain.interfaces import AbstractJobRepository
from cortex.schema.models import JobModel
from shared.exceptions import NotFoundError, InfrastructureError
import structlog

logger = structlog.get_logger()


def _model_to_entity(model: JobModel) -> Job:
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
        # Fix 2 — use async_sessionmaker instead of deprecated sessionmaker
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

    async def save(self, job: Job) -> Job:
        async with self._session_factory() as session:
            try:
                model = _entity_to_model(job)
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info("job_saved", job_id=job.id)
                return _model_to_entity(model)
            except Exception as e:
                await session.rollback()
                raise InfrastructureError(f"Failed to save job {job.id}: {e}")

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
                select(JobModel).order_by(JobModel.created_at.desc())
            )
            return [_model_to_entity(m) for m in result.scalars().all()]

    async def get_by_status(self, status: JobStatus) -> list[Job]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobModel)
                .where(JobModel.status == status.value)
                .order_by(JobModel.created_at.desc())
            )
            return [_model_to_entity(m) for m in result.scalars().all()]

    async def get_by_repo_url(self, repo_url: str) -> list[Job]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobModel)
                .where(JobModel.repo_url == repo_url)
                .order_by(JobModel.created_at.desc())
            )
            return [_model_to_entity(m) for m in result.scalars().all()]

    async def get_by_artifact_type(self, artifact_type: ArtifactType) -> list[Job]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobModel).where(
                    JobModel.artifact_type == artifact_type.value
                )
            )
            return [_model_to_entity(m) for m in result.scalars().all()]

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
                    "updated_at": datetime.now(timezone.utc),  # Fix 1
                }
                if error_message is not None:
                    values["error_message"] = error_message

                await session.execute(
                    update(JobModel).where(JobModel.id == job_id).values(**values)
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
                raise InfrastructureError(f"Failed to update job {job_id}: {e}")

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
                raise InfrastructureError(f"Failed to delete job {job_id}: {e}")

    async def count_by_status(self) -> dict[JobStatus, int]:
        """Fix 3 — proper GROUP BY COUNT query instead of full table scan."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(JobModel.status, func.count(JobModel.id))
                .group_by(JobModel.status)
            )
            counts: dict[JobStatus, int] = {s: 0 for s in JobStatus}
            for status_val, count in result.all():
                counts[JobStatus(status_val)] = count
            return counts
