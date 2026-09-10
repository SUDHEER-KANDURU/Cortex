# Cortex

**Engineering Reasoning Engine** — Understand Code. Learn Engineering.

Cortex scans any GitHub repository, builds a code knowledge graph from AST-level analysis (Python `ast` + tree-sitter), and generates structured artifacts that explain your system — architecture diagrams, learning paths, interview prep, and more. The graph is stored in SQLite by default (no external database required).

---

## How It Works

At a high level, you point Cortex at a GitHub repository and it turns that codebase into a queryable knowledge graph plus a set of human-readable artifacts. Data flows left to right:

```
You → API (FastAPI) → Jobs → Analysis Pipeline → GitHub (fetch files)
                                     │
                                     ├─ parse (AST / tree-sitter)
                                     ├─ detect (quality / "vibe")
                                     ├─ build  → Knowledge Graph ─┐
                                     └─ generate → Artifacts ─────┤
                                                                  ▼
   Read services (insights, reasoning, chat, overview, navigate)  SQLite
```

1. **Submit** a repo URL. The API creates a background **job**.
2. The **pipeline** fetches files from GitHub, parses them, detects quality signals, builds the **knowledge graph**, and generates **artifacts**.
3. Everything persists to **SQLite**. Read-side services then query the graph to answer questions, render diagrams, search, and chat.

A generated component diagram of the backend lives at [`docs/architecture/cortex-component-diagram.svg`](docs/architecture/cortex-component-diagram.svg) — it is produced directly from the real import graph by `docs/architecture/generate_component_diagram.py`, so it stays honest as the code changes.

---

## Features

Every feature below is backed by a real backend module. Nothing here is aspirational — planned-but-not-yet-active pieces (Neo4j, Redis/Celery, PostgreSQL) are called out explicitly in the Tech Stack section.

### Core Analysis Pipeline

The engine that turns a repository into structured knowledge.

- **Repository Scanning** — Paste any public GitHub URL. Cortex fetches the file tree and contents through the GitHub API (a `GITHUB_TOKEN` raises the rate limit from 60 to 5000 requests/hour) and indexes every file. No local clone required.
- **AST-Level Parsing** — Real abstract-syntax-tree analysis, not text grep. Python is parsed with the standard-library `ast` module; other languages use tree-sitter. Cortex extracts functions, classes, imports, and call relationships with accurate structure.
- **Code Knowledge Graph** — The heart of Cortex. Files become a graph of **nodes** (repository, modules, files, classes, functions, endpoints) connected by **typed relationships** (`CONTAINS`, `IMPORTS`, `CALLS`, `INHERITS`, `IMPLEMENTS`, `TESTS`). This graph is what every downstream feature queries. Stored in SQLite today; the repository interface is Neo4j-ready for a future swap without touching business logic.
- **Staged Pipeline** — Analysis runs as an ordered workflow: **fetch → parse → detect → build → generate**. Each stage reports live progress so the UI can show exactly where a job is.
- **Async Job Processing** — The pipeline runs in-process via FastAPI background tasks (no external broker needed). You get real-time **status and stage-progress** polling, and jobs can be cancelled mid-run. A durable queue (Celery/Redis) is a planned option for horizontal scaling.
- **Incremental Analysis** — On a re-scan, Cortex re-analyzes only the files that changed, avoiding full recomputation of large repositories.

### Generated Artifacts (6 Types)

The pipeline produces six kinds of ready-to-read documents, each grounded in the actual code.

| Artifact | What it is | Why it helps |
|---|---|---|
| **Architecture Diagrams** | Auto-generated Mermaid flowcharts of modules, dependencies, and service boundaries | See how a system fits together without reading every file |
| **Learning Paths** | An ordered curriculum of the concepts and patterns present in the codebase, from foundational to advanced | Learn a new codebase in a sensible sequence instead of wandering |
| **Interview Prep** | Technical questions derived from the project's real code, with model answers | Study a specific codebase for interviews or reviews |
| **Vibe Code Reports** | Flags likely AI-generated anti-patterns — missing error handling, duplicated logic, inconsistent naming | Catch low-quality or machine-generated code before it ships |
| **API Specifications** | Extracted API contracts and endpoint documentation | Understand the surface area of a service quickly |
| **Onboarding Guides** | Structured guides for developers joining a project | Shorten ramp-up time for new team members |

### Code Intelligence & Insights

Beyond raw structure, Cortex analyzes quality and risk.

- **Code Insights** — Structural metrics such as complexity, coupling, and cohesion, computed from the graph.
- **Security Analysis** — Scans for security-relevant patterns and issues in the analyzed code.
- **Performance Analysis** — Flags performance-sensitive constructs and potential hotspots.
- **Testing Analysis** — Assesses test coverage signals and testing patterns across the repository.
- **Blast Radius Analysis** — For any module or symbol, visualizes which dependent parts of the system a change would affect, so you can gauge impact before editing.

### Reasoning Engine

A graph-traversal reasoning layer that composes context and produces evidence-backed explanations rather than guesses.

