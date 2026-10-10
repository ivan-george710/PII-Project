# apps/api

Python backend for email/password authentication, company data, rule settings, reporting, file storage, engine orchestration, and LLM access.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `pyproject.toml` | Existing | Declare backend and engine dependencies needed to run the app. Owner: [issue 5](../../docs/issues/05-platform-deployment.md). |
| `alembic.ini` | Existing | Database migration configuration. Owner: [issue 3](../../docs/issues/03-auth-company-setup.md). |
| `Dockerfile` | Deferred | Optional future work; outside the five current issues. API runtime with required document-processing dependencies. |

## Subdirectories

- [app/](app/index.md): see its exact file manifest.
- [migrations/](migrations/index.md): see its exact file manifest.
- [tests/](tests/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)
- [Issue 5: Connect the app and document basic setup](../../docs/issues/05-platform-deployment.md) — [GitHub #5](https://github.com/ivan-george710/PII-Project/issues/5)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## PR 18 integration

`uv.lock` locks deployment dependencies, the local engine package and bundled OCR/face/NLP models. `pyproject.toml` declares the engine runtime extras and a local uv source.
