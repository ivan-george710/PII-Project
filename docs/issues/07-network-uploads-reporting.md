**Before starting: refer to the root `index.md` and the `index.md` in every directory you touch. Follow their exact filenames/responsibilities and update the indexes when files change.**

Status: Requested roadmap capability; **not implemented**. This issue includes implementation, integration, setup, synthetic demonstration data and tests. There is no separate testing/demo issue and no prerequisite issue-completion gate.

## Preserve the current app

Fetch current upstream main before starting and before submitting. Preserve local email/password auth, signup, Argon2 hashes, database sessions, CSRF, existing company/employee/manager assignments, monochrome icon-free UI, migrations and passing CI. Do not restore WorkOS. Email/password remain strings without format/verification/strength/length checks. Add migrations after the actual current head; never rewrite applied migrations. Use real implementations in production; explicit synthetic adapters are test/development-only. Missing privacy processing must block outgoing submissions.

Python boundaries use Pydantic v2 (`extra="forbid"`, strict booleans/integers, UUIDs, aware UTC timestamps, bounded lists/strings). Frontend boundaries use strict Zod schemas. Reject unknown fields and malformed data. Use the existing error envelope `{error:{code,message,fields,request_id}}`; messages/fields must not contain raw PII, passwords, tokens, upload bodies, or certificate private keys. Use 401 unauthenticated, 403 unauthorized, 404 unavailable/foreign resource, 409 conflict, 413 limits, 415 unsupported media, 422 validation, 503 unavailable enforcement components. Cookie mutations require existing CSRF and allowed Origin checks. IDs/roles/company membership are resolved from authenticated identities, never trusted from browser-supplied company/employee IDs.

# Redact external website submissions and report them to the employee's immediate manager

## Outcome

On the protected company network, an enrolled employee sends a message or uploads a file directly to an external LLM or another website. Hold the request, inspect the outbound content using company toggles/custom rules, forward only verified sanitized content and persist a report in that employee's immediate manager account. The employee does not need to use our chat app. Company policy remains shared with app-originated submissions; do not create a separate rule system.

This is application-layer inspection/rewrite within the network gateway, not packet-level regex replacement. Deliver parsing, sanitization integration, transport reconstruction, durable audit ingestion, manager report UI integration and fixtures together. Network enrollment and enforcement use the shared gateway context/decision contract; include tested integration against that interface without waiting for a different issue to close. When network routing, real engine or manager reports are absent, use explicitly labeled test adapters only in development, block real production uploads and state the missing capability in docs.

## Website coverage and boundaries

- Support HTTP/1.1 and HTTP/2 outbound POST/PUT/PATCH submissions using multipart/form-data, application/json, application/x-www-form-urlencoded and raw supported-file bodies. Inspect supported content independently of whether the host is classified as an LLM. Detect file format from bytes, not filename/header alone.
- Text includes message/form fields; artifacts include PDF, DOCX, PPTX, PNG and JPEG. Inspect native text, scanned pages, embedded scans/images, hidden content and faces using the engine contract. Do not implement a second OCR/face detector in the gateway. Image/face implementation is currently paused; the issue records that scope but does not authorize starting image implementation now. While a required detector is unavailable, block affected artifacts rather than presenting them as clean.
- Website-specific protocols require adapters. First prove one synthetic LLM JSON-message endpoint and one synthetic non-LLM multipart/raw-upload endpoint. Include a coverage matrix showing which real sites were verified, version/date and unverified/blocked cases. Do not claim every external website works transparently.
- Multipart uploads with multiple fields/files are atomic. Resumable/chunked upload sessions, application-signed bodies, client-side encryption, encrypted archives, unsupported file formats and WebSocket/WebTransport submissions are initially blocked unless an explicitly implemented adapter reconstructs, validates and safely releases the entire submission. Ordinary HTTP transfer encoding 'chunked' is supported by bounded full buffering; it is distinct from application-level resumable sessions.
- Treat signed URLs as opaque secrets. A raw-body pre-signed upload may work if only the URL is signed; body-hash/signed-header schemes may not. Never modify application signatures by guessing or reuse a request that no longer validates. Blocking is an honest supported outcome.
- Classification exempts tested authentication/password traffic from PII reporting; an exemption must not allow arbitrary user upload bodies. Do not log login credentials, website cookies/Authorization headers, unrelated browsing bodies or query values. Unknown body-bearing operations remain blocked until classification is supported. Inspect query-based submissions only with an explicit site adapter; otherwise block those known submission routes and document that generic GET/query exfiltration is not universally detected.

## Processing order: no original bytes leave early

