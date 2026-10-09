# CI/CD

The frontend uses React/Vite and the backend uses FastAPI. Local email/password authentication and company setup are implemented; employee chat, redaction and LLM calls remain with their feature issues. See [local setup](local-setup.md) for installation, account provisioning and migrations.

## GitHub Actions

`.github/workflows/ci.yml` builds/tests both apps and checks migration parity before deployment. Pushes to `main` deploy production; other branch pushes deploy previews. Pull requests run checks without deploying. Required repository settings:

- Secret `VERCEL_TOKEN`: token with access to the linked Vercel team/project.
- Variables `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`.

No external-auth secrets or staging-auth jobs are required. The workflow verifies the deployed frontend and `/api/health`, including the commit SHA. Production also requires anonymous `/api/v1/auth/me` to return401 UNAUTHENTICATED. Real login/logout behavior is verified in backend tests; the deployment smoke does not store a manager password in Actions.

Both services share `https://pii-guard-mu.vercel.app`; `/api` routes to the backend. Deployment protection is preserved; the CLI authenticates smoke requests. Production builds are staged with `--skip-domain`; live frontend/backend/session checks must pass before promotion. The production alias is then checked against the pushed SHA. Failed checks leave the previous production deployment active.

## Runtime configuration

Configure `DATABASE_URL`, `PUBLIC_APP_URL`, and stable `SESSION_SECRET` separately in Vercel. Use backend-only Secret values for database/session credentials. Production uses `https://pii-guard-mu.vercel.app`; the same-origin frontend always calls `/api`. Preview browser mutations need a public origin matching their preview deployment; a health check alone does not establish full preview login readiness.

Apply migrations with the direct PostgreSQL connection and provision local accounts using [the trusted operator command](local-setup.md). Demo adapters stay disabled. Passwords never enter source, build artifacts, Actions secrets, or frontend variables.

## Verified deployment

The Actions token was replaced and [run 37968276679](https://github.com/ivan-george710/PII-Project/actions/runs/37968276679) passed tests, deployment and live checks on 2026-10-09. Automatic deployment is working.

## Deployment source and timeouts

Actions exports the exact tested `GITHUB_SHA` with `git archive` into a temporary source directory and deploys it using the existing owner-authorized token. Git history and local credentials are absent from the upload. Source repository/SHA are recorded as explicit deployment metadata and `VERCEL_GIT_COMMIT_SHA` is passed to the backend, preserving the live commit check. Commit authors and repository history are unchanged.

Deploying directly from a Git checkout caused Vercel to block a merged collaborator-authored commit and leave the CLI waiting. Source snapshots separate the authorized CI release from Git-provider author authorization. The deployment step has an eight-minute timeout, the job has a fifteen-minute timeout, and live HTTP checks have bounded connection/request times. Preview pushes use the same source snapshot path; main deploys stage, verify, promote and verify the production alias.
