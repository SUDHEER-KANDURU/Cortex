"""Pydantic models for the Artifacts API."""

from datetime import datetime
from pydantic import BaseModel
from cortex.artifacts.domain.entities import ArtifactContentType


class ArtifactCreateRequest(BaseModel):
    job_id: str
    artifact_type: str
    content_type: ArtifactContentType
    content_inline: str | None = None
    storage_path: str | None = None


class ArtifactResponse(BaseModel):
    id: str
    job_id: str
    artifact_type: str
    content_type: ArtifactContentType
    content_inline: str | None = None
    storage_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_artifact(cls, artifact: "Artifact") -> "ArtifactResponse":  # type: ignore[name-defined]
        return cls(
            id=artifact.id,
            job_id=artifact.job_id,
            artifact_type=artifact.artifact_type,
            content_type=artifact.content_type,
            content_inline=artifact.content_inline,
            storage_path=artifact.storage_path,
            created_at=artifact.created_at,
        )


class ArtifactListResponse(BaseModel):
    artifacts: list[ArtifactResponse]
    total: int

    @classmethod
    def from_artifacts(cls, artifacts: list) -> "ArtifactListResponse":
        return cls(
            artifacts=[ArtifactResponse.from_artifact(a) for a in artifacts],
            total=len(artifacts),
        )