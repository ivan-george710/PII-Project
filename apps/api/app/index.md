# apps/api/app

Backend application source; main.py and config.py will provide startup and configuration.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Backend package marker. |
| `main.py` | Existing | Build the API application, register routes, and initialize lifecycle hooks. |
| `config.py` | Planned | Validate runtime settings; reject production use of demo adapters. |
| `dependencies.py` | Planned | Inject sessions, database access, policies, engine, and provider interfaces. |

## Subdirectories

- [auth/](auth/index.md): see its exact file manifest.
- [db/](db/index.md): see its exact file manifest.
- [llm/](llm/index.md): see its exact file manifest.
- [routes/](routes/index.md): see its exact file manifest.
- [schemas/](schemas/index.md): see its exact file manifest.
- [services/](services/index.md): see its exact file manifest.
- [storage/](storage/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
