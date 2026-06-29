# Testing Strategy

## Frontend

**Framework:** Vitest + React Testing Library

**Principles:**
- Test behavior, not implementation. Query by role and label text, not class names.
- Mock API calls — never make real HTTP requests in tests.
- Each component has at minimum: renders without crashing, key interactions, edge cases.

**Test file location:** Co-located with the component (`ComponentName.test.tsx`).

**Run tests:**
```bash
cd frontend
npm run test          # single run
npm run test:watch    # watch mode
npm run test:coverage # coverage report
```

## Backend

**Framework:** pytest + httpx (async test client)

- Unit tests for services and domain logic.
- Integration tests using a real PostgreSQL instance (via Docker in CI).
- Fixtures in `conftest.py` handle DB setup/teardown per test.
