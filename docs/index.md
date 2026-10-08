# docs

Architecture, local setup, engine contracts, and Spark/Still reuse notes. Spark face logic uses Apple frameworks and needs adaptation for a Python/Linux backend.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `architecture.md` | Planned | Product boundaries, data flow, contracts, and workstream ownership. |
| `local-setup.md` | Planned | Install, configure, and launch each application/package. |
| `engine-contract.md` | Planned | Define content, policy, artifacts, locations, findings, and failures. |
| `spark-reuse.md` | Planned | Map Apple/Swift face logic to the backend implementation and test cases. |
| `reporting-contract.md` | Planned | Define idempotent manager events and safe display fields. |
| `rule-policy.md` | Planned | Define rule IDs, versions, enabled states, precedence, and regex limits. |

## Subdirectories

- [issues/](issues/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