1. Resolve a trusted `EmployeeContext` using gateway device identity, never an employee header or target-site login. API must confirm active company/user/device and a current immediate-manager assignment. Snapshot assignment ID/manager ID and policy version server-side; manager must be active and same company.
2. Create a server-generated request/submission UUID and private body spool. Parse/decompress with limits before forwarding any user body bytes. Default total decoded body <=100MiB, <=5 files, <=25MiB/file, <=100 pages/slides/file, <=100000 Unicode text characters, processing deadline 60 seconds. Bound multipart headers/parts (<=100 parts), compression expansion (<=20x) and disk usage. Settings configurable; reject overlimits with 413. Never forward partial chunks on timeout.
3. Request immutable company policy snapshot. Enabled/disabled built-ins and custom rules obey the engine contract; detectors still run for disabled rules and yield `allowed_disabled`. All-rules-off permits detected content intentionally and reports it as allowed_disabled; it must not disable identity/audit/format validation or permit missing-engine bypass.
4. Call the reusable engine once for the complete submission; artifact count/IDs must match input. Every required detector/extractor/rewriter must succeed. Resolve overlap policy as defined by engine. Do not mark uninspectable/unsupported content as clean.
5. Reconstruct JSON/form/multipart/raw bodies. Preserve semantic field order where relevant, duplicate form keys, filename/content type relationships and non-content required site metadata. Replace only supported user-content fields/files. Regenerate multipart boundary/Content-Length and necessary content-encoding; remove stale body digests only when the verified adapter permits it, otherwise block. Preserve target cookies/authorization privately for forwarding but never include them in events. Filenames and metadata can contain PII: sanitize outward filenames, do not store raw filenames in reports.
6. Validate the final transport against the adapter contract and leak checks; use sanitized spools only. Before forwarding, persist an idempotent event batch and receive a durable receipt. If the reporting service is unavailable, block with `AUDIT_UNAVAILABLE` (no unbounded plaintext queue or silent dropped reports). Ensure manager assignment hasn't changed between initial snapshot and durable admission: a change causes policy/assignment re-evaluation before any bytes leave.
7. Forward the rebuilt request once. Preserve HTTP response status/body behavior for the site. Record delivery outcome without changing the findings: `not_sent|sent|accepted|rejected|unknown`. `accepted` means a successful upstream response only, not a guarantee the third-party stored the data. Network timeout after sending becomes unknown; never claim not_sent and never blindly retry a side-effecting upload.
8. Delete original/sanitized temporary spools on completion/failure. A janitor covers crashes with a documented TTL <=15 minutes; files use restricted permissions and encrypted volume, outside web-served paths. Report DTOs never expose spool paths, original bytes or sanitized download links. Never forward the original body on any exception.

## Gateway inspect contract

Implement `inspect_outbound(context,request) -> GatewayDecision` using the network contract in `packages/gateway/src/pii_gateway/contracts.py`:
`{request_id,action:"forward|block",body_path:<sanitized private spool or null>,headers:<rewritten transport headers>,event_receipt_id:<UUID or null>,reason_code:<safe code or null>}`.

`action=forward` for submissions requires a complete validated sanitized request and durable report receipt. Even no-finding and disabled-rule submissions need an audit admission record. `block` never includes original body as a fallback. Safe reason codes include `UNSUPPORTED_TRANSPORT`, `UNSUPPORTED_FILE`, `ENCRYPTED_FILE`, `IDENTITY_UNAVAILABLE`, `MANAGER_UNASSIGNED`, `POLICY_UNAVAILABLE`, `ENGINE_UNAVAILABLE`, `PROCESSING_TIMEOUT`, `REWRITE_FAILED`, `AUDIT_UNAVAILABLE`. Wire a required mitmproxy request hook that handles exceptions by blocking, because an addon exception alone must not accidentally resume forwarding.

## Service APIs and persistence

All `/api/v1/internal/network/...` endpoints use organization-scoped gateway mTLS identity from the network contract, not browser cookies. UUIDs/date strings validate explicitly; strict payloads reject extra fields. Resolve ownership from registered gateway/verified device, not a claimed company/manager ID. Reports have a distinct `source:"network"`; no fake chat conversation/message IDs.

