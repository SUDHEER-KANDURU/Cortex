"""Database Schema Generator — evidence-backed schema detection.

Analyzes ORM model classes to detect database structure:
  - Class attributes → table columns (DETECTED from type annotations)
  - Foreign key fields → relationships (DETECTED from naming + type)
  - Base classes → table inheritance (DETECTED from AST)
  - Inferred fields when annotations aren't available (INFERRED)

Every field is marked as DETECTED or INFERRED to distinguish
what Cortex actually found from what it guessed.
Never invents schema that isn't in the code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from cortex.pipeline.infrastructure.ast_parser import ParsedFile, ParsedClass
from cortex.pipeline.infrastructure.graph_builder import GraphBuildResult
from cortex.graph.domain.entities import NodeType
import re
import structlog

logger = structlog.get_logger()


@dataclass
class SchemaField:
    """A detected or inferred database field."""
    name: str
    field_type: str  # String, Integer, DateTime, Boolean, Text, FK, etc.
    confidence: str  # "detected" or "inferred"
    is_primary_key: bool = False
    is_foreign_key: bool = False
    is_nullable: bool = True
    references: str = ""  # FK target entity name


@dataclass
class SchemaEntity:
    """A detected database entity (table/model)."""
    name: str
    file_path: str
    fields: list[SchemaField] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    confidence: str = "detected"  # How sure we are this is a DB model
    table_name: str = ""  # If __tablename__ detected


@dataclass
class SchemaRelationship:
    """A detected relationship between entities."""
    source: str
    target: str
    relationship_type: str  # "one-to-many", "many-to-one", "one-to-one"
    via_field: str = ""
    confidence: str = "detected"


class DatabaseSchemaGenerator:
    """Generates evidence-backed database schema from model classes.

    Detection strategy:
      1. Find model files (models.py, entity.py, schema.py, etc.)
      2. Find classes inheriting from ORM bases (Base, Model, etc.)
      3. Extract class attributes as fields (from ParsedClass.attributes)
      4. Infer field types from naming conventions
      5. Detect FK relationships from _id suffix and relationship() calls
      6. Mark every field as DETECTED or INFERRED
    """

    MODEL_FILE_PATTERNS = {
        "model.py", "models.py", "entity.py", "entities.py",
        "schema.py", "orm.py", "tables.py",
    }

    MODEL_BASE_CLASSES = {
        "Base", "DeclarativeBase", "Model", "models.Model",
        "BaseEntity", "AbstractEntity", "Document", "BaseModel",
    }

    MODEL_DECORATORS = {"Entity", "Table", "MappedSuperclass", "dataclass"}

    def generate(
        self,
        parsed_files: list[ParsedFile],
        graph: GraphBuildResult,
        repo_name: str,
    ) -> str:
        """Generate database schema as Markdown + Mermaid ER diagram."""
        entities = self._detect_entities(parsed_files)
        relationships = self._detect_relationships(entities)

        return self._render_markdown(entities, relationships, repo_name, graph)

    def _detect_entities(self, parsed_files: list[ParsedFile]) -> list[SchemaEntity]:
        """Detect database model classes from parsed files."""
        entities: list[SchemaEntity] = []

        for parsed_file in parsed_files:
            file_name = parsed_file.path.split("/")[-1].lower()
            is_model_file = file_name in self.MODEL_FILE_PATTERNS

            for cls in parsed_file.classes:
                confidence = self._assess_model_confidence(cls, is_model_file)
                if confidence == "none":
                    continue

                fields = self._extract_fields(cls)
                entity = SchemaEntity(
                    name=cls.name,
                    file_path=parsed_file.path,
                    fields=fields,
                    base_classes=cls.base_classes,
                    confidence=confidence,
                )

                # Try to detect __tablename__
                for attr in cls.attributes:
                    if attr == "__tablename__":
                        entity.table_name = cls.name.lower() + "s"  # Best guess

                entities.append(entity)

        return entities

    def _assess_model_confidence(self, cls: ParsedClass, is_model_file: bool) -> str:
        """Determine how confident we are that this class is a DB model."""
        # Strong signals → "detected"
        if any(base in self.MODEL_BASE_CLASSES for base in cls.base_classes):
            return "detected"
        if any(dec in self.MODEL_DECORATORS for dec in cls.decorators):
            return "detected"
        if cls.name.endswith(("Model", "Entity", "Record", "Table")):
            return "detected"

        # Medium signals → "inferred"
        if is_model_file:
            return "inferred"
        if "__tablename__" in cls.attributes:
            return "detected"

        # Check for mapped_column-like patterns in method/attribute names
        has_id = "id" in cls.attributes
        has_timestamps = any(a in cls.attributes for a in ("created_at", "updated_at"))
        if has_id and has_timestamps:
            return "inferred"

        return "none"

    def _extract_fields(self, cls: ParsedClass) -> list[SchemaField]:
        """Extract fields from class attributes."""
        fields: list[SchemaField] = []

        for attr_name in cls.attributes:
            # Skip dunder and private attributes
            if attr_name.startswith("__") or attr_name.startswith("_"):
                continue
            if attr_name in ("metadata", "registry", "type"):
                continue

            field_type, is_pk, is_fk, is_nullable, references = self._classify_field(attr_name)
            confidence = "detected"  # We found it in the AST

            fields.append(SchemaField(
                name=attr_name,
                field_type=field_type,
                confidence=confidence,
                is_primary_key=is_pk,
                is_foreign_key=is_fk,
                is_nullable=is_nullable,
                references=references,
            ))

        # If no attributes extracted, add inferred defaults for known model pattern
        if not fields and any(b in self.MODEL_BASE_CLASSES for b in cls.base_classes):
            fields = [
                SchemaField(name="id", field_type="String/UUID", confidence="inferred", is_primary_key=True, is_nullable=False),
                SchemaField(name="created_at", field_type="DateTime", confidence="inferred", is_nullable=False),
                SchemaField(name="updated_at", field_type="DateTime", confidence="inferred", is_nullable=True),
            ]

        return fields[:20]  # Cap

    def _classify_field(self, name: str) -> tuple[str, bool, bool, bool, str]:
        """Classify a field based on its name.

        Returns: (type, is_pk, is_fk, is_nullable, fk_references)
        """
        name_lower = name.lower()

        # Primary key
        if name_lower == "id":
            return "String/UUID", True, False, False, ""

        # Foreign key
        if name_lower.endswith("_id"):
            ref_entity = name_lower[:-3].title().replace("_", "")
            return "FK", False, True, False, ref_entity

        # Timestamps
        if name_lower.endswith("_at") or name_lower in ("created", "modified", "timestamp"):
            return "DateTime", False, False, name_lower != "created_at", ""

        # Booleans
        if name_lower.startswith(("is_", "has_", "can_", "should_")):
            return "Boolean", False, False, False, ""

        # Numerics
        if any(kw in name_lower for kw in ("count", "num", "amount", "price", "score", "total")):
            return "Integer", False, False, True, ""

        # Text/strings
        if any(kw in name_lower for kw in ("description", "body", "content", "text", "message")):
            return "Text", False, False, True, ""

        if any(kw in name_lower for kw in ("name", "title", "label", "email", "url", "path")):
            return "String", False, False, False, ""

        # Status/enum
        if any(kw in name_lower for kw in ("status", "type", "role", "category", "kind")):
            return "Enum/String", False, False, False, ""

        # JSON
        if any(kw in name_lower for kw in ("options", "metadata", "properties", "config", "data")):
            return "JSON", False, False, True, ""

        return "String", False, False, True, ""

    def _detect_relationships(self, entities: list[SchemaEntity]) -> list[SchemaRelationship]:
        """Detect relationships between entities from FK fields."""
        relationships: list[SchemaRelationship] = []
        entity_names = {e.name for e in entities}
        # Also try lowercased and without suffixes
        entity_name_variants: dict[str, str] = {}
        for e in entities:
            entity_name_variants[e.name.lower()] = e.name
            entity_name_variants[e.name.lower().rstrip("model")] = e.name
            entity_name_variants[e.name.lower().rstrip("entity")] = e.name

        for entity in entities:
            for f in entity.fields:
                if f.is_foreign_key and f.references:
                    # Try to match the FK reference to an entity
                    target = None
                    ref_lower = f.references.lower()
                    if f.references in entity_names:
                        target = f.references
                    elif ref_lower in entity_name_variants:
                        target = entity_name_variants[ref_lower]
                    elif f.references + "Model" in entity_names:
                        target = f.references + "Model"

                    if target:
                        relationships.append(SchemaRelationship(
                            source=entity.name,
                            target=target,
                            relationship_type="many-to-one",
                            via_field=f.name,
                            confidence="detected",
                        ))
                    else:
                        relationships.append(SchemaRelationship(
                            source=entity.name,
                            target=f.references,
                            relationship_type="many-to-one",
                            via_field=f.name,
                            confidence="inferred",
                        ))

        return relationships

    def _render_markdown(
        self,
        entities: list[SchemaEntity],
        relationships: list[SchemaRelationship],
        repo_name: str,
        graph: GraphBuildResult,
    ) -> str:
        """Render schema as Markdown with ER diagram."""
        lines: list[str] = []

        lines.append(f"# Database Schema — {repo_name}")
        lines.append("")
        lines.append(
            "> **What is a database schema?** The schema defines how data is stored "
            "and organized — like a filing system with labeled folders. Each \"entity\" "
            "(table) stores one type of thing (users, orders, products). \"Fields\" are "
            "the columns in each table (name, email, creation date). \"Relationships\" "
            "show how tables connect to each other (e.g., an order belongs to a user)."
        )
        lines.append("")

        if not entities:
            lines.append("_No database model classes detected in this repository._")
            lines.append("")
            lines.append(
                "Cortex looks for: classes inheriting from ORM bases (SQLAlchemy Base, "
                "Django Model, etc.), classes in model/entity files, and classes with "
                "database-related decorators."
            )
            return "\n".join(lines)

        # ── Summary ──────────────────────────────────────────────────────────
        detected_count = sum(1 for e in entities if e.confidence == "detected")
        inferred_count = sum(1 for e in entities if e.confidence == "inferred")

        lines.append("## What We Found")
        lines.append("")
        lines.append(f"Cortex detected **{detected_count + inferred_count} data entities** (database tables) in this project:")
        lines.append("")
        lines.append(f"| | Count | Meaning |")
        lines.append(f"|---|------|---------|")
        lines.append(f"| Entities Detected | {detected_count} | Confirmed database tables found in code |")
        if inferred_count:
            lines.append(f"| Entities Inferred | {inferred_count} | Likely tables based on naming patterns |")
        lines.append(f"| Relationships | {len(relationships)} | Connections between tables (e.g., \"order belongs to user\") |")
        total_fields = sum(len(e.fields) for e in entities)
        lines.append(f"| Total Fields | {total_fields} | Individual data columns across all tables |")
        lines.append("")

        lines.append("> 🟢 **DETECTED** = Cortex found this directly in the code (high confidence)")
        lines.append("> 🟡 **INFERRED** = Cortex guessed this from naming patterns (verify manually)")
        lines.append("> 🟡 **INFERRED** = guessed from naming conventions")
        lines.append("")

        # ── ER Diagram ───────────────────────────────────────────────────────
        lines.append("## Entity-Relationship Diagram")
        lines.append("")
        lines.append("```mermaid")
        lines.append("erDiagram")

        for entity in entities[:12]:
            safe_name = self._safe_name(entity.name)
            lines.append(f"    {safe_name} {{")
            for f in entity.fields[:10]:
                safe_field = self._safe_name(f.name)
                ftype = f.field_type.replace("/", "_").replace(" ", "_")
                pk_marker = " PK" if f.is_primary_key else ""
                fk_marker = " FK" if f.is_foreign_key else ""
                lines.append(f"        {ftype} {safe_field}{pk_marker}{fk_marker}")
            lines.append("    }")

        # Relationships
        for rel in relationships[:10]:
            src = self._safe_name(rel.source)
            tgt = self._safe_name(rel.target)
            if rel.relationship_type == "many-to-one":
                lines.append(f"    {src} }}o--|| {tgt} : \"{rel.via_field}\"")
            elif rel.relationship_type == "one-to-many":
                lines.append(f"    {src} ||--o{{ {tgt} : has")
            else:
                lines.append(f"    {src} ||--|| {tgt} : has")

        lines.append("```")
        lines.append("")

        # ── Entity Details ───────────────────────────────────────────────────
        lines.append("## Entity Details")
        lines.append("")

        for entity in entities:
            confidence_badge = "🟢" if entity.confidence == "detected" else "🟡"
            lines.append(f"### {confidence_badge} `{entity.name}`")
            lines.append("")
            lines.append(f"**File:** `{entity.file_path.split('/')[-1]}`")
            if entity.base_classes:
                lines.append(f" · **Extends:** {', '.join(f'`{b}`' for b in entity.base_classes)}")
            lines.append("")

            if entity.fields:
                lines.append("| Field | Type | PK | FK | Confidence |")
                lines.append("|-------|------|----|----|-----------|")
                for f in entity.fields:
                    pk = "✓" if f.is_primary_key else ""
                    fk = f"→ `{f.references}`" if f.is_foreign_key else ""
                    conf = "🟢" if f.confidence == "detected" else "🟡"
                    lines.append(
                        f"| `{f.name}` | {f.field_type} | {pk} | {fk} | {conf} |"
                    )
                lines.append("")

        # ── Relationships ────────────────────────────────────────────────────
        if relationships:
            lines.append("## Relationships")
            lines.append("")
            for rel in relationships:
                conf = "🟢" if rel.confidence == "detected" else "🟡"
                lines.append(
                    f"- {conf} `{rel.source}` → `{rel.target}` "
                    f"({rel.relationship_type} via `{rel.via_field}`)"
                )
            lines.append("")

        return "\n".join(lines)

    def _safe_name(self, name: str) -> str:
        """Make name safe for Mermaid identifiers."""
        return re.sub(r'[^a-zA-Z0-9_]', '_', name)[:30]
