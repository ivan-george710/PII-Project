# frontend

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `THIRD_PARTY_NOTICES.md` | Existing | Existing project asset or configuration; preserve its behavior unless explicitly changed. |
| `components.json` | Existing | Existing project asset or configuration; preserve its behavior unless explicitly changed. |
| `eslint.config.js` | Existing | Existing project asset or configuration; preserve its behavior unless explicitly changed. |
| `index.html` | Implemented; integration in progress | Monochrome application HTML entry and title. |
| `package-lock.json` | Existing | Existing project asset or configuration; preserve its behavior unless explicitly changed. |
| `package.json` | Implemented; integration in progress | Frontend scripts and React/chart/motion/Strands dependencies. |
| `tsconfig.json` | Existing | Existing project asset or configuration; preserve its behavior unless explicitly changed. |
| `vite.config.ts` | Implemented; integration in progress | Local employee static build and separate manager-only hosted build mode; trusted-local development API proxy, obsolete-bundle cleanup and generated static manifests. |

Subdirectories contain their own manifests when touched. Engine implementation and phase evidence remain authoritative.

`public/favicon.svg` reuses the approved SVG mark for browser tabs; Vite serves it under the correct local/hosted base path.
