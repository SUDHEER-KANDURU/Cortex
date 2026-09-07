# System Overview

Cortex is an Engineering Reasoning Engine. It accepts a GitHub repository URL,
fetches and analyzes it via an in-process background task, then stores generated
artifacts for the user to browse.

## Request Flow

```
User → Frontend (Next.js) → FastAPI ──(BackgroundTasks)──> Analysis Pipeline
                               │                                  │
                               ▼                                  ▼
                            SQLite (jobs, artifacts, graph, memory, auth)
                               ▲
                        Frontend polls job status
```

1. The user submits a repo URL via the frontend form.
2. FastAPI creates a `Job` record in SQLite with status `pending`.
3. The analysis pipeline is scheduled as a FastAPI `BackgroundTask` that runs
   in the same process after the HTTP response is sent (no external queue).
4. The pipeline fetches the repo from the GitHub API, parses it, builds the
   knowledge graph, and generates the requested artifact.
5. Analysis results are stored as `Artifact` records and graph nodes/edges in
   the same SQLite database.
6. The background task updates the Job status to `completed` (or `failed`).
   Jobs left `running`/`pending` after a restart are reset to `failed` on the
   next startup (see `main.py` lifespan).
7. The frontend polls the job status every 3 seconds and displays artifacts
   when complete.

## Design Principles

- **Single-process** — pipeline analysis runs as asyncio background tasks inside
  the FastAPI process; there is no Celery, Redis queue, or separate worker.
- **SQLite-backed** — jobs, artifacts, the knowledge graph, memory, and auth all
  live in one SQLite database (`cortex.db`). No Postgres or Neo4j is required.
  (The repositories still support Postgres via `DATABASE_URL` if desired.)
- **Non-blocking** — long-running analysis never blocks the API response.
