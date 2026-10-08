# tests/e2e

Employee chat/upload through sanitization and LLM submission, with resulting events visible to the assigned manager and company rule settings applied.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `conftest.py` | Planned | Bring up test services and capture provider payloads. |
| `test_employee_to_manager.py` | Planned | Complete employee submission, sanitization, reply, and manager event flow. |
| `test_company_rules.py` | Planned | Custom/disabled rules, policy versions, and company isolation. |
| `test_processing_failures.py` | Planned | Verify errors block unsafe provider calls and retries remain consistent. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
