#!/usr/bin/env bash
# =============================================================================
# lint-all.sh — Run all linters across the monorepo
# =============================================================================

set -euo pipefail

echo "🔍 Running all linters..."

# Frontend
echo ""
echo "── Frontend: ESLint ──────────────────────────"
cd frontend && npm run lint && cd ..

echo ""
echo "── Frontend: Prettier ────────────────────────"
cd frontend && npx prettier --check src && cd ..

echo ""
echo "── Frontend: TypeScript ──────────────────────"
cd frontend && npx tsc --noEmit && cd ..

# Backend (placeholder)
echo ""
echo "── Backend: ruff (placeholder) ───────────────"
if command -v ruff &>/dev/null; then
  ruff check backend/
else
  echo "ruff not installed — skipping backend lint."
fi

echo ""
echo "✅ All linters passed."
