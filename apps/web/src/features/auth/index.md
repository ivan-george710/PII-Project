# apps/web/src/features/auth

Sign-in, sign-out, session state, and role-aware navigation.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `AuthProvider.tsx` | Planned | Load session identity and provide company/role state. |
| `RequireAuth.tsx` | Planned | Route guards and role-aware redirects; backend remains authoritative. |
| `useAuth.ts` | Planned | Access authentication state and login/logout actions. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
