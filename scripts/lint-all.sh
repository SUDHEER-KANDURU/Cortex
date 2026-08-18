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

# Backend
echo ""
echo "── Backend: Ruff ───────────────────────────"
cd backend
if python -m ruff --version >/dev/null 2>&1; then
  python -m ruff check src tests
else
  echo "ruff is not installed in the current backend environment. Install backend dev dependencies first."
  exit 1
fi
cd ..

echo ""
echo "✅ All linters passed."
