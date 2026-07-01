"""Job domain entities — the core business objects.
Zero dependencies on frameworks, databases, or HTTP."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactType(str, Enum):
    FOLDER_STRUCTURE = "folder_structure"
    MODULE_BREAKDOWN = "module_breakdown"
    ARCHITECTURE_DIAGRAM = "architecture_diagram"
    DATABASE_SCHEMA = "database_schema"
    API_SPEC = "api_spec"
    LEARNING_PATH = "learning_path"
    INTERVIEW_QUESTIONS = "interview_questions"


TERMINAL_STATUSES = {
    JobStatus.COMPLETED,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
}


@dataclass
class Job:
    repo_url: str
    artifact_type: ArtifactType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    error_message: str | None = None
    options: dict[str, str] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_terminal(self) -> bool:
        """Returns True if this job can no longer change status."""
        return self.status in TERMINAL_STATUSES

    def can_cancel(self) -> bool:
        """Returns True if this job can be cancelled."""
        return self.status in {JobStatus.PENDING, JobStatus.RUNNING}

    def can_retry(self) -> bool:
        """Returns True if this job can be retried."""
        return self.status == JobStatus.FAILED

    def mark_running(self) -> None:
        """Transition to RUNNING state."""
        self.status = JobStatus.RUNNING
        self.updated_at = datetime.utcnow()

    def mark_completed(self) -> None:
        """Transition to COMPLETED state."""
        self.status = JobStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def mark_failed(self, error_message: str) -> None:
        """Transition to FAILED state with an error message."""
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.utcnow()

    def mark_cancelled(self) -> None:
        """Transition to CANCELLED state."""
        self.status = JobStatus.CANCELLED
        self.updated_at = datetime.utcnow()