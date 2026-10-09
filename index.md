# PII Guard repository

Repository for the company PII guard: employee chat, backend, privacy engine, manager reporting, and deployment. apps/ contains product applications; packages/ contains the engine. The existing cadence-pii-guard/ code and root case-study documents are retained as reference during migration. This scaffold does not implement the planned product.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. **Deferred** files are optional future work, outside the current issues. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `README.md` | Existing | Short setup instructions and live frontend/backend links. Owner: [issue 5](docs/issues/05-platform-deployment.md). |
| `.env.example` | Existing | Only configuration actually used by the features, with placeholder values. Owner: [issue 5](docs/issues/05-platform-deployment.md). |
| `.dockerignore` | Deferred | Optional future work; outside the five current issues. Exclude secrets, uploads, caches, and prototype artifacts from repository-root Docker build contexts. |
| `.gitignore` | Existing | Keep secrets, uploads, caches, and model downloads out of Git. Owner: [issue 5](docs/issues/05-platform-deployment.md). |
| `Cadence_Group_Risk_Management_Policy__v6.0.pdf` | Existing | Existing case-study reference PDF; not a synthetic demo fixture. |
| `Cadence_TPRM_Training.docx` | Existing | Existing case-study reference Word document. |
| `Cadence_Financial_Group_Organizational_Pack.pptx` | Existing | Existing case-study reference presentation. |
| `vercel.json` | Existing | Keep frontend/backend services connected through same-origin /api routing. Owner: [issue 5](docs/issues/05-platform-deployment.md). |
| `.vercelignore` | Existing | Keep local/private/reference artifacts out of deployment uploads. Owner: [issue 5](docs/issues/05-platform-deployment.md). |

## Subdirectories

- [.github/](.github/index.md): see its exact file manifest.
- [apps/](apps/index.md): see its exact file manifest.
- [cadence-pii-guard/](cadence-pii-guard/index.md): see its exact file manifest.
- [contracts/](contracts/index.md): see its exact file manifest.
- [demo/](demo/index.md): see its exact file manifest.
- [docs/](docs/index.md): see its exact file manifest.
- [experiments/](experiments/index.md): see its exact file manifest.
- [infra/](infra/index.md): see its exact file manifest.
- [packages/](packages/index.md): see its exact file manifest.
- [scripts/](scripts/index.md): see its exact file manifest.
- [tests/](tests/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/anubhav20ch/PII-Project/issues/1)
- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/anubhav20ch/PII-Project/issues/2)
- [Issue 3: Deliver WorkOS authentication, company setup, and employee-manager assignments](docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/anubhav20ch/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/anubhav20ch/PII-Project/issues/4)
- [Issue 5: Connect the app and document basic setup](docs/issues/05-platform-deployment.md) — [GitHub #5](https://github.com/anubhav20ch/PII-Project/issues/5)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
