# infra/deploy

Deployment configuration, runtime provisioning, and release instructions.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `compose.production.yaml` | Planned | Production overrides with real integrations and persistent storage. |
| `.env.example` | Planned | Deployment environment placeholders. |
| `README.md` | Planned | Deployment, HTTPS, migration, readiness, and retention instructions. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
