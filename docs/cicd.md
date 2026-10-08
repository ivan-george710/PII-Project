# Minimal CI/CD baseline

The frontend is a plain Vite page. The backend is FastAPI with a Pydantic v2 health response. This baseline implements no authentication, redaction, database, or LLM calls.

## Local check

From `apps/api`, install `.[test]` into a Python 3.12+ virtual environment, run `python -m unittest discover -s tests -v`, and start `uvicorn app.main:app --port 8000`.

From `apps/web`, run `npm ci` and `npm run dev`. Its development proxy forwards `/api` to the backend. The page displays `Backend connected` after a successful request.

## Push deployment

The repository-root `vercel.json` defines frontend and backend services in one Vercel project. `/api/*` routes to the backend; other traffic routes to the frontend. The browser uses a relative URL, so previews and production always call their own backend.

GitHub Actions owns deployment. Each push first builds the frontend and tests the backend, then deploys both Vercel services. Main pushes deploy production; other branches deploy previews. PRs run CI without deploying. No Vercel GitHub app access is required.

Repository configuration:

- Actions variable `VERCEL_ORG_ID`: `team_eEyacnrwinZLoAL29yzQ2ouX`.
- Actions variable `VERCEL_PROJECT_ID`: `prj_pYUwh7wNPrBPOkYTCvERO5AlfN29`.
- Actions secret `VERCEL_TOKEN`: configure directly in repository settings; never commit or paste it into chat.

The workflow verifies the deployed frontend and `/api/health`, including a commit SHA check. Both services share a URL; the frontend uses relative `/api/health`. Deployment protection is preserved and the CLI authenticates smoke requests. CI success gates deployment, but the post-deployment smoke test does not automatically roll back a failed production release.

## Verify

- `/` serves the frontend and displays `Backend connected`.
- `GET /api/health` returns `{"status":"ok","service":"pii-guard-api","commit":null}` locally. On Vercel, `commit` contains the Git SHA when available.
- `/api/openapi.json` serves the backend schema.
- Check that GitHub CI passes and Vercel deployment metadata matches the pushed commit.

Vercel Services is in beta: https://vercel.com/docs/services.

## WorkOS staging check (issue #3)

The `smoke` job now includes frontend behavior tests and backend pytest checks. `workos-staging` uses only `WORKOS_TEST_API_KEY` and the public `WORKOS_TEST_CLIENT_ID` to verify a real temporary staging session; it is excluded for fork PRs. WorkOS credentials are not passed to Vercel deployment. Backend runtime auth/database configuration is a separate setup step documented in [local setup](local-setup.md).