- `GET /policy?device_id=<uuid>`: 200 `{employee_id,device_id,assignment_version,manager_id,policy:<existing PolicySnapshot>,expires_at:"<UTC>"}`. Resolve employee/manager from active device server-side; gateway scoped to that company. Expiry <=30 seconds. Existing policy contract reused byte-for-byte. 409 MANAGER_UNASSIGNED, 503 POLICY_UNAVAILABLE. This API never takes organization_id from query.
- `POST /events`: JSON `{submission_id,device_id,assignment_version,policy_version,occurred_at,destination_host,destination_port,transport,decision,reason_code,files,findings}`. IDs UUID; assignment_version is the current ManagerAssignment.updated_at UTC timestamp (not a nonexistent assignment UUID); policy_version strict integer >=1; destination_host validated lowercased DNS hostname or IP without scheme/path/userinfo/query <=253; port 1..65535; occurred_at aware UTC (reject >5 min future); `transport` one of `json|form|multipart|raw|unsupported`; `decision` one of `sanitized|allowed|blocked`; reason_code null unless blocked; <=5 files and <=10000 findings. `files`: `{artifact_id,mime_type,size_bytes,format_changed}`; size strict 0..25MiB, no raw filename or content. `findings` use existing safe engine fields `{id,rule_id,category,confidence,recognizer,location,action}` without matched values, input paths or filenames. `action` is `redacted|allowed_disabled|blocked`; blocked supports safe partial findings while clearly declaring inspection incomplete. `location` follows engine page/slide/bbox/spans/source-ref contract; strip unsafe original names from source_ref. Never report a match as redacted if sanitization failed.
- First valid `POST /events` returns 201 `{receipt_id,submission_id,manager_id,report_status:"recorded",delivery_state:"not_sent"}`. Resolve/verify manager and policy version server-side in the admission transaction; assignment changed =>409 ASSIGNMENT_CHANGED so gateway re-evaluates before sending. Exact repeat of canonical validated payload returns 200 same receipt; same submission_id with different payload returns409 IDEMPOTENCY_CONFLICT. Unique key `(organization_id,submission_id)`; canonical hash covers content, not transport TLS identity/receipt timestamp. If commit fails return503 and block. Do not trust a client-supplied receipt as permission to skip inspection.
- `PATCH /events/{submission_id}/delivery`: JSON `{state:"sent|accepted|rejected|unknown",upstream_status:<integer 100..599 or null>,completed_at:<UTC or null>}` returns200 `{receipt_id,delivery_state,upstream_status,completed_at}`. Authorize original company's gateway, validate state transitions and idempotent repeats; no backwards transition from terminal accepted/rejected. Require upstream_status for accepted/rejected; classify actual success codes per adapter. Tracking failure after send does not resend the request; recover persisted pending status as unknown.
- Persist admission rows, per-finding rows and delivery state with existing transaction/DB conventions. Store immediate manager/assignment version at event time for audit; current authorization still rechecks current assignment. Unassigned employees are blocked and create company-scoped operational records, not reports visible to an arbitrary manager. No email/Slack delivery required; visible manager-account reports satisfy reporting.

## Manager account integration

Reuse `/manager/reports` and existing report APIs/models if implemented; otherwise deliver their network subset with the same planned contracts. Read the current issue 4 contracts before editing shared filenames and merge rather than overwrite its work. Keep black/white/grayscale UI with no icons.

- Add filters `source=app|network`, destination host, decision and delivery_state, alongside employee/date/category/rule filters. Paginated list `{items:[...],next_cursor:null}` with stable descending `(occurred_at,id)`, limit1..100(default25), opaque cursor<=512 bound to company/manager/filters.
- Network summary: `{id,submission_id,source:"network",employee:{id,display_name},occurred_at,destination_host,decision,delivery_state,policy_version,finding_count,categories:[...],inspection_complete:<boolean>}`. No raw PII/content/website credentials/query strings/file names.
- Detail adds safe findings/locations/file metadata/reason code and upstream_status. `inspection_complete=false` for partial/unavailable inspections; blocked uploads remain visible and cannot appear as successful redaction.
- Immediate manager sees only currently assigned active employees in their company. Reassignment removes old manager access immediately and lets new manager see those employees' records according to existing report policy. Stored event-time manager does not override current permissions. Company/manager filters come from session, direct ID access is checked too. Cross-company/unauthorized IDs return404.
- No matches = admission audit with finding_count0, excluded from default PII-only list but available by explicit filter. Disabled-rule matches are visible as allowed_disabled. Manager UI may poll/refresh; no enterprise notification infrastructure needed.

## Acceptance and demonstration (included here)

