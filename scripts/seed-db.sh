#!/usr/bin/env bash
# =============================================================================
# seed-db.sh — Populate PostgreSQL with sample jobs and artifacts
# Requires the stack to be running: docker compose up
# =============================================================================

set -euo pipefail

echo "🌱 Seeding PostgreSQL with sample data..."

docker compose -f docker/docker-compose.yml exec api python -m app.scripts.seed_db

echo "✅ Database seeded."
