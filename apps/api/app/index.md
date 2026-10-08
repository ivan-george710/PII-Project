# apps/api/app

Backend application source; main.py and config.py will provide startup and configuration.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Backend package marker. Owner: [issue 5](../../../docs/issues/05-platform-deployment.md). |
| `main.py` | Existing | Register feature routers and assemble the FastAPI app. Owner: [issue 5](../../../docs/issues/05-platform-deployment.md). |
| `config.py` | Existing | Load required settings using pydantic-settings; keep secrets in SecretStr fields. Owner: [issue 5](../../../docs/issues/05-platform-deployment.md). |
| `dependencies.py` | Planned | Connect feature implementations through ordinary FastAPI dependencies. Owner: [issue 5](../../../docs/issues/05-platform-deployment.md). |

## Subdirectories

- [auth/](auth/index.md): see its exact file manifest.
- [db/](db/index.md): see its exact file manifest.
- [llm/](llm/index.md): see its exact file manifest.
- [routes/](routes/index.md): see its exact file manifest.
- [schemas/](schemas/index.md): see its exact file manifest.
- [services/](services/index.md): see its exact file manifest.
- [storage/](storage/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver WorkOS authentication, company setup, and employee-manager assignments](../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)
- [Issue 5: Connect the app and document basic setup](../../../docs/issues/05-platform-deployment.md) — [GitHub #5](https://github.com/ivan-george710/PII-Project/issues/5)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
