"""SQLAlchemy ORM models — the database schema for Cortex."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Text, DateTime, Enum as SAEnum, JSON,
    ForeignKey, Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from cortex.jobs.domain.entities import JobStatus, ArtifactType
from cortex.artifacts.domain.entities import ArtifactContentType
from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.chat.domain.entities import MessageRole


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)  # Fix 1


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    status: Mapped[str] = mapped_column(
        SAEnum(JobStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False, default=JobStatus.PENDING.value, index=True,
    )
    artifact_type: Mapped[str] = mapped_column(
        SAEnum(ArtifactType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    repo_url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, onupdate=_now)

    artifacts: Mapped[list["ArtifactModel"]] = relationship(
        "ArtifactModel", back_populates="job", cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_jobs_status_created", "status", "created_at"),
        Index("ix_jobs_repo_url_status", "repo_url", "status"),
    )


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content_type: Mapped[str] = mapped_column(
        SAEnum(ArtifactContentType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    content_inline: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    job: Mapped["JobModel"] = relationship("JobModel", back_populates="artifacts")


class GraphNodeModel(Base):
    __tablename__ = "graph_nodes"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    node_type: Mapped[str] = mapped_column(
        SAEnum(NodeType, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True,
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    properties: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    __table_args__ = (Index("ix_graph_nodes_job_type", "job_id", "node_type"),)


class GraphEdgeModel(Base):
    __tablename__ = "graph_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    target_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    relationship: Mapped[str] = mapped_column(
        SAEnum(RelationshipType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    properties: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    __table_args__ = (Index("ix_graph_edges_job_rel", "job_id", "relationship"),)


class ChatSessionModel(Base):
    """A chat conversation tied to one job/repo analysis.

    NEW — replaces the in-memory `_sessions` dict that used to live in
    chat_service.py. Sessions now survive a server restart.
    """
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)

    messages: Mapped[list["ChatMessageModel"]] = relationship(
        "ChatMessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by=lambda: ChatMessageModel.created_at.asc(),
    )

    __table_args__ = (Index("ix_chat_sessions_job", "job_id"),)


class ChatMessageModel(Base):
    """One message (user or assistant) within a chat session. NEW."""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(
        SAEnum(MessageRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, index=True)

    session: Mapped["ChatSessionModel"] = relationship("ChatSessionModel", back_populates="messages")

    __table_args__ = (Index("ix_chat_messages_session_created", "session_id", "created_at"),)

class RepositorySummaryModel(Base):
    """Accumulated cross-job knowledge about a single repository, keyed
    by repo_url (not job_id) so repeat analyses build up history instead
    of starting from zero each time. NEW — Repository Memory feature."""
    __tablename__ = "repository_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    repo_url: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    repo_name: Mapped[str] = mapped_column(String(200), nullable=False)
    last_job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    analysis_count: Mapped[int] = mapped_column(nullable=False, default=1)
    overall_score: Mapped[int | None] = mapped_column(nullable=True)
    overall_grade: Mapped[str | None] = mapped_column(String(2), nullable=True)
    dominant_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_files: Mapped[int] = mapped_column(nullable=False, default=0)
    total_classes: Mapped[int] = mapped_column(nullable=False, default=0)
    total_functions: Mapped[int] = mapped_column(nullable=False, default=0)
    headline: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, onupdate=_now)


class RepositoryFactModel(Base):
    """One durable, searchable fact extracted from a completed analysis
    (e.g. "UserManager is a god class with 12 methods"). NEW — Repository
    Memory feature. Facts are the unit of keyword/semantic search."""
    __tablename__ = "repository_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    repo_url: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_symbol: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, index=True)

    __table_args__ = (Index("ix_repo_facts_repo_category", "repo_url", "category"),)