# Local authentication and company setup

Issue #3 provides email/password sign-in, company setup and manager assignments. Employee chat and manager reporting remain with their own issues. Password hashing follows [FastAPI's pwdlib/Argon2 guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#password-hashing).

## Local run

1. In `apps/api`, use Python 3.12+: `python3 -m venv .venv`, then `.venv/bin/pip install '.[test]'`.
2. Copy root `.env.example` to `apps/api/.env`. Generate `SESSION_SECRET` with `.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"` and save it there.
3. Run `.venv/bin/alembic upgrade head`.
4. Create a new workspace through `/signup` after starting the apps, or provision an existing company/account with the trusted command below.
5. Run `.venv/bin/uvicorn app.main:app --reload --port 8000`.
6. In `apps/web`, run `npm ci`, then `npm run dev`. Open `http://localhost:5173`.

The browser calls `/api` on the same origin. Backend settings are `DATABASE_URL`, `PUBLIC_APP_URL`, and `SESSION_SECRET`. Production requires PostgreSQL, HTTPS, and demo adapters disabled.

## Company accounts

From `apps/api` with backend settings loaded:

```sh
PYTHONPATH=. .venv/bin/python ../../scripts/provision-company.py --organization-id 00000000-0000-4000-8000-000000000010 --name 'Demo Company' --email manager@your-company.example --display-name 'Demo Manager' --role manager
```

Enter a password twice. There are no email-format, email-verification, or password-strength/length rules. To add an employee, use the same company UUID with `--role employee`. Provisioning is idempotent and refuses changes to an existing account's company or role. To reset a password, repeat the command with `--reset-password`; existing sessions are revoked. Passwords are never printed or accepted as command-line arguments.

The monochrome, icon-free /login and /signup screens provide sign-in and public account creation. Signup creates a new company workspace, makes the new user its manager, and signs them in. Users cannot choose an existing company or submit their own role. Existing-account signup returns409 and leaves existing access unchanged. There is no forgot-password email flow; operators can reset passwords. Managers open `/company/setup` to rename their company and assign employees to managers. Public session/setup responses never contain password hashes or session credentials.

Email is stored as unconstrained text after migration `0003_signup`. No verification emails are sent. The frontend and API accept email/password strings without format, strength or length checks.

## Session behavior

Passwords are hashed with Argon2. Seven-day sessions use random opaque HttpOnly/SameSite=Lax cookies, Secure on HTTPS. The database stores only token hashes. Each authenticated request checks session expiry and the user's current active status/role/company. Logout deletes the session; password reset revokes that user's sessions. Login requires the configured Origin; mutations also require the CSRF token returned by login or `/auth/me`.

Five failed attempts lock that account for five minutes, using database state shared across server instances. Unknown emails and wrong passwords return the same error. Roles come from the database; submitting a role/company field during login fails validation.

## Existing deployments and demo data

Migration `0002_local_auth` keeps company/user UUIDs and manager assignments, removes external-provider identity columns, normalizes emails, and adds password/session storage. It rejects duplicate normalized emails before applying the unique constraint. Existing users start without passwords; provision them with the operator command. Restoring the old provider identity columns requires a database backup; the migration deliberately refuses an automatic downgrade.

The presentation deployment uses the existing free Neon database. `cafkeemail@gmail.com` remains the manager; its generated login password is kept privately outside tracked files. New environments must migrate/provision their own database. Use the direct database URL for migration commands. Runtime uses the pooled connection. Migrations never run at API import.

`APP_ENV=development DEMO_ADAPTERS_ENABLED=true scripts/seed-demo.sh` creates fictional company/users/assignments idempotently. These seed identities have no usable passwords until provisioned. Synthetic session adapters are explicitly opt-in for development/test and forbidden in production. Issue #4 supplies policy/report fixtures through an optional seed adapter; absent adapters report `policy_seeded=false`.

## Checks

- API: `.venv/bin/python -m pytest tests -q` from `apps/api`.
- Web: `npm run build` and `npm test` from `apps/web`.
- Migration parity: `.venv/bin/alembic check` after upgrading an isolated database.

CI uses no external authentication key or staging project. The tests exercise real password hashing and database sessions. Frontend API mocks are used only to test form feedback/navigation independently.

## Feature integration

The API registers health, local auth and company setup directly. It also registers chat, uploads, demo, rules and reports routers when their modules are implemented. Missing planned modules add no routes. Import errors inside an implemented module fail startup so broken features cannot silently disappear. `app.dependencies` exposes the existing database/session/permission/settings dependencies for feature routers; feature owners connect their actual engine, policy, reporting, storage and LLM services.

`packages/engine` currently contains only directory plans and cannot be installed or used to sanitize employee content. Issue 1 supplies its package metadata, `pii_guard.pipeline.sanitize` and runtime tools. Once that package exists, install it from the repository root with `apps/api/.venv/bin/pip install -e packages/engine` and declare its actual dependency in the backend/deployment setup. Do not install an unrelated public package with the same name, or invent an engine extra before the package exists. The prototype is reference material and stays out of Vercel uploads. No OCR/model tooling is currently required to run auth/company setup.

LLM keys/model, storage and `SHOW_DEMO_SAMPLES` are configured by issue 2 when their implementations exist; the current backend does not consume those settings. Unavailable privacy processing must block real submissions. Simulated adapters are explicit development/test helpers only.

Configuration failures return only setting names in `error.fields`, never their values. `/api/health` and API docs remain available for connectivity checks. Configuration errors are surfaced by the endpoints that need those settings.

## Adding employees from the app

Sign in as a manager and open Company setup / Workspace settings. Under Add an employee, enter the name, employee email and chosen password, select their immediate manager, and press Add employee. The account is created in the manager's existing workspace with employee role; public signup is for a separate workspace, not for joining a company. Share sign-in details directly with the employee; no invitation email is sent. Existing employees appear below with manager-assignment controls. Emails/passwords remain unrestricted strings; no verification/strength checks were added.

The API is `POST /api/v1/organization/employees` with `{display_name,email,password,manager_id?}`. The manager's session and CSRF token determine company access; manager_id defaults to the caller and must be an active manager in that same company. Response 201 is `{user:{id,email,display_name,role:"employee"},assignment:{employee_id,manager_id,updated_at}}`, without any password/hash. Duplicate account is 409, employee caller 403, foreign manager 404, invalid extra fields 422. Creation and assignment are one transaction.

Migration `0004_employee_chat` must be applied after `0003_signup` for actual employee chat. It adds chat tables without replacing existing users/sessions/assignments. The UI has saved system/light/dark appearance and reduced-motion support. React Bits Strands is installed from the shadcn registry and rendered only as a small loading status; its upstream license is included in components/Strands.LICENSE.txt.
