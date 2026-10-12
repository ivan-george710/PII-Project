# Phase 10B.1 — Review interaction and visible redacted download

## A. Root Cause of Review Button Bug

Reproduced in real headless Chromium against the existing React build and the local backend, before editing the frontend. After uploading the supplied Cadence PPTX, clicking the REVIEW funnel action opened the Review Workspace with the REVIEW filter active, but **zero selected rows and no bounded context**. The top-level document header also had **no download link**. Evidence is retained privately under `.private_review_app/phase10b-ui/` (`reproduction.json`, `review-bug-before.png`).

The click handler did navigate: `App.tsx::filter` changed navigation and filters. The usability gap was in `ReviewWorkspace`: it initialized `detail=null` and only fetched detail after another click on a finding ID. Actions then required a third click on “Review finding” to open the dialog. Sidebar navigation only changed the screen and could retain unrelated filters. There was no prominent post-processing Review Findings action. Downloads existed only in Artifact Verification.

The prior browser test manually selected a finding before opening its dialog, so it did not detect the missing automatic selection.

## B. Review Navigation Fix

The document header now exposes **Review Findings**. It enters the existing Review Workspace, activates REVIEW, and automatically loads/selects the first matching finding. The existing bounded detail and comparison endpoints supply the source context; stale requests cannot overwrite a newer selection.

Sidebar Review Queue, primary Review Findings, REVIEW funnel/count, review queue count badge, Open review workspace, and review-required privacy-map tiles all use the same workspace. Map tiles retain their location; tiles without REVIEW findings retain their existing all-decisions location view. Entity and search filters continue to work.

After successful feedback, the workspace resets to the document-wide REVIEW filter and selects the next finding, including one at a different location. This avoids leaving a user in an empty location filter while other REVIEW findings remain. Source loading and errors remain visible.

No findings produces **“No findings currently require human review.”** An unselected detail panel explicitly says **“Select a finding to review.”** No competing review screen or client-side detector was introduced.

## C. Review Action UX

The selected finding panel retains entity, recognizer, confidence, location, automated/effective decisions, original bounded context and current redacted comparison. **Confirm as PII** and **Mark False Positive** are visible beside that context.

Each opens the existing reviewer dialog with its selected action, finding ID, automated/effective decision, reviewer identifier and optional reason. Submission labels are **Confirm & Regenerate** and **Mark False Positive & Regenerate**.

Feedback uses the existing revision-aware `/feedback` API. A local submission guard and disabled controls prevent duplicate submission; a pending request shows regeneration status. The frontend waits for the backend, then reloads findings, summary/counts, artifact state and audit history. It does not invoke Presidio or independently classify findings.

The success notice identifies the finding/action and reports the actual returned artifact and verification states plus the previous/new audit revisions. Supported-mapping verification is explicitly distinguished from coverage. Failed regeneration produces a needs-attention notice and an unavailable download instead of an invented success.

## D. Artifact Download Improvement

**Download Redacted Review Copy** is now prominent in the document header, including on the Review screen. It remains available in Artifact Verification, whose technical details, residual/unsupported counters and PDF preview are retained.

The shared `ArtifactDownload` component uses the existing opaque endpoint:

```text
GET /api/documents/{session-id}/artifact?inline=false&revision={current-revision}
```

No internal path is exposed. Revision binding updates after feedback. During regeneration the anchor becomes a disabled **Regenerating redacted copy...** button. Unavailable/failed generation shows disabled **Redacted copy unavailable** and a visible status/reason. With no loaded document there is no active download.

The warning appears immediately alongside each download control:

> Private review artifact — complete PII coverage has not been verified.

The app does not call an output safe, clean, fully sanitized or approved for LLM submission.

## E. Post-Review Flow

When no effective REVIEW findings remain, the workspace displays its explicit empty state. **Known review queue complete** and **Download Latest Redacted Review Copy** appear only when the actual backend `human_review_complete` state is also true. If other known audit issues remain, the UI directs the user to the audit queue and artifact verification instead.

The completion CTA retains **Coverage verification remains NOT ESTABLISHED.** Artifact failure still disables its download. Clearing the known queue never grants coverage or downstream clearance.

## F. Tests

