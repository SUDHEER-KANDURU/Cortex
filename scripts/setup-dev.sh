#!/usr/bin/env bash
# =============================================================================
# setup-dev.sh — First-time development environment setup
# =============================================================================

set -euo pipefail

echo "🔧 Setting up Cortex development environment..."

# Copy env file if it doesn't exist
if [ ! -f docker/.env ]; then
  cp docker/.env.example docker/.env
  echo "✅ Created docker/.env from .env.example — update passwords before use."
else
  echo "⏭️  docker/.env already exists, skipping."
fi

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend && npm install && cd ..

echo ""
echo "✅ Setup complete! Start the stack with:"
echo "   cd docker && docker compose up --build"
