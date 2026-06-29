FROM python:3.11-slim AS base

WORKDIR /app

# Non-root user
RUN addgroup --system cortex && adduser --system --ingroup cortex cortex

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/src ./src
COPY backend/pyproject.toml .

USER cortex

EXPOSE 8000

CMD ["uvicorn", "src.cortex.main:app", "--host", "0.0.0.0", "--port", "8000"]
