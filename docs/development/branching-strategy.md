# Branching Strategy

Cortex uses a trunk-based development workflow with short-lived feature branches.

## Branch Naming

| Type      | Pattern                    | Example                     |
|-----------|----------------------------|-----------------------------|
| Feature   | `feat/<short-description>` | `feat/artifact-viewer`      |
| Bug fix   | `fix/<issue-or-description>` | `fix/polling-memory-leak` |
| Docs      | `docs/<topic>`             | `docs/api-reference`        |
| Chore     | `chore/<topic>`            | `chore/update-dependencies` |
| Release   | `release/v<version>`       | `release/v0.2.0`            |

## Workflow

1. Branch off `main`.
2. Make small, focused commits using Conventional Commits.
3. Open a PR — CI must pass before merge.
4. Squash-merge to keep `main` history clean.
5. Delete the branch after merge.

## Tags and Releases

Tags follow SemVer: `v0.1.0`, `v0.2.0`, etc.
The `release.yml` CI workflow triggers on tag push.
