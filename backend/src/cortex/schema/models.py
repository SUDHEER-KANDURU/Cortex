"""SQLAlchemy ORM models — the database schema for Cortex.
These map directly to PostgreSQL tables.
Run `alembic revision --autogenerate` to generate migrations."""

import uuid
from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, Boolean,
    DateTime, Enum as SAEnum, JSON,
    ForeignKey, Index,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship,
)
from sqlalchemy.dialects.postgresql import UUID
from cortex.jobs.domain.entities import JobStatus, ArtifactType
from cortex.artifacts.domain.entities import ArtifactContentType
from cortex.graph.domain.entities import NodeType, RelationshipType


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


class JobModel(Base):
    """PostgreSQL table for jobs."""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )
    status: Mapped[str] = mapped_column(
        SAEnum(JobStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=JobStatus.PENDING.value,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(
        SAEnum(ArtifactType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    repo_url: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    options: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now, onupdate=_now
    )

    # Relationships
    artifacts: Mapped[list["ArtifactModel"]] = relationship(
        "ArtifactModel",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_jobs_status_created", "status", "created_at"),
        Index("ix_jobs_repo_url_status", "repo_url", "status"),
    )


class ArtifactModel(Base):
    """PostgreSQL table for artifacts."""
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    content_type: Mapped[str] = mapped_column(
        SAEnum(
            ArtifactContentType,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    content_inline: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    storage_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )

    # Relationship
    job: Mapped["JobModel"] = relationship(
        "JobModel", back_populates="artifacts"
    )


class GraphNodeModel(Base):
    """PostgreSQL table for knowledge graph nodes."""
    __tablename__ = "graph_nodes"

    id: Mapped[str] = mapped_column(
        String(100), primary_key=True
    )
    label: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    node_type: Mapped[str] = mapped_column(
        SAEnum(
            NodeType,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    properties: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )

    __table_args__ = (
        Index("ix_graph_nodes_job_type", "job_id", "node_type"),
    )


class GraphEdgeModel(Base):
    """PostgreSQL table for knowledge graph edges."""
    __tablename__ = "graph_edges"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )
    source_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship: Mapped[str] = mapped_column(
        SAEnum(
            RelationshipType,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    properties: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_now
    )

    __table_args__ = (
        Index(
            "ix_graph_edges_job_rel",
            "job_id", "relationship",
        ),
    )