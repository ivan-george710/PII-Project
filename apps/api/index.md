# apps/api

Python backend for WorkOS authentication, company data, rule settings, reporting, file storage, engine orchestration, and LLM access.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `pyproject.toml` | Existing | Backend dependencies, package configuration, and test tooling. |
| `alembic.ini` | Planned | Database migration configuration. |
| `Dockerfile` | Planned | API runtime with required document-processing dependencies. |

## Subdirectories

- [app/](app/index.md): see its exact file manifest.
- [migrations/](migrations/index.md): see its exact file manifest.
- [tests/](tests/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
