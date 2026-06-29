# Error Handling

## Frontend

Every API call is wrapped in a `try/catch`. Components that fetch data must render an `<ErrorAlert>` when an error occurs — empty/null error states are not acceptable.

```typescript
try {
  const data = await someApiCall();
  setData(data);
} catch (err: unknown) {
  const message = err instanceof Error ? err.message : 'An unexpected error occurred.';
  setError(message);
}
```

HTTP errors from the API are surfaced via the Axios interceptor in `lib/api/client.ts`.

## Backend

- API errors return `{ "detail": "...", "correlation_id": "..." }` with the appropriate HTTP status code.
- 400 — validation errors (Pydantic)
- 404 — resource not found
- 409 — conflict (e.g., duplicate job)
- 422 — unprocessable entity
- 500 — unexpected server error (logged, generic message returned to client)

Internal server errors are logged with a correlation ID that is also returned to the client for tracing.
