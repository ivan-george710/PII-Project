# tests/e2e

Reserved for an optional future cross-app test suite. Current issues include their own tests and acceptance checks; a separate end-to-end framework is deferred.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `conftest.py` | Deferred | Optional future work; outside the five current issues. Bring up test services and capture provider payloads. |
| `test_employee_to_manager.py` | Deferred | Optional future work; outside the five current issues. Complete employee submission, sanitization, reply, and manager event flow. |
| `test_company_rules.py` | Deferred | Optional future work; outside the five current issues. Custom/disabled rules, policy versions, and company isolation. |
| `test_processing_failures.py` | Deferred | Optional future work; outside the five current issues. Verify errors block unsafe provider calls and retries remain consistent. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

See the [five approved issues](../../docs/issues/index.md). This directory has no required implementation files in the current scope; deferred entries remain optional.
