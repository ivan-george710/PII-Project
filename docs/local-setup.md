# WorkOS auth and company setup

Issue #3 provides sign-in, company setup and manager assignments. Employee chat and manager reporting remain with their own issues.

## Local run

1. In `apps/api`, use Python 3.12+: `python3 -m venv .venv`, then `.venv/bin/pip install '.[test]'`.
2. Copy the root `.env.example` to `apps/api/.env`. Fill `WORKOS_API_KEY` locally from your secret manager. Never commit it. The client ID is public.
3. Generate a cookie key with `.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and put it in the local `WORKOS_COOKIE_PASSWORD` setting.
4. Run `.venv/bin/alembic upgrade head`, then `.venv/bin/uvicorn app.main:app --reload --port 8000`.
5. In `apps/web`, run `npm ci`, then `npm run dev`. Open `http://localhost:5173`.

WorkOS staging project: **PIIdtc**, client ID `client_01M4DB2GA63J2DSF441YB66NZY`. Its allowed callbacks include `http://localhost:5173/api/v1/auth/callback` and `https://pii-guard-mu.vercel.app/api/v1/auth/callback`. Configure an exact callback separately for any new preview hostname. The browser always calls `/api` on the same origin.

## Provision real company accounts

Create the company and its users/memberships in the **testing WorkOS environment** through AuthKit/the dashboard. Copy the resulting WorkOS organization and user IDs. Signing in alone does not give a company role or manager privilege.

Create a local identity JSON file containing records like:

```json
[{"workos_user_id":"user_REPLACE","email":"manager@your-company.example","display_name":"Demo Manager","role":"manager"}]
```

From `apps/api`, with the required backend environment loaded, run:

```sh
PYTHONPATH=. .venv/bin/python ../../scripts/provision-company.py --organization-id 00000000-0000-4000-8000-000000000010 --name 'Demo Company' --workos-organization-id org_REPLACE --identities /absolute/path/company-users.json
```

Add employee records with role `employee` to the same file. This trusted command verifies each WorkOS user/email and active organization membership, creates local mappings idempotently, and refuses existing company/role conflicts. It stores no passwords or tokens. Existing membership must be provisioned before users can complete sign-in. Managers then open `/company/setup` to rename the company and assign employees to managers.

## Fictional development setup

Run `APP_ENV=development DEMO_ADAPTERS_ENABLED=true scripts/seed-demo.sh` from the repository root after configuring the database. It creates one fictional company, one manager, two employees and their assignments. Running it again makes no duplicates. These synthetic identities do not sign in through real WorkOS. The explicit helper in `demo/adapters/sessions.py` supports local dependency injection only; no HTTP login bypass exists, and production rejects the demo flag.

`demo/seed.py --environment demo --user-map /absolute/path/map.json --workos-organization-id org_REPLACE` can map the fictional emails to existing verified WorkOS users instead. The map is `{ "manager@example.com": "user_REPLACE", ... }`. Do not use the existing example.com test-SSO domain for password-based CI accounts.

Policy/report fixtures are owned by issue #4. Seeding accepts an idempotent `initialize_demo_policy(organization_id)` adapter when that feature exists; it explicitly reports `policy_seeded=false` without one. It creates no competing policy tables.

## Configuration and deployment

Production/preview requires PostgreSQL in `DATABASE_URL`, HTTPS in `PUBLIC_APP_URL`, matching `WORKOS_REDIRECT_URI`, WorkOS credentials and a stable Fernet cookie key. Vercel uses production-safe defaults, with no SQLite fallback. These settings are now configured for the presentation deployment, with a free Neon database, migrated company tables and the requested manager mapping. New deployments/environments still need their own runtime setup. The scoped WorkOS API key and stable cookie password are stored as Vercel Secrets; neither can be pulled back from Vercel. Keep migrations explicit and use the direct database URL for migration commands. Migrations are an explicit setup/release command, never run at API import.

`WORKOS_ISSUER` optionally pins a custom-domain issuer. By default the SDK accepts the app-scoped WorkOS issuer and its documented legacy issuer, and checks the token's client ID and subject. Cookies are HttpOnly/SameSite=Lax and Secure on HTTPS. Signed state expires after 10 minutes; login uses PKCE. Company/role/assignment authorization comes from current database mappings. WorkOS sessions refresh through the SDK; mutations also validate Origin and a session-bound CSRF token. API errors exclude rejected raw inputs and credentials.

## Checks

- API: `.venv/bin/python -m pytest tests -q` from `apps/api`.
- Web: `npm run build` and `npm test` from `apps/web`.
- Migration parity: `.venv/bin/alembic check` after upgrading an isolated database.
- Actions runs the optional real staging check using only `WORKOS_TEST_API_KEY` secret and `WORKOS_TEST_CLIENT_ID` variable. The test generates a temporary password in memory, authenticates one temporary example.org user, verifies SDK session handling, revokes the session and deletes the user in teardown. No verification/invitation emails are sent by this test.

The staging key configured for this task expires on **2026-10-15**. Rotate the Actions secret before then to keep the live check running. No WorkOS key is included in source, fixtures, build artifacts, or frontend variables.
