**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Connect the app and document basic setup

Status: Approved for implementation and GitHub publication.
Suggested ownership: App integration / setup

The frontend, backend, and GitHub Actions → Vercel deployment already work. This issue connects the feature modules to that existing app and provides short setup instructions.

## Current implementation to preserve (updated 2026-10-09)

- Start from current upstream `ivan-george710/PII-Project:main`, fetch it again before submitting, and merge current main into existing feature branches. Old branch code must not replace newer working features. Review the final diff against current main.
- Authentication is local email/password. WorkOS was removed intentionally: do not restore its SDK, redirects, settings, cookies, mocks, secrets or CI jobs. Preserve Argon2 hashing, database sessions, company/user/assignment models, permissions, logout/revocation, CSRF and account lockout.
- Preserve `POST /api/v1/auth/signup` (201 new isolated company + manager), `POST /api/v1/auth/login` (200), `GET /api/v1/auth/me` (200 session DTO or 401), and `POST /api/v1/auth/logout` (204). Session DTO: `{user:{id,email,display_name,role,organization_id},organization:{id,name},csrf_token}`. Cookie name is `pii-session`; the API resolves roles/company from its database. Signup cannot join an existing company or promote an existing user.
- Email/password inputs are strings with **no email-format/verification or password-strength/length checks**. Email is lowercased. Duplicate email is 409 ACCOUNT_EXISTS. Public email fields use Pydantic `str` / Zod `z.string()`, not EmailStr or email-format validators. Ordinary feature-specific text/file limits still apply.
- Preserve `/login`, `/signup` and `/company/setup`. Product screens use black/white and neutral grayscale only, no icons; simple text labels and controls. Keep the existing auth design. Employee chat remains a plain LLM interface, with attachments and built-in test samples in the composer addon menu.
- Existing migration chain is `0001_company_identity -> 0002_local_auth -> 0003_signup`. Keep those files, revision IDs, models and deployed data. Add a uniquely named feature migration after the current head; reconcile new parallel revisions on integration so there is one head. Never delete/rewrite an applied migration or recreate company/user/session tables.
- CI currently passes build/tests, migration parity, Vercel deployment and live checks. Preserve these checks; do not delete tests, skip jobs or weaken assertions to get green. Main pushes deploy production, other pushes previews; PRs run tests. Reuse VERCEL_TOKEN / VERCEL_ORG_ID / VERCEL_PROJECT_ID and same-origin `/api` routing. No external-auth credentials are needed.
- Only auth/company setup is implemented in the product. Chat, reports/policies and `packages/engine` are still feature work; the prototype is reference code. Never label placeholders, empty namespaces or `NotImplementedError` stubs as delivered integration. Missing production processing must block submissions; fake adapters require explicit development/test opt-in. A present feature with a broken import must fail checks/startup, not silently disappear.
- Before delivery run the existing backend and frontend checks, migration upgrade/parity and the feature's own checks. Verify the actual PR head and resolve conflicts. Update touched indexes and this issue's status to distinguish implemented work from pending work. This is a shared baseline, not a prerequisite issue dependency.

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

## Deployment implementation update

Use the tested source snapshot workflow now in `.github/workflows/ci.yml`: export exact GITHUB_SHA using git archive, deploy with the existing authorized token, supply the real SHA to runtime/metadata, stage production with --skip-domain, run live checks, and promote only after success. Preserve step/job/network timeouts and verify the production alias SHA. Do not revert to deploying the Git checkout or alter commit authors to impersonate the Vercel owner.
