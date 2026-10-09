# docs

Architecture, local setup, engine contracts, and Spark/Still reuse notes. Spark face logic uses Apple frameworks and needs adaptation for a Python/Linux backend.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `architecture.md` | Deferred | Optional future work; outside the five current issues. Product boundaries, data flow, contracts, and workstream ownership. |
| `local-setup.md` | Existing | Exact install/start commands and where to configure credentials. Owner: [issue 5](issues/05-platform-deployment.md). |
| `engine-contract.md` | Planned | Define content, policy, artifacts, locations, findings, and failures. Owner: [issue 1](issues/01-privacy-engine.md). |
| `spark-reuse.md` | Planned | Map Apple/Swift face logic to the backend implementation and test cases. Owner: [issue 1](issues/01-privacy-engine.md). |
| `reporting-contract.md` | Planned | Define idempotent manager events and safe display fields. Owner: [issue 4](issues/04-manager-settings-reports.md). |
| `rule-policy.md` | Planned | Define rule IDs, versions, enabled states, precedence, and regex limits. Owner: [issue 4](issues/04-manager-settings-reports.md). |
| `cicd.md` | Existing | Existing Actions configuration, deployed URLs, and simple verification commands. Owner: [issue 5](issues/05-platform-deployment.md). |

## Subdirectories

- [issues/](issues/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](issues/01-privacy-engine.md) — [GitHub #1](https://github.com/anubhav20ch/PII-Project/issues/1)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/anubhav20ch/PII-Project/issues/4)
- [Issue 5: Connect the app and document basic setup](issues/05-platform-deployment.md) — [GitHub #5](https://github.com/anubhav20ch/PII-Project/issues/5)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
