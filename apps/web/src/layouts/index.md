# apps/web/src/layouts

Minimal chat shell and manager navigation layouts.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `ChatLayout.tsx` | Planned | Minimal chat shell and conversation navigation. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `ManagerLayout.tsx` | Planned | Manager reports/settings/setup navigation. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
