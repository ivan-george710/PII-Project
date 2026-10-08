# apps/web/src/features/rules

Company-wide rule toggles, enable/disable all controls, custom phrase/regex rules, and sample-text rule testing.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `RuleToggles.tsx` | Planned | Individual and all-on/all-off company rule controls. |
| `CustomRuleEditor.tsx` | Planned | Create/edit exact-phrase and regex rules with case settings. |
| `RulePreview.tsx` | Planned | Preview matches against sample text before saving. |
| `useRules.ts` | Planned | Load, validate, save, and version company settings. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
