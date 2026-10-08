**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Deliver WorkOS authentication, company setup, and employee-manager assignments

Status: Approved for implementation and GitHub publication.
Suggested ownership: Full-stack authentication / company setup

Implement the complete sign-in and company setup experience, including its frontend, backend, database, and validation. Manager rule settings/reporting are a separate complete workstream (issue 4). Verification and fictional setup data belong inside this implementation, not a separate testing/demo issue.

## Scope

- WorkOS login/callback/logout/session validation and role-aware navigation.
- Organization/user/manager-assignment models, database connection setup and migrations, company setup APIs, and frontend screens.
- Central authorization helpers for company, role, assignment, and company-policy edit permissions.
- Trusted provisioning and idempotent fictional company/user setup; never derive manager privileges from email domains or client claims.
- Complete tests and local session adapters within this issue; no prerequisite issue gate.

## Acceptance criteria

- Employee/manager sign-in works and correct routes/permissions are enforced server-side.
- Managers can update company details and assign only same-company employees to valid managers.
- All requests/responses are Pydantic validated; frontend session/setup forms and payloads are Zod validated.
- Unauthorized, cross-company, forged role, bad CSRF/state, and missing membership cases fail explicitly.
- Provisioning never stores passwords/tokens and refuses accidental production fictional seeding.
- Role/assignment checks are injectable and testable before real reporting is connected.

## Mandatory validation and shared conventions

Use **Pydantic v2** for Python request/response models, engine contracts, stored JSON policies/events, and provider-bound requests. Use **Zod** for frontend forms, REST responses, and streaming event payloads; TypeScript types alone are not runtime validation. Add `apps/web/src/lib/schemas.ts` for Zod schemas. Use FastAPI’s generated OpenAPI and check matching frontend payloads within this feature’s tests.

