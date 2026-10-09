# Local authentication and company setup

Issue #3 provides email/password sign-in, company setup and manager assignments. Employee chat and manager reporting remain with their own issues. Password hashing follows [FastAPI's pwdlib/Argon2 guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#password-hashing).

## Local run

1. In `apps/api`, use Python 3.12+: `python3 -m venv .venv`, then `.venv/bin/pip install '.[test]'`.
2. Copy root `.env.example` to `apps/api/.env`. Generate `SESSION_SECRET` with `.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(48))"` and save it there.
3. Run `.venv/bin/alembic upgrade head`.
4. Provision accounts with the trusted command below. It prompts for passwords with hidden input.
5. Run `.venv/bin/uvicorn app.main:app --reload --port 8000`.
6. In `apps/web`, run `npm ci`, then `npm run dev`. Open `http://localhost:5173`.

The browser calls `/api` on the same origin. Backend settings are `DATABASE_URL`, `PUBLIC_APP_URL`, and `SESSION_SECRET`. Production requires PostgreSQL, HTTPS, and demo adapters disabled.

## Company accounts

From `apps/api` with backend settings loaded:

```sh
PYTHONPATH=. .venv/bin/python ../../scripts/provision-company.py --organization-id 00000000-0000-4000-8000-000000000010 --name 'Demo Company' --email manager@your-company.example --display-name 'Demo Manager' --role manager
```

Enter a password of 12–128 characters twice. To add an employee, use the same company UUID with `--role employee`. Provisioning is idempotent and refuses changes to an existing account's company or role. To reset a password, repeat the command with `--reset-password`; existing sessions are revoked. Passwords are never printed or accepted as command-line arguments.

There is no public signup or forgot-password email flow. Operators create accounts and reset passwords. Managers open `/company/setup` to rename their company and assign employees to managers. Public session/setup responses never contain password hashes or session credentials.

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
