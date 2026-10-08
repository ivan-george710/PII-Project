# apps/web/src

Frontend application source, including pages, features, shared components, layouts, API utilities, styles, and the application entry point.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `main.tsx` | Planned | Mount the React application. |
| `App.tsx` | Planned | Define routes and assemble auth-aware application layouts. |
| `vite-env.d.ts` | Planned | Vite environment types. |
| `main.js` | Existing | Current minimal browser health check; replace with the planned React main.tsx during frontend implementation. |

## Subdirectories

- [components/](components/index.md): see its exact file manifest.
- [features/](features/index.md): see its exact file manifest.
- [layouts/](layouts/index.md): see its exact file manifest.
- [lib/](lib/index.md): see its exact file manifest.
- [pages/](pages/index.md): see its exact file manifest.
- [styles/](styles/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
