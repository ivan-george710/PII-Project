**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Deliver project tooling, deployment, and a repeatable company demo

Status: Draft — awaiting individual approval before GitHub creation.
Suggested ownership: Platform / integration

Make the agreed monorepo easy to develop, deploy, and demonstrate, with one complete platform setup rather than separate setup and release issues.

## Scope
- Establish runnable web/API/package tooling, shared configuration conventions, environment examples, and health checks.
- Define integration fixtures/contracts for session identity, policy snapshots, engine results, report events, and LLM requests; generate the OpenAPI contract.
- Provide working development adapters so workstreams can be run without waiting for other implementations. Mark simulated/demo processing clearly and never use it for real employee submissions.
- Add Dockerfiles, Compose web/API/database services, OCR/rendering runtime tools, and model provisioning.
- Add migrations/seed commands and document WorkOS demo identity provisioning, callback URLs, LLM credentials, and startup.
- Seed a synthetic company, manager, employees, assignments, rules, and safe demonstration documents.
- Provide integration/end-to-end checks for sanitization boundaries, company access restrictions, report visibility, rule changes, and failures.
- Add CI, deployment instructions, HTTPS/session settings, persistent storage, cleanup/retention, and a short presentation walkthrough.
- Coordinate real adapters as available and document any unsupported capabilities explicitly; deployment must not silently fall back to simulated privacy processing.

## Acceptance criteria
- A developer can launch each workstream using documented commands and development fixtures.
- The deployment configuration provides the expected services, runtime dependencies, and environment validation.
- The demo walkthrough covers text, embedded scans/faces, custom rules, disabled rules, LLM submission, and manager reporting.
- End-to-end checks verify outgoing provider payloads and manager visibility when real integrations are present.
- Production mode fails clearly if real required integrations are missing and does not use demo stubs.
- Secrets, real uploads, demo credentials, and downloaded weights are excluded from Git.
- Remaining implementation limitations are visible in setup/demo documentation.

## Exact file ownership

Implement the following file plan. Shared directories assign individual files to their workstream; the directory indexes contain responsibilities and current/planned status. Existing prototype files remain reference material, not a second production implementation.

