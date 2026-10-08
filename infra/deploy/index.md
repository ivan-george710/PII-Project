# infra/deploy

Reserved for optional future deployment tooling. Current setup and deployment instructions belong in docs/local-setup.md and docs/cicd.md.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `compose.production.yaml` | Deferred | Optional future work; outside the five current issues. Production overrides with real integrations and persistent storage. |
| `.env.example` | Deferred | Optional future work; outside the five current issues. Deployment environment placeholders. |
| `README.md` | Deferred | Optional future work; outside the five current issues. Deployment, HTTPS, migration, readiness, and retention instructions. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

See the [five approved issues](../../docs/issues/index.md). This directory has no required implementation files in the current scope; deferred entries remain optional.
