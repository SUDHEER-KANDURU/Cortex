# Offline Validation Checklist

Run through this checklist before declaring a local Cortex deployment functional.

## Services

- [ ] `docker compose ps` shows both services (`api`, `frontend`) as healthy
- [ ] `http://localhost:3000` loads the Cortex dashboard
- [ ] `http://localhost:8000/api/v1/health` returns a healthy status
- [ ] `http://localhost:8000/api/docs` loads the Swagger UI

## End-to-End Test

- [ ] Submit a GitHub URL via the dashboard form
- [ ] Job appears in the list with status `pending` → `running`
- [ ] Job transitions to `completed` (or `failed` if the repo is private/invalid)
- [ ] Artifacts appear in the right panel when status is `completed`
- [ ] If an architecture diagram is requested, the Mermaid diagram renders

## Network Isolation

- [ ] No outbound HTTP requests to external services (verify with network monitor)
- [ ] All service-to-service communication goes through `cortex_network`
