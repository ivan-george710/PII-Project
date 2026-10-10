# packages/engine/src/pii_guard/rules

Built-in rule definitions, custom exact-phrase/regex evaluation, and company policy controlling enabled rules and actions.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Package marker and relevant public exports. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `builtins.py` | Existing | Define built-in categories and rule IDs, including faces. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `custom.py` | Existing | Literal/regex matching with bounded validation and execution, private source-linked candidates, a submission-wide match budget, and explicit rejection of conflicting duplicate sources/geometry. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `policy.py` | Existing | Snapshot immutable enabled states; validate rule/source kinds and produce separate overlapping finding events and enabled-only internal targets with policy-version context. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
