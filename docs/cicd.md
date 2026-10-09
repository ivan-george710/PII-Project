# CI/CD

The frontend uses React/Vite and the backend uses FastAPI. Local email/password authentication and company setup are implemented; employee chat, redaction and LLM calls remain with their feature issues. See [local setup](local-setup.md) for installation, account provisioning and migrations.

## GitHub Actions

`.github/workflows/ci.yml` builds/tests both apps and checks migration parity before deployment. Pushes to `main` deploy production; other branch pushes deploy previews. Pull requests run checks without deploying. Required repository settings:

- Secret `VERCEL_TOKEN`: token with access to the linked Vercel team/project.
- Variables `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`.

No external-auth secrets or staging-auth jobs are required. The workflow verifies the deployed frontend and `/api/health`, including the commit SHA. Production also requires anonymous `/api/v1/auth/me` to return401 UNAUTHENTICATED. Real login/logout behavior is verified in backend tests; the deployment smoke does not store a manager password in Actions.

Both services share `https://pii-guard-mu.vercel.app`; `/api` routes to the backend. Deployment protection is preserved; the CLI authenticates smoke requests. Checks gate deployment, but failed post-deployment smoke tests do not automatically roll back production.

## Runtime configuration

Configure `DATABASE_URL`, `PUBLIC_APP_URL`, and stable `SESSION_SECRET` separately in Vercel. Use backend-only Secret values for database/session credentials. Production uses `https://pii-guard-mu.vercel.app`; the same-origin frontend always calls `/api`. Preview browser mutations need a public origin matching their preview deployment; a health check alone does not establish full preview login readiness.

Apply migrations with the direct PostgreSQL connection and provision local accounts using [the trusted operator command](local-setup.md). Demo adapters stay disabled. Passwords never enter source, build artifacts, Actions secrets, or frontend variables.

## Current deployment credential limitation

The supplied Actions token is saved, but Vercel returns404 "User not found" for it. Account/project API probes also returned404. Automatic deployments remain blocked until a token authorized for `lqsky7s-projects` and project `pii-guard` is configured. The local CLI login can deploy manually; passing application tests does not imply automated deployment succeeded.
