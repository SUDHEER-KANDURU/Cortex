#!/usr/bin/env bash
# =============================================================================
# seed-graph.sh — Populate Neo4j with a sample code knowledge graph
# Requires the stack to be running: docker compose up
# =============================================================================

set -euo pipefail

echo "🌱 Seeding Neo4j graph database with sample data..."

docker compose -f docker/docker-compose.yml exec api python -m app.scripts.seed_graph

echo "✅ Graph database seeded. View at http://localhost:7474"
