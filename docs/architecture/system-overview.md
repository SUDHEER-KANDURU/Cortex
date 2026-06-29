# System Overview

Cortex is a fully offline Engineering Reasoning Engine. It accepts a GitHub repository URL, clones and analyzes it using a background worker, then stores generated artifacts for the user to browse.

## Request Flow

```
User → Frontend (Next.js) → FastAPI → Redis Queue → Worker
                                  ↓                    ↓
                             PostgreSQL           Neo4j Graph
                                  ↑
                             Artifacts stored
```

1. The user submits a repo URL via the frontend form.
2. FastAPI creates a `Job` record in PostgreSQL with status `pending`.
3. A task is pushed onto the Redis queue.
4. The Celery worker picks up the task, clones the repo, and analyzes it.
5. Analysis results are stored as `Artifact` records in PostgreSQL and graph nodes in Neo4j.
6. The worker updates the Job status to `completed` (or `failed`).
7. The frontend polls the job status every 3 seconds and displays artifacts when complete.

## Design Principles

- **Fully offline** — no external API calls at any point.
- **Stateless API** — all state is stored in PostgreSQL and Neo4j.
- **Asynchronous processing** — long-running analysis never blocks the API.
