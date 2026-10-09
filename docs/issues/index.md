# docs/issues

Five approved implementation issues. Each includes its own validation, tests, and demo/setup helpers; there is no separate testing/demo issue or prerequisite completion gate.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Approved issue manifest and GitHub links. |
| `01-privacy-engine.md` | Existing | Approved specification: Build the complete document and image privacy engine. |
| `02-employee-chat.md` | Existing | Approved specification: Deliver employee chat with guarded uploads and LLM responses. |
| `03-auth-company-setup.md` | Existing | Approved specification: Deliver local authentication, company setup, and employee-manager assignments. |
| `04-manager-settings-reports.md` | Existing | Approved specification: Deliver manager rule settings, custom rules, and employee PII reporting. |
| `05-platform-deployment.md` | Existing | Approved specification: Connect the app and document basic setup. |

## Approved issues

- [Issue 1: Build the complete document and image privacy engine](01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1) — published and approved.
- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2) — published and approved.
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3) — published and approved.
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4) — published and approved.
- [Issue 5: Connect the app and document basic setup](05-platform-deployment.md) — [GitHub #5](https://github.com/ivan-george710/PII-Project/issues/5) — published and approved.

## Implementation conventions

Refer to the root index and each touched directory index. Python models use Pydantic v2 and frontend boundary validation uses Zod. Issue 2 includes the chat plus-menu test samples; issue 3 includes company setup; issue 4 includes settings/reporting. Issue 5 only connects the app, documents setup, and preserves the existing CI/CD.
