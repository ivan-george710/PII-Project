# packages/engine/src/pii_guard/rules

Built-in rule definitions, custom exact-phrase/regex evaluation, and company policy controlling enabled rules and actions.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Package marker and relevant public exports. |
| `builtins.py` | Planned | Define built-in categories and rule IDs, including faces. |
| `custom.py` | Planned | Validate and evaluate bounded phrase/regex rules. |
| `policy.py` | Planned | Resolve supplied enabled states, precedence, and versioned actions. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