| File | Responsibility |
|---|---|
| `README.md` | Product overview, setup entry points, and links to directory indexes. |
| `.env.example` | Document required configuration with placeholders, never credentials. |
| `.gitignore` | Exclude secrets, uploaded/generated files, caches, environments, and model weights. |
| `.github/workflows/ci.yml` | Frontend/backend/engine checks and integration contract validation. |
| `apps/api/pyproject.toml` | Backend dependencies, package configuration, and test tooling. |
| `apps/api/alembic.ini` | Database migration configuration. |
| `apps/api/Dockerfile` | API runtime with required document-processing dependencies. |
| `apps/api/app/__init__.py` | Backend package marker. |
| `apps/api/app/main.py` | Build the API application, register routes, and initialize lifecycle hooks. |
| `apps/api/app/config.py` | Validate runtime settings; reject production use of demo adapters. |
| `apps/api/app/dependencies.py` | Inject sessions, database access, policies, engine, and provider interfaces. |
| `apps/api/app/db/__init__.py` | Database package marker. |
| `apps/api/app/db/base.py` | Shared declarative model base and metadata registration. |
| `apps/api/app/db/session.py` | Database connection and request/session lifecycle. |
| `apps/api/app/db/models/__init__.py` | Export/register all models (issue 4). |
| `apps/api/app/routes/__init__.py` | Routes package marker (issue 4). |
| `apps/api/app/routes/health.py` | Service readiness/liveness endpoints (issue 4). |
| `apps/api/app/schemas/__init__.py` | Schema package marker (issue 4). |
| `apps/api/app/schemas/common.py` | Shared pagination and error response types (issue 4). |
| `apps/api/app/services/__init__.py` | Services package marker (issue 4). |
| `apps/api/migrations/env.py` | Alembic runtime and model metadata integration (issue 4). |
| `apps/api/migrations/script.py.mako` | Migration file template (issue 4). |
| `apps/api/tests/conftest.py` | Shared isolated database/session fixtures (issue 4). |
| `apps/api/tests/test_health.py` | Readiness and production configuration checks (issue 4). |
| `apps/web/package.json` | Frontend dependencies and dev/build/test scripts. |
| `apps/web/index.html` | Web application mount document. |
| `apps/web/vite.config.ts` | React development server, build, and API proxy configuration. |
| `apps/web/tsconfig.json` | Frontend TypeScript configuration. |
| `apps/web/Dockerfile` | Build and serve the web application. |
| `apps/web/public/favicon.svg` | Simple application browser icon. |
| `apps/web/src/main.tsx` | Mount the React application. |
| `apps/web/src/App.tsx` | Define routes and assemble auth-aware application layouts. |
| `apps/web/src/vite-env.d.ts` | Vite environment types. |
| `apps/web/src/components/Button.tsx` | Accessible shared button. |
| `apps/web/src/components/Dialog.tsx` | Shared accessible modal. |
| `apps/web/src/components/FormField.tsx` | Labeled input with validation messages. |
| `apps/web/src/components/StatusMessage.tsx` | Shared loading/error/status feedback. |
| `apps/web/src/lib/api.ts` | Authenticated API transport and consistent error handling. |
| `apps/web/src/lib/types.ts` | Frontend API types generated or checked against OpenAPI. |
| `apps/web/src/styles/globals.css` | Minimal LLM-chat styling, shared tokens, and accessible states. |
| `apps/web/tests/setup.ts` | Shared frontend test environment (issue 4). |
| `contracts/openapi.json` | Generated backend API specification. |
| `contracts/engine.schema.json` | Engine input/output contract snapshot. |
| `contracts/integration.schema.json` | Session, policy, reporting event, and provider adapter contracts. |
| `demo/seed.py` | Seed synthetic company, users, assignments, policies, and events. |
| `demo/identities.json` | Fictional demo identity definitions without passwords or tokens. |
| `demo/walkthrough.md` | Employee-to-manager demonstration and WorkOS identity setup. |
| `demo/adapters/__init__.py` | Demo adapter exports. |
| `demo/adapters/sessions.py` | Explicitly simulated employee/manager identities for development. |
| `demo/adapters/policy.py` | Supplied versioned company policies for independent workstreams. |
| `demo/adapters/engine.py` | Clearly labeled simulated engine outputs; prohibited for real submissions. |
| `demo/adapters/llm.py` | Deterministic provider replies and outgoing payload capture. |
| `demo/adapters/reporting.py` | Synthetic idempotent reporting sink/source. |
| `demo/sample_documents/message.txt` | Synthetic text with known PII. |
| `demo/sample_documents/text.pdf` | Native-text PDF. |
| `demo/sample_documents/mixed.pdf` | PDF with native text and scanned/face content on the same page. |
| `demo/sample_documents/scanned.pdf` | Image-only scanned document. |
| `demo/sample_documents/embedded.docx` | Word document with native text, scans, and faces. |
| `demo/sample_documents/embedded.pptx` | Slides containing native text, scans, and faces. |
| `demo/sample_documents/scan.png` | Synthetic scanned paper image. |
| `demo/sample_documents/faces.jpg` | Face-detection example with documented redistribution rights. |
| `demo/sample_documents/manifest.json` | Demo scenario descriptions, synthetic provenance, and asset permissions. |
| `docs/architecture.md` | Product boundaries, data flow, contracts, and workstream ownership. |
| `docs/local-setup.md` | Install, configure, and launch each application/package. |
| `docs/engine-contract.md` | Define content, policy, artifacts, locations, findings, and failures. |
| `docs/spark-reuse.md` | Map Apple/Swift face logic to the backend implementation and test cases. |
| `docs/reporting-contract.md` | Define idempotent manager events and safe display fields. |
| `docs/rule-policy.md` | Define rule IDs, versions, enabled states, precedence, and regex limits. |
| `experiments/README.md` | Scratch-work conventions and prototype migration notes; no production imports from experiments. |
| `infra/compose.yaml` | Connect web, API, database, storage, and development configuration. |
| `infra/.dockerignore` | Exclude irrelevant/sensitive files from the Compose build contexts. |
| `infra/deploy/compose.production.yaml` | Production overrides with real integrations and persistent storage. |
| `infra/deploy/.env.example` | Deployment environment placeholders. |
| `infra/deploy/README.md` | Deployment, HTTPS, migration, readiness, and retention instructions. |
| `scripts/dev.sh` | Start the documented development stack. |
| `scripts/seed-demo.sh` | Migrate and seed the synthetic demo environment. |
| `scripts/export-api-schema.sh` | Regenerate and check contract snapshots. |
| `scripts/provision-models.py` | Acquire licensed models with checksum validation outside Git. |
| `scripts/verify.sh` | Run relevant frontend, backend, engine, and integration checks. |
| `tests/e2e/conftest.py` | Bring up test services and capture provider payloads. |
| `tests/e2e/test_employee_to_manager.py` | Complete employee submission, sanitization, reply, and manager event flow. |
| `tests/e2e/test_company_rules.py` | Custom/disabled rules, policy versions, and company isolation. |
| `tests/e2e/test_processing_failures.py` | Verify errors block unsafe provider calls and retries remain consistent. |

## Working independently

Use the shared contract snapshots and development adapters for integration points. Do not wait for another issue to close. Test this workstream against those interfaces, then connect real implementations without changing the contract. Production must never substitute simulated privacy processing.

- Keep all touched directory indexes accurate and distinguish planned files from implemented files.
