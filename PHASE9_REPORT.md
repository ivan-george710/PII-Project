# Phase 9 local privacy review application

Implemented 12 October 2026. The browser workspace supports upload, processing, bounded source review, all three feedback actions, artifact regeneration/download, audit history and explicit save/reload. The real supplied PPTX interview workflow was exercised end to end. **Coverage remains unverified and downstream submission blocked.**

## A. Architecture

FastAPI serves a lightweight same-origin API and vanilla JavaScript/CSS workspace. Processing remains synchronous, with one reusable `DocumentPipeline` and a process-local lock around processing/review state. There are no workers, queues, WebSockets, frontend state packages, database or cloud connections.

| File | Purpose |
| --- | --- |
| `app/web/server.py` | Local request boundary, private uploads, in-memory sessions, typed review routes, safe downloads and existing audit persistence. |
| `app/web/models.py` | Typed request/response schemas with bounded inputs and revision guards. |
| `app/web/static/index.html`, `style.css` | Responsive dark enterprise workspace, findings, source navigator, artifact, audit and dialogs. |
| `app/web/static/app.mjs`, `core.mjs` | Same-origin UI workflows, safe text rendering and exact selection offsets. |
| `app/main.py`, `run.py` | Application entry point and loopback-only launcher with access logging disabled. |
| `tests/test_review_api.py` | 19 API cases covering the required upload/security/review/download behaviors. |
| `tests/frontend/core.test.mjs` | Four Node built-in tests, including Unicode selection and offset-only feedback payloads. |
| `tests/frontend/browser_smoke.mjs` | Optional installed-Chrome end-to-end smoke test; isolated private profile/evidence. |
| `requirements.txt`, `.gitignore`, `README.md`, `PHASE9_REPORT.md` | Framework pins, private working-area exclusion, run/demo documentation and this report. |

Dependencies added: FastAPI 0.143.0, Uvicorn 0.54.0, Starlette 1.7.0, python-multipart 0.0.32. Existing HTTPX/Pydantic remain in use. All processing calls use `process`, `apply_feedback`, `save_audit` and `load_audit`. Engines 1–5, detection policies/thresholds, the pipeline and artifact engines were not rewritten or modified in this phase. No Qwen, authentication system, LLM connection, commits or pushes.

## B. Application Screens / Workflow

One workspace includes a session-document sidebar, drag/drop upload card, document identity, detection metrics, separate coverage/clearance notice, measured stage details, paginated findings, bounded source navigator, artifact section and audit trail. Review and missed-PII dialogs keep decisions close to their source context.

The design uses near-black/charcoal surfaces, restrained mint accents, amber review indicators, compact tables and high-contrast typography. Desktop and 390-pixel mobile screenshots were inspected. Mobile checks detected no horizontal document overflow. Only a small processing indicator animates; reduced-motion preferences are respected.

During processing the UI displays **“Processing document…”**. It does not pretend to know which synchronous stage is currently running. After completion, actual stage timings and Pending/Completed/Failed states are shown. Verification check failures are surfaced as a failed verification stage even when a partial private artifact exists. Failed processing without an audit displays unknown metrics rather than inventing zero detections.

## C. API Endpoints

| Method / route | Boundary and purpose |
| --- | --- |
| `GET /api/config` | Upload size/formats and trusted-local indicator. |
| `POST /api/documents` | Multipart upload → validate → private copy → pipeline. Returns sanitized state with opaque session ID. |
| `GET /api/documents` | Sanitized state for all current sessions. |
| `GET /api/documents/{id}` | Sanitized current processing/counts/artifact/stage state. |
| `GET /api/documents/{id}/review` | Authorized document display name and page/slide/logical-segment convention. |
| `GET /api/documents/{id}/findings` | Authorized metadata list; decision/entity/location filters, metadata search and pagination. |
| `GET /api/documents/{id}/findings/{finding_id}` | Authorized bounded source context and finding metadata. |
| `GET /api/documents/{id}/source` | Authorized source window and offset highlights. |
| `POST /api/documents/{id}/feedback` | Existing-finding CONFIRM_PII/FALSE_POSITIVE through the pipeline. |
| `POST /api/documents/{id}/missed-pii` | Validated source offsets/entity type through Engine 5. |
| `GET /api/documents/{id}/artifact` | Current private artifact download; optional inline PDF preview. |
| `GET /api/documents/{id}/audit` | Authorized feedback events plus a sanitized aggregate summary. |
| `POST /api/documents/{id}/save` | Explicit Engine 5 snapshot save, with current/persisted revision guards. |
| `GET /api/saved-audits` | Opaque references to local saved audits; no source paths or stored hash filenames. |
| `POST /api/load-audit` | Resolve a known reference and call pipeline audit reload/regeneration. |

