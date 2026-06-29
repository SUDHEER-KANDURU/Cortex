# Offline Validation Checklist

Run through this checklist before declaring a local Cortex deployment functional.

## Services

- [ ] `docker compose ps` shows all 6 services as healthy
- [ ] `http://localhost:3000` loads the Cortex dashboard
- [ ] `http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `http://localhost:8000/docs` loads the Swagger UI
- [ ] `http://localhost:7474` loads the Neo4j Browser

## End-to-End Test

- [ ] Submit a GitHub URL via the dashboard form
- [ ] Job appears in the list with status `pending` → `running`
- [ ] Job transitions to `completed` (or `failed` if the repo is private/invalid)
- [ ] Artifacts appear in the right panel when status is `completed`
- [ ] If an architecture diagram is requested, the Mermaid diagram renders

## Network Isolation

- [ ] No outbound HTTP requests to external services (verify with network monitor)
- [ ] All service-to-service communication goes through `cortex_network`
