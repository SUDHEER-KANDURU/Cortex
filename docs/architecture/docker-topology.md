# Docker Topology

Cortex runs two services on a single `cortex_network` bridge network. Pipeline
analysis runs in-process inside the `api` container (asyncio background tasks),
so there is no separate worker, and persistence is SQLite on a mounted volume —
no Postgres, Redis, or Neo4j is required.

```
                    ┌─────────────────────────────────┐
                    │          cortex_network          │
                    │                                  │
   :3000 ──────── frontend ──▶ api                     │
                    │                                  │
   :8000 ──────── api                                  │
                    │   └─ SQLite: /app/data/cortex.db │
                    │      (cortex_data volume)        │
                    └─────────────────────────────────┘

   (optional) redis :6379 — only if running multiple API workers that need
   shared rate-limit state; commented out in docker-compose.yml by default.
```

## Health Check Dependencies

- `frontend` waits for: `api` healthy
- `api` has no service dependencies (SQLite is a local file on the `cortex_data` volume)

## Notes

- `infrastructure/docker/worker.Dockerfile` is retained only as a deprecated
  placeholder; there is no running `worker` service.
- To use PostgreSQL instead of SQLite, set `DATABASE_URL=postgresql+asyncpg://...`
  and add a `postgres` service; the repositories support both backends.
