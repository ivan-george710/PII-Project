# apps/web/src/features/auth

Sign-in, sign-out, session state, and role-aware navigation.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `AuthProvider.tsx` | Existing | Load session identity and provide company/role state. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |
| `RequireAuth.tsx` | Existing | Route guards and role-aware redirects; backend remains authoritative. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |
| `useAuth.ts` | Existing | Access authentication state and login/logout actions. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 3: Deliver WorkOS authentication, company setup, and employee-manager assignments](../../../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/anubhav20ch/PII-Project/issues/3)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
