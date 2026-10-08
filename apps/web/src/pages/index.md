# apps/web/src/pages

Login, Chat, ManagerReports, ManagerSettings, and CompanySetup page components.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `Login.tsx` | Planned | WorkOS sign-in entry page. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `Chat.tsx` | Planned | Plain employee conversation page. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `ManagerReports.tsx` | Planned | Assigned-employee event reporting page. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |
| `ManagerSettings.tsx` | Planned | Company policy toggles and custom rules page. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |
| `CompanySetup.tsx` | Planned | Company/users/manager assignment page. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver WorkOS authentication, company setup, and employee-manager assignments](../../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
