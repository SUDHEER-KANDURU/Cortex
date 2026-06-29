# Cortex

**Engineering Reasoning Engine** — Understand Code. Learn Engineering.

Cortex scans a GitHub repository, builds a knowledge graph of the codebase, and produces structured artifacts: architecture diagrams, module breakdowns, learning paths, vibe-code detection reports, and interview preparation guides. Fully offline — no API keys required.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind CSS · React Flow |
| Backend | Python 3.11 · FastAPI · Celery · Redis |
| Databases | PostgreSQL 16 · Neo4j 5.20 |
| Infrastructure | Docker · Docker Compose · GitHub Actions |

---

## Quick Start

```bash
git clone https://github.com/SUDHEER-KANDURU/cortex.git
cd cortex
cp docker/.env.example docker/.env
docker compose -f docker/docker-compose.yml up
```

Frontend → http://localhost:3000  
API docs → http://localhost:8000/api/docs

---

## Project Structure

```
cortex/
├── frontend/        Next.js 14 app — UI, job submission, artifact viewer
├── backend/         FastAPI API · Celery workers · Clean Architecture
├── docker/          Docker Compose stack — all 6 services
├── infrastructure/  Dockerfiles for api, worker, frontend
├── docs/            Architecture, API, and development documentation
├── scripts/         Dev setup, DB seed, lint scripts
└── .github/         CI/CD workflows and issue templates
```

---

## Services

| Service | URL | Description |
|---|---|---|
| frontend | http://localhost:3000 | Next.js frontend |
| api | http://localhost:8000 | FastAPI backend |
| api docs | http://localhost:8000/api/docs | Swagger UI |
| postgres | localhost:5432 | PostgreSQL database |
| redis | localhost:6379 | Job queue / cache |
| neo4j | http://localhost:7474 | Graph database browser |
| worker | — | Background job processor |

### Docker commands

```bash
docker compose -f docker/docker-compose.yml up --build     # build and start
docker compose -f docker/docker-compose.yml up -d --build  # background
docker compose -f docker/docker-compose.yml down           # stop (keeps volumes)
docker compose -f docker/docker-compose.yml down -v        # stop + delete volumes
```

---

## Frontend Dev

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run build
npm run lint
npm run test
npm run test:coverage
```

Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` to override the backend URL (default: `http://localhost:8000`).

---

## Backend Dev

```bash
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn src.cortex.main:app --reload --port 8000
```

---

## Backend Modules

| Module | Responsibility |
|---|---|
| jobs | Job lifecycle — create, track status, cancel |
| artifacts | Store and retrieve generated documentation artifacts |
| graph | Build and query the Neo4j engineering knowledge graph |
| pipeline | Orchestrate async repo analysis via Celery tasks |
| health | Liveness and readiness probe endpoint |
| shared | Exceptions, structured logging, correlation middleware |

Clean Architecture — four layers per module: `domain/` → `application/` → `infrastructure/` → `presentation/`  
The `domain/` layer has zero outward dependencies. import-linter enforces this in CI.

---

## API Contract

| Method | Path | Description |
|---|---|---|
| GET | /api/v1/health | Liveness + readiness probe |
| POST | /api/v1/jobs | Submit a new analysis job |
| GET | /api/v1/jobs | List all jobs |
| GET | /api/v1/jobs/{id} | Get job status |
| DELETE | /api/v1/jobs/{id} | Cancel a job |
| GET | /api/v1/artifacts/{id} | Get an artifact |
| GET | /api/v1/artifacts/job/{job_id} | List artifacts for a job |
| GET | /api/v1/graph/nodes | Query graph nodes |
| GET | /api/v1/graph/relationships | Query graph edges |

---

## Scripts

| Script | When to use |
|---|---|
| `setup-dev.sh` | First-time dev environment setup (install deps, copy env) |
| `seed-db.sh` | Populate PostgreSQL with sample jobs and artifacts |
| `seed-graph.sh` | Populate Neo4j with a sample code knowledge graph |
| `lint-all.sh` | Run all linters (frontend ESLint + Prettier, backend ruff) |

```bash
chmod +x scripts/*.sh
./scripts/setup-dev.sh
```

---

## CI/CD

| Workflow | Trigger | Jobs |
|---|---|---|
| `ci.yml` | PR to `main` | frontend-lint, frontend-test, backend-lint, backend-test |
| `release.yml` | Push tag `v*.*.*` | Build + publish Docker images |
| `security.yml` | Weekly + PR | Dependency vulnerability scan |

---

## Status

Active development — v0.1 Foundation in progress.