- Base Python schema: `BaseModel` with `ConfigDict(extra="forbid", validate_assignment=True)`. Use `StrictBool`, `StrictInt`, constrained strings/lists, enums, UUID, and timezone-aware datetime fields. Do not coerce strings such as `"false"` into booleans. Parse legitimate UUID/date strings deliberately at the transport boundary. Do not use `model_construct()` for external data. Use `model_validate`/`model_validate_json` on integrations and `model_dump(mode="json")` for serialization.
- Frontend: strict Zod objects, matching bounds/enums, `.safeParse()` with field feedback for forms, `.parse()`/`.safeParse()` for every API/SSE response. Malformed responses are errors, not a successful operation. Python validation remains authoritative.
- REST prefix `/api/v1`; health stays `/api/health`. Field names use snake_case. IDs are UUID strings; timestamps are RFC3339 UTC (`Z`). Organization and acting-user IDs always come from the validated session, never a client claim.
- JSON error shape: `{"error":{"code":"VALIDATION_ERROR","message":"Invalid request","fields":[{"path":"text","message":"Too long"}],"request_id":"<uuid>"}}`. Never include original PII, secrets, tracebacks, or rejected raw field values. Use 401 unauthenticated, 403 wrong role, 404 unavailable/foreign resource, 409 conflict, 413 limit exceeded, 415 unsupported file, 422 invalid payload, 502 provider error, 503 required component unavailable.
- Pagination: `limit` integer 1..100 (default 25), optional opaque `cursor` max 512 characters; response `{"items":[...],"next_cursor":null}`. Stable descending `created_at,id` ordering; no cross-company cursor reuse.
- Cookie-auth mutations require CSRF validation and an allowed Origin. Frontend sends credentials; do not put bearer/session credentials in localStorage. Validate authorization again on every endpoint and every file access.
- Each issue includes its own migrations, UI/backend/package work, integration adapters, fixtures, and checks. Do not wait for another issue to close. Implement against the contracts below; simulated adapters are explicit development-only substitutes, prohibited in production.
- Official validation reference: [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), [strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), [Zod basics](https://zod.dev/basics).


## Authentication and company API/model specification

Session roles: `employee|manager`. All company settings are writable by managers in that company for the demo; reports are restricted further to assigned employees. Do not let a login claim or email domain create manager privileges. Bootstrap the first manager via trusted seed/provisioning; no public administrator promotion endpoint.

### Authentication and organization endpoints

| Endpoint | Exact input | Output |
|---|---|---|
| `GET /api/v1/auth/login` | Optional `return_to` string max255, allowlisted relative app path only |302 WorkOS authorization URL; signed expiring state/PKCE where SDK supports it |
| `GET /api/v1/auth/callback` | WorkOS `code` and validated `state` query |302 allowlisted return path plus HttpOnly/Secure/SameSite=Lax session cookie; invalid state400 AUTH_STATE_INVALID; unprovisioned membership403 |
| `POST /api/v1/auth/logout` | `{}`, CSRF required |204, revoke session and clear cookie |
| `GET /api/v1/auth/me` | No body |200 `{user:{id,email,display_name,role,organization_id},organization:{id,name},csrf_token:"..."}`;401 without session |
| `GET /api/v1/organization` | Session company |200 `{id,name,created_at}` |
| `PATCH /api/v1/organization` | Manager; `{name:str}` trimmed1..120 |200 organization; no client-supplied identity fields |
| `GET /api/v1/organization/users` | Manager; pagination, optional role enum |200 paginated `{id,email,display_name,role}` same-company users |
| `GET /api/v1/organization/assignments` | Manager; pagination |200 paginated `{employee_id,manager_id,updated_at}` |
| `PUT /api/v1/organization/assignments/{employee_id}` | Manager; `{manager_id:UUID}` |200 assignment; both users must be same company with matching roles; one manager per employee; invalid roles422 |
| `DELETE /api/v1/organization/assignments/{employee_id}` | Manager; no body |204; subsequent report access denied; manager may not self-assign an employee identity |

Use WorkOS SDK session validation, not a frontend role assertion. WorkOS email is checked using Pydantic EmailStr (declare email-validator dependency); public DTO never contains WorkOS session/token secrets. Seed or trusted provisioning creates users and roles, never password storage in this database.

### Data models and implementation order

- Organization: UUID id, name1..120, UTC created_at/updated_at.
- User: UUID id/company_id, unique WorkOS user ID, validated email, display_name1..120, employee/manager role, UTC timestamps.
- ManagerAssignment: employee_id unique, manager_id, company_id, UTC updated_at; foreign keys, same-company validation, correct-role validation. One manager per employee for the presentation.
- `SessionIdentity` Pydantic contract: `{user_id:UUID,organization_id:UUID,role:"employee"|"manager",email:EmailStr,display_name:str}`. Resolve it only after validating the WorkOS session. Other workstreams consume this contract through dependency injection.
- Implement models/migration → session and permission services → typed routes → setup/login frontend → positive and negative checks. Central helpers expose `require_employee`, `require_manager`, `require_company`, and `require_assigned_employee`; manager reports still scope queries on every call.
- Company policy initialization is idempotent through a documented policy-store interface; policy table ownership stays with issue 4. Use an explicit local policy adapter when implementing this workflow independently; do not create competing policy tables.

### Fictional setup included with this feature

`seed.py --environment demo --organization-name 'Demo Company'` is idempotent by fixed seed keys and refuses production. Creates one company, one manager, two employees, assignments,13 enabled built-ins, one custom exact rule, one regex rule. WorkOS identities must be provisioned through approved account setup and mapped to local rows; local synthetic identities do not grant real login automatically. `identities.json` contains only fictional emails/names/roles; no tokens/passwords.

Use adapter interfaces to seed rules/events if those implementations are present; document exactly what was populated. WorkOS identity provisioning is real and distinct from local synthetic session adapters. `scripts/seed-demo.sh` must use an explicit non-production target. Tests cover idempotent setup, assignment changes, deactivation/missing membership, and subsequent authorization checks.

## Exact file ownership

Each listed file has one issue owner. Update its directory index when implementing it.

| File | Responsibility |
|---|---|
| `apps/api/app/auth/__init__.py` | Auth package marker. |
| `apps/api/app/auth/workos.py` | WorkOS login/callback/logout integration and identity mapping. |
| `apps/api/app/auth/sessions.py` | Validate sessions and resolve company/user identity. |
| `apps/api/app/auth/permissions.py` | Enforce company, role, manager-assignment, and policy-edit permissions. |
| `apps/api/app/db/models/organization.py` | Company identity and administrative settings (issue 3). |
| `apps/api/app/db/models/user.py` | WorkOS identity, company membership, and role (issue 3). |
| `apps/api/app/db/models/manager_assignment.py` | Employee-to-manager relationship within a company (issue 3). |
| `apps/api/app/routes/auth.py` | Login/callback/logout and current-session endpoints (issue 3). |
| `apps/api/app/routes/organization.py` | Company setup, user, and manager-assignment endpoints (issue 3). |
| `apps/api/app/schemas/auth.py` | Session identity and roles (issue 3). |
| `apps/api/app/schemas/organization.py` | Company/user/assignment request/response types (issue 3). |
| `apps/api/app/services/organization.py` | Company membership and manager-assignment workflows (issue 3). |
| `apps/api/tests/test_auth.py` | WorkOS/session behavior and role enforcement (issue 3). |
| `apps/api/tests/test_organization.py` | Membership and manager-assignment boundaries (issue 3). |
| `apps/web/src/features/auth/AuthProvider.tsx` | Load session identity and provide company/role state. |
| `apps/web/src/features/auth/RequireAuth.tsx` | Route guards and role-aware redirects; backend remains authoritative. |
| `apps/web/src/features/auth/useAuth.ts` | Access authentication state and login/logout actions. |
| `apps/web/src/features/setup/OrganizationForm.tsx` | Set company details and policy-editing permissions. |
| `apps/web/src/features/setup/EmployeeAssignments.tsx` | Assign employees to managers within their company. |
| `apps/web/src/features/setup/useOrganization.ts` | Load users and persist company setup. |
| `apps/web/src/pages/Login.tsx` | WorkOS sign-in entry page (issue 3). |
| `apps/web/src/pages/CompanySetup.tsx` | Company/users/manager assignment page (issue 3). |
| `apps/web/tests/auth.test.tsx` | Session and role-aware navigation behavior (issue 3). |
| `apps/web/tests/setup.test.tsx` | Company setup and assignment interactions (issue 3). |
| `apps/api/migrations/versions/0001_company_identity.py` | Company, WorkOS user identities, and manager assignments; company/auth foreign keys. |
| `demo/seed.py` | Seed synthetic company, users, assignments, policies, and events. |
| `demo/identities.json` | Fictional demo identity definitions without passwords or tokens. |
| `demo/adapters/sessions.py` | Explicitly simulated employee/manager identities for development. |
| `scripts/seed-demo.sh` | Migrate and seed the synthetic demo environment. |
| `apps/api/alembic.ini` | Database migration configuration. |
| `apps/api/app/db/__init__.py` | Database package marker. |
| `apps/api/app/db/base.py` | Shared declarative model base and metadata registration. |
| `apps/api/app/db/session.py` | Database connection and request/session lifecycle. |
| `apps/api/app/db/models/__init__.py` | Export/register all models (issue 3). |
| `apps/api/migrations/env.py` | Alembic runtime and model metadata integration (issue 3). |
| `apps/api/migrations/script.py.mako` | Migration file template (issue 3). |
| `apps/api/tests/conftest.py` | Shared isolated database/session fixtures (issue 3). |

## Working independently

Use the documented interfaces and feature-owned development adapters for integration points. Do not wait for another issue to close. Test this workstream against those interfaces, then connect real implementations without changing the contract. Production must never substitute simulated privacy processing.

- Keep all touched directory indexes accurate and distinguish planned files from implemented files.
