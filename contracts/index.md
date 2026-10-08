# contracts

Optional future saved contract snapshots. Current API documentation comes from FastAPI at /api/docs and /api/openapi.json; snapshot tooling is deferred.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `openapi.json` | Deferred | Optional future work; outside the five current issues. Generated backend API specification. |
| `engine.schema.json` | Deferred | Optional future work; outside the five current issues. Engine input/output contract snapshot. |
| `integration.schema.json` | Deferred | Optional future work; outside the five current issues. Session, policy, reporting event, and provider adapter contracts. |
| `examples.json` | Deferred | Optional future work; outside the five current issues. Safe valid/invalid examples for Pydantic/Zod schema parity checks. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

See the [five approved issues](../docs/issues/index.md). This directory has no required implementation files in the current scope; deferred entries remain optional.
