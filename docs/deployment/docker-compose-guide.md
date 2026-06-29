# Docker Compose Guide

## Prerequisites

- Docker Desktop 4.x+ (or Docker Engine 24+ with Compose plugin)
- 8 GB RAM recommended (Neo4j is memory-intensive)

## First-Time Setup

```bash
# 1. Copy env file
cp docker/.env.example docker/.env

# 2. Edit passwords (optional for local dev)
# Edit docker/.env

# 3. Build and start
cd docker
docker compose up --build
```

## Useful Commands

```bash
# View logs for a specific service
docker compose logs -f api

# Restart a single service
docker compose restart frontend

# Rebuild a single service
docker compose up --build frontend

# Stop without removing data
docker compose down

# Stop and remove all data volumes (destructive)
docker compose down -v
```

## Accessing Services

| Service    | URL                          |
|------------|------------------------------|
| Frontend   | http://localhost:3000        |
| API        | http://localhost:8000        |
| API Docs   | http://localhost:8000/docs   |
| Neo4j Browser | http://localhost:7474     |