- Instrumented LLM JSON receiver and non-LLM multipart/raw receiver observe only rewritten output, never original enabled-rule values. Uploads from browser outside our chat app create events for the correct manager.
- PDF/PPTX/DOCX include native text plus embedded scans/faces; standalone scans/images are covered once real detectors exist. Tests prove output cannot reveal originals through extractable text, image regions, metadata/comments/notes or removable overlays. Current image pause must be documented rather than bypassed.
- Two companies, two employees under different immediate managers, reassignment and inactive users/devices cannot leak report visibility; forged headers/company/manager IDs fail.
- Toggle all on/off, single built-in off, custom exact/regex rules and policy changes: outbound behavior and safe report actions match the snapshot. Disabled matches still reported. Regex timeout blocks rather than passing raw content.
- Unknown MIME, encrypted input, incomplete OCR/face processing, malformed JSON/multipart, overlimits, unsupported resumable/encrypted/signed/streaming payloads, disk full and audit/database failure result in zero outbound user-body bytes. Verify using instrumented receiver, not only mocks.
- Replay event IDs: exact replay no duplicate reports, conflicting replay409. Upstream timeout after send yields unknown; downstream4xx/5xx yields rejection metadata without claiming successful delivery or auto-retrying.
- Verify duplicate form keys, Unicode, compression, filenames and reconstructed headers/boundaries. Existing login/password traffic continues working without storing credentials in reports.
- Demo script creates synthetic uploads and employee/manager accounts using existing setup helpers, shows manager report and receiver output, and labels simulations. No separate test/demo issue; no requirement to break real third-party websites/accounts to prove coverage.

## Exact file ownership

Create/update directory indexes for every touched/new directory; new files remain planned until implemented.

| File | Responsibility |
|---|---|
| `packages/gateway/src/pii_gateway/uploads.py` | Required request hook and atomic inspection lifecycle. |
| `packages/gateway/src/pii_gateway/parsers.py` | Strict bounded multipart/JSON/form/raw decoding. |
| `packages/gateway/src/pii_gateway/rewrite.py` | Safe request reconstruction and transport validation. |
| `packages/gateway/src/pii_gateway/spool.py` | Restricted temporary storage, limits, cleanup and crash janitor. |
| `packages/gateway/src/pii_gateway/engine.py` | Actual shared-engine adapter; missing processing blocks. |
| `packages/gateway/src/pii_gateway/adapters/__init__.py` | Adapter registry and explicit coverage declarations. |
| `packages/gateway/src/pii_gateway/adapters/generic.py` | Supported transport/content-field classification. |
| `packages/gateway/src/pii_gateway/adapters/llm.py` | Verified LLM request adapter(s), not blanket host exemptions. |
| `packages/gateway/tests/test_uploads.py` | Atomic transport interception/rewriting, limits and failure tests. |
| `packages/gateway/tests/test_reporting.py` | Receipt admission/replay and upstream delivery status tests. |
| `packages/gateway/tests/fixtures/receiver.py` | Synthetic HTTPS LLM/non-LLM destinations recording received bytes. |
| `packages/gateway/tests/fixtures/requests.json` | Synthetic supported/unsupported payload manifest and expected outcomes. |
| `apps/api/app/routes/network_events.py` | mTLS policy/admission/delivery service routes. |
| `apps/api/app/schemas/network_events.py` | Strict policy/event/receipt/delivery DTOs. |
| `apps/api/app/services/network_events.py` | Assignment-bound policy and transactional event admission. |
| `apps/api/app/db/models/network_submission.py` | Source/destination/assignment/admission/delivery without original body. |
| `apps/api/migrations/versions/<next_unique_revision>_network_submissions.py` | Add network submission/event metadata after actual current head. |
| `apps/api/app/services/reporting.py` | Reuse manager report query/authorization and add network source. |
| `apps/api/app/routes/reports.py` | Extend shared reports contract with network filters/detail. |
| `apps/api/app/schemas/reports.py` | Safe source-discriminated app/network report DTOs. |
| `apps/api/tests/test_network_events.py` | mTLS scoping, replay/conflicts, assignment race and delivery states. |
| `apps/web/src/features/reports/NetworkReportDetails.tsx` | Safe network event detail in existing manager screen. |
| `apps/web/src/features/reports/schemas.ts` | Zod network report union/filters; integrate existing schema naming if present. |
| `docs/network-upload-contract.md` | Request/admission/delivery/report contracts and failure semantics. |
| `docs/website-coverage.md` | Verified protocols/sites/formats and explicit blocked/unverified coverage. |

## Official technical references

See [mitmproxy request modification](https://docs.mitmproxy.org/stable/mitmproxytutorial-modifyrequests/), [addon examples](https://docs.mitmproxy.org/stable/addons/examples/) and [addon error behavior](https://docs.mitmproxy.org/stable/addons/overview/). Implement explicit error blocking; do not assume a thrown addon exception blocks a request. HTTPS trust/protocol limits are documented in the network-enforcement issue and must remain visible in demos/presentations.
