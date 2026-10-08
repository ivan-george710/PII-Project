# demo/adapters

Contains the modules and files listed below.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Feature-owned development adapter package marker. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `sessions.py` | Planned | Explicitly simulated employee/manager identities for development. Owner: [issue 3](../../docs/issues/03-auth-company-setup.md). |
| `policy.py` | Planned | Supplied versioned company policies for independent workstreams. Owner: [issue 4](../../docs/issues/04-manager-settings-reports.md). |
| `engine.py` | Planned | Clearly labeled simulated engine outputs; prohibited for real submissions. Owner: [issue 1](../../docs/issues/01-privacy-engine.md). |
| `llm.py` | Planned | Deterministic provider replies and outgoing payload capture. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `reporting.py` | Planned | Synthetic idempotent reporting sink/source. Owner: [issue 4](../../docs/issues/04-manager-settings-reports.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)
- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver WorkOS authentication, company setup, and employee-manager assignments](../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
