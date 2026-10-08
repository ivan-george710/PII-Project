# apps/web/src/features/reports

Manager views of assigned employees’ PII events, detected categories, source locations, and redaction actions.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `ReportFilters.tsx` | Planned | Employee, date, and category filters. |
| `EventList.tsx` | Planned | Show safe PII event summaries and counts. |
| `EventDetails.tsx` | Planned | Show source locations, policy/rule identity, and redacted/allowed actions. |
| `useReports.ts` | Planned | Fetch and paginate authorized manager reports. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
