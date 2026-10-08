# apps/api/migrations

Versioned database schema migrations.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `env.py` | Planned | Alembic runtime and model metadata integration (issue 4). |
| `script.py.mako` | Planned | Migration file template (issue 4). |

## Subdirectories

- [versions/](versions/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
