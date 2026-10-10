# .github/workflows

Continuous integration workflows for relevant application, engine, and integration checks.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `ci.yml` | Existing | Build/test apps and migrations; deploy exact source snapshots with bounded waits, verify SHA/session responses, then promote production. Owner: [issue 5](../../docs/issues/05-platform-deployment.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 5: Connect the app and document basic setup](../../docs/issues/05-platform-deployment.md) — [GitHub #5](https://github.com/ivan-george710/PII-Project/issues/5)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
