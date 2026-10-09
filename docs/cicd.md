# Minimal CI/CD baseline

The frontend uses React/Vite and the backend uses FastAPI. WorkOS authentication and company setup are implemented; employee chat, redaction and LLM calls remain with their feature issues.

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

The workflow verifies the deployed frontend and `/api/health`, including a commit SHA check. For production it also requires `/api/v1/auth/login` to redirect to WorkOS with PKCE and a secure state cookie, and anonymous `/api/v1/auth/me` to return 401. Configuration errors therefore fail production deployment checks. Preview health checks do not establish that preview sign-in is configured. Both services share a URL. Deployment protection is preserved and the CLI authenticates smoke requests. CI success gates deployment, but the post-deployment smoke test does not automatically roll back a failed production release.

## Verify

- `/` serves the frontend and displays `Backend connected`.
- `GET /api/health` returns `{"status":"ok","service":"pii-guard-api","commit":null}` locally. On Vercel, `commit` contains the Git SHA when available.
- `/api/openapi.json` serves the backend schema.
- Check that GitHub CI passes and Vercel deployment metadata matches the pushed commit.

Vercel Services is in beta: https://vercel.com/docs/services.

## WorkOS staging check (issue #3)

The `smoke` job includes frontend behavior tests and backend pytest checks. `workos-staging` uses only `WORKOS_TEST_API_KEY` and the public `WORKOS_TEST_CLIENT_ID` to verify a real temporary staging session; it is excluded for fork PRs. Deployment waits for this check and syncs these scoped credentials into Vercel's backend-only `WORKOS_API_KEY` Secret and `WORKOS_CLIENT_ID` Config settings. Values travel through stdin and never enter source, frontend variables or command arguments.

Configure `DATABASE_URL`, `PUBLIC_APP_URL`, `WORKOS_REDIRECT_URI`, and a stable `WORKOS_COOKIE_PASSWORD` separately in Vercel, then migrate the database and provision company users as documented in [local setup](local-setup.md). Production uses `https://pii-guard-mu.vercel.app`; preview sign-in requires its own exact public origin/callback registered with WorkOS. A healthy `/api/health` response alone does not establish that authentication is configured.
