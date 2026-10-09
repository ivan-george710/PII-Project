# apps/web/src

Frontend application source, including pages, features, shared components, layouts, API utilities, styles, and the application entry point.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `main.tsx` | Existing | Mount the React application. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |
| `App.tsx` | Existing | Define /login and /signup routes and assemble auth-aware application layouts. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |
| `vite-env.d.ts` | Existing | Vite environment types. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |

## Subdirectories

- [components/](components/index.md): see its exact file manifest.
- [features/](features/index.md): see its exact file manifest.
- [layouts/](layouts/index.md): see its exact file manifest.
- [lib/](lib/index.md): see its exact file manifest.
- [pages/](pages/index.md): see its exact file manifest.
- [styles/](styles/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
