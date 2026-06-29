# Security

See the root [SECURITY.md](../../SECURITY.md) for the security policy and vulnerability reporting process.

## Security Considerations for Contributors

- Never commit credentials, API keys, or passwords. Use `.env` files listed in `.gitignore`.
- Do not add external service calls. Cortex is strictly offline.
- Validate all user input on both client and server sides.
- Use parameterized queries for all database access — no string concatenation.
- Dependencies: pin exact versions, review changelogs before upgrading.
