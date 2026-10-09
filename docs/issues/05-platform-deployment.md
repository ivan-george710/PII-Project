**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Connect the app and document basic setup

Status: Approved for implementation and GitHub publication.
Suggested ownership: App integration / setup

The frontend, backend, and GitHub Actions → Vercel deployment already work. This issue connects the feature modules to that existing app and provides short setup instructions.

## Work to do

1. Register the feature routers in `apps/api/app/main.py` and connect the real session, policy, engine, reporting, storage, and LLM implementations through `dependencies.py`. Use the interfaces defined in issues 1–4; keep business logic in those features.
2. Load configuration with Pydantic Settings. Add the settings each feature actually uses to `.env.example`, with placeholders and a brief description. Use `SecretStr` for credentials; report missing setting names without printing values.
3. Ensure the API can import the engine package through a normal package dependency. Document its install command and any runtime tools the chosen implementation actually requires.
4. Document commands to install dependencies, start the API and frontend, apply the auth issue's database migrations, and configure local session settings and LLM credentials. List the live URLs in README.
5. Keep the existing GitHub Actions workflow and Vercel routing working as feature dependencies are added. Add the features' own check commands to the existing check job when they exist.

## Inputs and outputs

- **Input:** Feature routers/services from issues 1–4, runtime environment variables, and the existing Vercel project/Actions configuration.
- **Output:** One runnable app with connected features, a placeholder environment file, and concise setup instructions. This issue adds no new product API.
- The browser uses relative `/api/...` URLs. Vercel routes `/api/*` to FastAPI and other paths to the frontend; local Vite proxies `/api` to the API.
- Preserve `GET /api/health`: HTTP 200, `{"status":"ok","service":"pii-guard-api","commit":null}`. `commit` is the deployed Git SHA when available, otherwise null. Keep its existing no-cache behavior.
- Preserve `/api/docs` and `/api/openapi.json`; FastAPI generates the schema from Pydantic models.
- Python API models use Pydantic v2; frontend feature forms/responses use Zod as specified in their own issues. Match their documented payloads without adding a separate schema-generation system.

## Configuration

Use the names documented by the feature implementations. At minimum, record the chosen database connection, SESSION_SECRET and public app origin, LLM key/model, and file-storage settings. `SHOW_DEMO_SAMPLES` controls the chat's built-in sample menu. Keep credentials on the backend and in environment settings.

The deployment already uses Actions secret `VERCEL_TOKEN` and variables `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID`. Reuse them. Main pushes deploy production, other pushes deploy previews, and pull requests run checks.

## Acceptance checks

- Following the setup instructions starts the frontend and API with the documented configuration.
- The app registers the implemented feature endpoints and the frontend reaches them through `/api`.
- Existing frontend build/backend health checks pass; feature-specific checks remain with their owning issues.
- The existing deployment workflow can still serve the frontend and return the deployed SHA from `/api/health`.
- Missing required configuration gives a useful error without exposing secrets. Actual employee submissions use real processing; simulated adapters remain explicit development/test helpers.

## Scope limits

Docker/Compose, a new readiness endpoint, separate release tooling, contract snapshot generators, automated model provisioning, and a new end-to-end testing framework are outside this issue. Database models/migrations belong to issue 3; frontend bootstrapping belongs to issue 2. Each feature keeps its own tests and sample data.

## Exact file ownership

Update the relevant directory indexes when these files change. Existing files need changes only where feature integration requires them.

| File | Responsibility |
|---|---|
| `README.md` | Short setup instructions and live frontend/backend links. |
| `.env.example` | Only configuration actually used by the features, with placeholder values. |
| `.gitignore` | Keep secrets, uploads, caches, and model downloads out of Git. |
| `apps/api/pyproject.toml` | Declare backend and engine dependencies needed to run the app. |
| `apps/api/app/__init__.py` | Backend package marker. |
| `apps/api/app/main.py` | Register feature routers and assemble the FastAPI app. |
| `apps/api/app/config.py` | Load required settings using pydantic-settings; keep secrets in SecretStr fields. |
| `apps/api/app/dependencies.py` | Connect feature implementations through ordinary FastAPI dependencies. |
| `apps/api/app/routes/__init__.py` | Routes package marker. |
| `apps/api/app/routes/health.py` | Preserve the existing health response and commit field. |
| `apps/api/app/schemas/__init__.py` | Schema package marker. |
| `apps/api/app/schemas/common.py` | Existing HealthResponse plus shared API error/pagination models. |
| `apps/api/app/services/__init__.py` | Services package marker. |
| `apps/api/tests/test_health.py` | Preserve the existing health smoke test. |
| `vercel.json` | Keep frontend/backend services connected through same-origin /api routing. |
| `.vercelignore` | Keep local/private/reference artifacts out of deployment uploads. |
| `.github/workflows/ci.yml` | Keep the existing build, checks, Vercel deployment, and live SHA check working. |
| `docs/local-setup.md` | Exact install/start commands and where to configure credentials. |
| `docs/cicd.md` | Existing Actions configuration, deployed URLs, and simple verification commands. |

## Working independently

Implement the registration/configuration glue against the interfaces in the other drafts, using their explicit development helpers where needed. Do not require another issue to close before starting, and do not build a second adapter framework.

This specification has been approved by the user for publication and implementation.
