# apps/web

Simple LLM-style web application for employees, with manager reports, company settings, and setup. Frontend teammate owns this application.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `package.json` | Existing | Frontend dependencies and dev/build/test scripts. |
| `index.html` | Existing | Web application mount document. |
| `vite.config.ts` | Planned | React development server, build, and API proxy configuration. |
| `tsconfig.json` | Planned | Frontend TypeScript configuration. |
| `Dockerfile` | Planned | Build and serve the web application. |
| `package-lock.json` | Existing | Lock minimal frontend build dependencies. |
| `vite.config.js` | Existing | Current Vite development proxy to FastAPI; replace with the planned TypeScript config when the frontend is implemented. |

## Subdirectories

- [public/](public/index.md): see its exact file manifest.
- [src/](src/index.md): see its exact file manifest.
- [tests/](tests/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