The whole app is a **trusted local review boundary**, not a public service. General document state responses exclude names, candidate strings, reasons and all internal paths. Finding context, source windows, original display names and feedback-event reasons appear only in the purpose-specific authorized review endpoints. They are not part of public sanitized summaries.

## D. Upload and Security Handling

- 30 MiB file limit, plus bounded multipart overhead. Requests are bounded before parsing, including streamed bodies; file bytes are also checked while copying.
- Extension checks and Engine 1 content classification must agree. Corrupt, empty, unsupported or mismatched uploads are rejected with fixed messages. Legacy browser Windows fake paths are normalized by the multipart parser; remaining path separators/control characters are rejected.
- Uploads and session identifiers use unrelated randomized UUIDs. User filenames are display labels, never server lookup paths.
- `.private_review_app/{uploads,artifacts,audits}` uses existing Engine 5 private-directory guards/permissions and local/root gitignore rules. ACL inspection confirmed current Windows user and SYSTEM FullControl, with inheritance disabled at the protected directory.
- Multipart spool thresholds exceed the bounded request size, keeping parser data in memory until explicitly written privately. No PII spool file is intentionally created in the public OS temp directory.
- Downloads resolve server-owned paths by opaque session ID, enforce the private artifact directory/format and reject symlink/junction traversal. There is no arbitrary-path file read endpoint and no static mount of private data.
- The launcher binds to `127.0.0.1:8765`, disables proxy-header trust and access logs, and limits request concurrency. Host/origin checks and a required custom mutation header prevent ordinary cross-origin browser changes. CORS is not enabled.
- Review responses use no-store, no-referrer, nosniff, frame and same-origin CSP headers. Source text, filenames and reasons are rendered as text nodes, never inserted as HTML. Vendor exceptions/tracebacks are caught at the application boundary; fixed sanitized messages are returned without console dumping.

This is not enterprise authorization. Other trusted processes on the same computer can call the local API. Do not expose it on a network or use this demo as a multi-user production service.

## E. Review Workflow

Finding rows show ID, entity, location, original automated/effective decisions, confidence, recognizer and redaction/review status. Filters support All, REVIEW, Confirmed, Rejected, entity and location. Search matches finding IDs/entity/recognizer metadata only, not raw candidate values.

Review details expose at most 120 characters before, 240 candidate characters and 120 after; oversized candidates are visibly marked truncated. The reviewer identifier is required and reason optional. Human-added findings display “Not scored,” avoiding interpretation of Engine 5's uncalibrated 0.0 sentinel as model confidence.

Feedback requests carry the current revision. Stale revisions return 409; the UI refreshes and requires reopening the finding. The backend derives the expected current decision and calls `DocumentPipeline.apply_feedback`, then adopts only the returned result. Counts, queue, current decisions, history and artifact/verification state refresh. Source extraction, OCR and Presidio do not repeat. Document-switch guards prevent late responses from attaching source/finding context to the wrong session.

If feedback updates an audit but source integrity prevents artifact generation, the failed pipeline state is surfaced, with a specific fixed source-changed/missing notice where applicable. Stale artifacts are not offered as the current download.

## F. Missed-PII Workflow

