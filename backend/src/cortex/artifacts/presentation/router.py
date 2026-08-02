"""Artifacts API router."""

from fastapi import APIRouter, HTTPException, Depends
from cortex.artifacts.application.use_cases import ArtifactService
from cortex.artifacts.infrastructure.dependencies import artifact_repository
from cortex.artifacts.presentation.models import (
    ArtifactCreateRequest,
    ArtifactResponse,
    ArtifactListResponse,
)
from shared.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def get_artifact_service() -> ArtifactService:
    """Returns an ArtifactService backed by the shared repository singleton."""
    return ArtifactService(artifact_repository)


# Backwards-compatible alias — kept so any cached import still resolves.
def get_shared_artifact_repository() -> ArtifactService:
    return get_artifact_service()


@router.post(
    "",
    response_model=ArtifactResponse,
    status_code=201,
    summary="Create a new artifact",
)
async def create_artifact(
    request: ArtifactCreateRequest,
    service: ArtifactService = Depends(get_artifact_service),
) -> ArtifactResponse:
    try:
        artifact = await service.create(
            job_id=request.job_id,
            artifact_type=request.artifact_type,
            content_type=request.content_type,
            content_inline=request.content_inline,
            storage_path=request.storage_path,
        )
        return ArtifactResponse.from_artifact(artifact)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get(
    "/job/{job_id}",
    response_model=ArtifactListResponse,
    summary="List artifacts for a job",
)
async def list_artifacts_for_job(
    job_id: str,
    service: ArtifactService = Depends(get_artifact_service),
) -> ArtifactListResponse:
    artifacts = await service.list_for_job(job_id)
    return ArtifactListResponse.from_artifacts(artifacts)


@router.get(
    "/{artifact_id}",
    response_model=ArtifactResponse,
    summary="Get an artifact by ID",
)
async def get_artifact(
    artifact_id: str,
    service: ArtifactService = Depends(get_artifact_service),
) -> ArtifactResponse:
    try:
        artifact = await service.get(artifact_id)
        return ArtifactResponse.from_artifact(artifact)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Artifact not found")


# Fix 8 — DELETE /job/{job_id} must be defined BEFORE DELETE /{artifact_id}
# to prevent FastAPI routing /job/... as an artifact_id match.
@router.delete(
    "/job/{job_id}",
    summary="Delete all artifacts for a job",
)
async def delete_artifacts_for_job(
    job_id: str,
    service: ArtifactService = Depends(get_artifact_service),
) -> dict:
    count = await service.delete_all_for_job(job_id)
    return {"deleted": count, "job_id": job_id}


@router.delete(
    "/{artifact_id}",
    status_code=204,
    summary="Delete an artifact",
)
async def delete_artifact(
    artifact_id: str,
    service: ArtifactService = Depends(get_artifact_service),
) -> None:
    try:
        await service.delete(artifact_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Artifact not found")
