# PII Guard repository

Repository for the company PII guard: employee chat, backend, privacy engine, manager reporting, and deployment. apps/ contains product applications; packages/ contains the engine. The existing cadence-pii-guard/ code and root case-study documents are retained as reference during migration. This scaffold does not implement the planned product.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `README.md` | Existing | Product overview, setup entry points, and links to directory indexes. |
| `.env.example` | Planned | Document required configuration with placeholders, never credentials. |
| `.dockerignore` | Planned | Exclude secrets, uploads, caches, and prototype artifacts from repository-root Docker build contexts. |
| `.gitignore` | Existing | Exclude secrets, uploaded/generated files, caches, environments, and model weights. |
| `Cadence_Group_Risk_Management_Policy__v6.0.pdf` | Existing | Existing case-study reference PDF; not a synthetic demo fixture. |
| `Cadence_TPRM_Training.docx` | Existing | Existing case-study reference Word document. |
| `Cadence_Financial_Group_Organizational_Pack.pptx` | Existing | Existing case-study reference presentation. |
| `vercel.json` | Existing | Define frontend/backend Vercel Services and same-origin /api routing. |
| `.vercelignore` | Existing | Exclude prototype files, case-study documents, and local artifacts from CLI deployment uploads. |

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
