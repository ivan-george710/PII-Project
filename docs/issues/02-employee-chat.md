**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Deliver employee chat with guarded uploads and LLM responses

Status: Approved for implementation and GitHub publication.
Suggested ownership: Full-stack employee experience

Deliver the complete employee workflow: plain chat, file attachments, sanitization before submission, and LLM responses.

## Scope
- Implement the minimal chat page, composer, attachments, conversation history, and streaming responses.
- Implement authenticated chat/upload routes, conversation/message/attachment persistence, storage access, and file cleanup.
- Implement a guard service that resolves the employee’s company policy and calls the engine before sending anything to the provider.
- Add a provider abstraction and one working LLM integration, including a supported sanitized attachment representation.
- Preserve the sanitization boundary when resending history, handling retries, and loading conversations.
- Publish findings/actions through the reporting event interface.
- Show simple processing and failure states; block submission when sanitization cannot complete.
- Include API schemas, frontend/backend tests, and a deterministic development mode using supplied session/policy/engine/provider adapters.

## Acceptance criteria
- The complete chat flow is reviewable using development adapters and can connect to real configured integrations without rewriting the flow.
- An employee can send text and supported attachments and receive streaming replies.
- Captured outgoing provider payloads contain sanitized content and never original attachments or original sensitive history for enabled rules.
- Disabled-rule matches follow saved company policy and generate allowed events.
- Failure/retry states do not send unsanitized content or duplicate submissions/events.
- Users cannot access another employee’s conversations or files through direct resource requests.
- UI stays a plain LLM-style chat interface.

## Mandatory validation and shared conventions

Use **Pydantic v2** for Python request/response models, engine contracts, stored JSON policies/events, and provider-bound requests. Use **Zod** for frontend forms, REST responses, and streaming event payloads; TypeScript types alone are not runtime validation. Add `apps/web/src/lib/schemas.ts` for Zod schemas. Use FastAPI’s generated OpenAPI and check matching frontend payloads within this feature’s tests.

