# apps/web/src/features/setup

Company onboarding, user setup, and employee-to-manager assignments.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `OrganizationForm.tsx` | Planned | Set company details and policy-editing permissions. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |
| `EmployeeAssignments.tsx` | Planned | Assign employees to managers within their company. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |
| `useOrganization.ts` | Planned | Load users and persist company setup. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 3: Deliver WorkOS authentication, company setup, and employee-manager assignments](../../../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