- **Contextual Reasoning** — Traverses the knowledge graph to resolve references and assemble the relevant context for a question.
- **Scoped Explanations** — Explains a specific symbol, file, or module using only evidence found in the graph.
- **Learning Path Generation** — Builds the ordered curriculum used by the Learning Path artifact.
- **Root-Cause Analysis** — Traces a problem back through call and dependency edges to likely origins.
- **Fix Intelligence** — Suggests where and how a fix should land, informed by the surrounding graph.

### Interactive Features

How you explore an analyzed repository.

- **AI Chat** — A conversational interface grounded in the knowledge graph. Cortex authors an evidence-backed answer **deterministically** from the graph; NVIDIA NIM (if configured) only refines the wording. A grounding guard rejects any file or symbol the model invents. The feature is fully functional with NIM turned off.
- **Conversation Memory** — Chat retains per-session context and repository facts so follow-up questions stay coherent.
- **Full-Text Search** — SQLite **FTS5**-powered search across all analyzed artifacts and code.
- **Knowledge Graph Viewer** — Interactive visualization (React Flow) for exploring and querying code relationships.
- **Code Navigation** — Jump-to-definition-style navigation across the analyzed codebase.
- **Repository Overview** — A high-level summary dashboard for any analyzed repo, aggregating stats and insight scores.
- **Diagram Viewer** — Renders the generated architecture and dependency diagrams in the UI.

### Platform Features

The production-minded plumbing around the product.

- **User Authentication** — Full account lifecycle: signup, login, email verification, and password reset, with JWT-based auth.
- **Startup Safety Checks** — The app refuses to boot with the insecure default `JWT_SECRET` unless `ALLOW_INSECURE_JWT_SECRET=true` (dev only), and warns clearly about missing `GITHUB_TOKEN`/`NIM_API_KEY`/`INTERNAL_SECRET`.
- **Background Jobs** — Submit, track, and cancel analysis jobs with real-time status; jobs orphaned by a restart are automatically marked failed so nothing hangs forever.
- **Rate Limiting** — Built-in request throttling middleware to prevent abuse.
- **Health Probes** — Liveness and readiness endpoints for orchestration.
- **Structured Logging & Correlation** — `structlog`-based structured logs with a correlation ID per request for traceable debugging.
- **Clean Architecture** — Every module is split into `domain → application → infrastructure → presentation`, with the dependency rule enforced in CI by import-linter.
- **Docker-First Deployment** — A single `docker compose up` brings up the entire stack.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind CSS · React Flow · Framer Motion |
| Backend | Python 3.11 · FastAPI · structlog · tree-sitter · Python `ast` |
| Databases | SQLite (jobs, artifacts, graph, memory) · SQLite FTS5 (full-text search) |
| Job processing | In-process FastAPI background tasks (default) |
| Infrastructure | Docker · Docker Compose · GitHub Actions |
| AI | NVIDIA NIM API (**optional** — used only to refine wording; Cortex produces its own deterministic, evidence-grounded analysis and answers with NIM off) |
| Planned / optional | Neo4j (graph), PostgreSQL (relational), Celery + Redis (durable queue) — the code is structured for these but they are **not** required or used by default |

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
| postgres | localhost:5432 | PostgreSQL (optional; only if the compose profile enables it — default is SQLite) |
| redis | localhost:6379 | Redis (reserved for a future durable queue; not used by the default pipeline) |
| neo4j | http://localhost:7474 | Neo4j browser (reserved for a future graph backend; not used by default) |
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
| graph | Build and query the engineering knowledge graph (SQLite-backed; Neo4j-ready interface) |
| pipeline | Orchestrate repo analysis as an in-process staged pipeline (fetch → parse → vibe → graph → artifact) with live stage progress |
| insights | Structural code analysis and metrics |
| chat | Conversational interface grounded in the graph; NIM refines wording only (optional) |
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
| `JWT_SECRET` | **Yes (production)** | Signing key for auth tokens. The default is an insecure placeholder; the app refuses to start with it unless `ALLOW_INSECURE_JWT_SECRET=true` (dev only). |
| `ALLOW_INSECURE_JWT_SECRET` | No | Set `true` for local dev to permit the default `JWT_SECRET`. Must be `false`/unset in production. |
| `GITHUB_TOKEN` | Recommended | Raises GitHub API limit from 60 to 5000 req/hr |
| `NIM_API_KEY` | Optional | Enables NVIDIA NIM wording refinement for chat/explanations. Cortex works fully without it. |
| `INTERNAL_SECRET` | Optional | Secures internal job completion endpoints |
| `DATABASE_URL` | No | Database URL. Defaults to `sqlite+aiosqlite:///./cortex.db`. A PostgreSQL URL also works (SQLAlchemy async). |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | No | Reserved for a future Neo4j graph backend. **Not used** by the current SQLite-backed graph. |
| `REDIS_URL` | No | Reserved for a future Celery/Redis durable queue and shared rate limiting. **Not used** by the default in-process pipeline. |

---

## Scripts

| Script | When to use |
|---|---|
| `setup-dev.sh` | First-time dev environment setup (install deps, copy env) |
| `seed-db.sh` | Populate the database with sample jobs and artifacts |
| `seed-graph.sh` | Populate the knowledge graph with a sample code graph |
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