| Check | Final result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests -q` | **284 passed**, 1 existing Starlette HTTPX TestClient deprecation warning; **77.42s** |
| `npm.cmd test` in `frontend/` | **30 passed**; 9.13s total |
| `npm.cmd run lint` in `frontend/` | Passed, zero warnings |
| `npm.cmd run build` in `frontend/` | TypeScript + Vite passed; 468.58 kB JS / 149.27 kB gzip; 43.83 kB CSS |
| `node --test tests/frontend/core.test.mjs` | **4 passed**, zero failures |
| Protected engine/pipeline source fingerprints | **45 unchanged** |

The 19 existing React tests were adapted to the direct action labels, and 11 regression cases were added. They cover primary navigation, active REVIEW, first context/action visibility, dialog metadata, sidebar/count/map shortcuts, refreshed counts, next-location selection, revised artifact URL, pending regeneration/duplicate prevention, queue-empty/completion states, PDF/DOCX/PPTX header downloads, absent/unavailable downloads, nearby warning and truthful regeneration failure.

Initial test-only failures were corrected: a notice selector also matched the new selected-finding heading; unavailable controls intentionally appeared in more than one place; and an unsupported Testing Library `exact` role option failed TypeScript. Selectors were scoped to the relevant header/dialog/notice without removing the assertions. An unused icon import was removed. Final tests, lint and build all pass.

The build updates the existing backend static bundle. Engines 1–5, detector policy, pipeline/redaction semantics, Phase 10A measurements and clearance flags were not changed. No backend storage or authentication was added.

## G. Real Browser Acceptance

`tests/frontend/phase10b1_browser.mjs` uses installed Chrome, the actual production bundle and a real local FastAPI backend at `http://127.0.0.1:8766`. It uses neither mocked HTTP nor injected engines. The requested upload → primary Review Findings → automatically selected context → reviewer dialog → backend feedback → refreshed counts/revision → next REVIEW → header download sequence was exercised in Chromium. Downloaded files were reopened with python-pptx, PyMuPDF and python-docx, respectively.

| Input | Counts after first confirmation: raw / confirmed / REVIEW / rejected | Revisions tested | Download size | Reopened |
| --- | --- | --- | ---: | --- |
| Supplied Cadence organizational PPTX | 59 / **26** / **14** / 19; previously 59 / 25 / 15 / 19 | 0 → 1 | 68,314 bytes | Yes, PPTX |
| Fictional PDF fixture | 6 / **4** / **1** / 1; previously 6 / 3 / 2 / 1 | 0 → 1 → 2 | 1,222 bytes | Yes, PDF |
| Fictional DOCX fixture | 7 / **4** / **1** / 2; previously 7 / 3 / 2 / 2 | 0 → 1 → 2 | 36,708 bytes | Yes, DOCX |

Both fictional runs additionally marked the remaining driver-license interpretation false positive and exercised the real backend's complete-queue state, latest-download CTA and unverified-coverage notice. The real PPTX confirmation was a demonstration on a newly uploaded copy, **not labeled ground truth** or a modification of a previously saved reviewer decision. Original supplied documents were not edited.

All focused runs verified every review shortcut, visible dialog/actions, disabled regeneration controls, refreshed revision-bound header link, counts, next selection and no horizontal overflow at 390px. **Zero runtime exceptions, zero security/CSP errors and zero failed API responses** were observed. Desktop selected-context and mobile screenshots were visually inspected. Screenshots, browser profiles, downloads and aggregate evidence remain in the existing private working area; no sensitive page inventories were printed.

The existing broader `tests/frontend/phase10b_browser.mjs` was updated for the direct action labels and also passed on the fictional DOCX with CONFIRM_PII, MISSED_PII and FALSE_POSITIVE, revision-3 save/reload, PDF/Office download contracts, detector disclaimer and responsive checks. It reported zero runtime/security errors.

Commands (project root unless indicated):

```powershell
# Before frontend changes, against the old production bundle:
$env:CADENCE_UI_REPRO='1'
node tests/frontend/phase10b1_browser.mjs
# The reproduction mode asserts the historical missing selection/download.
# Clear this variable for acceptance against the fixed bundle.
Remove-Item Env:CADENCE_UI_REPRO -ErrorAction SilentlyContinue

.venv/Scripts/python.exe -m pytest tests -q
node --test tests/frontend/core.test.mjs

# In frontend/:
npm.cmd test
npm.cmd run lint
npm.cmd run build

# Against the existing isolated current-backend server on 8766:
node tests/frontend/phase10b1_browser.mjs
$env:CADENCE_UI_FIXTURE=(Join-Path (Get-Location) '.private_review_app/phase10b-fixtures/synthetic.pdf')
$env:CADENCE_UI_COMPLETE='1'
node tests/frontend/phase10b1_browser.mjs
$env:CADENCE_UI_FIXTURE=(Join-Path (Get-Location) '.private_review_app/phase10b-fixtures/synthetic.docx')
node tests/frontend/phase10b1_browser.mjs
$env:CADENCE_UI_SYNTHETIC='1'
node tests/frontend/phase10b_browser.mjs
```

These are actual browser-controlled acceptance steps with visual inspection, not a claim of an independent human usability study. PDF/DOCX acceptance used small fictional fixtures; the supplied large scanned policy PDF was not OCR-processed again for this frontend repair.

## H. Remaining Issues

Underlying detector/OCR/unsupported-content limitations remain. Artifact verification and known queue completion do not establish complete PII coverage; downstream remains blocked. Processing remains synchronous and may take time for large documents.

At narrow widths the existing responsive layout stacks context below the findings list; the header actions and warnings remain visible. Selecting/searching a filter automatically selects its first match, and successful decisions reset to document-wide REVIEW so the next pending item can be reached.

The already-running primary application at `http://127.0.0.1:8765` was checked for compatible config/review metadata endpoints and preserved with its existing sessions. **Refresh the browser to load the newly built frontend**; no restart was forced or unsaved user session discarded. No commit or push was performed.

**Completed:** review now opens evidence and actions immediately, feedback reports actual regenerated state, and the latest private redacted review copy is directly downloadable from the document header.
