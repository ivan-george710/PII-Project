# demo

Reproducible demo setup: seed company/users/assignments/rules, synthetic sample documents, and a walkthrough.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `seed.py` | Planned | Seed synthetic company, users, assignments, policies, and events. |
| `identities.json` | Planned | Fictional demo identity definitions without passwords or tokens. |
| `walkthrough.md` | Planned | Employee-to-manager demonstration and WorkOS identity setup. |

## Subdirectories

- [adapters/](adapters/index.md): see its exact file manifest.
- [sample_documents/](sample_documents/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
