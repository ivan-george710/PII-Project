# CI/CD and Deployment Baseline

The application uses GitHub Actions for continuous integration and Vercel Services for unified frontend/backend hosting.

---

## Live Deployed URLs

- **Frontend Application**: [https://pii-guard-mu.vercel.app](https://pii-guard-mu.vercel.app)
- **Backend API Documentation**: [https://pii-guard-mu.vercel.app/api/docs](https://pii-guard-mu.vercel.app/api/docs)
- **Health Endpoint**: [https://pii-guard-mu.vercel.app/api/health](https://pii-guard-mu.vercel.app/api/health)
- **Latest CI Runs**: [GitHub Actions Workflow Runs](https://github.com/anubhav20ch/PII-Project/actions)

---

## Architecture & Routing

The repository-root `vercel.json` defines both frontend and backend services in one Vercel project:
- `/api/*` routes to the FastAPI backend service (`apps/api/app/main:app`).
- All other routes resolve to the Vite React frontend (`apps/web`).
- Browser requests use relative `/api/...` paths, ensuring seamless same-origin communication across local development, preview deployments, and production.

---

## GitHub Actions Workflow (`.github/workflows/ci.yml`)

The CI pipeline runs on every push and pull request with three main jobs:

1. **`smoke`**:
   - Builds and tests the React frontend (`npm ci`, `npm run build`, `npm test`).
   - Installs backend dependencies (`pip install '.[test]'`) and runs pytest (`pytest tests -q`).
   - Checks database migration integrity (`alembic upgrade head` and `alembic check`).

2. **`workos-staging`**:
   - Executes live authentication checks against the WorkOS staging environment using configured repository secrets (`WORKOS_TEST_API_KEY`) and variables (`WORKOS_TEST_CLIENT_ID`).

3. **`deploy`** (on pushes only):
   - Deploys preview environments for feature branches and production for pushes to `main`.
   - Reuses secret `VERCEL_TOKEN` and variables `VERCEL_ORG_ID` (`team_eEyacnrwinZLoAL29yzQ2ouX`) / `VERCEL_PROJECT_ID` (`prj_pYUwh7wNPrBPOkYTCvERO5AlfN29`).
   - Verifies the deployed frontend title and verifies `GET /api/health` returns the exact deployed Git SHA (`commit == GITHUB_SHA`).

---

## Verification Commands

To verify health and openapi locally:

```sh
curl -s http://localhost:8000/api/health
# {"status":"ok","service":"pii-guard-api","commit":null}

curl -s http://localhost:8000/api/openapi.json | jq .info
```
