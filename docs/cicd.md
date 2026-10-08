# Minimal CI/CD baseline

The frontend is a plain Vite page. The backend is FastAPI with a Pydantic v2 health response. This baseline implements no authentication, redaction, database, or LLM calls.

## Local check

From `apps/api`, install `.[test]` into a Python 3.12+ virtual environment, run `python -m unittest discover -s tests -v`, and start `uvicorn app.main:app --port 8000`.

From `apps/web`, run `npm ci` and `npm run dev`. Its development proxy forwards `/api` to the backend. The page displays `Backend connected` after a successful request.

## Push deployment

The repository-root `vercel.json` defines frontend and backend services in one Vercel project. `/api/*` routes to the backend; other traffic routes to the frontend. The browser uses a relative URL, so previews and production always call their own backend.

Connect the Vercel project's Git integration to `ivan-george710/PII-Project`, with `main` as the production branch and the repository root as the project root. Main pushes deploy production; other branch pushes deploy previews. Both services ship in the same deployment. GitHub Actions runs frontend build and backend smoke checks on pushes and PRs. Git integration owns deployment, so no Vercel tokens are stored in GitHub Actions.

GitHub CI and Vercel builds run in parallel; CI is not a release gate in this minimal baseline.

## Verify

- `/` serves the frontend and displays `Backend connected`.
- `GET /api/health` returns `{"status":"ok","service":"pii-guard-api","commit":null}` locally. On Vercel, `commit` contains the Git SHA when available.
- `/api/openapi.json` serves the backend schema.
- Check that GitHub CI passes and Vercel deployment metadata matches the pushed commit.

Vercel Services is in beta: https://vercel.com/docs/services.
