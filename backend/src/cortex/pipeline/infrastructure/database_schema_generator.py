"""Database schema artifact generator.
Analyzes model/entity classes and generates a visual
database schema as a Mermaid ER diagram."""

from cortex.pipeline.infrastructure.ast_parser import ParsedFile
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult
from cortex.graph.domain.entities import NodeType
import re
import structlog

logger = structlog.get_logger()


class DatabaseSchemaGenerator:
    """Generates Mermaid ER diagrams from model and entity classes.

    Detects model classes by looking for:
    - Classes in files named model.py, models.py, entity.py, entities.py
    - Classes with JPA/SQLAlchemy annotations or base classes
    - Java classes extending JpaRepository or annotated @Entity
    - Python classes inheriting from Base or DeclarativeBase
    """

    # Patterns that indicate a database model class
    MODEL_FILE_PATTERNS = {
        "model.py", "models.py", "entity.py", "entities.py",
        "schema.py", "orm.py", "db.py",
    }

    MODEL_BASE_CLASSES = {
        # SQLAlchemy
        "Base", "DeclarativeBase", "Model",
        # Django
        "models.Model",
        # Java JPA
        "BaseEntity", "AbstractEntity",
    }

    MODEL_ANNOTATIONS = {
        "Entity", "Table", "MappedSuperclass",
        "mapped_column", "Column",
    }

    def generate(
        self,
        parsed_files: list[ParsedFile],
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        """Generate a Mermaid ER diagram from model classes."""

        model_classes = self._detect_model_classes(parsed_files)

        if not model_classes:
            # Fall back to showing all classes as entities
            return self._generate_from_graph(graph, repo_name)

        return self._generate_er_diagram(model_classes, repo_name)

    def _detect_model_classes(
        self, parsed_files: list[ParsedFile]
    ) -> list[dict]:
        """Find classes that represent database models."""
        model_classes = []

        for parsed_file in parsed_files:
            file_name = parsed_file.path.split("/")[-1].lower()
            is_model_file = file_name in self.MODEL_FILE_PATTERNS

            for cls in parsed_file.classes:
                is_model = False

                # Check if in a model file
                if is_model_file:
                    is_model = True

                # Check base classes
                if any(
                    base in self.MODEL_BASE_CLASSES
                    for base in cls.base_classes
                ):
                    is_model = True

                # Check decorators
                if any(
                    dec in self.MODEL_ANNOTATIONS
                    for dec in cls.decorators
                ):
                    is_model = True

                # Check class name patterns
                if any(
                    cls.name.endswith(suffix)
                    for suffix in [
                        "Model", "Entity", "Record",
                        "Schema", "Table",
                    ]
                ):
                    is_model = True

                if is_model:
                    fields = self._extract_fields(cls, parsed_file)
                    model_classes.append({
                        "name": cls.name,
                        "file": parsed_file.path,
                        "fields": fields,
                        "base_classes": cls.base_classes,
                    })

        return model_classes

    def _extract_fields(
        self, cls: "ParsedClass", parsed_file: "ParsedFile"  # type: ignore[name-defined]
    ) -> list[dict]:
        """Extract field definitions from a model class."""
        fields = []

        for method in cls.methods:
            # Skip common non-field methods
            if method.name in {
                "__init__", "__str__", "__repr__",
                "__eq__", "__hash__", "save", "delete",
                "get", "create", "update",
            }:
                continue

            # Treat short methods as potential properties/fields
            if method.line_count() <= 5:
                field_type = self._guess_field_type(method.name)
                fields.append({
                    "name": method.name,
                    "type": field_type,
                    "nullable": not method.name.endswith("_id"),
                })

        # If no methods detected as fields, use common defaults
        if not fields:
            fields = [
                {"name": "id", "type": "String", "nullable": False},
                {"name": "created_at", "type": "DateTime", "nullable": False},
                {"name": "updated_at", "type": "DateTime", "nullable": True},
            ]

        return fields[:10]  # Cap at 10 fields

    def _guess_field_type(self, field_name: str) -> str:
        """Guess the database type from a field name."""
        name_lower = field_name.lower()

        if name_lower.endswith("_id") or name_lower == "id":
            return "String PK"
        if name_lower.endswith("_at") or "date" in name_lower or "time" in name_lower:
            return "DateTime"
        if "email" in name_lower:
            return "String"
        if "count" in name_lower or "num" in name_lower or "age" in name_lower:
            return "Integer"
        if "is_" in name_lower or "has_" in name_lower or "enabled" in name_lower:
            return "Boolean"
        if "price" in name_lower or "amount" in name_lower or "salary" in name_lower:
            return "Decimal"
        if "url" in name_lower or "path" in name_lower or "description" in name_lower:
            return "Text"
        return "String"

    def _generate_er_diagram(
        self,
        model_classes: list[dict],
        repo_name: str,
    ) -> str:
        """Generate Mermaid ER diagram from model classes."""
        lines = [
            "erDiagram",
            f"    %% Database Schema — {repo_name}",
            f"    %% {len(model_classes)} entities detected",
            "",
        ]

        # Generate entity definitions
        for model in model_classes[:10]:  # Cap at 10 entities
            name = self._safe_entity_name(model["name"])
            lines.append(f"    {name} {{")

            for field in model["fields"]:
                field_name = self._safe_field_name(field["name"])
                field_type = field["type"].replace(" ", "_")
                nullable = (
                    "" if field.get("nullable") else " PK"
                )
                lines.append(
                    f"        {field_type} {field_name}{nullable}"
                )

            lines.append("    }")
            lines.append("")

        # Generate relationships based on foreign key naming
        relationships = self._detect_relationships(model_classes)
        for rel in relationships:
            lines.append(rel)

        if not relationships:
            lines.append(
                f"    %% No relationships detected automatically"
            )

        return "\n".join(lines)

    def _detect_relationships(
        self, model_classes: list[dict]
    ) -> list[str]:
        """Detect FK relationships from field names."""
        relationships = []
        entity_names = {
            self._safe_entity_name(m["name"])
            for m in model_classes
        }

        for model in model_classes:
            entity = self._safe_entity_name(model["name"])
            for field in model["fields"]:
                if field["name"].endswith("_id"):
                    # Guess the referenced entity
                    ref_name = field["name"][:-3].title().replace("_", "")
                    if ref_name in entity_names:
                        relationships.append(
                            f"    {entity} }}o--|| {ref_name} : has"
                        )

        return relationships[:8]  # Cap relationships

    def _generate_from_graph(
        self,
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        """Fall back to showing class hierarchy when no models detected."""
        lines = [
            "erDiagram",
            f"    %% Class diagram — {repo_name}",
            f"    %% No database model classes detected",
            f"    %% Showing domain entities instead",
            "",
        ]

        classes = graph.nodes_by_type(NodeType.CLASS)
        for cls in classes[:8]:
            name = self._safe_entity_name(cls.label)
            lines.append(f"    {name} {{")
            lines.append(f"        String id PK")
            lines.append(f"        String name")
            lines.append("    }")
            lines.append("")

        return "\n".join(lines)

    def _safe_entity_name(self, name: str) -> str:
        """Make entity name safe for Mermaid."""
        return re.sub(r'[^a-zA-Z0-9_]', '_', name)[:30]

    def _safe_field_name(self, name: str) -> str:
        """Make field name safe for Mermaid."""
        return re.sub(r'[^a-zA-Z0-9_]', '_', name)[:25]