The reviewer opens the source navigator and chooses a page, slide or DOCX logical segment. The API sends only a bounded source window: default 1,600, maximum 2,000 characters. Highlight offsets refer to the original extraction.

The browser computes selected offsets from exact DOM text using **Unicode code-point counts**, not JavaScript UTF-16 length. This preserves Python slicing with emoji/non-BMP characters and formatted highlight nodes. Selections must remain inside the source preview and contain 1–1,000 characters. The dialog freezes the selected range while editing reviewer/entity/reason fields.

Only location, original start/end, entity and reviewer metadata are submitted. Arbitrary replacement text is forbidden by the typed request schema. Engine 5 validates/slices the original source and regenerates the artifact. Invalid/out-of-range selections fail with sanitized 422 errors. This workflow covers supported extracted text; image pixels and unextracted Office objects cannot be selected through this text navigator.

## G. Artifact Download

The artifact panel shows format, generated/reopened state, supported-content verification, applied replacements, mapping issues and verification failures, plus unsupported categories. The link uses a session endpoint and a fixed download name `private-review-copy.<format>`; internal paths and randomized artifact filenames are never sent as lookup parameters.

The notice states that redactions reflect currently confirmed findings, complete coverage is unverified, and unresolved/unsupported sensitive content may remain. Partial artifacts may be downloaded for internal review with failure status displayed. Missing/stale artifacts are disabled. Downloads are never labeled safe/approved/fully sanitized.

PDF review copies use a real browser PDF preview. A synthetic selectable PDF was uploaded through the UI; its inline viewer rendered the tagged artifact with no runtime/security errors. DOCX/PPTX use textual structure/source navigation and actual artifact downloads rather than fabricated Office visual rendering.

## H. Audit View

The audit panel displays revision, event count, unique corrected-finding count, review queue, saved revision and artifact/coverage state. Authorized event rows include action, finding ID, timestamp, reviewer, previous/new decision and optional reason. These event reasons/identifiers are excluded from the sanitized summary toggle.

Save/reload uses Engine 5's existing JSON snapshots. Upload and feedback do not automatically save audits. Sources/artifacts remain in the private working area so explicitly saved audits can regenerate after restart. In-memory sessions and opaque saved-reference mappings are not persisted; the saved-audit picker rebuilds references from the dedicated audit directory. No second database or elaborate recovery system was added.

## I. Tests

Exact final Python command:

```powershell
.venv/Scripts/python.exe -m pytest tests -q
```

**252 passed, 1 warning in 70.27s (0:01:10).** This includes all 233 existing tests and 19 API cases. Tests cover real small PDF/DOCX/PPTX extraction/artifacts, unsupported/corrupt/mismatched/oversized uploads, filename normalization, summary/path separation, session/result/findings retrieval, REVIEW filters/search/pagination, all three feedback actions, download, opaque IDs, traversal, missing findings, stale revisions, invalid selections, Unicode offsets, verification failure state, source immutability/changes, persistence/reload and no repeat detection/extraction.

The one warning is Starlette's TestClient deprecation notice for HTTPX, recommending HTTPX2. Existing installed HTTPX works and all tests passed; no warning was hidden and no additional client stack was introduced.

Frontend commands:

```powershell
node --check app/web/static/app.mjs
node --test tests/frontend/core.test.mjs
node tests/frontend/browser_smoke.mjs
node tests/frontend/browser_smoke.mjs --pdf
```

Module syntax passed. Node built-in suite: **4 tests passed, 0 failed**, final reported duration **83.8236 ms**. There is no bundler/build step or npm package installation. The browser check requires a running local app, installed Chrome and the supplied PPTX; the PDF mode used a small private ReportLab fixture generated locally.

