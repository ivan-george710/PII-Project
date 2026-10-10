# demo

Reproducible demo setup: seed company/users/assignments/rules, synthetic sample documents, and a walkthrough.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `seed.py` | Existing | Seed synthetic company, users, assignments, policies, and events. Owner: [issue 3](../docs/issues/03-auth-company-setup.md). |
| `identities.json` | Existing | Fictional demo identity definitions without passwords or tokens. Owner: [issue 3](../docs/issues/03-auth-company-setup.md). |
| `walkthrough.md` | Implemented | Employee-to-manager demonstration with local account and WorkOS identity setup. Owner: [issue 2](../docs/issues/02-employee-chat.md). |

## Subdirectories

- [adapters/](adapters/index.md): see its exact file manifest.
- [sample_documents/](sample_documents/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)
- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
