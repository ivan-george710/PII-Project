# apps/web/src/lib

Backend API client and frontend utilities. The frontend communicates with the backend rather than directly invoking the engine.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `api.ts` | Existing | Authenticated API transport and consistent error handling. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `types.ts` | Implemented | Frontend API types generated or checked against OpenAPI. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `schemas.ts` | Implemented | Shared strict Zod API/SSE runtime schemas, discriminated stream events, and auth request/response validation; preserve lowercase email normalization and unrestricted credential inputs. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

Use Zod to validate API/SSE payloads at runtime; generated TypeScript types alone are insufficient. Align schemas with backend Pydantic/OpenAPI and contracts/examples.json.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## Delivered interface update

`schemas.ts` adds strict employeeInput/employeeCreated schemas; credentials remain unrestricted strings and emails normalize to lowercase.