Browser-control tools initially failed to initialize (`failed to write kernel assets`, OS error 3). The fallback used an installed Chrome binary with an isolated headless profile through Node's built-in CDP WebSocket, following [Chrome's supported headless testing mode](https://developer.chrome.com/docs/automation-and-testing/headless). It introduced no browser testing dependency or interaction with the user's existing Chrome profile.

Real browser demo results:

| Check | Measured result |
| --- | --- |
| Supplied PPTX uploaded/processed | 59 raw, 25 confirmed, 15 REVIEW, 19 rejected |
| One REVIEW finding confirmed | 26 confirmed, 14 REVIEW; revision 1 |
| Artifact regenerated | Supported-content verification passed |
| Download completed | 68,314 bytes; reopened with python-pptx; 9 slides |
| Audit saved | Revision 1 visible in the UI |
| Source text selection/dialog | Exact range enabled the missed-PII dialog; no arbitrary second real-document correction was submitted |
| Mobile viewport | 390 pixels; no horizontal page overflow |
| Browser runtime exceptions | 0 |
| PDF inline preview | Opened/rendered; 0 runtime/security errors |
| Original supplied PPTX | Byte SHA-256 unchanged from Phase 8 evidence |

The real confirmation used reviewer `phase9-demo` with a reason explicitly identifying a demonstration override, not a ground-truth/coverage assessment. Synthetic API tests exercised actual MISSED_PII and false-positive submissions. The original supplied document was not edited. Private profiles, screenshots, downloads and smoke summaries are under `.private_review_app/ui-check/`.

## J. Demo Instructions

1. From the project root, run `.venv/Scripts/python.exe run.py`; open **http://127.0.0.1:8765**.
2. Choose the supplied Cadence organizational PPTX for a short demo. Upload using the picker or drag/drop. PDF/DOCX use the same workflow; a scanned PDF can take longer because uploads do not silently substitute a cached extraction.
3. Wait for the honest processing indicator; expand measured stages afterward. Show raw/current decision counts and the separate amber coverage/clearance strip.
4. Select REVIEW, open a finding and inspect its bounded context. Record an actual reviewer ID/reason, then confirm or reject.
5. Show the revision increment, event row and regenerated artifact verification. Original automated decisions remain visible next to effective decisions.
6. Open source navigation and select an exact supported text range to demonstrate the missed-PII dialog. Submit only a genuine reviewer-identified omission; the synthetic test suite covers a controlled missed value.
7. Download the **private review artifact** and show the actual file. For PDF, demonstrate the inline browser viewer.
8. Open the sanitized audit summary, save explicitly, then explain the saved-audit picker/restart behavior.
9. End with **Supported-content artifact verification: PASSED**, **Coverage: NOT ESTABLISHED**, **Downstream submission: BLOCKED**. Successful artifact generation does not establish detection recall.

The full supplied-PPTX workflow was verified and is suitable for a 10–15 minute demonstration. The local server was restarted with the final backend and left running at the URL above.

## K. Known Limitations

This is trusted local/demo use without authentication, user isolation or production multi-worker coordination. A process-local lock serializes processing/corrections; long OCR operations hold a synchronous request and there is no cancellation/job progress infrastructure. Memory/body size is bounded per request, but session count and saved-file retention are not automatically cleaned up. Uploads/artifacts/audits are local plaintext under existing restricted permissions, not encrypted.

UI source previews cover extracted text, not image/unsupported objects, and selection cannot span separate source windows. Full Word/PowerPoint rendering is outside scope. Existing artifact/OCR/layout limitations and REVIEW/unsupported/residual findings remain. Stale revisions/source changes are rejected/surfaced; the app does not repair altered originals or approve coverage.

Use the default loopback launcher and retained originals for saved-audit reload. Legacy snapshots without required artifact mapping metadata may fail closed as documented in Phase 8. Browser smoke checks are optional and require a compatible installed Chrome executable; production UI functionality does not depend on Chrome-specific automation.

## L. Completion Status

**Phase 9 complete.** A reviewer can upload all three formats, inspect findings and bounded source context, confirm/reject/add missed PII, regenerate files, inspect/save audit history and download private review artifacts. All existing backend tests pass, frontend checks pass and the real interview workflow was exercised. Backend clearance flags remain false; detection/coverage safety is not inferred from artifact verification.
