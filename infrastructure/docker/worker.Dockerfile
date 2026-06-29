FROM python:3.11-slim AS base

WORKDIR /app

RUN addgroup --system cortex && adduser --system --ingroup cortex cortex

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/src ./src
COPY backend/pyproject.toml .

USER cortex

CMD ["celery", "-A", "worker.celery_app:celery_app", "worker", "--loglevel=info"]
