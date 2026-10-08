# infra

Local multi-service orchestration and deployment configuration; compose.yaml will connect web, API, and database.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `compose.yaml` | Planned | Connect web, API, database, storage, and development configuration. |
| `.dockerignore` | Planned | Exclude irrelevant/sensitive files from the Compose build contexts. |

## Subdirectories

- [deploy/](deploy/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
