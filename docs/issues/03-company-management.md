**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Deliver WorkOS company accounts, manager settings, and PII reports

Status: Draft — awaiting individual approval before GitHub creation.
Suggested ownership: Full-stack company management

Deliver the complete company-management workflow: WorkOS sign-in, company/user setup, employee-to-manager relationships, company-wide policies, and manager-visible reports.

## Scope
- Integrate WorkOS login, callbacks, logout, session validation, and role-aware navigation.
- Implement organization/user/manager-assignment models, migrations, setup APIs, and setup screens.
- Restrict company data and employee reports by company membership and manager assignment.
- Define which managers can edit company-wide policy, including companies with multiple managers.
- Implement manager settings with individual built-in toggles and enable/disable-all controls.
- Implement custom exact-phrase/regex creation, editing, deletion, validation, bounded sample-text preview, and case settings.
- Persist policy versions; expose an explicit policy snapshot for each employee submission.
- Implement idempotent event ingestion and manager reports with employee/date/category filters and submission detail.
- Show text/custom-rule/face categories, source locations, timestamps, redacted/allowed actions, and processing failures. Keep raw sensitive values out of reports by default.
- Supply development users, policies, and synthetic events so all screens and endpoints can be reviewed independently.

## Acceptance criteria
- Employee and manager accounts sign in and receive the appropriate permissions/navigation.
- A manager can set up assigned employees, change company rules, and test custom patterns without calling the LLM.
- Invalid or expensive patterns fail with useful feedback; company rule versions are recorded.
- Synthetic or real ingested events appear only to authorized managers of the submitting employee.
- Reports distinguish redacted findings, disabled-rule matches, and processing failures.
- Cross-company access, unassigned-employee report access, and employee access to manager endpoints are denied.
- Retried event ingestion does not create duplicates.

## Exact file ownership

Implement the following file plan. Shared directories assign individual files to their workstream; the directory indexes contain responsibilities and current/planned status. Existing prototype files remain reference material, not a second production implementation.

| File | Responsibility |
|---|---|
| `apps/api/app/auth/__init__.py` | Auth package marker. |
| `apps/api/app/auth/workos.py` | WorkOS login/callback/logout integration and identity mapping. |
| `apps/api/app/auth/sessions.py` | Validate sessions and resolve company/user identity. |
| `apps/api/app/auth/permissions.py` | Enforce company, role, manager-assignment, and policy-edit permissions. |
| `apps/api/app/db/models/organization.py` | Company identity and administrative settings (issue 3). |
| `apps/api/app/db/models/user.py` | WorkOS identity, company membership, and role (issue 3). |
| `apps/api/app/db/models/manager_assignment.py` | Employee-to-manager relationship within a company (issue 3). |
| `apps/api/app/db/models/rule.py` | Company built-in overrides, custom rules, and policy versions (issue 3). |
| `apps/api/app/db/models/pii_event.py` | Submission findings/actions and idempotency identifiers (issue 3). |
| `apps/api/app/routes/auth.py` | Login/callback/logout and current-session endpoints (issue 3). |
| `apps/api/app/routes/reports.py` | Assigned-employee report and event detail endpoints (issue 3). |
| `apps/api/app/routes/rules.py` | Company rule CRUD/toggles and sample preview endpoints (issue 3). |
| `apps/api/app/routes/organization.py` | Company setup, user, and manager-assignment endpoints (issue 3). |
| `apps/api/app/schemas/auth.py` | Session identity and roles (issue 3). |
| `apps/api/app/schemas/reports.py` | Report filters, event summaries, and details (issue 3). |
| `apps/api/app/schemas/rules.py` | Company policy, custom rule, and preview request/response types (issue 3). |
| `apps/api/app/schemas/organization.py` | Company/user/assignment request/response types (issue 3). |
| `apps/api/app/services/reporting.py` | Idempotent event ingestion and manager report queries (issue 3). |
| `apps/api/app/services/rules.py` | Policy snapshots/versioning and bounded custom-rule preview (issue 3). |
| `apps/api/app/services/organization.py` | Company membership and manager-assignment workflows (issue 3). |
| `apps/api/migrations/versions/0001_company_identity_policy_events.py` | Company, users, assignments, rule versions, and event tables (issue 3). |
| `apps/api/tests/test_auth.py` | WorkOS/session behavior and role enforcement (issue 3). |
| `apps/api/tests/test_organization.py` | Membership and manager-assignment boundaries (issue 3). |
| `apps/api/tests/test_rules.py` | Policy versioning, isolation, preview, and invalid-pattern behavior (issue 3). |
| `apps/api/tests/test_reports.py` | Report authorization and idempotent event ingestion (issue 3). |
| `apps/web/src/features/auth/AuthProvider.tsx` | Load session identity and provide company/role state. |
| `apps/web/src/features/auth/RequireAuth.tsx` | Route guards and role-aware redirects; backend remains authoritative. |
| `apps/web/src/features/auth/useAuth.ts` | Access authentication state and login/logout actions. |
| `apps/web/src/features/reports/ReportFilters.tsx` | Employee, date, and category filters. |
| `apps/web/src/features/reports/EventList.tsx` | Show safe PII event summaries and counts. |
| `apps/web/src/features/reports/EventDetails.tsx` | Show source locations, policy/rule identity, and redacted/allowed actions. |
| `apps/web/src/features/reports/useReports.ts` | Fetch and paginate authorized manager reports. |
| `apps/web/src/features/rules/RuleToggles.tsx` | Individual and all-on/all-off company rule controls. |
| `apps/web/src/features/rules/CustomRuleEditor.tsx` | Create/edit exact-phrase and regex rules with case settings. |
| `apps/web/src/features/rules/RulePreview.tsx` | Preview matches against sample text before saving. |
| `apps/web/src/features/rules/useRules.ts` | Load, validate, save, and version company settings. |
| `apps/web/src/features/setup/OrganizationForm.tsx` | Set company details and policy-editing permissions. |
| `apps/web/src/features/setup/EmployeeAssignments.tsx` | Assign employees to managers within their company. |
| `apps/web/src/features/setup/useOrganization.ts` | Load users and persist company setup. |
| `apps/web/src/layouts/ManagerLayout.tsx` | Manager reports/settings/setup navigation (issue 3). |
| `apps/web/src/pages/Login.tsx` | WorkOS sign-in entry page (issue 3). |
| `apps/web/src/pages/ManagerReports.tsx` | Assigned-employee event reporting page (issue 3). |
| `apps/web/src/pages/ManagerSettings.tsx` | Company policy toggles and custom rules page (issue 3). |
| `apps/web/src/pages/CompanySetup.tsx` | Company/users/manager assignment page (issue 3). |
| `apps/web/tests/auth.test.tsx` | Session and role-aware navigation behavior (issue 3). |
| `apps/web/tests/rules.test.tsx` | Toggle, custom-rule validation, preview, and saving behavior (issue 3). |
| `apps/web/tests/reports.test.tsx` | Authorized reporting states and filters (issue 3). |
| `apps/web/tests/setup.test.tsx` | Company setup and assignment interactions (issue 3). |

## Working independently

Use the shared contract snapshots and development adapters for integration points. Do not wait for another issue to close. Test this workstream against those interfaces, then connect real implementations without changing the contract. Production must never substitute simulated privacy processing.

- Keep all touched directory indexes accurate and distinguish planned files from implemented files.
