# Environment Variables

Docker variables are set in `docker/.env` (copy from `docker/.env.example`).
Backend variables can also be set in `backend/.env` for local runs. Cortex uses
SQLite by default, so no database credentials are required to run it.

## Docker Variables (`docker/.env.example`)

| Variable          | Default                    | Description                                             |
|-------------------|----------------------------|---------------------------------------------------------|
| `GITHUB_TOKEN`    | — (empty)                  | GitHub PAT; raises API limit from 60 → 5000 req/hr      |
| `NIM_API_KEY`     | — (empty)                  | NVIDIA NIM key for optional AI refinement; falls back to rule-based |
| `INTERNAL_SECRET` | `change-me-to-random-string` | Secret for internal pipeline callback endpoints (`/complete`, `/fail`) |
| `JWT_SECRET`      | `change-me-in-production`  | JWT signing secret (MUST change in production)          |
| `LOG_LEVEL`       | `INFO`                     | `DEBUG`, `INFO`, `WARNING`, or `ERROR`                  |

## Frontend Variables

| Variable              | Default                 | Description         |
|-----------------------|-------------------------|---------------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Cortex API base URL |

## Application / Backend Variables (see `backend/src/cortex/config.py`)

| Variable        | Default                                  | Description                                                    |
|-----------------|------------------------------------------|----------------------------------------------------------------|
| `DATABASE_URL`  | `sqlite+aiosqlite:///./cortex.db`        | Storage backend. Default is SQLite (no external DB needed).    |
| `CORS_ORIGINS`  | `["http://localhost:3000"]`              | Allowed CORS origins                                           |
| `HOST` / `PORT` | `0.0.0.0` / `8000`                       | Bind address for the API                                      |

### Optional / not required by default

Cortex runs entirely on SQLite. The settings below exist in `config.py` for an
*optional* alternate deployment and are **not required** for the default setup:

| Variable       | Purpose (optional)                                              |
|----------------|-----------------------------------------------------------------|
| `DATABASE_URL` (Postgres) | Set to `postgresql+asyncpg://...` to use PostgreSQL instead of SQLite. The repositories support both. |
| `REDIS_URL`    | Only relevant if you later add shared, multi-worker rate-limit state. Not used in the single-process default. |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | Present in config for a possible future Neo4j graph backend. The current graph is SQLite-backed and does not use them. |
| SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, ...) | Enable outbound verification/reset emails. If unset, email sending is skipped. |
