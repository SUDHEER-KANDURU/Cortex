# =============================================================================
# Cortex Worker — DEPRECATED
#
# Cortex does NOT use Celery or a separate background worker process.
# Pipeline jobs run as asyncio background tasks within the FastAPI process.
#
# This file is retained for reference only. If you need to scale pipeline
# processing to a separate worker in the future, you would implement a
# job-queue consumer here (e.g., using arq, dramatiq, or a custom asyncio
# worker that polls the jobs table).
#
# For now, the api.Dockerfile serves both API requests and background pipeline
# execution in the same process.
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

RUN addgroup --system cortex && adduser --system --ingroup cortex cortex

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/src ./src
COPY backend/pyproject.toml .

USER cortex

# Placeholder — not actively used
CMD ["echo", "Worker not implemented. Pipeline runs in the API process."]
