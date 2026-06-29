# Docker Topology

All six Cortex services run on a single `cortex_network` bridge network.

```
                    ┌─────────────────────────────────┐
                    │         cortex_network           │
                    │                                 │
   :3000 ──────── frontend                           │
                    │      │                          │
   :8000 ──────── api ─────┤                          │
                    │      │                          │
                  worker ──┤                          │
                    │      ▼                          │
   :5432 ──────── postgres (postgres_data volume)    │
   :6379 ──────── redis                              │
   :7474/:7687 ── neo4j (neo4j_data volume)          │
                    └─────────────────────────────────┘
```

## Health Check Dependencies

- `api` waits for: postgres healthy, redis healthy, neo4j healthy
- `worker` waits for: postgres healthy, redis healthy, neo4j healthy
- `frontend` waits for: api healthy
