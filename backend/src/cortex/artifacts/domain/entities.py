"""Artifact domain entities — the core business objects.
Zero dependencies on frameworks, databases, or HTTP."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class ArtifactContentType(str, Enum):
    MERMAID = "mermaid"
    MARKDOWN = "text/markdown"
    JSON = "application/json"
    PLAIN = "text/plain"


@dataclass
class Artifact:
    job_id: str
    artifact_type: str
    content_type: ArtifactContentType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_inline: str | None = None
    storage_path: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def has_content(self) -> bool:
        """Returns True if artifact has any content."""
        return self.content_inline is not None or \
               self.storage_path is not None

    def is_diagram(self) -> bool:
        """Returns True if this artifact is a Mermaid diagram."""
        return self.content_type == ArtifactContentType.MERMAID

    def is_markdown(self) -> bool:
        """Returns True if this artifact is markdown."""
        return self.content_type == ArtifactContentType.MARKDOWN

    def content_preview(self, max_chars: int = 200) -> str:
        """Returns a short preview of the content."""
        if not self.content_inline:
            return ""
        return self.content_inline[:max_chars] + (
            "..." if len(self.content_inline) > max_chars else ""
        )