# Environment Variables

All variables are set in `docker/.env`. See `docker/.env.example` for the template.

## Required Variables

| Variable             | Default           | Description                     |
|----------------------|-------------------|---------------------------------|
| `POSTGRES_DB`        | `cortex`          | PostgreSQL database name        |
| `POSTGRES_USER`      | `cortex`          | PostgreSQL username             |
| `POSTGRES_PASSWORD`  | —                 | PostgreSQL password (required)  |
| `NEO4J_USER`         | `neo4j`           | Neo4j username                  |
| `NEO4J_PASSWORD`     | —                 | Neo4j password (required)       |

## Frontend Variables

| Variable                 | Default                   | Description                     |
|--------------------------|---------------------------|---------------------------------|
| `NEXT_PUBLIC_API_URL`    | `http://localhost:8000`   | Cortex API base URL             |

## Application Variables

| Variable        | Default       | Description                                  |
|-----------------|---------------|----------------------------------------------|
| `ENVIRONMENT`   | `development` | `development` or `production`                |
