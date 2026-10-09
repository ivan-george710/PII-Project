# apps/web/src/features/rules

Company-wide rule toggles, enable/disable all controls, custom phrase/regex rules, and sample-text rule testing.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `RuleToggles.tsx` | Planned | Individual and all-on/all-off company rule controls. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |
| `CustomRuleEditor.tsx` | Planned | Create/edit exact-phrase and regex rules with case settings. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |
| `RulePreview.tsx` | Planned | Preview matches against sample text before saving. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |
| `useRules.ts` | Planned | Load, validate, save, and version company settings. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