- Base Python schema: `BaseModel` with `ConfigDict(extra="forbid", validate_assignment=True)`. Use `StrictBool`, `StrictInt`, constrained strings/lists, enums, UUID, and timezone-aware datetime fields. Do not coerce strings such as `"false"` into booleans. Parse legitimate UUID/date strings deliberately at the transport boundary. Do not use `model_construct()` for external data. Use `model_validate`/`model_validate_json` on integrations and `model_dump(mode="json")` for serialization.
- Frontend: strict Zod objects, matching bounds/enums, `.safeParse()` with field feedback for forms, `.parse()`/`.safeParse()` for every API/SSE response. Malformed responses are errors, not a successful operation. Python validation remains authoritative.
- REST prefix `/api/v1`; health stays `/api/health`. Field names use snake_case. IDs are UUID strings; timestamps are RFC3339 UTC (`Z`). Organization and acting-user IDs always come from the validated session, never a client claim.
- JSON error shape: `{"error":{"code":"VALIDATION_ERROR","message":"Invalid request","fields":[{"path":"text","message":"Too long"}],"request_id":"<uuid>"}}`. Never include original PII, secrets, tracebacks, or rejected raw field values. Use 401 unauthenticated, 403 wrong role, 404 unavailable/foreign resource, 409 conflict, 413 limit exceeded, 415 unsupported file, 422 invalid payload, 502 provider error, 503 required component unavailable.
- Pagination: `limit` integer 1..100 (default 25), optional opaque `cursor` max 512 characters; response `{"items":[...],"next_cursor":null}`. Stable descending `created_at,id` ordering; no cross-company cursor reuse.
- Cookie-auth mutations require CSRF validation and an allowed Origin. Frontend sends credentials; do not put bearer/session credentials in localStorage. Validate authorization again on every endpoint and every file access.
- Each issue includes its own migrations, UI/backend/package work, integration adapters, fixtures, and checks. Do not wait for another issue to close. Implement against the contracts below; simulated adapters are explicit development-only substitutes, prohibited in production.
- Official validation reference: [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), [strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), [Zod basics](https://zod.dev/basics).

## Employee APIs: exact requests, responses, and state

All below require an employee session (manager-only accounts get403); infer company/user from session. Use models in `schemas/chat.py` and `schemas/uploads.py`. Existing `/api/health` remains a200 `HealthResponse` and stays callable without employee auth.

### JSON models

- `Conversation`: `{id, title, created_at, updated_at}`; UUID IDs, title1..120, UTC times.
- `Attachment`: `{id, filename, mime_type, size_bytes, state, sanitized_download_url}`; filename basename1..255, size1..26214400, state=`pending_upload|uploaded|processing|sanitized|failed`, download URL null until sanitized. Never expose storage keys/original URLs.
- `Message`: `{id, conversation_id, role, text, attachment_ids, state, created_at}`; role=`user|assistant`, text is sanitized content only, IDs max5, state=`processing|completed|failed|cancelled`. Original draft stays transient until engine processing and is not public history.

| Endpoint | Input | Output and behavior |
|---|---|---|
| `POST /api/v1/conversations` | JSON `{title:"New chat"}`; title optional default, trimmed1..120 |201 `Conversation` owned by session employee |
| `GET /api/v1/conversations` | Pagination only |200 paginated `Conversation` list owned by employee |
| `GET /api/v1/conversations/{id}/messages` | UUID path and pagination |200 paginated `Message`; missing/foreign conversation404 |
| `POST /api/v1/uploads/init` | `{filename, declared_mime, size_bytes}`; allowed declarations PDF/DOCX/PPTX/PNG/JPEG, size1..25MiB |201 `{attachment:Attachment, upload:{method:"PUT",url:"<short-lived signed URL>",headers:{"Content-Type":"..."},expires_at:"<UTC>"}}`; signed storage upload bypasses Vercel function body limit; server sets storage key/company/user |
| `POST /api/v1/uploads/{id}/complete` | Empty JSON `{}` after client PUT |200 `Attachment` with state uploaded only after storage existence/size/content MIME checks; invalid file415, size mismatch422, foreign ID404 |
| `GET /api/v1/uploads/{id}` | UUID path |200 authorized `Attachment` status |
| `GET /api/v1/uploads/{id}/sanitized` | UUID path |200 sanitized file bytes with correct Content-Type and safe Content-Disposition, or302 short-lived sanitized download URL; unsanitized state409, foreign404 |
| `POST /api/v1/conversations/{id}/messages` | JSON `{text,attachment_ids,client_request_id}`; text max100000, IDs unique max5, at least nonblank text or one file; client_request_id UUID required |SSE200 after validating ownership/limits; follows event contract below; one submission per employee/conversation/client_request_id; duplicate identical request replays completed stored result, different body409 |

No endpoint accepts arbitrary server paths, employee IDs, company IDs, raw provider credentials, or model selection. Signed upload URLs are ephemeral sensitive URLs and must not enter logs, chat text, or manager reports.

### Stream contract (POST response consumed using fetch streaming, not EventSource)

Each frame: `event: <name>\ndata: <one JSON object>\n\n`, UTF-8, Cache-Control no-store, Content-Type text/event-stream. Validate frames using a Zod discriminated union. Emit:

1. `processing`: `{type:"processing",submission_id,stage:"sanitizing"}`.
2. `sanitized`: `{type:"sanitized",submission_id,user_message:Message,attachments:[Attachment],policy_version}` after all artifacts succeed and reporting is durably recorded.
3. `delta`: `{type:"delta",submission_id,assistant_message_id,sequence:positive int,text:str}`; sequences start1.
4. `done`: `{type:"done",submission_id,assistant_message:Message}` exactly once; completed message matches accumulated deltas.
5. On processing/provider failure after headers: `error` `{type:"error",submission_id,code,message,retryable:bool}` then close; never emit done. Before headers use standard JSON error/status. Sanitization error sends no provider request.

If the client disconnects before provider submission, cancel processing safely. After submission, stop streaming and persist the completed or cancelled status consistently; do not start another provider call on reconnect. Use persisted idempotency/result state, not module globals. Same conversation allows one active submission; concurrent request409.

### Pipeline and integrations

Order: authenticate → validate → reserve idempotency key → verify conversation/files ownership → obtain immutable policy → engine → persist sanitized user content/artifacts and events → construct provider payload → provider stream → persist assistant result. If policy retrieval, sanitization, storage, or reporting ingestion fails, do not submit to provider. Revalidate all retained conversation turns/attachments against the current policy before each new provider call; policy changes must not leave previously allowed PII in outbound history. Avoid duplicate historical report events by versioned idempotency keys.

Define injectable methods: `policy_store.get_snapshot(organization_id)->PolicySnapshot`, `engine.sanitize(SanitizeRequest)->SanitizeResult`, `event_sink.record(EventBatch)->None`, `llm.stream(ProviderRequest)->AsyncIterator[ProviderDelta]`, `storage.create_upload/verify_upload/read_original/write_sanitized/read_sanitized`. `ProviderRequest` is Pydantic with ordered sanitized messages and sanitized artifact references only; configure provider/model server-side. Validate responses/deltas from provider adapters. Represent unsupported provider document formats as sanitized extracted text/images, never an original fallback.

### Database and UI implementation details

Conversation fields: id/company_id/employee_id/title/timestamps. Message fields: id/company_id/conversation_id/role/sanitized_text/state/policy_version/timestamps. Attachment fields: id/company_id/employee_id/conversation_id nullable/original_key/sanitized_key/filename/mime/size/hash/state/timestamps. Persist submission idempotency and assistant sequencing in an additional `submission.py` model with unique `(employee_id,conversation_id,client_request_id)`; never assume messages alone prevent retries. Add matching indexes/foreign keys in the chat migration.

UI: plain composer and message list; attachments show filename/status; Enter sends, Shift+Enter newline; disable duplicate sends during processing; show useful error/retry states. Replace the current minimal health page with React while preserving health connectivity and CI. Do not render an unsanitized submitted draft as completed history. Escape/render user content safely. Tests capture outgoing provider payloads, disabled-rule actions, policy-change resanitization, storage/report failures, duplicate IDs, Unicode/invalid SSE, and employee/company isolation.

## Built-in test data in the chat attachment menu

The app itself must expose presentation samples from the `+` button on the left of the chat composer, alongside ordinary file attachment. Do not make the presenter find files on disk.

- `AttachmentMenu.tsx` contains `Upload file` and `Try test data` entries. The test-data submenu groups Message, PDF, Word, PowerPoint, and Image examples.
- `DemoSamplePicker.tsx` displays each sample’s title, short description, format, and whether it covers text PII, scans, embedded faces, or custom rules. Keep the menu simple; no separate employee dashboard.
- Selecting a message fills the draft without submitting it. Selecting a file creates an employee-owned attachment and adds it to the composer without automatically sending it. The employee can inspect/remove it and press Send normally.
- Samples must pass through the exact same company-policy, engine, LLM, and manager-event flow as real uploads. Never substitute known/precomputed redaction boxes or pretend synthetic engine results are real processing. Disabled/custom rules affect samples normally.
- Show loading/errors and prevent duplicate attachments on repeated selection. Provide all test scenarios in the seeded manifest, including native text, mixed/scan PDF, embedded scans/faces in DOCX/PPTX, standalone scan/face images, and custom-rule text.
- Sample images must have documented redistribution rights; message/document PII is fictional. This feature does not enable simulated auth/engine/provider adapters. It can be enabled in the actual presentation deployment using `SHOW_DEMO_SAMPLES=true`, independent of `DEMO_ADAPTERS_ENABLED`.

### Sample API: authenticated, scoped, and typed

Implement in `routes/demo.py`, `services/demo.py`, and `schemas/demo.py`:

| Endpoint | Exact input | Output |
|---|---|---|
| `GET /api/v1/demo/samples` | Employee session; no body; only available when SHOW_DEMO_SAMPLES=true |200 `{items:[DemoSample]}`; feature disabled404 |
| `POST /api/v1/demo/samples/{sample_id}/attachments` | Employee session; UUID path; JSON `{client_request_id:UUID}` |201 `Attachment` in uploaded state, scoped to acting employee/company; same employee/sample/client_request_id replays the same attachment200; message sample422, unknown404 |

`DemoSample` is a Pydantic/Zod discriminated union: common `{id:UUID,title:str1..80,description:str1..240,tags:list[Literal["text_pii","scanned_text","faces","custom_rules"]]max4,kind:"message"|"file"}`; message adds `{text:str1..100000}`; file adds `{filename:str1..255,mime_type:allowed MIME,size_bytes:int1..25MiB}`. Extra fields forbidden; message objects have no file fields and file objects no text field. Never return server paths, original storage keys, or manager/employee IDs.

The file endpoint copies a known manifest asset into the trusted employee storage namespace, validates it as an ordinary uploaded file, and returns the same Attachment model used by uploads. It accepts no arbitrary URL/path. Apply the usual session/CSRF/authorization and limits. Catalog does not enumerate real employee documents. Test menu keyboard accessibility, message draft insertion, file removal, idempotent selection, feature disabled state, forged IDs, and real submission/report flow.

### Sample assets included in this feature

The app plus menu loads every demonstration example from `demo/sample_documents/manifest.json`. The manifest contains fixed UUIDs, kind, title, description, tags, fictional message text or a server-relative licensed asset reference, MIME, byte size, and SHA256. Provision file samples into trusted private storage; seed the catalog idempotently. Message samples and file sample DTOs must match issue 2. Add `messages.json` for the fictional message scenarios and `faces.jpg` only with permission/provenance. The sample selector uses real processing and is not an engine stub.

Walkthrough: login employee → select test examples from the composer plus menu → text with name/email/employee ID → PDF mixed native/scan/face → PPTX and DOCX embedded content → standalone image → see sanitized LLM payload/reply → login manager → see matching employee/category/location/actions → disable email rule → resubmit and see allowed_disabled → enable custom project-name rule and verify → demonstrate unsupported file/failure blocks provider → verify other manager/company cannot see events.


The chat implementation also owns the minimal React/TypeScript entry point, shared UI/API utilities, and frontend build setup. Register the feature page routes in `App.tsx` as they are implemented.

## Exact file ownership

Implement the following file plan. Shared directories assign individual files to their workstream; the directory indexes contain responsibilities and current/planned status. Existing prototype files remain reference material, not a second production implementation.

| File | Responsibility |
|---|---|
| `apps/api/app/routes/demo.py` | Authenticated built-in sample catalog and attachment selection endpoints. |
| `apps/api/app/schemas/demo.py` | Pydantic sample union and attachment-selection request models. |
| `apps/api/app/services/demo.py` | Load safe sample assets and create employee-owned attachments. |
| `apps/api/tests/test_demo.py` | Catalog scoping, feature toggle, selection idempotency, and file limits. |
| `apps/web/src/features/chat/AttachmentMenu.tsx` | Composer-left plus menu for Upload file and Try test data. |
| `apps/web/src/features/chat/DemoSamplePicker.tsx` | Simple grouped sample selector; insert drafts or attach files without sending. |
| `apps/web/src/features/chat/useDemoSamples.ts` | Load the typed catalog and select message/file examples. |
| `apps/web/tests/demo_samples.test.tsx` | Menu accessibility, draft insertion, attachment selection/removal, and failures. |
| `apps/api/app/db/models/submission.py` | Persist submission state, idempotency, request hash, and stream result. |
| `apps/api/app/db/models/conversation.py` | Employee-owned conversations (issue 2). |
| `apps/api/app/db/models/message.py` | Conversation turns and safe provider history (issue 2). |
| `apps/api/app/db/models/attachment.py` | File ownership, storage references, and processing state (issue 2). |
| `apps/api/app/llm/__init__.py` | LLM package marker. |
| `apps/api/app/llm/client.py` | Provider-neutral request, streaming, and attachment interface. |
| `apps/api/app/llm/providers/__init__.py` | Provider adapter exports. |
| `apps/api/app/llm/providers/openai.py` | Initial configurable OpenAI provider adapter; accept sanitized payloads only. |
| `apps/api/app/routes/chat.py` | Conversation, submission, and streaming endpoints (issue 2). |
| `apps/api/app/routes/uploads.py` | Authorized upload and sanitized-file access endpoints (issue 2). |
| `apps/api/app/schemas/chat.py` | Conversation, message, submission, and stream events (issue 2). |
| `apps/api/app/schemas/uploads.py` | File metadata, processing state, and authorized output responses (issue 2). |
| `apps/api/app/services/guard.py` | Apply company policy, sanitize, block failures, and publish events (issue 2). |
| `apps/api/app/services/chat.py` | Persist conversation flow, build safe history, and stream LLM results (issue 2). |
| `apps/api/app/storage/__init__.py` | Storage package marker. |
| `apps/api/app/storage/files.py` | Separate original/sanitized artifact storage and enforce authorized access. |
| `apps/api/app/storage/cleanup.py` | Apply configured file retention and cleanup. |
| `apps/api/migrations/versions/0002_conversations_messages_attachments.py` | Chat and attachment tables (issue 2); enforce ownership relationships and coordinate migration ordering through shared contracts. |
| `apps/api/tests/test_chat.py` | Safe history, guarded provider calls, streaming, and retry behavior (issue 2). |
| `apps/api/tests/test_uploads.py` | Upload authorization, supported inputs, and output access (issue 2). |
| `apps/api/tests/test_guard.py` | Sanitized-only payloads, disabled rules, and blocked failures (issue 2). |
| `apps/web/src/features/chat/ChatComposer.tsx` | Message input, file selection, and send/cancel controls. |
| `apps/web/src/features/chat/MessageList.tsx` | Render conversation turns and streamed responses. |
| `apps/web/src/features/chat/AttachmentList.tsx` | Display attached files and processing states. |
| `apps/web/src/features/chat/useChat.ts` | Manage conversations, submissions, retries, and response streaming. |
| `apps/web/src/layouts/ChatLayout.tsx` | Minimal chat shell and conversation navigation (issue 2). |
| `apps/web/src/pages/Chat.tsx` | Plain employee conversation page (issue 2). |
| `apps/web/tests/chat.test.tsx` | Composer, attachment, streaming, retry, and error behavior (issue 2). |
| `demo/walkthrough.md` | Employee-to-manager demonstration and WorkOS identity setup. |
| `demo/adapters/__init__.py` | Feature-owned development adapter package marker. |
| `demo/adapters/llm.py` | Deterministic provider replies and outgoing payload capture. |
| `demo/sample_documents/message.txt` | Synthetic text with known PII. |
| `demo/sample_documents/text.pdf` | Native-text PDF. |
| `demo/sample_documents/mixed.pdf` | PDF with native text and scanned/face content on the same page. |
| `demo/sample_documents/scanned.pdf` | Image-only scanned document. |
| `demo/sample_documents/embedded.docx` | Word document with native text, scans, and faces. |
| `demo/sample_documents/embedded.pptx` | Slides containing native text, scans, and faces. |
| `demo/sample_documents/scan.png` | Synthetic scanned paper image. |
| `demo/sample_documents/faces.jpg` | Face-detection example with documented redistribution rights. |
| `demo/sample_documents/messages.json` | Fictional text examples for contact details, employee IDs, government/financial IDs, and custom rules in the app sample menu. |
| `demo/sample_documents/manifest.json` | Demo scenario descriptions, synthetic provenance, and asset permissions. |
| `apps/web/package.json` | Frontend dependencies and dev/build/test scripts. |
| `apps/web/index.html` | Web application mount document. |
| `apps/web/vite.config.ts` | React development server, build, and API proxy configuration. |
| `apps/web/tsconfig.json` | Frontend TypeScript configuration. |
| `apps/web/src/main.tsx` | Mount the React application. |
| `apps/web/src/App.tsx` | Define routes and assemble auth-aware application layouts. |
| `apps/web/src/vite-env.d.ts` | Vite environment types. |
| `apps/web/src/components/Button.tsx` | Accessible shared button. |
| `apps/web/src/components/Dialog.tsx` | Shared accessible modal. |
| `apps/web/src/components/FormField.tsx` | Labeled input with validation messages. |
| `apps/web/src/components/StatusMessage.tsx` | Shared loading/error/status feedback. |
| `apps/web/src/lib/api.ts` | Authenticated API transport and consistent error handling. |
| `apps/web/src/lib/schemas.ts` | Shared strict Zod runtime schemas and discriminated SSE unions. |
| `apps/web/src/lib/types.ts` | Frontend API types generated or checked against OpenAPI. |
| `apps/web/src/styles/globals.css` | Minimal LLM-chat styling, shared tokens, and accessible states. |
| `apps/web/tests/setup.ts` | Shared frontend test environment (issue 2). |

## Working independently

Use the documented interfaces and feature-owned development adapters for integration points. Do not wait for another issue to close. Test this workstream against those interfaces, then connect real implementations without changing the contract. Production must never substitute simulated privacy processing.

- Keep all touched directory indexes accurate and distinguish planned files from implemented files.
