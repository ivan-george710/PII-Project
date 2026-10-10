# apps/web/tests

Frontend component and interaction tests.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `chat.test.tsx` | Implemented | Composer, attachment, streaming, retry, and error behavior. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |
| `auth.test.tsx` | Existing | Sign-in/sign-up navigation, unrestricted credentials, password visibility and form feedback. Owner: [issue 3](../../../docs/issues/03-auth-company-setup.md). |
| `rules.test.tsx` | Existing | Toggle, custom-rule validation, preview, and saving behavior. Owner: [issue 4](../../../docs/issues/04-manager-settings-reports.md). |
| `reports.test.tsx` | Existing | Authorized reporting states and filters. Owner: [issue 4](../../../docs/issues/04-manager-settings-reports.md). |
| `setup.test.tsx` | Existing | Company setup and assignment interactions. Owner: [issue 3](../../../docs/issues/03-auth-company-setup.md). |
| `setup.ts` | Existing | Shared frontend test environment. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |
| `demo_samples.test.tsx` | Implemented | Menu accessibility, draft insertion, attachment selection/removal, and failures. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## Interface and employee creation update

| Filename | Status | Responsibility |
|---|---|---|
| employee_creation.test.tsx | Existing | Unrestricted credential inputs, assigned creation, success cleanup and duplicate failure feedback. |
