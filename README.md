# Cortex

**Engineering Reasoning Engine** — Understand Code. Learn Engineering.

Cortex scans any GitHub repository, builds a Neo4j knowledge graph from AST-level analysis, and generates structured artifacts that explain your system — architecture diagrams, learning paths, interview prep, and more.

---

## Features

### Core Analysis Pipeline

- **Repository Scanning** — Paste a GitHub URL; Cortex clones and indexes every file
- **AST-Level Parsing** — Full abstract syntax tree analysis extracting functions, classes, imports, and call graphs (not text grep)
- **Neo4j Knowledge Graph** — 241+ nodes and 387+ relationships mapped per average repo into a queryable graph
- **Async Job Processing** — Background Celery workers handle large repos without blocking the UI, with real-time status polling

### Generated Artifacts (6 Types)

| Artifact | Description |
|---|---|
| Architecture Diagrams | Auto-generated Mermaid flowcharts showing modules, dependencies, and service boundaries |
| Learning Paths | Personalised curriculum identifying every concept and pattern in the codebase |
| Interview Prep | Technical questions grounded in actual project code with model answers |
| Vibe Code Reports | Flags AI-generated anti-patterns — missing error handling, duplicate logic, inconsistent naming |
| API Specifications | Extracted API contracts and endpoint documentation |
| Onboarding Guides | Structured guides for new developers joining a project |

### Interactive Features

| Feature | Description |
|---|---|
| AI Chat | Conversational interface powered by NVIDIA NIM with rule-based fallback |
| Full-Text Search | FTS5-powered search across all analyzed artifacts and code |
| Knowledge Graph Viewer | Interactive visualization and querying of code relationships |
| Code Navigation | Jump-to-definition style navigation across the analyzed codebase |
| Blast Radius Analysis | Visualize impact of changes across dependent modules |
| Repository Overview | High-level summary dashboard for any analyzed repo |
| Code Insights | Structural analysis results — complexity, coupling, cohesion metrics |
| Reasoning Engine | Graph traversal-based reasoning that resolves references and composes context |
| Diagram Viewer | Rendered architecture and dependency diagrams |

### Platform Features

| Feature | Description |
|---|---|
| User Authentication | Signup, login, email verification, and password reset |
| Background Jobs | Submit, track, and cancel analysis jobs with real-time status |
| Rate Limiting | Built-in request throttling to prevent abuse |
| Incremental Analysis | Re-analyze only changed files on subsequent scans |
| Health Probes | Liveness and readiness endpoints for orchestration |
| Docker-First Deployment | Single `docker compose up` spins the entire stack |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind CSS · React Flow · Framer Motion |
| Backend | Python 3.11 · FastAPI · Celery · Redis · structlog |
| Databases | PostgreSQL 16 · Neo4j 5.20 · SQLite (FTS5) |
| Infrastructure | Docker · Docker Compose · GitHub Actions |
| AI | NVIDIA NIM API (optional — falls back to rule-based analysis) |

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
├── docker/          Docker Compose stack — all services
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
| insights | Structural code analysis and metrics |
| chat | AI-powered conversational interface (NIM API + fallback) |
| memory | Conversation context and memory management |
| diagrams | Architecture and dependency diagram generation |
| search | Full-text search across artifacts and code (FTS5) |
| overview | Repository-level summary and statistics |
| auth | User authentication — signup, login, verify, reset |
| reasoning | Graph-based reasoning engine for context composition |
| navigate | Code navigation and jump-to-definition |
| health | Liveness and readiness probe endpoint |
| shared | Exceptions, structured logging, correlation middleware, rate limiting |

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
| POST | /api/v1/chat | Send a chat message |
| GET | /api/v1/memory/{session_id} | Retrieve conversation memory |
| GET | /api/v1/search | Full-text search across artifacts |
| GET | /api/v1/overview/{job_id} | Get repository overview |
| GET | /api/v1/insights/{job_id} | Get code insights for a job |
| GET | /api/v1/diagrams/{job_id} | Get generated diagrams |
| GET | /api/v1/navigate/{job_id} | Navigate code structure |
| POST | /api/v1/reasoning/query | Query the reasoning engine |
| POST | /api/v1/auth/signup | Create a new account |
| POST | /api/v1/auth/login | Authenticate and get token |
| POST | /api/v1/auth/verify | Verify email address |
| POST | /api/v1/auth/reset-password | Reset user password |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | Recommended | Raises GitHub API limit from 60 to 5000 req/hr |
| `NIM_API_KEY` | Optional | Enables AI chat via NVIDIA NIM (falls back to rule-based without it) |
| `INTERNAL_SECRET` | Optional | Secures internal job completion endpoints |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `NEO4J_URI` | Yes | Neo4j bolt connection URI |
| `REDIS_URL` | Yes | Redis connection for Celery and caching |

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
