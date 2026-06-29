# Clean Architecture

Cortex follows a layered architecture to keep business logic independent of frameworks.

## Layers

| Layer        | Responsibility                                      | Examples                       |
|--------------|-----------------------------------------------------|--------------------------------|
| Presentation | HTTP request/response, serialization                | FastAPI routes, Pydantic schemas |
| Application  | Use cases, orchestration                            | JobService, ArtifactService    |
| Domain       | Business entities and rules                         | Job, Artifact, GraphNode       |
| Infrastructure | External systems (DB, queue, Neo4j, filesystem)   | SQLAlchemy repos, Celery tasks |

## Dependency Rule

Dependencies point inward only. Domain has no knowledge of FastAPI or SQLAlchemy. Infrastructure implements interfaces defined in the domain.
