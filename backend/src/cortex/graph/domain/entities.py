"""Graph domain entities — nodes and relationships in the knowledge graph.
Zero dependencies on Neo4j, FastAPI, or any framework."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class NodeType(str, Enum):
    REPOSITORY = "Repository"
    MODULE = "Module"
    FILE = "File"
    FUNCTION = "Function"
    CLASS = "Class"
    PATTERN = "Pattern"


class RelationshipType(str, Enum):
    CONTAINS = "CONTAINS"
    IMPORTS = "IMPORTS"
    DEPENDS_ON = "DEPENDS_ON"
    EXHIBITS = "EXHIBITS"
    CALLS = "CALLS"
    INHERITS = "INHERITS"


@dataclass
class GraphNode:
    id: str
    label: str
    node_type: NodeType
    job_id: str
    properties: dict[str, str | int | float | bool] = field(
        default_factory=dict
    )
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_entry_point(self) -> bool:
        """Returns True if this node is a top-level entry point."""
        return self.node_type in {
            NodeType.REPOSITORY,
            NodeType.MODULE,
        }

    def display_label(self) -> str:
        """Returns a human-readable label for UI display."""
        return f"{self.node_type.value}: {self.label}"


@dataclass
class GraphEdge:
    id: str
    source_id: str
    target_id: str
    relationship: RelationshipType
    job_id: str
    properties: dict[str, str | int | float | bool] = field(
        default_factory=dict
    )
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_dependency(self) -> bool:
        """Returns True if this edge represents a dependency."""
        return self.relationship in {
            RelationshipType.IMPORTS,
            RelationshipType.DEPENDS_ON,
        }