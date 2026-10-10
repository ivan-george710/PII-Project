# apps/web/src/features/reports

Manager views of assigned employees’ PII events, detected categories, source locations, and redaction actions.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `ReportFilters.tsx` | Existing | Employee, date, and category filters. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |
| `EventList.tsx` | Existing | Show safe PII event summaries and counts. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |
| `EventDetails.tsx` | Existing | Show source locations, policy/rule identity, and redacted/allowed actions. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |
| `useReports.ts` | Existing | Fetch and paginate authorized manager reports. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
