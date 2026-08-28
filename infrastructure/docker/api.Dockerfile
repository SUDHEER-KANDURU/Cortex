FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies for aiosqlite and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN addgroup --system cortex && adduser --system --ingroup cortex cortex

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/src ./src
COPY backend/pyproject.toml .

# Create data directory for SQLite database (writable by cortex user)
RUN mkdir -p /app/data && chown -R cortex:cortex /app/data

USER cortex

EXPOSE 8000

# Use the module path that matches the source layout
CMD ["uvicorn", "cortex.main:app", "--host", "0.0.0.0", "--port", "8000"]
