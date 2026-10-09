# apps/web

Simple LLM-style web application for employees, with manager reports, company settings, and setup. The chat, authentication, and manager issues each own their complete frontend/backend feature.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `package.json` | Existing | Frontend dependencies and dev/build/test scripts. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `index.html` | Existing | Web application mount document. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `vite.config.ts` | Existing | React development server, build, and API proxy configuration. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `tsconfig.json` | Existing | Frontend TypeScript configuration. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `Dockerfile` | Deferred | Optional future work; outside the five current issues. Build and serve the web application. |
| `package-lock.json` | Existing | Lock minimal frontend build dependencies. |

## Subdirectories

- [public/](public/index.md): see its exact file manifest.
- [src/](src/index.md): see its exact file manifest.
- [tests/](tests/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/anubhav20ch/PII-Project/issues/2)
- [Issue 3: Deliver WorkOS authentication, company setup, and employee-manager assignments](../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/anubhav20ch/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/anubhav20ch/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
