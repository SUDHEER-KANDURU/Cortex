# Logging Strategy

## Frontend

- No `console.log` in production code.
- Development-only logs are guarded: `if (process.env.NODE_ENV === 'development') { console.error(...) }`
- The Axios interceptor in `lib/api/client.ts` logs API errors in development mode only.

## Backend

- Structured JSON logging (using `structlog` or `python-json-logger`).
- Log levels: DEBUG (development), INFO (production).
- Every request logs: method, path, status code, duration, correlation_id.
- Worker tasks log: task name, job_id, start/end time, status.
- Sensitive data (secrets, tokens) must never appear in logs.
