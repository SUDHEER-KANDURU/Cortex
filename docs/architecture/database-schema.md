# Database Schema

PostgreSQL 16 schema for Cortex.

## jobs

| Column        | Type        | Notes                                  |
|---------------|-------------|----------------------------------------|
| id            | UUID PK     | gen_random_uuid()                      |
| status        | ENUM        | pending, running, completed, failed, cancelled |
| artifact_type | ENUM        | folder_structure, module_breakdown, … |
| repo_url      | TEXT        | GitHub repository URL                  |
| options       | JSONB       | Optional analysis options              |
| created_at    | TIMESTAMPTZ | Default now()                          |
| updated_at    | TIMESTAMPTZ | Updated by trigger                     |

## artifacts

| Column         | Type    | Notes                            |
|----------------|---------|----------------------------------|
| id             | UUID PK |                                  |
| job_id         | UUID FK | References jobs(id) ON DELETE CASCADE |
| content_type   | TEXT    | mermaid, text/markdown, application/json |
| content_inline | TEXT    | Inline content (< 1MB)           |
| storage_path   | TEXT    | Path for large artifacts         |
| created_at     | TIMESTAMPTZ |                              |
