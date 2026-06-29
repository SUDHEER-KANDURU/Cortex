# Coding Standards

## TypeScript (Frontend)

- **Strict mode** enabled — no `any` types anywhere.
- All component props must have a named `interface` exported from the same file.
- Hooks are named `useXxx` and live in `features/*/hooks/`.
- Every `useEffect` that sets up a subscription or interval must return a cleanup function.
- No `console.log` in production code. Development logging only inside `if (process.env.NODE_ENV === 'development')`.
- Component files: `PascalCase.tsx`. Hook files: `camelCase.ts`. Utility files: `camelCase.ts`.
- Tailwind only for styling — no CSS modules, no `style={{}}` except for React Flow dynamic colors.

## Python (Backend)

- Python 3.12+, type hints everywhere, `mypy --strict` compatible.
- Pydantic v2 for all request/response schemas.
- SQLAlchemy 2.0 (async) for database access.
- No bare `except:` — always catch specific exceptions.
- Docstrings for all public functions and classes (Google style).
